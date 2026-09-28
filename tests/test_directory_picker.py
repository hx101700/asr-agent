import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

from asr_agent.directory_picker import choose_directory, validate_directory
from asr_agent.environment import SetupError
from tests.support import ProjectTestCase


class FakeTclError(Exception):
    pass


class DirectoryPickerTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.tk = ModuleType("tkinter")
        self.tk.Tk = MagicMock()
        self.tk.TclError = FakeTclError
        self.tk.filedialog = ModuleType("tkinter.filedialog")
        self.tk.filedialog.askdirectory = MagicMock(return_value=str(self.project.root))
        self.modules = patch.dict(sys.modules, {
            "tkinter": self.tk, "tkinter.filedialog": self.tk.filedialog,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.platform = patch("asr_agent.directory_picker.sys.platform", "win32")
        self.platform.start()
        self.addCleanup(self.platform.stop)

    def test_returns_resolved_directory_and_destroys_hidden_parent(self):
        selected = self.project.root / "chosen"
        selected.mkdir()
        self.tk.filedialog.askdirectory.return_value = str(selected)
        result = choose_directory(self.project.root)
        self.assertEqual(result, selected.resolve())
        window = self.tk.Tk.return_value
        window.withdraw.assert_called_once()
        window.attributes.assert_called_once_with("-topmost", True)
        window.destroy.assert_called_once()
        self.tk.filedialog.askdirectory.assert_called_once_with(
            parent=window, initialdir=str(self.project.root.resolve()),
            title="选择保存位置", mustexist=True,
        )

    def test_cancel_returns_none_and_cleans_up(self):
        self.tk.filedialog.askdirectory.return_value = ""
        self.assertIsNone(choose_directory(self.project.root))
        self.tk.Tk.return_value.destroy.assert_called_once()

    def test_missing_tkinter_gives_component_error(self):
        with patch.dict(sys.modules, {"tkinter": None}):
            with self.assertRaisesRegex(SetupError, "缺少 tkinter/Tcl/Tk"):
                choose_directory(self.project.root)
        self.tk.Tk.assert_not_called()

    def test_failed_tk_creation_is_reported_without_retry(self):
        self.tk.Tk.side_effect = FakeTclError("synthetic initialization failure")
        with self.assertRaisesRegex(SetupError, "无法打开文件夹选择窗口"):
            choose_directory(self.project.root)
        self.tk.Tk.assert_called_once()
        self.tk.filedialog.askdirectory.assert_not_called()

    def test_dialog_failure_preserves_user_error_and_cleans_up(self):
        self.tk.filedialog.askdirectory.side_effect = FakeTclError("synthetic dialog failure")
        self.tk.Tk.return_value.destroy.side_effect = FakeTclError("already destroyed")
        with self.assertRaisesRegex(SetupError, "无法打开文件夹选择窗口"):
            choose_directory(self.project.root)
        self.tk.filedialog.askdirectory.assert_called_once()
        self.tk.Tk.return_value.destroy.assert_called_once()

    def test_missing_directory_is_not_created(self):
        missing = self.project.root / "not-created"
        self.tk.filedialog.askdirectory.return_value = str(missing)
        with self.assertRaisesRegex(SetupError, "不存在或无法访问"):
            choose_directory(self.project.root)
        self.assertFalse(missing.exists())
        self.tk.Tk.return_value.destroy.assert_called_once()

    def test_file_is_not_accepted_as_directory(self):
        file = self.project.root / "file.txt"
        file.write_text("synthetic", encoding="utf-8")
        with self.assertRaisesRegex(SetupError, "不是文件夹"):
            validate_directory(file)

    def test_invalid_initial_directory_does_not_open_dialog(self):
        with self.assertRaisesRegex(SetupError, "不存在或无法访问"):
            choose_directory(self.project.root / "missing")
        self.tk.Tk.assert_not_called()

    def test_unsupported_platform_does_not_open_dialog(self):
        with patch("asr_agent.directory_picker.sys.platform", "linux"):
            with self.assertRaisesRegex(SetupError, "仅支持 Windows"):
                choose_directory(self.project.root)
        self.tk.Tk.assert_not_called()
