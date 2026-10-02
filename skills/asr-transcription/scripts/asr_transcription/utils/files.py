"""检查本机文件路径与内容身份，并提供JSON原子写入。"""

import hashlib
import json
import os
from pathlib import Path


class FileError(ValueError):
    """表示可向用户展示的本机文件错误。"""


def resolve_input(root: Path, value: str | Path, allowed_suffixes) -> Path:
    """核对输入的会话归属、真实路径、文件类型和扩展名。"""
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise FileError("本机文件位置无效，请重新添加文件。")
    try:
        root = root.resolve(strict=True)
        path = Path(value)
        if (not path.is_absolute() or not path.is_relative_to(root)
                or path.resolve(strict=True) != path):
            raise FileError("文件不是当前会话的本机副本，请重新添加。")
        if not path.is_file():
            raise FileError("请选择普通文件，不能选择目录。")
        if path.suffix.lower() not in allowed_suffixes:
            raise FileError("文件扩展名不在允许的格式范围内。")
        return path
    except (OSError, RuntimeError) as exc:
        raise FileError("无法读取指定文件，请检查路径和访问权限。") from exc


def file_fingerprint(path: Path) -> dict:
    """读取完整内容建立SHA基线，并检查读取期间的常规修改。"""
    try:
        before = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                after.st_size, after.st_mtime_ns, after.st_ino):
            raise FileError("文件在校验期间发生变化，请重新校验。")
        return {"size_bytes": after.st_size, "mtime_ns": after.st_mtime_ns,
                "sha256": digest.hexdigest()}
    except OSError as exc:
        raise FileError("无法读取文件，请检查访问权限后重新校验。") from exc


def check_file_unchanged(path: Path, fingerprint: dict) -> None:
    """比较文件大小与修改时间，检查文件是否发生变化。"""
    current = path.stat()
    if (current.st_size, current.st_mtime_ns) != (
            fingerprint["size_bytes"], fingerprint["mtime_ns"]):
        raise FileError("文件在校验期间发生变化，请重新校验。")


def write_json_atomic(path: Path, payload: dict) -> None:
    """写入JSON临时文件，再原子替换目标记录。"""
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
