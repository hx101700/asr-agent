"""用本机 Python、Node 和 pip/npm 安装项目锁定依赖。"""

import json
import shutil
import venv

from .. import BAILIAN_VERSION
from ..tools.bailian import installed_bl_version, verify_bl_installation
from ..tools.environment import (
    Project,
    SetupError,
    check_node,
    check_python,
    installed_python_versions,
    locked_python_versions,
    npm_entry,
    run_process,
)


def bootstrap(project: Project) -> dict:
    """检查本机运行时，安装或复用项目锁定依赖。"""
    check_python()
    node, _ = check_node(project)

    source = project.path("tools/bailian")
    lock_path = source / "package-lock.json"
    if not lock_path.is_file():
        raise SetupError("缺少BL依赖锁文件，停止安装。")
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        locked_version = lock["packages"]["node_modules/bailian-cli"]["version"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SetupError("BL依赖锁文件损坏，停止安装。") from exc
    if locked_version != BAILIAN_VERSION:
        raise SetupError("BL锁文件版本与当前命令契约不一致。")
    expected = locked_python_versions(project)

    # 先检查已有BL，避免明知其冲突仍修改Python环境。
    installed = installed_bl_version(project)
    destination = project.bl_directory
    if installed is not None:
        if installed != BAILIAN_VERSION or not project.bl_entry.is_file():
            raise SetupError("已有BL安装不匹配或不完整，未覆盖，请先检查。")
        verify_bl_installation(project)
    elif destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise SetupError("BL目标目录非空，未覆盖或自动重试，请先检查上次安装状态。")
    if installed is None:
        npm = npm_entry(node)

    project.prepare()
    environment = project.path(".venv")
    if environment.exists() and not (environment / "pyvenv.cfg").is_file():
        raise SetupError(".venv已存在且不是可识别的虚拟环境，未覆盖。")
    if not environment.exists():
        venv.EnvBuilder(with_pip=False).create(environment)
    python = project.path(".venv/Scripts/python.exe")
    if not python.is_file():
        raise SetupError("已有虚拟环境不完整，未覆盖或自动重建。")
    checked = run_process(project, [str(python), "-c",
        "import sys, sysconfig; raise SystemExit(sys.version_info[:2] != (3, 12) "
        "or sys.implementation.name != 'cpython' or sysconfig.get_platform() != 'win-amd64')"])
    if checked.returncode:
        raise SetupError("项目虚拟环境无法启动或不是Windows x64的CPython 3.12，未覆盖。")
    if installed_python_versions(project, expected) != expected:
        if not (environment / "Lib/site-packages/pip").is_dir():
            result = run_process(project, [str(python), "-m", "ensurepip", "--default-pip"])
            if result.returncode:
                raise SetupError("无法在项目虚拟环境中准备pip，未自动重试。")
        result = run_process(project, [
            str(python), "-m", "pip", "install", "--require-hashes", "--only-binary=:all:",
            "--no-cache-dir", "--retries", "0", "--timeout", "120",
            "--index-url", "https://mirrors.aliyun.com/pypi/simple/",
            "-r", str(project.path("requirements.txt")),
        ], timeout=None)
        if result.returncode:
            log = project.path(".runtime/python-install.log")
            log.write_text(result.stdout + result.stderr, encoding="utf-8")
            raise SetupError(f"Python依赖安装失败，未重试；本地日志：{log}")
        if installed_python_versions(project, expected) != expected:
            raise SetupError("pip结束但Python依赖校验失败，未自动重试。")

    if installed is not None:
        return {"status": "already_installed", "version": installed, "directory": str(destination)}

    destination.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(source / name, destination / name)

    result = run_process(
        project,
        [str(node), str(npm), "ci", "--prefix", str(destination), "--ignore-scripts", "--no-audit",
         "--no-fund", "--fetch-retries=0"],
        timeout=None,
    )
    if result.returncode:
        # 第三方安装输出仅落在本地日志，不直接带入聊天。
        log = project.path(".runtime/bootstrap.log")
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        raise SetupError(f"npm安装失败，未自动重试；本地日志：{log}")
    verify_bl_installation(project)
    return {"status": "installed", "version": BAILIAN_VERSION, "directory": str(destination)}
