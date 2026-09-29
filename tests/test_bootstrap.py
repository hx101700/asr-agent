import json
import shutil
import subprocess
import tomllib
from unittest.mock import patch

from asr_agent import BAILIAN_VERSION
from asr_agent.bootstrap import bootstrap
from asr_agent.environment import SetupError, locked_python_versions
from tests.support import ProjectTestCase, ROOT


class BootstrapTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "tools/bailian", self.project.path("tools/bailian"))
        shutil.copyfile(ROOT / "requirements.txt", self.project.path("requirements.txt"))
        python = self.project.path(".venv/Scripts/python.exe")
        python.parent.mkdir(parents=True)
        python.touch()
        self.project.path(".venv/pyvenv.cfg").touch()
        self.project.path(".venv/Lib/site-packages/pip").mkdir(parents=True)
        self.project.bl_entry.parent.mkdir(parents=True)
        self.project.bl_entry.touch()
        self.manifest = self.project.path(".tools/bailian/node_modules/bailian-cli/package.json")
        self.manifest.write_text(json.dumps({"version": BAILIAN_VERSION}), encoding="utf-8")
        for name, value in (
            ("check_node", (self.project.root / "node.exe", "v24.19.0")),
            ("npm_entry", self.project.root / "npm-cli.js"),
            ("verify_bl_installation", None),
        ):
            patcher = patch(f"asr_agent.bootstrap.{name}", return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.expected = locked_python_versions(self.project)

    def test_complete_environment_skips_pip_and_npm_install(self):
        with patch("asr_agent.bootstrap.installed_python_versions", return_value=self.expected), \
             patch("asr_agent.bootstrap.run_process", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            report = bootstrap(self.project)
        self.assertEqual(report["status"], "already_installed")
        self.assertEqual(run.call_count, 1)  # 仅检查现有venv的Python版本。
        self.assertNotIn("pip", run.call_args.args[1])

    def test_package_metadata_matches_the_runtime_lock(self):
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        declared = dict(item.split("==", 1) for item in metadata["project"]["dependencies"])
        self.assertEqual(declared, locked_python_versions(self.project))

    def test_conflicting_bl_is_rejected_before_python_mutation(self):
        self.manifest.write_text(json.dumps({"version": "0.0.0"}), encoding="utf-8")
        with patch("asr_agent.bootstrap.run_process") as run:
            with self.assertRaisesRegex(SetupError, "BL安装不匹配"):
                bootstrap(self.project)
        run.assert_not_called()
        self.assertFalse(self.project.path(".runtime").exists())

    def test_corrupt_lock_stops_before_install(self):
        self.project.path("tools/bailian/package-lock.json").write_text("[]", encoding="utf-8")
        with patch("asr_agent.bootstrap.run_process") as run:
            with self.assertRaisesRegex(SetupError, "锁文件"):
                bootstrap(self.project)
        run.assert_not_called()

    def test_python_install_is_followed_by_version_and_import_check(self):
        with patch("asr_agent.bootstrap.installed_python_versions", side_effect=[None, self.expected]) as inspect, \
             patch("asr_agent.bootstrap.run_process", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            bootstrap(self.project)
        self.assertEqual(inspect.call_count, 2)
        install_args = run.call_args_list[1].args[1]
        self.assertIn("--require-hashes", install_args)
        self.assertEqual(install_args[install_args.index("--retries") + 1], "0")
        self.assertEqual(run.call_count, 2)

    def test_pip_success_without_working_dependencies_is_not_success(self):
        with patch("asr_agent.bootstrap.installed_python_versions", return_value=None), \
             patch("asr_agent.bootstrap.run_process", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            with self.assertRaisesRegex(SetupError, "依赖校验失败"):
                bootstrap(self.project)
        self.assertEqual(run.call_count, 2)

    def test_pip_failure_stops_without_retry_or_npm_install(self):
        outputs = [subprocess.CompletedProcess([], 0, "", ""),
                   subprocess.CompletedProcess([], 1, "synthetic install failure", "")]
        with patch("asr_agent.bootstrap.installed_python_versions", return_value=None), \
             patch("asr_agent.bootstrap.run_process", side_effect=outputs) as run:
            with self.assertRaisesRegex(SetupError, "Python依赖安装失败"):
                bootstrap(self.project)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(self.project.path(".runtime/python-install.log").read_text(encoding="utf-8"),
                         "synthetic install failure")
