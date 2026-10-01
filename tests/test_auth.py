import json
import os
from unittest.mock import patch

from asr_agent.tools.auth import api_key_status, bailian_environment, read_api_key
from asr_agent.tools.environment import SetupError
from tests.support import ProjectTestCase


class ApiKeyTests(ProjectTestCase):
    def test_missing_and_empty_key_are_local_errors(self):
        """验证缺失或空Key返回配置缺失状态。"""
        self.assertFalse(api_key_status(self.project)["configured"])
        self.project.path(".env").write_text("DASHSCOPE_API_KEY=\n", encoding="utf-8")
        self.assertFalse(api_key_status(self.project)["configured"])

    def test_status_never_returns_key_or_claims_online_verification(self):
        """验证状态报告使用本地配置标记并隐藏密钥。"""
        self.project.path(".env").write_text('DASHSCOPE_API_KEY="synthetic-secret"\n', encoding="utf-8")
        status = api_key_status(self.project)
        self.assertTrue(status["configured"])
        self.assertFalse(status["verified_online"])
        self.assertNotIn("synthetic-secret", json.dumps(status))

    def test_key_only_reaches_explicit_api_key_environment(self):
        """验证指定Key与控制台模式的凭据环境隔离。"""
        self.project.path(".env").write_text("DASHSCOPE_API_KEY=synthetic-secret\n", encoding="utf-8")
        self.assertNotIn("DASHSCOPE_API_KEY", bailian_environment(self.project, "console"))
        self.assertEqual(bailian_environment(self.project, "api_key")["DASHSCOPE_API_KEY"], "synthetic-secret")

    def test_does_not_use_process_key_or_expand_variables(self):
        """验证.env值按原文读取并保持进程环境。"""
        self.project.path(".env").write_text("DASHSCOPE_API_KEY=${UNRELATED_SECRET}\n", encoding="utf-8")
        with patch.dict(os.environ, {"UNRELATED_SECRET": "outside-secret", "DASHSCOPE_API_KEY": "outside-key"}):
            self.assertEqual(read_api_key(self.project), "${UNRELATED_SECRET}")
            self.assertEqual(os.environ["DASHSCOPE_API_KEY"], "outside-key")

    def test_console_does_not_read_dotenv(self):
        """验证控制台模式使用独立凭据环境。"""
        with patch("asr_agent.tools.auth.read_api_key", side_effect=AssertionError("must not read")):
            bailian_environment(self.project, "console")

    def test_multiline_key_is_rejected_without_echo(self):
        """验证含换行Key返回脱敏配置错误。"""
        self.project.path(".env").write_text('DASHSCOPE_API_KEY="synthetic\nsecret"\n', encoding="utf-8")
        report = api_key_status(self.project)
        self.assertFalse(report["configured"])
        self.assertNotIn("synthetic", json.dumps(report))

    def test_unknown_mode_is_rejected(self):
        """验证拒绝未知鉴权方式。"""
        with self.assertRaises(SetupError):
            bailian_environment(self.project, "unknown")
