"""仅管理项目路径和子进程环境，不处理百炼凭据或网络协议。"""

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import BAILIAN_VERSION


class SetupError(Exception):
    """可向用户解释的环境或探针错误。"""


@dataclass(frozen=True)
class Project:
    root: Path

    def path(self, relative: str) -> Path:
        root = self.root.resolve()
        path = (root / relative).resolve()
        # Windows junction / 符号链接不能把安装、配置或临时文件引向项目外。
        if not path.is_relative_to(root):
            raise SetupError(f"项目路径指向工作区外：{relative}")
        return path

    @property
    def bl_directory(self) -> Path:
        return self.path(".tools/bailian")

    @property
    def bl_entry(self) -> Path:
        return self.path(".tools/bailian/node_modules/bailian-cli/dist/bailian.mjs")

    def prepare(self) -> None:
        for relative in (".runtime/tmp", ".runtime/npm-cache", ".state/bailian"):
            self.path(relative).mkdir(parents=True, exist_ok=True)
        for name in ("npm-user.npmrc", "npm-global.npmrc"):
            path = self.path(f".runtime/{name}")
            # 自有空配置阻止 npm 读取用户已有的 registry/token 设置。
            if path.exists() and path.read_text(encoding="utf-8").strip():
                raise SetupError(f"隔离配置应为空，请检查：{path}")
            path.touch(exist_ok=True)


def child_environment(project: Project, *, probe_mode: bool = False) -> dict[str, str]:
    """使用白名单构造环境，不继承API Key、NODE_OPTIONS或npm token。"""
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
    found = shutil.which("node")
    if not found:
        raise SetupError("未找到Node.js；本阶段先复用现有运行时，便携运行时安装尚未实现。")
    return Path(found).resolve()


def npm_entry(node: Path) -> Path:
    path = node.parent / "node_modules/npm/bin/npm-cli.js"
    if not path.is_file():
        raise SetupError("未找到Node安装目录下的npm-cli.js；请使用包含npm的Windows Node发行版。")
    return path


def run_process(
    project: Project, argv: list[str], timeout: float = 60, *, probe_mode: bool = False,
) -> subprocess.CompletedProcess[str]:
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
    node = find_node()
    result = run_process(project, [str(node), "--version"])
    version = result.stdout.strip()
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", version)
    if result.returncode or not match or tuple(map(int, match.groups())) < (18, 17, 0):
        raise SetupError("Node.js版本不满足BL要求：需要18.17.0或更高版本。")
    return node, version


def installed_bl_version(project: Project) -> str | None:
    path = project.path(".tools/bailian/node_modules/bailian-cli/package.json")
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))["version"]
    except (ValueError, KeyError) as exc:
        raise SetupError("项目内BL包信息损坏，请检查安装目录。") from exc


def bl_command(project: Project, arguments: list[str]) -> list[str]:
    if installed_bl_version(project) != BAILIAN_VERSION or not project.bl_entry.is_file():
        raise SetupError(f"需要项目内BL {BAILIAN_VERSION}，请先运行bootstrap。")
    # --quiet是已核实的禁止命令结束后自动全局升级的路径；不猜造环境开关。
    return [str(find_node()), str(project.bl_entry), *arguments, "--quiet"]


def verify_bl_installation(project: Project) -> None:
    # 包信息可能先于依赖写入；真正启动入口才能发现中断安装留下的缺依赖。
    result = run_process(project, bl_command(project, ["--version"]), probe_mode=True)
    if result.returncode or result.stdout.strip() != f"bl {BAILIAN_VERSION}":
        raise SetupError("BL入口无法按锁定版本启动，安装可能不完整；未自动重装。")


def doctor(project: Project) -> dict:
    report = {
        "stage": "S1",
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "project": str(project.root),
        "transcription_available": False,
        "issues": [],
    }
    if os.name != "nt":
        report["issues"].append("首版仅验收Windows。")
    if sys.version_info < (3, 12):
        report["issues"].append("需要Python 3.12或更高版本。")
    try:
        node, version = check_node(project)
        report["node"] = {"path": str(node), "version": version, "npm_entry": str(npm_entry(node))}
    except SetupError as exc:
        report["issues"].append(str(exc))
    version = installed_bl_version(project)
    report["bailian"] = {"version": version, "expected": BAILIAN_VERSION, "entry": str(project.bl_entry)}
    if version != BAILIAN_VERSION or not project.bl_entry.is_file():
        report["issues"].append("项目内BL尚未安装或版本不匹配。")
    else:
        try:
            verify_bl_installation(project)
        except SetupError as exc:
            report["issues"].append(str(exc))
    venv_python = project.path(".venv/Scripts/python.exe")
    report["venv_python"] = str(venv_python) if venv_python.is_file() else None
    if not venv_python.is_file():
        report["issues"].append("项目虚拟环境尚未创建或不完整。")
    else:
        # 检查真正使用的虚拟环境，不依赖启动脚本的全局Python是否装过这些库。
        result = run_process(project, [str(venv_python), "-c",
            "import av, dotenv, openpyxl, defusedxml, importlib.metadata as m, json; "
            "print(json.dumps({name:m.version(name) for name in "
            "['av','python-dotenv','openpyxl','et-xmlfile','defusedxml']}))"])
        if result.returncode:
            report["issues"].append("Python运行依赖缺失或无法加载，请运行bootstrap。")
        else:
            report["python_packages"] = json.loads(result.stdout)
    report["note"] = "仅检查本地环境；不读取凭据，不验证账号权限，不执行转写。"
    return report
