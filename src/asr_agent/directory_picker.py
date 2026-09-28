"""使用本机目录弹窗取得保存位置，不读取目录内容或创建文件。"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from threading import Event

from .environment import SetupError

DIALOG_TIMEOUT_SECONDS = 5 * 60
WAIT_SLICE_SECONDS = 0.2


def validate_directory(path: Path) -> Path:
    """返回现有目录的绝对路径；写入权限留给实际保存时检查。"""
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_dir():
            raise SetupError("所选位置不是文件夹，请重新选择。")
        return resolved
    except (OSError, RuntimeError) as exc:
        raise SetupError("所选文件夹不存在或无法访问，请重新选择。") from exc


def choose_directory(initial: Path, *, cancel_event: Event | None = None) -> Path | None:
    """隔离原生窗口，取消或超时时终止自己的子进程，不让请求无限等待。"""
    if sys.platform != "win32":
        raise SetupError("文件夹选择窗口目前仅支持 Windows。")
    initial = validate_directory(initial)
    cancelled = cancel_event or Event()
    if cancelled.is_set():
        return None
    # 不把API Key等环境变量传给纯本地GUI。CREATE_NO_WINDOW仅隐藏控制台，不隐藏目录窗口。
    # Windows Shell用SystemDrive/ProgramData展开系统缓存位置，不能随凭据一起删掉。
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {"SYSTEMROOT", "SYSTEMDRIVE", "PROGRAMDATA", "WINDIR", "PATH", "TEMP", "TMP"}}
    try:
        process = subprocess.Popen(
            [sys.executable, "-I", "-X", "utf8", str(Path(__file__).with_name("_directory_dialog.py")), str(initial)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", env=env, shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except OSError as exc:
        raise SetupError("无法启动文件夹窗口，请检查 Python 运行环境。") from exc
    deadline = time.monotonic() + DIALOG_TIMEOUT_SECONDS
    try:
        while True:
            if cancelled.is_set():
                return None
            if time.monotonic() >= deadline:
                raise SetupError("文件夹窗口等待超时。若窗口未显示，请从正常 Windows 桌面重新启动服务。")
            try:
                output, _ = process.communicate(timeout=WAIT_SLICE_SECONDS)
                break
            except subprocess.TimeoutExpired:
                continue  # 仅等待本机窗口；不重开窗口，不重发请求。
        if cancelled.is_set():
            return None
        if process.returncode:
            raise SetupError("文件夹窗口异常退出，请重新选择。")
        try:
            result = json.loads(output)
            if not isinstance(result, dict):
                raise ValueError
            if "error" in result:
                raise SetupError(str(result["error"]))
            selected = result["path"]
            if selected is not None and not isinstance(selected, str):
                raise ValueError
        except (ValueError, KeyError) as exc:
            raise SetupError("无法读取文件夹选择结果，请重新选择。") from exc
        return validate_directory(Path(selected)) if selected else None
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate()
