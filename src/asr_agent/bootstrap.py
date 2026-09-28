"""用pip/npm安装锁定依赖；不自建工具下载器或修改BL源码。"""

import json
import os
import shutil
import sys
import venv

from . import BAILIAN_VERSION
from .environment import (
    Project,
    SetupError,
    check_node,
    installed_bl_version,
    npm_entry,
    run_process,
    verify_bl_installation,
)

EXPECTED_BAILIAN_INTEGRITY = (
    "sha512-G90UvW74qgMzZWSonLsbfCAca9+md6jnP99xFI8KkDR2xUPH7TlUmNKQENDTB2GeVAGcvCWSbUysjIAZtrn8Kw=="
)


def bootstrap(project: Project) -> dict:
    if os.name != "nt" or sys.version_info < (3, 12):
        raise SetupError("本阶段需要Windows和Python 3.12或更高版本。")
    node, _ = check_node(project)
    npm = npm_entry(node)
    source = project.path("tools/bailian")
    lock_path = source / "package-lock.json"
    if not lock_path.is_file():
        raise SetupError("缺少已验证的BL依赖锁文件，停止安装。")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    locked = lock["packages"]["node_modules/bailian-cli"]
    if locked["version"] != BAILIAN_VERSION or locked["integrity"] != EXPECTED_BAILIAN_INTEGRITY:
        raise SetupError("BL锁文件版本/完整性摘要与已核实的发布包不一致。")

    project.prepare()
    environment = project.path(".venv")
    if environment.exists() and not (environment / "pyvenv.cfg").is_file():
        raise SetupError(".venv已存在且不是可识别的虚拟环境，未覆盖。")
    if not environment.exists():
        # ensurepip也通过受控子进程执行，临时文件留在项目内。
        venv.EnvBuilder(with_pip=False).create(environment)
    python = project.path(".venv/Scripts/python.exe")
    if not python.is_file():
        raise SetupError("已有虚拟环境不完整，未覆盖或自动重建。")
    checked = run_process(project, [str(python), "-c", "import sys; raise SystemExit(sys.version_info < (3, 12))"])
    if checked.returncode:
        raise SetupError("项目虚拟环境无法启动或Python版本低于3.12，未覆盖。")
    if not (environment / "Lib/site-packages/pip").is_dir():
        result = run_process(project, [str(python), "-m", "ensurepip", "--default-pip"])
        if result.returncode:
            raise SetupError("无法在项目虚拟环境中准备pip，未自动重试。")
    result = run_process(project, [
        str(python), "-m", "pip", "install", "--require-hashes", "--only-binary=:all:",
        "--no-cache-dir", "--retries", "0", "--index-url", "https://pypi.org/simple",
        "-r", str(project.path("requirements.txt")),
    ], timeout=300)
    if result.returncode:
        project.path(".runtime/python-install.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        raise SetupError("Python依赖安装失败，未重试；详见.runtime/python-install.log。")

    installed = installed_bl_version(project)
    if installed is not None:
        if installed != BAILIAN_VERSION or not project.bl_entry.is_file():
            raise SetupError("已有BL安装不匹配或不完整，未覆盖，请先检查。")
        verify_bl_installation(project)
        return {"status": "already_installed", "version": installed, "directory": str(project.bl_directory)}

    destination = project.bl_directory
    if destination.exists() and any(destination.iterdir()):
        raise SetupError("BL目标目录非空，未覆盖或自动重试，请先检查上次安装状态。")
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(source / name, destination / name)

    result = run_process(
        project,
        [str(node), str(npm), "ci", "--prefix", str(destination), "--ignore-scripts", "--no-audit", "--no-fund"],
        timeout=600,
    )
    if result.returncode:
        # 安装输出仅存项目内；不把第三方日志不加筛选地送进聊天。
        log = project.path(".runtime/bootstrap.log")
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        raise SetupError(f"npm安装失败，未自动重试；本地日志：{log}")
    if installed_bl_version(project) != BAILIAN_VERSION or not project.bl_entry.is_file():
        raise SetupError("npm结束但BL入口校验失败，未自动重试。")
    verify_bl_installation(project)
    return {"status": "installed", "version": BAILIAN_VERSION, "directory": str(destination)}
