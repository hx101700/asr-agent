import json
import shutil
import subprocess
import tomllib
from unittest.mock import patch

from asr_agent import BAILIAN_VERSION
from asr_agent.application.bootstrap import bootstrap
from asr_agent.tools.environment import SetupError, locked_python_versions
from tests.support import ProjectTestCase, ROOT


class BootstrapTests(ProjectTestCase):
    def setUp(self):
        """准备依赖锁、安装目录和命令替身。"""
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
            ("check_python", None),
            ("check_node", (self.project.root / "node.exe", "v24.19.0")),
            ("npm_entry", self.project.root / "npm-cli.js"),
            ("verify_bl_installation", None),
        ):
            patcher = patch(f"asr_agent.application.bootstrap.{name}", return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.expected = locked_python_versions(self.project)

    def test_complete_environment_skips_pip_and_npm_install(self):
        """验证完整环境跳过pip和npm安装。"""
        with patch("asr_agent.application.bootstrap.installed_python_versions", return_value=self.expected), \
             patch("asr_agent.application.bootstrap.npm_entry", side_effect=AssertionError("已有BL不需要npm")), \
             patch("asr_agent.application.bootstrap.run_process", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            report = bootstrap(self.project)
        self.assertEqual(report["status"], "already_installed")
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("pip", run.call_args.args[1])

    def test_package_metadata_matches_the_runtime_lock(self):
        """验证包元信息与运行时锁定版本一致。"""
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        declared = dict(item.split("==", 1) for item in metadata["project"]["dependencies"])
        self.assertEqual(declared, self.expected)

    def test_conflicting_bl_is_rejected_before_python_mutation(self):
        """验证BL版本冲突在修改Python环境前停止。"""
        self.manifest.write_text(json.dumps({"version": "0.0.0"}), encoding="utf-8")
        with patch("asr_agent.application.bootstrap.run_process") as run:
            with self.assertRaisesRegex(SetupError, "BL安装不匹配"):
                bootstrap(self.project)
        run.assert_not_called()
        self.assertFalse(self.project.path(".runtime").exists())

    def test_corrupt_lock_stops_before_install(self):
        """验证损坏依赖锁在安装前停止。"""
        self.project.path("tools/bailian/package-lock.json").write_text("[]", encoding="utf-8")
        with patch("asr_agent.application.bootstrap.run_process") as run:
            with self.assertRaisesRegex(SetupError, "锁文件"):
                bootstrap(self.project)
        run.assert_not_called()

    def test_python_install_is_followed_by_dependency_check(self):
        """验证Python安装完成后检查实际依赖。"""
        with patch("asr_agent.application.bootstrap.installed_python_versions", side_effect=[None, self.expected]) as inspect, \
             patch("asr_agent.application.bootstrap.run_process", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            bootstrap(self.project)
        self.assertEqual(inspect.call_count, 2)
        install_args = run.call_args_list[1].args[1]
        self.assertIn("--require-hashes", install_args)
        self.assertEqual(install_args[install_args.index("--retries") + 1], "0")
        self.assertEqual(install_args[install_args.index("--timeout") + 1], "120")
        self.assertEqual(install_args[install_args.index("--index-url") + 1],
                         "https://mirrors.aliyun.com/pypi/simple/")
        self.assertEqual(run.call_count, 2)

    def test_pip_success_without_working_dependencies_is_not_success(self):
        """验证pip成功但依赖检查失败时返回安装错误。"""
        with patch("asr_agent.application.bootstrap.installed_python_versions", return_value=None), \
             patch("asr_agent.application.bootstrap.run_process", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            with self.assertRaisesRegex(SetupError, "依赖校验失败"):
                bootstrap(self.project)
        self.assertEqual(run.call_count, 2)

    def test_pip_failure_stops_without_retry_or_npm_install(self):
        """验证pip失败后结束安装流程且调用次数为一。"""
        outputs = [subprocess.CompletedProcess([], 0, "", ""),
                   subprocess.CompletedProcess([], 1, "synthetic install failure", "")]
        with patch("asr_agent.application.bootstrap.installed_python_versions", return_value=None), \
             patch("asr_agent.application.bootstrap.run_process", side_effect=outputs) as run:
            with self.assertRaisesRegex(SetupError, "Python依赖安装失败"):
                bootstrap(self.project)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(self.project.path(".runtime/python-install.log").read_text(encoding="utf-8"),
                         "synthetic install failure")

    def test_installs_hash_locked_mirror_dependencies_and_native_npm_lock(self):
        """验证通过镜像及摘要锁安装Python和npm依赖。"""
        shutil.rmtree(self.project.bl_directory)
        node = self.project.root / "node.exe"
        npm = self.project.root / "npm-cli.js"
        python = self.project.path(".venv/Scripts/python.exe")
        calls = []

        def run(_project, argv, timeout=60, **_kwargs):
            """记录安装命令并模拟对应依赖落盘。"""
            calls.append((argv, timeout))
            if argv[0] == str(python) and "sysconfig" in " ".join(argv):
                return subprocess.CompletedProcess(argv, 0, "", "")
            if "--version" in argv:
                return subprocess.CompletedProcess(argv, 0, f"bl {BAILIAN_VERSION}\n", "")
            if "ci" in argv:
                entry = self.project.bl_entry
                entry.parent.mkdir(parents=True, exist_ok=True)
                entry.touch()
                manifest = entry.parents[1] / "package.json"
                manifest.write_text(json.dumps({"version": BAILIAN_VERSION}), encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with patch("asr_agent.application.bootstrap.check_python"), \
             patch("asr_agent.application.bootstrap.check_node", return_value=(node, "v24.0.0")), \
             patch("asr_agent.application.bootstrap.npm_entry", return_value=npm), \
             patch("asr_agent.application.bootstrap.venv.EnvBuilder.create", side_effect=lambda path: (
                 python.parent.mkdir(parents=True),
                 (path / "pyvenv.cfg").write_text("home = python\\n", encoding="utf-8"),
                 python.touch(),
             )), \
             patch("asr_agent.application.bootstrap.installed_python_versions", side_effect=[None, self.expected]), \
             patch("asr_agent.application.bootstrap.verify_bl_installation") as verify, \
             patch("asr_agent.application.bootstrap.run_process", side_effect=run):
            result = bootstrap(self.project)

        self.assertEqual(result["status"], "installed")
        verify.assert_called_once_with(self.project)
        pip = next(argv for argv, _ in calls if "--require-hashes" in argv)
        self.assertIn("--require-hashes", pip)
        self.assertIn("--retries", pip)
        self.assertEqual(pip[pip.index("--retries") + 1], "0")
        self.assertEqual(pip[pip.index("--index-url") + 1], "https://mirrors.aliyun.com/pypi/simple/")
        npm_command = next(argv for argv, _ in calls if "ci" in argv)
        self.assertEqual(npm_command[:3], [str(node), str(npm), "ci"])
        self.assertIn("--prefix", npm_command)
        self.assertIn("--fetch-retries=0", npm_command)
        self.assertEqual(next(timeout for argv, timeout in calls if "ci" in argv), None)

    def test_existing_nonempty_destination_stops_without_retry(self):
        """验证非空BL目标目录保留原内容并拒绝安装。"""
        destination = self.project.bl_directory
        shutil.rmtree(destination)
        destination.mkdir(parents=True)
        (destination / "partial").touch()
        with patch("asr_agent.application.bootstrap.check_python"), \
             patch("asr_agent.application.bootstrap.check_node", return_value=(self.project.root / "node.exe", "v24.0.0")), \
             patch("asr_agent.application.bootstrap.npm_entry", return_value=self.project.root / "npm.js"), \
             patch("asr_agent.application.bootstrap.run_process") as run:
            with self.assertRaisesRegex(SetupError, "非空"):
                bootstrap(self.project)
        run.assert_not_called()
