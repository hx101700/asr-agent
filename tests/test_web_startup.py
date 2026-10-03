"""验证网页服务启动回执与浏览器打开请求分别报告。"""

import io
import json
import webbrowser
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from asr_runtime import web
from tests.support import RuntimeTestCase


class WebStartupTests(RuntimeTestCase):
    def setUp(self) -> None:
        """准备可结束服务循环的本机服务器替身。"""
        super().setUp()
        self.server = Mock(spec=web.LocalServer)
        self.server.server_port = 12345
        self.server.session = Mock(token="synthetic-session-token")
        self.server.serve_forever.side_effect = KeyboardInterrupt

    def start(self, *, automatic: bool, browser_result: bool | Exception = True) -> dict[str, object]:
        """执行启动入口并读取唯一的启动回执。"""
        output = io.StringIO()
        with patch.object(web, "create_server", return_value=self.server), \
             patch.object(web.webbrowser, "open") as launch, redirect_stdout(output):
            if isinstance(browser_result, Exception):
                launch.side_effect = browser_result
            else:
                launch.return_value = browser_result
            web.serve(self.runtime, open_browser=automatic)
        if automatic:
            launch.assert_called_once_with("http://127.0.0.1:12345/#token=synthetic-session-token")
        else:
            launch.assert_not_called()
        self.server.serve_forever.assert_called_once()
        self.server.server_close.assert_called_once()
        receipt = json.loads(output.getvalue())
        self.assertEqual(receipt["event"], "listening")
        self.assertEqual(receipt["url"], "http://127.0.0.1:12345/#token=synthetic-session-token")
        self.assertIsInstance(receipt["pid"], int)
        return receipt

    def test_browser_tool_mode_leaves_opening_to_the_caller(self) -> None:
        """验证浏览器工具模式交付URL，并明确跳过系统打开。"""
        self.assertEqual(self.start(automatic=False)["browser_request"], "skipped")

    def test_system_browser_request_is_reported_as_requested(self) -> None:
        """验证系统接受请求时回执仅报告已请求打开。"""
        self.assertEqual(self.start(automatic=True)["browser_request"], "requested")

    def test_rejected_browser_request_keeps_the_server_available(self) -> None:
        """验证系统拒绝打开时报告失败并继续提供本机服务。"""
        self.assertEqual(self.start(automatic=True, browser_result=False)["browser_request"], "failed")

    def test_browser_exception_keeps_the_server_available(self) -> None:
        """验证浏览器调用异常沿既有启动回执报告。"""
        for error in (OSError("synthetic launch failure"), webbrowser.Error("synthetic unavailable")):
            with self.subTest(error=type(error).__name__):
                self.server.reset_mock()
                self.assertEqual(self.start(automatic=True, browser_result=error)["browser_request"], "failed")

    def test_failed_startup_receipt_closes_the_server(self) -> None:
        """验证输出通道关闭时释放已绑定的服务器。"""
        with patch.object(web, "create_server", return_value=self.server), \
             patch("builtins.print", side_effect=BrokenPipeError("synthetic closed output")):
            with self.assertRaises(BrokenPipeError):
                web.serve(self.runtime, open_browser=False)
        self.server.serve_forever.assert_not_called()
        self.server.server_close.assert_called_once()
