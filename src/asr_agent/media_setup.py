"""安装固定媒体工具；这里只下载发行包，不涉及任何ASR服务调用。"""

import hashlib
import json
import os
import platform
import stat
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .environment import Project, SetupError, media_paths, run_process


def validate_archive(archive: Path, size: int, sha256: str) -> None:
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if archive.stat().st_size != size or digest != sha256:
        raise SetupError("FFmpeg发行包大小或SHA-256不匹配，未解压或执行。")


def validate_zip_paths(archive: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.infolist():
        target = (root / member.filename).resolve()
        mode = member.external_attr >> 16
        if not target.is_relative_to(root) or stat.S_ISLNK(mode):
            raise SetupError("FFmpeg发行包包含越界路径或符号链接，停止解压。")


def bootstrap_media(project: Project) -> dict:
    # socket超时不覆盖慢速持续响应的总耗时；独立进程让安装拥有真正的截止时间。
    result = run_process(project, [sys.executable, str(project.path("scripts/media_worker.py"))], timeout=360)
    try:
        report = json.loads(result.stdout)
    except ValueError as exc:
        raise SetupError("媒体安装进程未返回有效报告，未自动重试。") from exc
    if result.returncode:
        raise SetupError(report.get("message", "媒体工具安装失败，未自动重试。"))
    return report


def install_media_in_worker(project: Project) -> dict:
    if os.name != "nt" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise SetupError("当前锁定的媒体工具仅支持Windows x64。")
    lock = json.loads(project.path("tools/media-lock.json").read_text(encoding="utf-8"))
    project.prepare()
    tools = media_paths(project)
    destination = project.path(".tools/ffmpeg")
    already_installed = all(path.is_file() for path in tools.values())
    if not already_installed:
        if destination.exists() and any(destination.iterdir()):
            raise SetupError("媒体工具目录非空且安装不完整，未覆盖或自动重试。")
        archive = project.path(f".runtime/{lock['archive']}")
        if not archive.exists():
            partial = project.path(f".runtime/{lock['archive']}.part")
            deadline = time.monotonic() + 300
            try:
                with partial.open("xb") as output, urllib.request.urlopen(lock["url"], timeout=30) as response:
                    while chunk := response.read1(64 * 1024):
                        output.write(chunk)
                        if output.tell() > lock["size"] or time.monotonic() > deadline:
                            raise SetupError("媒体工具下载超过预期大小或时限，已停止且未重试。")
            except FileExistsError as exc:
                raise SetupError(f"存在未完成下载，请先检查：{partial}；未覆盖或重复下载。") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                raise SetupError("媒体工具下载失败；保留项目内part文件，未自动重试。") from exc
            validate_archive(partial, lock["size"], lock["sha256"])
            partial.replace(archive)
        validate_archive(archive, lock["size"], lock["sha256"])
        try:
            with zipfile.ZipFile(archive) as package:
                validate_zip_paths(package, destination)
                destination.mkdir(parents=True, exist_ok=True)
                # 保留包内LICENSE/README；不把二进制加入Git或改系统PATH。
                package.extractall(destination)
        except zipfile.BadZipFile as exc:
            raise SetupError("媒体发行包不是可完整读取的ZIP，未执行其中程序。") from exc
    versions = {}
    for name, path in tools.items():
        result = run_process(project, [str(path), "-version"])
        first_line = result.stdout.splitlines()[0] if result.stdout else ""
        if result.returncode or not first_line.startswith(f"{name} version {lock['version']}"):
            raise SetupError(f"{name}实际版本与锁定版本不一致。")
        versions[name] = first_line
    return {"status": "already_installed" if already_installed else "installed",
            "directory": str(destination), "versions": versions}
