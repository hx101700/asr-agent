import json
import os
import subprocess
import sys
from pathlib import Path
from threading import Event, Timer
from types import ModuleType
from unittest.mock import MagicMock, patch

from asr_agent._directory_dialog import show_directory_dialog
from asr_agent.directory_picker import choose_directory, validate_directory
from asr_agent.environment import SetupError
from tests.support import ProjectTestCase


class DirectoryPickerTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.process = MagicMock()
        self.process.returncode = 0
        self.process.poll.return_value = 0
        self.process.communicate.return_value = (json.dumps({"path": str(self.project.root)}), "")
        start_process = patch("asr_agent.directory_picker.subprocess.Popen", return_value=self.process)
        self.popen = start_process.start()
        self.addCleanup(start_process.stop)
        platform = patch("asr_agent.directory_picker.sys.platform", "win32")
        platform.start()
        self.addCleanup(platform.stop)

    def test_selected_directory_is_resolved(self):
        selected = self.project.root / "中文 目录"
        selected.mkdir()
        self.process.communicate.return_value = (json.dumps({"path": str(selected)}), "")
        self.assertEqual(choose_directory(self.project.root), selected.resolve())
        self.popen.assert_called_once()
        self.process.kill.assert_not_called()

    def test_native_cancel_returns_none(self):
        self.process.communicate.return_value = ('{"path": null}', "")
        self.assertIsNone(choose_directory(self.project.root))
        self.process.kill.assert_not_called()

    def test_already_cancelled_does_not_start_process(self):
        cancelled = Event()
        cancelled.set()
        self.assertIsNone(choose_directory(self.project.root, cancel_event=cancelled))
        self.popen.assert_not_called()

    def test_cancel_during_wait_kills_and_reaps_process(self):
        cancelled = Event()

        def communicate(*, timeout=None):
            if timeout is not None:
                cancelled.set()
                raise subprocess.TimeoutExpired("synthetic-picker", timeout)
            return "", ""

        self.process.communicate.side_effect = communicate
        self.process.poll.return_value = None
        self.assertIsNone(choose_directory(self.project.root, cancel_event=cancelled))
        self.popen.assert_called_once()
        self.process.kill.assert_called_once()
        self.assertEqual(self.process.communicate.call_args.kwargs, {})

    def test_cancellation_during_response_discards_selected_path(self):
        cancelled = Event()

        def communicate(*, timeout=None):
            cancelled.set()
            return json.dumps({"path": str(self.project.root)}), ""

        self.process.communicate.side_effect = communicate
        self.assertIsNone(choose_directory(self.project.root, cancel_event=cancelled))

    def test_five_minute_timeout_kills_process_without_reopening(self):
        self.process.poll.return_value = None
        self.process.communicate.side_effect = [
            subprocess.TimeoutExpired("synthetic-picker", 0.2), ("", ""),
        ]
        # 使用时钟边界验证五分钟上限，不在测试中真的等待五分钟。
        with patch("asr_agent.directory_picker.time.monotonic", side_effect=[10, 309.9, 310]):
            with self.assertRaisesRegex(SetupError, "等待超时"):
                choose_directory(self.project.root)
        self.popen.assert_called_once()
        self.process.kill.assert_called_once()
        self.assertEqual(self.process.communicate.call_count, 2)

    def test_process_failure_does_not_expose_stderr(self):
        self.process.returncode = 1
        self.process.poll.return_value = 1
        self.process.communicate.return_value = ("", "synthetic private diagnostic")
        with self.assertRaisesRegex(SetupError, "异常退出") as caught:
            choose_directory(self.project.root)
        self.assertNotIn("synthetic private", str(caught.exception))
        self.popen.assert_called_once()

    def test_invalid_protocol_is_reported(self):
        for output in ("not-json", "[]", "{}", '{"path": 42}', '{"path": []}'):
            with self.subTest(output=output):
                self.process.communicate.return_value = (output, "")
                with self.assertRaisesRegex(SetupError, "无法读取文件夹选择结果"):
                    choose_directory(self.project.root)

    def test_helper_error_is_reported(self):
        self.process.communicate.return_value = (json.dumps({"error": "测试窗口不可用"}), "")
        with self.assertRaisesRegex(SetupError, "测试窗口不可用"):
            choose_directory(self.project.root)

    def test_launch_failure_is_reported_without_retry(self):
        self.popen.side_effect = OSError("synthetic launch failure")
        with self.assertRaisesRegex(SetupError, "无法启动文件夹窗口"):
            choose_directory(self.project.root)
        self.popen.assert_called_once()

    def test_gui_process_does_not_inherit_keys_or_python_injection(self):
        environment = {
            "SystemRoot": "C:\\Windows", "PATH": "synthetic-path", "TEMP": str(self.project.root),
            "SystemDrive": "C:", "ProgramData": "C:\\ProgramData",
            "DASHSCOPE_API_KEY": "synthetic-api-key", "BAILIAN_API_KEY": "synthetic-bl-key",
            "PYTHONPATH": "synthetic-python-path", "PYTHONSTARTUP": "synthetic-startup",
        }
        with patch.dict(os.environ, environment, clear=True):
            choose_directory(self.project.root)
        args, kwargs = self.popen.call_args
        self.assertEqual(args[0][:4], [sys.executable, "-I", "-X", "utf8"])
        self.assertEqual(Path(args[0][4]).name, "_directory_dialog.py")
        self.assertEqual(args[0][5], str(self.project.root.resolve()))
        self.assertEqual({key.upper(): value for key, value in kwargs["env"].items()}, {
            "SYSTEMROOT": "C:\\Windows", "PATH": "synthetic-path", "TEMP": str(self.project.root),
            "SYSTEMDRIVE": "C:", "PROGRAMDATA": "C:\\ProgramData",
        })
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)

    def test_missing_selection_is_not_created(self):
        missing = self.project.root / "not-created"
        self.process.communicate.return_value = (json.dumps({"path": str(missing)}), "")
        with self.assertRaisesRegex(SetupError, "不存在或无法访问"):
            choose_directory(self.project.root)
        self.assertFalse(missing.exists())

    def test_file_is_not_accepted_as_directory(self):
        file = self.project.root / "file.txt"
        file.write_text("synthetic", encoding="utf-8")
        with self.assertRaisesRegex(SetupError, "不是文件夹"):
            validate_directory(file)

    def test_invalid_initial_directory_does_not_start_process(self):
        with self.assertRaisesRegex(SetupError, "不存在或无法访问"):
            choose_directory(self.project.root / "missing")
        self.popen.assert_not_called()

    def test_unsupported_platform_does_not_start_process(self):
        with patch("asr_agent.directory_picker.sys.platform", "linux"):
            with self.assertRaisesRegex(SetupError, "仅支持 Windows"):
                choose_directory(self.project.root)
        self.popen.assert_not_called()


class DirectoryPickerProcessTests(ProjectTestCase):
    def test_cancel_terminates_real_unresponsive_child_without_gui(self):
        if sys.platform != "win32":
            self.skipTest("目录窗口运行边界仅支持 Windows")
        real_popen = subprocess.Popen
        cancelled = Event()
        children = []
        timer = None

        def start_sleeping_child(command, **kwargs):
            nonlocal timer
            # 真子进程只等待、不创建窗口，验证取消后确实回收进程。
            child = real_popen([sys.executable, "-I", "-c", "import time; time.sleep(30)"], **kwargs)
            children.append(child)
            timer = Timer(0.05, cancelled.set)
            timer.start()
            return child

        try:
            with patch("asr_agent.directory_picker.subprocess.Popen", side_effect=start_sleeping_child):
                self.assertIsNone(choose_directory(self.project.root, cancel_event=cancelled))
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


class NativeDirectoryDialogTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.tk = ModuleType("tkinter")
        self.tk.Tk = MagicMock()
        self.tk.TclError = FakeTclError
        self.tk.filedialog = ModuleType("tkinter.filedialog")
        self.tk.filedialog.askdirectory = MagicMock(return_value=str(self.project.root))
        modules = patch.dict(sys.modules, {"tkinter": self.tk, "tkinter.filedialog": self.tk.filedialog})
        modules.start()
        self.addCleanup(modules.stop)

    def test_selected_directory_cleans_up_hidden_parent(self):
        self.assertEqual(show_directory_dialog(str(self.project.root)), str(self.project.root))
        window = self.tk.Tk.return_value
        window.withdraw.assert_called_once()
        window.attributes.assert_called_once_with("-topmost", True)
        window.destroy.assert_called_once()
        self.tk.filedialog.askdirectory.assert_called_once_with(
            parent=window, initialdir=str(self.project.root), title="asr-agent · 选择保存位置", mustexist=True,
        )

    def test_cancel_cleans_up_hidden_parent(self):
        self.tk.filedialog.askdirectory.return_value = ""
        self.assertIsNone(show_directory_dialog(str(self.project.root)))
        self.tk.Tk.return_value.destroy.assert_called_once()

    def test_missing_tkinter_reports_component_error(self):
        with patch.dict(sys.modules, {"tkinter": None}):
            with self.assertRaisesRegex(RuntimeError, "缺少 tkinter/Tcl/Tk"):
                show_directory_dialog(str(self.project.root))
        self.tk.Tk.assert_not_called()

    def test_failed_tk_creation_does_not_open_or_retry_dialog(self):
        self.tk.Tk.side_effect = FakeTclError("synthetic initialization failure")
        with self.assertRaisesRegex(RuntimeError, "无法打开文件夹窗口"):
            show_directory_dialog(str(self.project.root))
        self.tk.Tk.assert_called_once()
        self.tk.filedialog.askdirectory.assert_not_called()

    def test_dialog_error_survives_cleanup_error(self):
        self.tk.filedialog.askdirectory.side_effect = FakeTclError("synthetic dialog failure")
        self.tk.Tk.return_value.destroy.side_effect = FakeTclError("already destroyed")
        with self.assertRaisesRegex(RuntimeError, "无法打开文件夹窗口"):
            show_directory_dialog(str(self.project.root))
        self.tk.filedialog.askdirectory.assert_called_once()
        self.tk.Tk.return_value.destroy.assert_called_once()
