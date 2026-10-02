"""显示独立进程中的目录窗口，通过管道返回选择结果。"""

import json
import sys


def show_directory_dialog(initial: str, title: str) -> str | None:
    """显示原生目录窗口并返回选择，取消返回None且销毁窗口。"""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError as exc:
        raise RuntimeError("当前 Python 缺少 tkinter/Tcl/Tk 组件。") from exc
    window = None
    try:
        window = tkinter.Tk()
        window.withdraw()
        window.attributes("-topmost", True)
        window.update_idletasks()
        return filedialog.askdirectory(
            parent=window, initialdir=initial, title=title, mustexist=True,
        ) or None
    except tkinter.TclError as exc:
        raise RuntimeError("无法打开文件夹窗口，请从正常 Windows 桌面重新启动服务。") from exc
    finally:
        if window is not None:
            try:
                window.destroy()
            except tkinter.TclError:
                pass


if __name__ == "__main__":
    try:
        result = {"path": show_directory_dialog(sys.argv[1], sys.argv[2])}
    except RuntimeError as exc:
        result = {"error": str(exc)}
    # 仅写入父进程的私有管道，不进入应用日志。
    print(json.dumps(result, ensure_ascii=False), flush=True)
