"""管理项目路径、子进程环境与运行依赖检查。"""

import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
from dataclasses import dataclass
from pathlib import Path


class SetupError(Exception):
    """表示可向用户解释的环境或探针错误。"""


@dataclass(frozen=True)
class Project:
    root: Path

    def path(self, relative: str) -> Path:
        """解析路径并核对其位于项目目录内。"""
        root = self.root.resolve()
        path = (root / relative).resolve()
        # Windows junction / 符号链接不能把安装、配置或临时文件引向项目外。
        if not path.is_relative_to(root):
            raise SetupError(f"项目路径指向工作区外：{relative}")
        return path

    @property
    def bl_directory(self) -> Path:
        """返回项目独立安装BL的位置。"""
        return self.path(".tools/bailian")

    @property
    def bl_entry(self) -> Path:
        """返回项目BL的Node入口路径。"""
        return self.path(".tools/bailian/node_modules/bailian-cli/dist/bailian.mjs")

    def prepare(self) -> None:
        """创建项目运行目录和空npm配置，隔离用户的npm设置。"""
        for relative in (".runtime/tmp", ".runtime/npm-cache", ".state/bailian"):
            self.path(relative).mkdir(parents=True, exist_ok=True)
        for name in ("npm-user.npmrc", "npm-global.npmrc"):
            path = self.path(f".runtime/{name}")
            # 自有空配置阻止 npm 读取用户已有的 registry/token 设置。
            if path.exists() and path.read_text(encoding="utf-8").strip():
                raise SetupError(f"隔离配置应为空，请检查：{path}")
            path.touch(exist_ok=True)


def child_environment(project: Project, *, probe_mode: bool = False) -> dict[str, str]:
    """构造子进程环境，合并白名单变量与项目设置。"""
    allowed = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "PROCESSOR_ARCHITECTURE"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    temp = str(project.path(".runtime/tmp"))
    env.update({
        "TEMP": temp,
        "TMP": temp,
        "TMPDIR": temp,
        "BAILIAN_CONFIG_DIR": str(project.path(".state/bailian-probe" if probe_mode else ".state/bailian")),
        "DO_NOT_TRACK": "1",
        "NO_COLOR": "1",
        "NPM_CONFIG_USERCONFIG": str(project.path(".runtime/npm-user.npmrc")),
        "NPM_CONFIG_GLOBALCONFIG": str(project.path(".runtime/npm-global.npmrc")),
        "NPM_CONFIG_CACHE": str(project.path(".runtime/npm-cache")),
        "NPM_CONFIG_PREFIX": str(project.bl_directory),
        "NPM_CONFIG_REGISTRY": "https://registry.npmjs.org/",
        "NPM_CONFIG_UPDATE_NOTIFIER": "false",
        "NPM_CONFIG_FETCH_RETRIES": "0",
        "NPM_CONFIG_AUDIT": "false",
        "NPM_CONFIG_FUND": "false",
        # 已审阅BL的postinstall只预下载推荐器Wiki，ASR不需要该技能资产。
        "NPM_CONFIG_IGNORE_SCRIPTS": "true",
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONNOUSERSITE": "1",
    })
    return env


def find_node() -> Path:
    """定位当前PATH中的Node，缺失时提示安装。"""
    found = shutil.which("node")
    if not found:
        raise SetupError("未找到Node.js；请安装包含npm的Node.js，再运行bootstrap。")
    return Path(found).resolve()


def check_python() -> None:
    """确认当前Python符合依赖锁的Windows x64 CPython 3.12要求。"""
    # requirements锁定的是此平台的二进制wheel，不把更高版本误报为支持。
    if (sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12)
            or sysconfig.get_platform() != "win-amd64"):
        raise SetupError("当前依赖锁需要Windows x64的CPython 3.12。")


def npm_entry(node: Path) -> Path:
    """定位与Node配套的npm入口脚本。"""
    path = node.parent / "node_modules/npm/bin/npm-cli.js"
    if not path.is_file():
        raise SetupError("未找到Node安装目录下的npm-cli.js；请使用包含npm的Windows Node发行版。")
    return path


def run_process(
    project: Project, argv: list[str], timeout: float | None = 60, *, probe_mode: bool = False,
) -> subprocess.CompletedProcess[str]:
    """执行项目隔离环境中的本机命令，并返回捕获输出。"""
    try:
        return subprocess.run(
            argv,
            cwd=project.root,
            env=child_environment(project, probe_mode=probe_mode),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired as exc:
        # 仅用于环境/合约探针；超时不重跑命令，不打印可能敏感的进程输出。
        raise SetupError("子进程等待超时，已停止，未自动重试。") from exc
    except OSError as exc:
        raise SetupError(f"无法启动子进程：{type(exc).__name__}") from exc


def check_node(project: Project) -> tuple[Path, str]:
    """运行Node版本检查，返回满足BL要求的入口与版本。"""
    node = find_node()
    result = run_process(project, [str(node), "--version"])
    version = result.stdout.strip()
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", version)
    if result.returncode or not match or tuple(map(int, match.groups())) < (18, 17, 0):
        raise SetupError("Node.js版本不满足BL要求：需要18.17.0或更高版本。")
    return node, version


def locked_python_versions(project: Project) -> dict[str, str]:
    """读取依赖锁中的精确版本，并核对版本与SHA256格式。"""
    try:
        lines = project.path("requirements.txt").read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SetupError("无法读取Python依赖锁文件requirements.txt。") from exc
    versions = {}
    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+)(?:\s+--hash=sha256:[0-9a-f]{64})+", line)
        if not match or match[1] in versions:
            raise SetupError(f"requirements.txt第{number}行不是唯一的锁定依赖，请检查。")
        versions[match[1]] = match[2]
    if not versions:
        raise SetupError("requirements.txt没有锁定依赖，停止检查/安装。")
    return versions


def installed_python_versions(project: Project, packages: dict[str, str]) -> dict[str, str] | None:
    """加载项目venv依赖并返回版本，加载失败时返回None。"""
    python = project.path(".venv/Scripts/python.exe")
    if not python.is_file():
        return None
    result = run_process(project, [str(python), "-c",
        "import av, dotenv, openpyxl, et_xmlfile, defusedxml, docx, lxml.etree, typing_extensions; "
        "import importlib.metadata as m, json, sys; "
        "print(json.dumps({name:m.version(name) for name in sys.argv[1:]}))", *packages])
    if result.returncode:
        return None
    try:
        versions = json.loads(result.stdout)
        if not isinstance(versions, dict) or set(versions) != set(packages):
            raise ValueError("invalid package report")
        if not all(isinstance(version, str) for version in versions.values()):
            raise ValueError("invalid package version")
    except ValueError as exc:
        raise SetupError("Python依赖检查返回异常，未自动安装或重试。") from exc
    return versions
