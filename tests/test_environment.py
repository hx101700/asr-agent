import contextlib
import io
import json
import os
import subprocess
import shutil
from unittest.mock import patch

from asr_agent import BAILIAN_VERSION
from asr_agent.application.bootstrap import bootstrap
from asr_agent.tools.environment import SetupError, child_environment, check_python, find_node, installed_python_versions, locked_python_versions, run_process
from asr_agent.tools.bailian import bl_command, verify_bl_installation
from asr_agent.application.diagnostics import doctor
from scripts.probe_bl import SYNTHETIC_AUDIO_URL, probe
from scripts.probe_bl import main as probe_main
from asr_agent.__main__ import main as runtime_main
from tests.support import ProjectTestCase, ROOT


class EnvironmentTests(ProjectTestCase):
    def test_runtime_cli_rejects_development_probe(self):
        """验证用户命令入口拒绝开发合约探针。"""
        with contextlib.redirect_stderr(io.StringIO()) as error:
            with self.assertRaises(SystemExit) as stopped:
                runtime_main(["probe-bl"])
        self.assertEqual(stopped.exception.code, 2)
        self.assertIn("invalid choice", error.getvalue())

    def test_development_probe_rejects_audio_arguments(self):
        """验证开发探针的独立入口拒绝外部音频参数。"""
        with patch("scripts.probe_bl.probe") as run, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                probe_main(["--url", "https://example.invalid/another.wav"])
        self.assertEqual(stopped.exception.code, 2)
        run.assert_not_called()

    def test_python_runtime_matches_locked_binary_wheels(self):
        """验证Python平台与锁定二进制依赖匹配。"""
        for version, platform in (((3, 12, 1), "win-amd64"), ((3, 13, 0), "win-amd64"),
                                  ((3, 12, 1), "win32"), ((3, 12, 1), "win-arm64")):
            with self.subTest(version=version, platform=platform), \
                 patch("asr_agent.tools.environment.sys.version_info", version), \
                 patch("asr_agent.tools.environment.sysconfig.get_platform", return_value=platform):
                if version[:2] == (3, 12) and platform == "win-amd64":
                    check_python()
                else:
                    with self.assertRaisesRegex(SetupError, "CPython 3.12"):
                        check_python()

    def test_paths_cannot_leave_project(self):
        """验证项目外路径返回范围错误。"""
        with self.assertRaises(SetupError):
            self.project.path("../outside")

    def test_child_does_not_inherit_credentials_or_node_injection(self):
        """验证子进程环境按白名单隔离凭据和注入项。"""
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
        """验证探针与登录状态使用独立目录。"""
        normal = child_environment(self.project)
        isolated = child_environment(self.project, probe_mode=True)
        self.assertNotEqual(normal["BAILIAN_CONFIG_DIR"], isolated["BAILIAN_CONFIG_DIR"])

    def test_nonempty_npm_configuration_is_not_overwritten(self):
        """验证npm隔离配置冲突时保留原内容并报错。"""
        self.project.prepare()
        config = self.project.path(".runtime/npm-user.npmrc")
        config.write_text("registry=https://example.invalid\n", encoding="utf-8")
        with self.assertRaises(SetupError):
            self.project.prepare()
        self.assertIn("example.invalid", config.read_text(encoding="utf-8"))

    def test_failed_subprocess_is_not_retried_and_uses_argument_array(self):
        """验证子进程返回失败退出码且按参数数组调用一次。"""
        with patch("asr_agent.tools.environment.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 6, "", "network failure")
            result = run_process(self.project, ["node.exe", "file with spaces.mjs", "--help"])
        self.assertEqual(result.returncode, 6)
        run.assert_called_once()
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(run.call_args.args[0][1], "file with spaces.mjs")

    def test_timeout_is_not_retried(self):
        """验证子进程超时返回环境错误且调用次数为一。"""
        with patch("asr_agent.tools.environment.subprocess.run", side_effect=subprocess.TimeoutExpired([], 1)) as run:
            with self.assertRaises(SetupError):
                run_process(self.project, ["node.exe"], timeout=1)
        run.assert_called_once()

    def test_missing_local_bl_does_not_fall_back_to_global(self):
        """验证缺少项目内BL时返回安装错误。"""
        with self.assertRaises(SetupError):
            bl_command(self.project, ["--version"])

    def test_bl_command_always_disables_automatic_upgrade(self):
        """验证BL命令携带quiet参数。"""
        self.project.bl_entry.parent.mkdir(parents=True)
        self.project.bl_entry.touch()
        manifest = self.project.path(".tools/bailian/node_modules/bailian-cli/package.json")
        manifest.write_text(json.dumps({"version": BAILIAN_VERSION}), encoding="utf-8")
        with patch("asr_agent.tools.bailian.find_node", return_value=self.project.root / "node.exe") as find:
            command = bl_command(self.project, ["speech", "recognize", "--dry-run"])
        find.assert_called_once_with()
        self.assertIn("--quiet", command)
        self.assertEqual(command[1], str(self.project.bl_entry))

    def test_bootstrap_requires_lock_before_installing(self):
        """验证安装前必须存在依赖锁。"""
        with patch("asr_agent.application.bootstrap.check_node", return_value=(self.project.root / "node.exe", "v24.19.0")), \
             patch("asr_agent.application.bootstrap.npm_entry", return_value=self.project.root / "npm-cli.js"):
            with self.assertRaisesRegex(SetupError, "锁文件"):
                bootstrap(self.project)
        self.assertFalse(self.project.path(".venv").exists())

    def test_node_requires_existing_path_installation(self):
        """验证Node必须来自已有本机安装。"""
        with patch("asr_agent.tools.environment.shutil.which", return_value=None) as which:
            with self.assertRaisesRegex(SetupError, "未找到Node.js"):
                find_node()
        which.assert_called_once_with("node")

    def test_release_preparation_can_find_existing_node(self):
        """验证发行准备能够找到已安装Node。"""
        node = self.project.root / "existing/node.exe"
        with patch("asr_agent.tools.environment.shutil.which", return_value=str(node)):
            self.assertEqual(find_node(), node.resolve())

    def test_doctor_does_not_require_npm(self):
        """验证环境诊断直接检查已安装的BL和Python依赖。"""
        node = self.project.root / "node.exe"
        with patch("asr_agent.application.diagnostics.check_node", return_value=(node, "v24.19.0")):
            report = doctor(self.project)
        self.assertEqual(report["node"], {"path": str(node), "version": "v24.19.0"})

    def test_metadata_alone_cannot_mark_incomplete_installation_ready(self):
        """验证BL入口启动失败被报告为安装异常。"""
        with patch("asr_agent.tools.bailian.bl_command", return_value=["node.exe", "bl.mjs", "--version", "--quiet"]), \
             patch("asr_agent.tools.bailian.run_process", return_value=subprocess.CompletedProcess([], 1, "", "missing dependency")) as run:
            with self.assertRaisesRegex(SetupError, "不完整"):
                verify_bl_installation(self.project)
        run.assert_called_once()

    def test_doctor_reports_python_version_drift(self):
        """验证环境诊断报告Python依赖版本偏差。"""
        shutil.copyfile(ROOT / "requirements.txt", self.project.path("requirements.txt"))
        python = self.project.path(".venv/Scripts/python.exe")
        python.parent.mkdir(parents=True)
        python.touch()
        packages = {**locked_python_versions(self.project), "av": "0.0.0"}
        with patch("asr_agent.application.diagnostics.check_node", side_effect=SetupError("test Node unavailable")), \
             patch("asr_agent.application.diagnostics.installed_bl_version", return_value=None), \
             patch("asr_agent.tools.environment.run_process", return_value=subprocess.CompletedProcess([], 0, json.dumps(packages), "")):
            report = doctor(self.project)
        self.assertEqual(report["python_packages"], packages)
        self.assertTrue(any("av" in issue and "18.1.0" in issue for issue in report["issues"]))

    def test_doctor_reports_corrupt_bl_metadata_without_aborting(self):
        """验证损坏BL元信息加入诊断问题列表。"""
        manifest = self.project.path(".tools/bailian/node_modules/bailian-cli/package.json")
        manifest.parent.mkdir(parents=True)
        manifest.write_text("[]", encoding="utf-8")
        with patch("asr_agent.application.diagnostics.check_node", side_effect=SetupError("test Node unavailable")):
            report = doctor(self.project)
        self.assertTrue(any("包信息损坏" in issue for issue in report["issues"]))

    def test_dependency_probe_rejects_malformed_report(self):
        """验证依赖探针拒绝异常返回结构。"""
        python = self.project.path(".venv/Scripts/python.exe")
        python.parent.mkdir(parents=True)
        python.touch()
        for output in ("not JSON", "[]", '{"av": null}', '{}'):
            with self.subTest(output=output), \
                 patch("asr_agent.tools.environment.run_process", return_value=subprocess.CompletedProcess([], 0, output, "")):
                with self.assertRaisesRegex(SetupError, "依赖检查返回异常"):
                    installed_python_versions(self.project, {"av": "18.1.0"})

    def test_dependency_lock_requires_exact_versions_and_hashes(self):
        """验证依赖锁必须使用精确版本和摘要。"""
        path = self.project.path("requirements.txt")
        for content in ("", "av>=18.0.0", "av==18.1.0"):
            with self.subTest(content=content):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(SetupError):
                    locked_python_versions(self.project)

    def test_probe_refuses_existing_configuration_without_reading(self):
        """验证探针发现既有配置后返回配置冲突。"""
        config = self.project.path(".state/bailian-probe/config.json")
        config.parent.mkdir(parents=True)
        config.write_text("not JSON: must not be read", encoding="utf-8")
        with self.assertRaisesRegex(SetupError, "配置/凭据"):
            probe(self.project)

    def test_probe_uses_only_reserved_url_and_dedicated_environment(self):
        """验证探针使用虚构URL及独立环境。"""
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
        with patch("scripts.probe_bl.bl_command", side_effect=lambda project, args: ["node.exe", *args, "--quiet"]), \
             patch("scripts.probe_bl.run_process", side_effect=outputs) as run:
            self.assertEqual(probe(self.project)["status"], "passed")
        for call in run.call_args_list:
            self.assertTrue(call.kwargs["probe_mode"])
        request_args = run.call_args_list[-1].args[1]
        self.assertEqual(request_args[request_args.index("--url") + 1], SYNTHETIC_AUDIO_URL)
        self.assertEqual(request_args[request_args.index("--language") + 1], "zh")
        self.assertEqual(request_args[request_args.index("--speaker-count") + 1], "3")
