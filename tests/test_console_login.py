"""Windows登录备用链接：合成进程验证管道与清理，始终替换真实浏览器入口。"""

import contextlib
import io
import os
import subprocess
import sys
from unittest.mock import patch

from asr_agent.bailian import (
    BailianFailure, PreparedCommand, _communicate_login, _open_console_fallback, _run_bl,
)
from asr_agent.environment import SetupError, child_environment
from tests.support import ProjectTestCase


STATE = "0123456789abcdef0123456789abcdef"
LOGIN_URL = ("https://bailian.console.aliyun.com/console-login?"
             f"notice=127.0.0.1:12345?state={STATE}&needapikey=true")


class ConsoleLoginTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.project.prepare()
        browser_patch = patch("asr_agent.bailian.os.startfile")
        self.open_browser = browser_patch.start()
        self.addCleanup(browser_patch.stop)

    def start_process(self, script: str, *arguments: str):
        process = subprocess.Popen(
            [sys.executable, "-c", script, *arguments], cwd=self.project.root,
            env=child_environment(self.project), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        def cleanup():
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            process.stdout.close()
            process.stderr.close()

        self.addCleanup(cleanup)
        return process

    def assert_reaped_and_closed(self, process):
        self.assertIsNotNone(process.poll())
        self.assertTrue(process.stdout.closed)
        self.assertTrue(process.stderr.closed)

    def test_full_url_reaches_shell_execute_without_losing_needapikey(self):
        _open_console_fallback(LOGIN_URL)
        self.open_browser.assert_called_once_with(LOGIN_URL)
        self.assertIn("&needapikey=true", self.open_browser.call_args.args[0])

    def test_official_url_without_optional_key_parameter_is_supported(self):
        url = LOGIN_URL.removesuffix("&needapikey=true")
        _open_console_fallback(url)
        self.open_browser.assert_called_once_with(url)

    def test_invalid_url_or_nonce_never_opens_or_leaks_to_public_output(self):
        invalid = [
            LOGIN_URL.replace("https://", "http://"),
            LOGIN_URL.replace("bailian.console.aliyun.com", "example.invalid"),
            LOGIN_URL.replace("bailian.console.aliyun.com", "bailian.console.aliyun.com.example.invalid"),
            LOGIN_URL.replace("bailian.console.aliyun.com", "synthetic@bailian.console.aliyun.com"),
            LOGIN_URL.replace("/console-login?", "/other?"),
            LOGIN_URL.replace("127.0.0.1", "127.0.0.2"),
            LOGIN_URL.replace(":12345?", ":0?"),
            LOGIN_URL.replace(":12345?", ":65536?"),
            LOGIN_URL.replace(STATE, "synthetic-short-state"),
            LOGIN_URL.replace(STATE, "g" * 32),
            LOGIN_URL.replace("needapikey=true", "needapikey=false"),
            LOGIN_URL + "&needapikey=true",
            LOGIN_URL + "&notice=127.0.0.1:12345?state=" + STATE,
            LOGIN_URL + "&unexpected=synthetic",
            LOGIN_URL + "#fragment",
            LOGIN_URL + " ",
            LOGIN_URL.replace("?notice=", "?notice"),
        ]
        for url in invalid:
            with self.subTest(url=url), contextlib.redirect_stdout(io.StringIO()) as stdout, \
                 contextlib.redirect_stderr(io.StringIO()) as stderr:
                with self.assertRaises(SetupError) as caught:
                    _open_console_fallback(url)
                self.assertNotIn(STATE, str(caught.exception))
                self.assertNotIn(url, str(caught.exception))
                self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(stderr.getvalue(), "")
        self.open_browser.assert_not_called()

    def test_duplicate_fallback_lines_open_once(self):
        marker = self.project.path("opened.txt")
        script = (
            "import pathlib,sys,time\n"
            "print(sys.argv[1],flush=True); print(sys.argv[1],flush=True)\n"
            "while not pathlib.Path(sys.argv[2]).exists(): time.sleep(0.01)\n"
        )
        process = self.start_process(script, LOGIN_URL, str(marker))
        self.open_browser.side_effect = lambda url: marker.write_text("opened", encoding="utf-8")
        self.assertEqual(_communicate_login(process, 5), (None, ""))
        self.open_browser.assert_called_once_with(LOGIN_URL)
        self.assert_reaped_and_closed(process)

    def test_link_is_opened_while_process_waits_for_callback(self):
        marker = self.project.path("opened.txt")
        script = (
            "import pathlib,sys,time\n"
            "marker=pathlib.Path(sys.argv[2])\n"
            "print(sys.argv[1],flush=True)\n"
            "deadline=time.monotonic()+3\n"
            "while not marker.exists() and time.monotonic()<deadline: time.sleep(0.01)\n"
            "sys.exit(0 if marker.exists() else 17)\n"
        )
        process = self.start_process(script, LOGIN_URL, str(marker))

        def open_marker(url):
            self.assertIsNone(process.poll())
            self.assertEqual(url, LOGIN_URL)
            marker.write_text("opened", encoding="utf-8")

        self.open_browser.side_effect = open_marker
        self.assertEqual(_communicate_login(process, 5), (None, ""))
        self.assertEqual(process.returncode, 0)
        self.assertTrue(marker.is_file())
        self.assert_reaped_and_closed(process)

    def test_large_stderr_is_drained_before_process_can_print_url(self):
        size = 1024 * 1024
        marker = self.project.path("opened.txt")
        script = (
            "import pathlib,sys,time\n"
            "sys.stderr.write('x'*int(sys.argv[2])); sys.stderr.flush()\n"
            "print(sys.argv[1],flush=True)\n"
            "while not pathlib.Path(sys.argv[3]).exists(): time.sleep(0.01)\n"
        )
        process = self.start_process(script, LOGIN_URL, str(size), str(marker))
        self.open_browser.side_effect = lambda url: marker.write_text("opened", encoding="utf-8")
        stdout, stderr = _communicate_login(process, 5)
        self.assertIsNone(stdout)
        self.assertEqual(len(stderr), size)
        self.open_browser.assert_called_once_with(LOGIN_URL)
        self.assert_reaped_and_closed(process)

    def test_timeout_kills_waiter_and_closes_both_pipes(self):
        process = self.start_process("import time; time.sleep(30)")
        with self.assertRaises(subprocess.TimeoutExpired):
            _communicate_login(process, 0.05)
        self.open_browser.assert_not_called()
        self.assert_reaped_and_closed(process)

    def test_open_failure_stops_waiting_and_does_not_expose_url(self):
        process = self.start_process("import sys,time; print(sys.argv[1],flush=True); time.sleep(30)", LOGIN_URL)
        self.open_browser.side_effect = OSError("synthetic browser failure " + LOGIN_URL)
        with self.assertRaises(SetupError) as caught:
            _communicate_login(process, 5)
        self.assertNotIn(LOGIN_URL, str(caught.exception))
        self.assertNotIn(STATE, str(caught.exception))
        self.open_browser.assert_called_once_with(LOGIN_URL)
        self.assert_reaped_and_closed(process)

    def test_invalid_link_stops_waiting_and_reaps_process(self):
        process = self.start_process("import sys,time; print(sys.argv[1],flush=True); time.sleep(30)",
                                     LOGIN_URL.replace(STATE, "invalid-state"))
        with self.assertRaisesRegex(SetupError, "官方格式"):
            _communicate_login(process, 5)
        self.open_browser.assert_not_called()
        self.assert_reaped_and_closed(process)

    def test_overlong_stdout_stops_waiting_instead_of_reading_without_limit(self):
        process = self.start_process("import sys,time; print('x'*4097,flush=True); time.sleep(30)")
        with self.assertRaisesRegex(SetupError, "超出预期长度"):
            _communicate_login(process, 5)
        self.open_browser.assert_not_called()
        self.assert_reaped_and_closed(process)

    def test_login_timeout_is_translated_once_without_second_cleanup_or_restart(self):
        process = self.start_process("import time; time.sleep(30)")
        command = PreparedCommand(("synthetic-bl", "auth", "login", "--console"), {})
        with patch("asr_agent.bailian.subprocess.Popen", return_value=process) as start:
            with self.assertRaises(BailianFailure) as caught:
                _run_bl(self.project, command, [], timeout=0.05, console_login=True)
        self.assertTrue(caught.exception.started)
        self.assertEqual(caught.exception.report["code"], "LOCAL_WAIT_INTERRUPTED")
        start.assert_called_once()
        self.assertEqual(start.call_args.kwargs["stdout"], subprocess.PIPE)
        self.assert_reaped_and_closed(process)
