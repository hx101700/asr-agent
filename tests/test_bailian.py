"""BL薄适配器合约：只用合成凭据和本地进程，不登录或访问真实ASR。"""

import json
import os
import shutil
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from asr_agent import BAILIAN_VERSION, MODEL
from asr_agent.bailian import (
    BailianFailure, check_command_length, console_status, explain_cli_error,
    login_console, redact_message, run_recognition,
)
from asr_agent.environment import SetupError
from tests.support import ProjectTestCase, ROOT


_REAL_POPEN = subprocess.Popen


class BailianTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.project.prepare()
        # 仅创建假入口供命令构造使用，所有BL进程均由测试替身接管。
        self.project.bl_entry.parent.mkdir(parents=True)
        self.project.bl_entry.touch()
        manifest = self.project.bl_entry.parent.parent / "package.json"
        manifest.write_text(json.dumps({"version": BAILIAN_VERSION}), encoding="utf-8")
        self.key = "asr-agent-synthetic-process-key"
        self.project.path(".env").write_text(f"DASHSCOPE_API_KEY={self.key}\n", encoding="utf-8")
        self.node = self.project.root / "node.exe"
        self.arguments = [
            "speech", "recognize", "--model", MODEL,
            "--url", str(self.project.root / "本地 audio.wav"),
            "--out", str(self.project.root / "result.json"),
            "--base-url", "https://dashscope.aliyuncs.com", "--config", "default",
            "--output", "json", "--diarization", "--speaker-count", "3",
            "--context", "本地合成上下文", "--vocabulary", '{"合成词":4}',
        ]
        self.process = Mock()
        self.process.returncode = 0
        self.process.communicate.return_value = (None, "")
        node_patch = patch("asr_agent.environment.find_node", return_value=self.node)
        process_patch = patch("asr_agent.bailian.subprocess.Popen", return_value=self.process)
        node_patch.start()
        self.popen = process_patch.start()
        self.addCleanup(node_patch.stop)
        self.addCleanup(process_patch.stop)

    def test_recognition_uses_local_entry_and_public_arguments_without_shell(self):
        run_recognition(self.project, self.arguments, "api_key", [])
        self.popen.assert_called_once()
        argv = self.popen.call_args.args[0]
        self.assertEqual(argv, [str(self.node), str(self.project.bl_entry), *self.arguments, "--quiet"])
        self.assertNotIn("--file", argv)
        self.assertNotIn("--async", argv)
        self.assertFalse(self.popen.call_args.kwargs["shell"])
        self.assertEqual(self.popen.call_args.kwargs["cwd"], self.project.root)

    def test_api_key_only_reaches_child_environment_and_transcript_is_not_captured(self):
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "unrelated-synthetic-key",
                                     "NODE_OPTIONS": "--require unwanted.cjs"}):
            result = run_recognition(self.project, self.arguments, "api_key", [])
        self.assertIsNone(result)
        kwargs = self.popen.call_args.kwargs
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.PIPE)
        self.assertEqual(kwargs["env"]["DASHSCOPE_API_KEY"], self.key)
        self.assertEqual(kwargs["env"]["DO_NOT_TRACK"], "1")
        self.assertNotIn("NODE_OPTIONS", kwargs["env"])
        self.assertNotIn(self.key, repr(self.popen.call_args.args))

    def test_console_mode_does_not_inherit_api_key(self):
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "unrelated-synthetic-key"}):
            run_recognition(self.project, self.arguments, "console", [])
        self.assertNotIn("DASHSCOPE_API_KEY", self.popen.call_args.kwargs["env"])
        self.assertEqual(self.popen.call_args.kwargs["env"]["BAILIAN_CONFIG_DIR"],
                         str(self.project.path(".state/bailian")))

    def test_command_length_includes_terminating_nul(self):
        check_command_length(["a" * 32766])
        with self.assertRaisesRegex(SetupError, "32768"):
            check_command_length(["a" * 32767])

    def test_command_length_counts_surrogate_pairs(self):
        check_command_length(["😀" * 16383])
        with self.assertRaises(SetupError):
            check_command_length(["😀" * 16383 + "a"])

    def test_command_length_includes_windows_quotes_and_escaped_trailing_slash(self):
        # 空格触发外层引号，末尾反斜线在结束引号前必须翻倍。
        argument = "prefix " + "a" * 32755 + "\\"
        self.assertEqual(len(subprocess.list2cmdline([argument])), 32766)
        check_command_length([argument])
        with self.assertRaises(SetupError):
            check_command_length([argument + "\\"])

    def test_oversized_command_stops_before_loading_credentials_or_starting_bl(self):
        with patch("asr_agent.bailian.bailian_environment") as environment:
            with self.assertRaises(SetupError):
                run_recognition(self.project, [*self.arguments, "--context", "a" * 32767], "api_key", [])
        self.popen.assert_not_called()
        environment.assert_not_called()

    def test_process_start_failure_is_distinct_from_unknown_cloud_result(self):
        self.popen.side_effect = OSError("synthetic process start failure")
        with self.assertRaises(BailianFailure) as caught:
            run_recognition(self.project, self.arguments, "api_key", [])
        self.assertFalse(caught.exception.started)
        self.assertEqual(caught.exception.report["code"], "LOCAL_PROCESS_START_FAILED")
        self.popen.assert_called_once()

    def test_failed_recognition_is_not_retried_and_redacts_key_from_error(self):
        self.process.returncode = 1
        self.process.communicate.return_value = (None, json.dumps({"error": {
            "code": 1, "api_code": "InvalidApiKey", "http_status": 401,
            "message": f"rejected {self.key}", "request_id": "synthetic-request",
        }}))
        with self.assertRaises(BailianFailure) as caught:
            run_recognition(self.project, self.arguments, "api_key", [])
        self.assertTrue(caught.exception.started)
        self.assertEqual(caught.exception.report["http_status"], 401)
        self.assertEqual(caught.exception.report["code"], "InvalidApiKey")
        self.assertNotIn(self.key, json.dumps(caught.exception.report))
        self.popen.assert_called_once()
        self.process.communicate.assert_called_once()
        self.process.kill.assert_not_called()

    def test_interrupted_wait_kills_and_reaps_the_existing_process_without_retry(self):
        for failure in (subprocess.TimeoutExpired("synthetic", 1), KeyboardInterrupt(),
                        OSError("synthetic pipe failure")):
            with self.subTest(failure=type(failure).__name__):
                self.process.reset_mock()
                self.popen.reset_mock()
                self.process.communicate.side_effect = [failure, (None, "private output")]
                with self.assertRaises(BailianFailure) as caught:
                    run_recognition(self.project, self.arguments, "api_key", [])
                self.assertTrue(caught.exception.started)
                self.assertEqual(caught.exception.report["code"], "LOCAL_WAIT_INTERRUPTED")
                self.assertIn("中断", str(caught.exception))
                self.assertNotIn("private output", json.dumps(caught.exception.report))
                self.popen.assert_called_once()
                self.process.kill.assert_called_once()
                self.assertEqual(self.process.communicate.call_count, 2)
                self.assertEqual(self.process.communicate.call_args.kwargs, {})

    def test_timeout_reaps_an_actual_local_waiting_process(self):
        # 真进程只等待，不读凭据、不访问网络，验证超时处理确实回收Windows进程。
        children = []

        def start_waiter(*args, **kwargs):
            child = _REAL_POPEN([sys.executable, "-c", "import time; time.sleep(30)"],
                               cwd=self.project.root, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8",
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            children.append(child)
            return child

        self.popen.side_effect = start_waiter
        try:
            with patch("asr_agent.bailian.PROCESS_SECONDS", 0.05):
                with self.assertRaises(BailianFailure) as caught:
                    run_recognition(self.project, self.arguments, "console", [])
            self.assertTrue(caught.exception.started)
            self.assertEqual(len(children), 1)
            self.assertIsNotNone(children[0].poll())
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.communicate()

    def test_error_report_separates_cli_exit_code_from_api_error(self):
        payload = {"error": {"code": 999, "api_code": "InvalidParameter", "http_status": 400,
                             "request_id": "synthetic-request", "message": "bad parameter",
                             "cause": {"message": "private detail"}, "hint": "private hint"}}
        report = explain_cli_error(1, json.dumps(payload), [])
        self.assertEqual(report["cli_exit_code"], 1)
        self.assertEqual(report["code"], "InvalidParameter")
        self.assertEqual(report["request_id"], "synthetic-request")
        self.assertIn("参数", report["explanation"])
        self.assertTrue(report["source_url"].startswith("https://"))
        self.assertNotIn("cause", report)
        self.assertNotIn("hint", report)

    def test_unknown_api_code_preserves_scalar_evidence_without_inventing_meaning(self):
        report = explain_cli_error(91, json.dumps({"error": {
            "api_code": "Synthetic.NewError", "http_status": 599,
            "request_id": "synthetic-request", "message": "synthetic problem",
        }}), [])
        self.assertEqual(report["code"], "Synthetic.NewError")
        self.assertEqual(report["http_status"], 599)
        self.assertEqual(report["message"], "synthetic problem")
        self.assertIn("未收录", report["explanation"])
        self.assertIsNone(report["source_url"])

    def test_malformed_stderr_is_not_forwarded(self):
        for payload in ("raw private stderr", "null", "[]", '{"error": []}',
                        '{"error":{"api_code":[],"request_id":{},"http_status":true,"message":{}}}'):
            with self.subTest(payload=payload):
                report = explain_cli_error(1, payload, [])
                self.assertIsNone(report["code"])
                self.assertIsNone(report["request_id"])
                self.assertIsNone(report["http_status"])
                self.assertIn("未提供可解析", report["message"])

    def test_redaction_covers_private_values_urls_tokens_and_all_visible_error_fields(self):
        private = ["synthetic-token", "合成私密上下文", "合成词"]
        text = ("synthetic-token 合成私密上下文 合成词 "
                "https://example.invalid/result?signature=secret oss://synthetic/audio "
                "sk-synthetic-key LTAIsyntheticAK Bearer opaqueSyntheticToken\nline")
        redacted = redact_message(text, private)
        for fragment in (*private, "example.invalid", "oss://", "sk-synthetic-key",
                         "LTAIsyntheticAK", "opaqueSyntheticToken"):
            self.assertNotIn(fragment, redacted)
        self.assertNotIn("\n", redacted)
        report = explain_cli_error(1, json.dumps({"error": {
            "message": text, "api_code": "synthetic-token", "request_id": "合成私密上下文",
        }}), private)
        self.assertEqual(report["code"], "[已隐藏]")
        self.assertEqual(report["request_id"], "[已隐藏]")
        self.assertLessEqual(len(redact_message("a" * 1000, [])), 800)

    def test_console_status_requires_model_key_not_just_authenticated(self):
        for status, configured in (({"authenticated": True, "console": {"masked": "masked"}}, False),
                                   ({"authenticated": True, "openapi": {"source": "config"}}, False),
                                   ({"authenticated": True, "api_key": "invalid"}, False),
                                   ({"authenticated": False}, False),
                                   ({"authenticated": True, "api_key": {"masked": "masked"}}, True)):
            with self.subTest(status=status):
                self.process.communicate.return_value = (json.dumps(status), "")
                report = console_status(self.project)
                self.assertEqual(report["configured"], configured)
                self.assertFalse(report["verified_online"])
                self.assertNotIn("masked", json.dumps(report))
        self.assertEqual(self.popen.call_args.kwargs["stdout"], subprocess.PIPE)
        argv = self.popen.call_args.args[0]
        self.assertEqual(argv[2:], ["auth", "status", "--config", "default", "--output", "json", "--quiet"])

    def test_console_status_rejects_nonobject_or_invalid_json(self):
        for output in ("not json", "[]", "null", "true"):
            with self.subTest(output=output):
                self.process.communicate.return_value = (output, "")
                with self.assertRaisesRegex(SetupError, "登录状态"):
                    console_status(self.project)

    def test_successful_login_process_still_checks_public_status(self):
        self.process.communicate.side_effect = [(None, ""), (json.dumps({"authenticated": False}), "")]
        report = login_console(self.project)
        self.assertFalse(report["configured"])
        self.assertEqual(self.popen.call_count, 2)
        first, second = self.popen.call_args_list
        self.assertEqual(first.args[0][2:], ["auth", "login", "--console", "--console-site", "domestic",
                                             "--config", "default", "--output", "json", "--quiet"])
        self.assertNotIn("--base-url", first.args[0])
        self.assertEqual(second.args[0][2:4], ["auth", "status"])
        self.assertNotIn("DASHSCOPE_API_KEY", first.kwargs["env"])

    def test_failed_login_does_not_repeat_login_or_request_status(self):
        self.process.returncode = 6
        self.process.communicate.return_value = (None, '{"error":{"code":6,"message":"synthetic network failure"}}')
        with self.assertRaises(BailianFailure):
            login_console(self.project)
        self.popen.assert_called_once()

    @unittest.skipUnless((ROOT / ".tools/bailian/node_modules/bailian-cli/dist/bailian.mjs").is_file()
                         and shutil.which("node"), "需要项目内BL和Node运行本机状态合约")
    def test_real_cli_status_reads_only_synthetic_project_configuration(self):
        config = self.project.path(".state/bailian/config.json")
        config.write_text(json.dumps({"api_key": self.key,
                                     "base_url": "https://dashscope.aliyuncs.com"}), encoding="utf-8")
        self.popen.side_effect = _REAL_POPEN
        entry = ROOT / ".tools/bailian/node_modules/bailian-cli/dist/bailian.mjs"
        with patch("asr_agent.bailian.bl_command", side_effect=lambda project, args:
                   [shutil.which("node"), str(entry), *args, "--quiet"]):
            report = console_status(self.project)
        self.assertTrue(report["configured"])
        self.assertFalse(report["verified_online"])
        self.assertNotIn(self.key, json.dumps(report))
        self.assertEqual(self.popen.call_args.kwargs["env"]["BAILIAN_CONFIG_DIR"], str(config.parent))
