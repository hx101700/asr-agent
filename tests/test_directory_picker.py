import json
import os
import subprocess
import sys
from pathlib import Path
from threading import Event, Timer
from types import ModuleType
from unittest.mock import MagicMock, patch

from asr_runtime.utils._directory_dialog import show_directory_dialog
from asr_runtime.utils.directory_picker import choose_directory, validate_directory
from asr_runtime.utils.environment import SetupError
from asr_runtime.utils.i18n import language_scope
from tests.support import RuntimeTestCase


class DirectoryPickerTests(RuntimeTestCase):
    def setUp(self):
        """准备目录选择器的进程替身。"""
        super().setUp()
        self.process = MagicMock()
        self.process.returncode = 0
        self.process.poll.return_value = 0
        self.process.communicate.return_value = (json.dumps({"path": str(self.runtime.root)}), "")
        start_process = patch("asr_runtime.utils.directory_picker.subprocess.Popen", return_value=self.process)
        self.popen = start_process.start()
        self.addCleanup(start_process.stop)
        platform = patch("asr_runtime.utils.directory_picker.sys.platform", "win32")
        platform.start()
        self.addCleanup(platform.stop)

    def test_selected_directory_is_resolved(self):
        """验证所选目录返回规范的绝对路径。"""
        selected = self.runtime.root / "中文 目录"
        selected.mkdir()
        self.process.communicate.return_value = (json.dumps({"path": str(selected)}), "")
        self.assertEqual(choose_directory(self.runtime.root), selected.resolve())
        self.popen.assert_called_once()
        self.process.kill.assert_not_called()

    def test_page_language_sets_child_title_and_translates_child_error(self) -> None:
        """验证父进程传递英文窗口标题并翻译独立窗口的错误。"""
        self.process.communicate.return_value = (json.dumps({"error": "当前 Python 缺少 tkinter/Tcl/Tk 组件。"}), "")
        with language_scope("en"), self.assertRaisesRegex(SetupError, "missing tkinter/Tcl/Tk"):
            choose_directory(self.runtime.root)
        self.assertEqual(self.popen.call_args.args[0][-1], "Audio transcription · Choose an output folder")

    def test_native_cancel_returns_none(self):
        """验证原生窗口取消后返回空结果。"""
        self.process.communicate.return_value = ('{"path": null}', "")
        self.assertIsNone(choose_directory(self.runtime.root))
        self.process.kill.assert_not_called()

    def test_already_cancelled_does_not_start_process(self):
        """验证提前取消目录选择时直接返回空结果。"""
        cancelled = Event()
        cancelled.set()
        self.assertIsNone(choose_directory(self.runtime.root, cancel_event=cancelled))
        self.popen.assert_not_called()

    def test_cancel_during_wait_kills_and_reaps_process(self):
        """验证等待时取消会终止并回收窗口进程。"""
        cancelled = Event()

        def communicate(*, timeout=None):
            """模拟等待中发生取消并返回超时。"""
            if timeout is not None:
                cancelled.set()
                raise subprocess.TimeoutExpired("synthetic-picker", timeout)
            return "", ""

        self.process.communicate.side_effect = communicate
        self.process.poll.return_value = None
        self.assertIsNone(choose_directory(self.runtime.root, cancel_event=cancelled))
        self.popen.assert_called_once()
        self.process.kill.assert_called_once()
        self.assertEqual(self.process.communicate.call_args.kwargs, {})

    def test_cancellation_during_response_discards_selected_path(self):
        """验证响应返回时已取消则丢弃选定路径。"""
        cancelled = Event()

        def communicate(*, timeout=None):
            """模拟响应已返回时发生取消。"""
            cancelled.set()
            return json.dumps({"path": str(self.runtime.root)}), ""

        self.process.communicate.side_effect = communicate
        self.assertIsNone(choose_directory(self.runtime.root, cancel_event=cancelled))

    def test_waiting_longer_than_five_minutes_still_allows_selection_or_cancel(self):
        """验证等待超过五分钟仍能选择或取消。"""
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                self.process.reset_mock()
                self.popen.reset_mock()
                cancelled = Event()
                waits = []

                def communicate(*, timeout=None):
                    """模拟长时间窗口等待及最终选择或取消。"""
                    if timeout is not None:
                        waits.append(timeout)
                        if len(waits) <= 1501:
                            raise subprocess.TimeoutExpired("synthetic-picker", timeout)
                        if cancel:
                            cancelled.set()
                    return json.dumps({"path": str(self.runtime.root)}), ""

                # 模拟超过五分钟的等待片段，不实际停留五分钟，也不重开窗口。
                self.process.communicate.side_effect = communicate
                self.process.poll.return_value = None if cancel else 0
                selected = choose_directory(self.runtime.root, cancel_event=cancelled)
                self.assertGreater(sum(waits), 300)
                self.assertEqual(selected, None if cancel else self.runtime.root.resolve())
                self.popen.assert_called_once()
                self.assertEqual(self.process.kill.call_count, int(cancel))

    def test_process_failure_does_not_expose_stderr(self):
        """验证窗口进程失败返回固定错误说明。"""
        self.process.returncode = 1
        self.process.poll.return_value = 1
        self.process.communicate.return_value = ("", "synthetic private diagnostic")
        with self.assertRaisesRegex(SetupError, "异常退出") as caught:
            choose_directory(self.runtime.root)
        self.assertNotIn("synthetic private", str(caught.exception))
        self.popen.assert_called_once()

    def test_invalid_protocol_is_reported(self):
        """验证非法窗口返回协议有明确错误。"""
        for output in ("not-json", "[]", "{}", '{"path": 42}', '{"path": []}'):
            with self.subTest(output=output):
                self.process.communicate.return_value = (output, "")
                with self.assertRaisesRegex(SetupError, "无法读取文件夹选择结果"):
                    choose_directory(self.runtime.root)

    def test_helper_error_is_reported(self):
        """验证窗口辅助程序报告的错误被保留。"""
        self.process.communicate.return_value = (json.dumps({"error": "测试窗口不可用"}), "")
        with self.assertRaisesRegex(SetupError, "测试窗口不可用"):
            choose_directory(self.runtime.root)

    def test_launch_failure_is_reported_without_retry(self):
        """验证窗口启动失败返回对应说明且启动次数为一。"""
        self.popen.side_effect = OSError("synthetic launch failure")
        with self.assertRaisesRegex(SetupError, "无法启动文件夹窗口"):
            choose_directory(self.runtime.root)
        self.popen.assert_called_once()

    def test_gui_process_does_not_inherit_keys_or_python_injection(self):
        """验证窗口进程使用系统环境白名单。"""
        environment = {
            "SystemRoot": "C:\\Windows", "PATH": "synthetic-path", "TEMP": str(self.runtime.root),
            "SystemDrive": "C:", "ProgramData": "C:\\ProgramData",
            "DASHSCOPE_API_KEY": "synthetic-api-key", "BAILIAN_API_KEY": "synthetic-bl-key",
            "PYTHONPATH": "synthetic-python-path", "PYTHONSTARTUP": "synthetic-startup",
        }
        with patch.dict(os.environ, environment, clear=True):
            choose_directory(self.runtime.root)
        args, kwargs = self.popen.call_args
        self.assertEqual(args[0][:4], [sys.executable, "-I", "-X", "utf8"])
        self.assertEqual(Path(args[0][4]).name, "_directory_dialog.py")
        self.assertEqual(args[0][5], str(self.runtime.root.resolve()))
        self.assertEqual({key.upper(): value for key, value in kwargs["env"].items()}, {
            "SYSTEMROOT": "C:\\Windows", "PATH": "synthetic-path", "TEMP": str(self.runtime.root),
            "SYSTEMDRIVE": "C:", "PROGRAMDATA": "C:\\ProgramData",
        })
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)

    def test_missing_selection_is_not_created(self):
        """验证缺失保存目录返回选择错误。"""
        missing = self.runtime.root / "not-created"
        self.process.communicate.return_value = (json.dumps({"path": str(missing)}), "")
        with self.assertRaisesRegex(SetupError, "不存在或无法访问"):
            choose_directory(self.runtime.root)
        self.assertFalse(missing.exists())

    def test_file_is_not_accepted_as_directory(self):
        """验证选择普通文件时返回目录类型错误。"""
        file = self.runtime.root / "file.txt"
        file.write_text("synthetic", encoding="utf-8")
        with self.assertRaisesRegex(SetupError, "不是文件夹"):
            validate_directory(file)

    def test_invalid_initial_directory_does_not_start_process(self):
        """验证初始目录无效时返回目录检查错误。"""
        with self.assertRaisesRegex(SetupError, "不存在或无法访问"):
            choose_directory(self.runtime.root / "missing")
        self.popen.assert_not_called()

    def test_unsupported_platform_does_not_start_process(self):
        """验证其他平台返回Windows支持范围说明。"""
        with patch("asr_runtime.utils.directory_picker.sys.platform", "linux"):
            with self.assertRaisesRegex(SetupError, "仅支持 Windows"):
                choose_directory(self.runtime.root)
        self.popen.assert_not_called()


class DirectoryPickerProcessTests(RuntimeTestCase):
    def test_cancel_terminates_real_unresponsive_child_without_gui(self):
        """验证取消能终止真实等待子进程。"""
        if sys.platform != "win32":
            self.skipTest("目录窗口运行边界仅支持 Windows")
        real_popen = subprocess.Popen
        cancelled = Event()
        children = []
        timer = None

        def start_sleeping_child(command, **kwargs):
            """启动本机等待进程并定时触发取消。"""
            nonlocal timer
            # 真子进程只等待、不创建窗口，验证取消后确实回收进程。
            child = real_popen([sys.executable, "-I", "-c", "import time; time.sleep(30)"], **kwargs)
            children.append(child)
            timer = Timer(0.05, cancelled.set)
            timer.start()
            return child

        try:
            with patch("asr_runtime.utils.directory_picker.subprocess.Popen", side_effect=start_sleeping_child):
                self.assertIsNone(choose_directory(self.runtime.root, cancel_event=cancelled))
            self.assertEqual(len(children), 1)
            self.assertIsNotNone(children[0].poll())
            self.assertNotEqual(children[0].returncode, 0)
        finally:
            if timer is not None:
                timer.cancel()
                timer.join()
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.communicate()


class FakeTclError(Exception):
    pass


class NativeDirectoryDialogTests(RuntimeTestCase):
    def setUp(self):
        """准备原生目录窗口的Tk组件替身。"""
        super().setUp()
        self.tk = ModuleType("tkinter")
        self.tk.Tk = MagicMock()
        self.tk.TclError = FakeTclError
        self.tk.filedialog = ModuleType("tkinter.filedialog")
        self.tk.filedialog.askdirectory = MagicMock(return_value=str(self.runtime.root))
        modules = patch.dict(sys.modules, {"tkinter": self.tk, "tkinter.filedialog": self.tk.filedialog})
        modules.start()
        self.addCleanup(modules.stop)

    def test_selected_directory_cleans_up_hidden_parent(self):
        """验证成功选择后销毁隐藏父窗口。"""
        self.assertEqual(show_directory_dialog(str(self.runtime.root), "录音转写 · 选择保存位置"), str(self.runtime.root))
        window = self.tk.Tk.return_value
        window.withdraw.assert_called_once()
        window.attributes.assert_called_once_with("-topmost", True)
        window.destroy.assert_called_once()
        self.tk.filedialog.askdirectory.assert_called_once_with(
            parent=window, initialdir=str(self.runtime.root), title="录音转写 · 选择保存位置", mustexist=True,
        )

    def test_cancel_cleans_up_hidden_parent(self):
        """验证取消后销毁隐藏父窗口。"""
        self.tk.filedialog.askdirectory.return_value = ""
        self.assertIsNone(show_directory_dialog(str(self.runtime.root), "录音转写 · 选择保存位置"))
        self.tk.Tk.return_value.destroy.assert_called_once()

    def test_missing_tkinter_reports_component_error(self):
        """验证缺少Tkinter时说明组件错误。"""
        with patch.dict(sys.modules, {"tkinter": None}):
            with self.assertRaisesRegex(RuntimeError, "缺少 tkinter/Tcl/Tk"):
                show_directory_dialog(str(self.runtime.root), "录音转写 · 选择保存位置")
        self.tk.Tk.assert_not_called()

    def test_failed_tk_creation_does_not_open_or_retry_dialog(self):
        """验证Tk创建失败时直接返回组件错误。"""
        self.tk.Tk.side_effect = FakeTclError("synthetic initialization failure")
        with self.assertRaisesRegex(RuntimeError, "无法打开文件夹窗口"):
            show_directory_dialog(str(self.runtime.root), "录音转写 · 选择保存位置")
        self.tk.Tk.assert_called_once()
        self.tk.filedialog.askdirectory.assert_not_called()

    def test_dialog_error_survives_cleanup_error(self):
        """验证清理失败时保留原始弹窗错误。"""
        self.tk.filedialog.askdirectory.side_effect = FakeTclError("synthetic dialog failure")
        self.tk.Tk.return_value.destroy.side_effect = FakeTclError("already destroyed")
        with self.assertRaisesRegex(RuntimeError, "无法打开文件夹窗口"):
            show_directory_dialog(str(self.runtime.root), "录音转写 · 选择保存位置")
        self.tk.filedialog.askdirectory.assert_called_once()
        self.tk.Tk.return_value.destroy.assert_called_once()
