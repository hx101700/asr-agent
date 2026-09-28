import json
import os
from unittest.mock import patch

from asr_agent.auth import api_key_status, bailian_environment, read_api_key
from asr_agent.environment import SetupError
from tests.support import ProjectTestCase


class ApiKeyTests(ProjectTestCase):
    def test_missing_and_empty_key_are_local_errors(self):
        self.assertFalse(api_key_status(self.project)["configured"])
        self.project.path(".env").write_text("DASHSCOPE_API_KEY=\n", encoding="utf-8")
        self.assertFalse(api_key_status(self.project)["configured"])

    def test_status_never_returns_key_or_claims_online_verification(self):
        self.project.path(".env").write_text('DASHSCOPE_API_KEY="synthetic-secret"\n', encoding="utf-8")
        status = api_key_status(self.project)
        self.assertTrue(status["configured"])
        self.assertFalse(status["verified_online"])
        self.assertNotIn("synthetic-secret", json.dumps(status))

    def test_key_only_reaches_explicit_api_key_environment(self):
        self.project.path(".env").write_text("DASHSCOPE_API_KEY=synthetic-secret\n", encoding="utf-8")
        self.assertNotIn("DASHSCOPE_API_KEY", bailian_environment(self.project, "console"))
        self.assertEqual(bailian_environment(self.project, "api_key")["DASHSCOPE_API_KEY"], "synthetic-secret")

    def test_does_not_use_process_key_or_expand_variables(self):
        self.project.path(".env").write_text("DASHSCOPE_API_KEY=${UNRELATED_SECRET}\n", encoding="utf-8")
        with patch.dict(os.environ, {"UNRELATED_SECRET": "outside-secret", "DASHSCOPE_API_KEY": "outside-key"}):
            self.assertEqual(read_api_key(self.project), "${UNRELATED_SECRET}")
            self.assertEqual(os.environ["DASHSCOPE_API_KEY"], "outside-key")

    def test_console_does_not_read_dotenv(self):
        with patch("asr_agent.auth.read_api_key", side_effect=AssertionError("must not read")):
            bailian_environment(self.project, "console")

    def test_multiline_key_is_rejected_without_echo(self):
        self.project.path(".env").write_text('DASHSCOPE_API_KEY="synthetic\nsecret"\n', encoding="utf-8")
        report = api_key_status(self.project)
        self.assertFalse(report["configured"])
        self.assertNotIn("synthetic", json.dumps(report))

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(SetupError):
            bailian_environment(self.project, "unknown")
