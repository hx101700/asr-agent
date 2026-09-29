import json
import os
import subprocess
import shutil
from unittest.mock import patch

from asr_agent import BAILIAN_VERSION
from asr_agent.bootstrap import bootstrap
from asr_agent.environment import (
    SetupError, bl_command, child_environment, doctor, installed_python_versions,
    locked_python_versions, run_process, verify_bl_installation,
)
from asr_agent.probe import SYNTHETIC_AUDIO_URL, probe
from tests.support import ProjectTestCase, ROOT


class EnvironmentTests(ProjectTestCase):
    def test_paths_cannot_leave_project(self):
        with self.assertRaises(SetupError):
            self.project.path("../outside")

    def test_child_does_not_inherit_credentials_or_node_injection(self):
        private = {
            "DASHSCOPE_API_KEY": "synthetic-key",
            "DASHSCOPE_BASE_URL": "https://example.invalid",
            "NODE_OPTIONS": "--require unwanted.js",
            "NPM_TOKEN": "synthetic-token",
            "NPM_CONFIG_USERCONFIG": "outside.npmrc",
        }
        with patch.dict(os.environ, private):
            env = child_environment(self.project)
        for name in private.keys() - {"NPM_CONFIG_USERCONFIG"}:
            self.assertNotIn(name, env)
        self.assertTrue(env["NPM_CONFIG_USERCONFIG"].startswith(str(self.project.root)))
        self.assertEqual(env["NPM_CONFIG_FETCH_RETRIES"], "0")
        self.assertEqual(env["DO_NOT_TRACK"], "1")

    def test_probe_does_not_share_login_directory(self):
        normal = child_environment(self.project)
        isolated = child_environment(self.project, probe_mode=True)
        self.assertNotEqual(normal["BAILIAN_CONFIG_DIR"], isolated["BAILIAN_CONFIG_DIR"])

    def test_nonempty_npm_configuration_is_not_overwritten(self):
        self.project.prepare()
        config = self.project.path(".runtime/npm-user.npmrc")
        config.write_text("registry=https://example.invalid\n", encoding="utf-8")
        with self.assertRaises(SetupError):
            self.project.prepare()
        self.assertIn("example.invalid", config.read_text(encoding="utf-8"))

    def test_failed_subprocess_is_not_retried_and_uses_argument_array(self):
        with patch("asr_agent.environment.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 6, "", "network failure")
            result = run_process(self.project, ["node.exe", "file with spaces.mjs", "--help"])
        self.assertEqual(result.returncode, 6)
        run.assert_called_once()
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(run.call_args.args[0][1], "file with spaces.mjs")

    def test_timeout_is_not_retried(self):
        with patch("asr_agent.environment.subprocess.run", side_effect=subprocess.TimeoutExpired([], 1)) as run:
            with self.assertRaises(SetupError):
                run_process(self.project, ["node.exe"], timeout=1)
        run.assert_called_once()

    def test_missing_local_bl_does_not_fall_back_to_global(self):
        with self.assertRaises(SetupError):
            bl_command(self.project, ["--version"])

    def test_bl_command_always_disables_automatic_upgrade(self):
        self.project.bl_entry.parent.mkdir(parents=True)
        self.project.bl_entry.touch()
        manifest = self.project.path(".tools/bailian/node_modules/bailian-cli/package.json")
        manifest.write_text(json.dumps({"version": BAILIAN_VERSION}), encoding="utf-8")
        with patch("asr_agent.environment.find_node", return_value=self.project.root / "node.exe"):
            command = bl_command(self.project, ["speech", "recognize", "--dry-run"])
        self.assertIn("--quiet", command)
        self.assertEqual(command[1], str(self.project.bl_entry))

    def test_bootstrap_requires_lock_before_installing(self):
        with patch("asr_agent.bootstrap.check_node", return_value=(self.project.root / "node.exe", "v24.19.0")), \
             patch("asr_agent.bootstrap.npm_entry", return_value=self.project.root / "npm-cli.js"):
            with self.assertRaisesRegex(SetupError, "锁文件"):
                bootstrap(self.project)
        self.assertFalse(self.project.path(".venv").exists())

    def test_metadata_alone_cannot_mark_incomplete_installation_ready(self):
        with patch("asr_agent.environment.bl_command", return_value=["node.exe", "bl.mjs", "--version", "--quiet"]), \
             patch("asr_agent.environment.run_process", return_value=subprocess.CompletedProcess([], 1, "", "missing dependency")) as run:
            with self.assertRaisesRegex(SetupError, "不完整"):
                verify_bl_installation(self.project)
        run.assert_called_once()

    def test_doctor_reports_python_version_drift(self):
        shutil.copyfile(ROOT / "requirements.txt", self.project.path("requirements.txt"))
        python = self.project.path(".venv/Scripts/python.exe")
        python.parent.mkdir(parents=True)
        python.touch()
        packages = {"av": "0.0.0", "python-dotenv": "1.2.3", "openpyxl": "3.1.5",
                    "et-xmlfile": "2.0.0", "defusedxml": "0.7.1"}
        with patch("asr_agent.environment.check_node", side_effect=SetupError("test Node unavailable")), \
             patch("asr_agent.environment.installed_bl_version", return_value=None), \
             patch("asr_agent.environment.run_process", return_value=subprocess.CompletedProcess([], 0, json.dumps(packages), "")):
            report = doctor(self.project)
        self.assertEqual(report["python_packages"], packages)
        self.assertTrue(any("av" in issue and "18.1.0" in issue for issue in report["issues"]))

    def test_doctor_reports_corrupt_bl_metadata_without_aborting(self):
        manifest = self.project.path(".tools/bailian/node_modules/bailian-cli/package.json")
        manifest.parent.mkdir(parents=True)
        manifest.write_text("[]", encoding="utf-8")
        with patch("asr_agent.environment.check_node", side_effect=SetupError("test Node unavailable")):
            report = doctor(self.project)
        self.assertTrue(any("包信息损坏" in issue for issue in report["issues"]))

    def test_dependency_probe_rejects_malformed_report(self):
        python = self.project.path(".venv/Scripts/python.exe")
        python.parent.mkdir(parents=True)
        python.touch()
        for output in ("not JSON", "[]", '{"av": null}', '{}'):
            with self.subTest(output=output), \
                 patch("asr_agent.environment.run_process", return_value=subprocess.CompletedProcess([], 0, output, "")):
                with self.assertRaisesRegex(SetupError, "依赖检查返回异常"):
                    installed_python_versions(self.project, {"av": "18.1.0"})

    def test_dependency_lock_requires_exact_versions_and_hashes(self):
        path = self.project.path("requirements.txt")
        for content in ("", "av>=18.0.0", "av==18.1.0"):
            with self.subTest(content=content):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(SetupError):
                    locked_python_versions(self.project)

    def test_probe_refuses_existing_configuration_without_reading(self):
        config = self.project.path(".state/bailian-probe/config.json")
        config.parent.mkdir(parents=True)
        config.write_text("not JSON: must not be read", encoding="utf-8")
        with self.assertRaisesRegex(SetupError, "配置/凭据"):
            probe(self.project)

    def test_probe_uses_only_reserved_url_and_dedicated_environment(self):
        from asr_agent import MODEL
        payload = {"request": {
            "model": MODEL,
            "input": {"file_urls": [SYNTHETIC_AUDIO_URL], "context": [{"content": [{"text": "本地合约探针"}]}]},
            "parameters": {"diarization_enabled": True, "speaker_count": 3,
                           "language_hints": ["zh"], "vocabulary": {"测试术语": 4}},
        }}
        outputs = [
            subprocess.CompletedProcess([], 0, "bl 2.1.0\n", ""),
            *[subprocess.CompletedProcess([], 0, "", "Usage: test") for _ in range(3)],
            subprocess.CompletedProcess([], 0, json.dumps(payload), ""),
        ]
        with patch("asr_agent.probe.bl_command", side_effect=lambda project, args: ["node.exe", *args, "--quiet"]), \
             patch("asr_agent.probe.run_process", side_effect=outputs) as run:
            self.assertEqual(probe(self.project)["status"], "passed")
        for call in run.call_args_list:
            self.assertTrue(call.kwargs["probe_mode"])
        request_args = run.call_args_list[-1].args[1]
        self.assertEqual(request_args[request_args.index("--url") + 1], SYNTHETIC_AUDIO_URL)
        self.assertEqual(request_args[request_args.index("--language") + 1], "zh")
        self.assertEqual(request_args[request_args.index("--speaker-count") + 1], "3")
