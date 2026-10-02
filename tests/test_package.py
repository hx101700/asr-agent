import posixpath
from pathlib import Path
import re
import shutil
import subprocess
import sys
from unittest.mock import patch
from zipfile import ZipFile

from scripts.build_zip import REQUIRED_FILES, RELEASE_TEMPLATES, build_zip
from tests.support import ProjectTestCase, ROOT


class PackageTests(ProjectTestCase):
    def setUp(self):
        """准备构建器和工作区内的发行测试目录。"""
        super().setUp()
        # 用没有 Git 的独立源码树验证白名单，不依赖开发目录的忽略规则。
        self.source = self.project.path("中文 源码目录")
        for relative in (*REQUIRED_FILES, *RELEASE_TEMPLATES.values()):
            destination = self.source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)

    def test_release_contains_only_manifest_and_user_templates(self):
        """验证ZIP内容与发行清单和用户模板一致。"""
        excluded = (
            ".env", "data/audio/private.mp3", "outputs/job/transcription.md",
            ".state/jobs/config.json", ".venv/Lib/site-packages/private.py",
            ".tools/node/node.exe", ".runtime/result.md", "dist/old.zip",
            "doc/private.md", "src/asr_agent/job/private.py", "src/asr_agent/debug.py",
            "src/asr_agent/static/debug.mjs", "src/asr_agent/static/job/private.mjs",
            "tests/test_package.py", "tests/job/private.py", "pyproject.toml",
            "scripts/build_zip.py", "doc/README.md", "doc/STATUS.md", "doc/DEVLOG.md",
            "doc/ISSUES.md", "doc/DEVELOPMENT.md", "doc/ACCEPTANCE.md",
            ".agents/private/SKILL.md", "tools/bailian/node_modules/private.js",
            "tools/bailian/bailian-runtime.tgz", "tools/bailian/runtime-manifest.json",
            "tools/python-wheels/dependency.whl", "tools/runtime-assets/python.zip",
            "tools/python-wheels/av-18.1.0-cp311-abi3-win_amd64.whl",
            "tools/runtime-assets.json", "scripts/install.ps1",
            "scripts/prepare_bailian_bundle.py",
            "src/asr_agent/transcription.py", "src/asr_agent/validation.py",
            "src/asr_agent/session.py", "src/asr_agent/environment.py",
            "src/asr_agent/bailian.py", "src/asr_agent/media.py",
        )
        for relative in excluded:
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic-private-marker", encoding="utf-8")
        for name in RELEASE_TEMPLATES:
            (self.source / name).write_text("developer-only-marker", encoding="utf-8")

        report = build_zip(self.source)
        self.assertEqual(Path(report["path"]), self.source / "dist/asr-agent.zip")
        with ZipFile(report["path"]) as archive:
            names = archive.namelist()
            self.assertEqual(names, report["files"])
            self.assertEqual(len(names), report["file_count"])
            self.assertTrue(all(name.startswith("asr-agent/") for name in names))
            self.assertEqual(set(names), {f"asr-agent/{name}" for name in (*REQUIRED_FILES, *RELEASE_TEMPLATES)})
            for name in ("README.md", "README.en.md", "AGENTS.md", "AGENTS.en.md"):
                self.assertIn(f"asr-agent/{name}", names)
            for relative in REQUIRED_FILES:
                self.assertIn(f"asr-agent/{relative}", names)
            for relative in excluded:
                self.assertNotIn(f"asr-agent/{relative}", names)
            for name, source in RELEASE_TEMPLATES.items():
                self.assertEqual(archive.read(f"asr-agent/{name}"), (self.source / source).read_bytes())
            self.assertTrue(all(archive.read(name) != b"synthetic-private-marker" for name in names))
            self.assertTrue(all(archive.read(name) != b"developer-only-marker" for name in names))

    def test_existing_zip_is_not_overwritten(self):
        """验证ZIP已存在时保留原文件并拒绝构建。"""
        destination = self.project.path("existing.zip")
        destination.write_bytes(b"previous-package")
        with self.assertRaises(FileExistsError):
            build_zip(self.source, destination)
        self.assertEqual(destination.read_bytes(), b"previous-package")

    def test_missing_skill_stops_before_creating_archive(self):
        """验证缺少Skill时返回构建错误。"""
        (self.source / ".agents/skills/asr-agent/SKILL.md").unlink()
        with self.assertRaises(FileNotFoundError):
            build_zip(self.source)
        self.assertFalse((self.source / "dist").exists())

    def test_missing_release_instructions_stop_before_creating_archive(self):
        """验证缺少发行说明时返回构建错误。"""
        (self.source / "release/AGENTS.md").unlink()
        with self.assertRaises(FileNotFoundError):
            build_zip(self.source)
        self.assertFalse((self.source / "dist").exists())

    def test_redirected_source_file_is_rejected(self):
        """验证运行源文件重定向时拒绝打包。"""
        redirected = self.source / "requirements.txt"
        outside = self.project.path("outside.md")
        outside.write_text("synthetic-private-marker", encoding="utf-8")
        original_resolve = Path.resolve

        def resolve(path, *args, **kwargs):
            """模拟源文件解析到发行范围之外。"""
            return outside if path == redirected else original_resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve):
            with self.assertRaisesRegex(ValueError, "发行文件不是普通文件"):
                build_zip(self.source)
        self.assertFalse((self.source / "dist").exists())

    def test_redirected_release_template_is_rejected(self):
        """验证发行模板重定向时拒绝打包。"""
        redirected = self.source / "release/AGENTS.md"
        outside = self.project.path("outside-instructions.md")
        outside.write_text("synthetic-private-marker", encoding="utf-8")
        original_resolve = Path.resolve

        def resolve(path, *args, **kwargs):
            """模拟发行模板解析到发行范围之外。"""
            return outside if path == redirected else original_resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve):
            with self.assertRaisesRegex(ValueError, "发行文件不是普通文件"):
                build_zip(self.source)
        self.assertFalse((self.source / "dist").exists())

    def test_extracted_chinese_space_path_runs_without_git_or_site_packages(self):
        """验证中文空格路径下解压包入口成功显示命令帮助。"""
        report = build_zip(self.source)
        unpacked = self.project.path("解压 验收目录")
        with ZipFile(report["path"]) as archive:
            archive.extractall(unpacked)
        project = unpacked / "asr-agent"
        self.assertFalse((project / ".git").exists())
        result = subprocess.run(
            [sys.executable, "-S", "-X", "utf8", "scripts/asr.py", "--help"],
            cwd=project, capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("bootstrap", result.stdout)
        self.assertIn("transcribe", result.stdout)
        for relative in ("tests", "scripts/build_zip.py", "pyproject.toml", "doc/STATUS.md",
                         "src/asr_agent/transcription.py", "src/asr_agent/validation.py"):
            self.assertFalse((project / relative).exists())

    def test_extracted_runtime_imports_use_only_the_release_source(self):
        """验证解压后的运行模块从发行包加载。"""
        report = build_zip(self.source)
        unpacked = self.project.path("运行 验收目录")
        with ZipFile(report["path"]) as archive:
            archive.extractall(unpacked)
        project = unpacked / "asr-agent"
        script = (
            "import importlib, pathlib, sys; "
            "root=pathlib.Path('src').resolve(); sys.path.insert(0,str(root)); "
            "modules=[importlib.import_module('asr_agent.'+name) for name in "
            "['__main__','web','application.transcription','application.inputs','tools.media','tools.documents']]; "
            "assert all(pathlib.Path(module.__file__).is_relative_to(root) for module in modules)"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-X", "utf8", "-c", script],
            cwd=project, capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_release_markdown_links_resolve_inside_archive(self):
        """验证发行Markdown链接都指向包内文件。"""
        report = build_zip(self.source)
        with ZipFile(report["path"]) as archive:
            names = set(archive.namelist())
            for name in sorted(names):
                if not name.endswith(".md"):
                    continue
                for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", archive.read(name).decode("utf-8")):
                    if target.startswith(("https://", "http://", "#")):
                        continue
                    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target.split("#")[0]))
                    self.assertIn(resolved, names, f"{name} 指向发行包中不存在的 {target}")
