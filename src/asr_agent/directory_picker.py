"""使用本机目录弹窗取得保存位置，不读取目录内容或创建文件。"""

import sys
from pathlib import Path

from .environment import SetupError


def validate_directory(path: Path) -> Path:
    """返回现有目录的绝对路径；写入权限留给实际保存时检查。"""
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_dir():
            raise SetupError("所选位置不是文件夹，请重新选择。")
        return resolved
    except (OSError, RuntimeError) as exc:
        raise SetupError("所选文件夹不存在或无法访问，请重新选择。") from exc


def choose_directory(initial: Path) -> Path | None:
    """显示 Windows 文件夹选择窗口；取消选择时返回 None。"""
    if sys.platform != "win32":
        raise SetupError("文件夹选择窗口目前仅支持 Windows。")
    initial = validate_directory(initial)
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError as exc:
        raise SetupError("当前 Python 缺少 tkinter/Tcl/Tk 组件，无法打开文件夹选择窗口。") from exc

    window = None
    try:
        # Tk 实例仅在本次调用的线程中创建、使用和销毁，不跨 HTTP 请求复用。
        window = tkinter.Tk()
        window.withdraw()
        window.attributes("-topmost", True)
        window.update_idletasks()
        selected = filedialog.askdirectory(
            parent=window,
            initialdir=str(initial),
            title="选择保存位置",
            mustexist=True,
        )
        return validate_directory(Path(selected)) if selected else None
    except tkinter.TclError as exc:
        raise SetupError("无法打开文件夹选择窗口，请检查 Python 的 Tcl/Tk 组件及 Windows 桌面会话。") from exc
    finally:
        if window is not None:
            try:
                window.destroy()
            except tkinter.TclError:
                # 弹窗异常时父窗口可能已经销毁，保留原始错误而非清理错误。
                pass
