"""验证发行 ZIP 更新边界、运行占用和目录替换回滚。"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest import skipUnless
from unittest.mock import patch
from zipfile import BadZipFile, ZipFile, ZipInfo

from update_skill import main, update_skill
from tests.support import RuntimeTestCase, SKILL_ROOT


@skipUnless(os.name == "nt", "发行更新目前只支持 Windows")
class SkillUpdateTests(RuntimeTestCase):
    def setUp(self):
        """准备独立的安装目录、新包和不应被更新器改动的用户数据。"""
        super().setUp()
        self.installed = self.temporary_root / "skills" / "asr-transcription"
        (self.installed / "scripts/bailian").mkdir(parents=True)
        (self.installed / "SKILL.md").write_text(
            "---\nname: asr-transcription\ndescription: test\n---\n", encoding="utf-8")
        shutil.copyfile(SKILL_ROOT / "scripts/asr.py", self.installed / "scripts/asr.py")
        (self.installed / "scripts/requirements.txt").write_bytes(b"av==18.1.0\n")
        (self.installed / "scripts/bailian/package-lock.json").write_text("{}")
        (self.installed / "old-resource.txt").write_text("old file")
        self.archive = self.temporary_root / "新版发行包.zip"
        self.files = {
            "SKILL.md": (self.installed / "SKILL.md").read_bytes(),
            "scripts/asr.py": b"print('new entry')\n",
            "scripts/requirements.txt": b"av==18.1.0\n",
            "scripts/bailian/package-lock.json": b"{}",
        }
        for relative, content in {
            ".env": b"DASHSCOPE_API_KEY=synthetic-secret",
            ".state/jobs/job/config.json": b'{"status":"CONFIGURED"}',
            ".venv/pyvenv.cfg": b"synthetic environment",
        }.items():
            path = self.runtime.path(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.user_data = {path: path.read_bytes() for path in self.runtime.root.rglob("*") if path.is_file()}

    def write_archive(self, extra=None):
        """写入本例发行内容及指定测试条目。"""
        with ZipFile(self.archive, "w") as archive:
            for name, content in self.files.items():
                archive.writestr(name, content)
            if extra:
                for name, content in extra:
                    if isinstance(name, str):
                        info = ZipInfo()
                        info.filename = name
                    else:
                        info = name
                    archive.writestr(info, content)

    def test_update_replaces_resources_and_preserves_workspace(self):
        """完整替换旧资源并逐字节保留工作目录的数据。"""
        self.write_archive()
        report = update_skill(self.archive, self.installed, tasks_finished=True)
        self.assertEqual(report["status"], "updated")
        self.assertFalse(report["dependencies_changed"])
        self.assertIsNone(report["retained_backup"])
        self.assertFalse((self.installed / "old-resource.txt").exists())
        self.assertEqual((self.installed / "scripts/asr.py").read_bytes(), self.files["scripts/asr.py"])
        self.assertEqual({path: path.read_bytes() for path in self.user_data}, self.user_data)
        self.assertEqual(list(self.installed.parent.iterdir()), [self.installed])

    def test_dependency_changes_are_reported(self):
        """依赖锁变更时通知调用方准备新版本的运行依赖。"""
        self.files["scripts/requirements.txt"] = b"av==19.0.0\n"
        self.write_archive()
        report = update_skill(self.archive, self.installed, tasks_finished=True)
        self.assertTrue(report["dependencies_changed"])

    def test_changed_python_lock_does_not_skip_a_missing_bl_lock(self):
        """验证Python锁先变化时，BL锁缺失仍在替换原目录前被拒绝。"""
        self.files["scripts/requirements.txt"] = b"av==19.0.0\n"
        del self.files["scripts/bailian/package-lock.json"]
        self.write_archive()
        with patch.object(Path, "rename") as rename, self.assertRaises(FileNotFoundError):
            update_skill(self.archive, self.installed, tasks_finished=True)
        rename.assert_not_called()
        self.assertTrue((self.installed / "old-resource.txt").is_file())
        self.assertEqual(list(self.installed.parent.iterdir()), [self.installed])
        self.assertEqual({path: path.read_bytes() for path in self.user_data}, self.user_data)

    def test_missing_idle_confirmation_preserves_installation(self):
        """未确认其他任务结束时停止并保留原资源。"""
        self.write_archive()
        with self.assertRaisesRegex(ValueError, "--tasks-finished"):
            update_skill(self.archive, self.installed, tasks_finished=False)
        self.assertTrue((self.installed / "old-resource.txt").is_file())
        self.assertEqual(list(self.installed.parent.iterdir()), [self.installed])

    def test_running_entry_blocks_replacement_until_process_ends(self):
        """通过真实 CLI 子进程验证运行占用阻止更新且结束后可成功更新。"""
        package = self.installed / "scripts/asr_runtime"
        package.mkdir()
        (package / "__init__.py").write_text("")
        (package / "__main__.py").write_text(
            "import sys\ndef main():\n    print('ready', flush=True)\n    sys.stdin.readline()\n    return 0\n")
        self.write_archive()
        process = subprocess.Popen(
            [sys.executable, "-S", "-B", str(self.installed / "scripts/asr.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", cwd=self.temporary_root,
        )
        try:
            assert process.stdout is not None
            self.assertEqual(process.stdout.readline().strip(), "ready")
            with self.assertRaisesRegex(ValueError, "正被任务使用"):
                update_skill(self.archive, self.installed, tasks_finished=True)
            self.assertIsNone(process.poll())
            self.assertTrue((self.installed / "old-resource.txt").is_file())
            self.assertEqual(list(self.installed.parent.iterdir()), [self.installed])
        finally:
            process.communicate(input="\n", timeout=10)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(update_skill(self.archive, self.installed, tasks_finished=True)["status"], "updated")

    def test_rejected_paths_preserve_original(self):
        """越界、链接、Windows 同名和非发行路径在替换前被拒绝。"""
        link = ZipInfo("scripts/link")
        link.external_attr = 0o120777 << 16
        for entry in ("../outside.txt", "scripts/../../outside.txt", "scripts\\outside.py",
                      "scripts/CON", "scripts/a.py:stream", "Scripts/ASR.py", ".env", link):
            with self.subTest(entry=entry):
                self.write_archive([(entry, b"outside")])
                with self.assertRaises((ValueError, OSError)):
                    update_skill(self.archive, self.installed, tasks_finished=True)
                self.assertTrue((self.installed / "old-resource.txt").is_file())
                self.assertEqual(list(self.installed.parent.iterdir()), [self.installed])
        self.assertFalse((self.temporary_root / "outside.txt").exists())

    def test_invalid_skill_name_preserves_original(self):
        """错误的 Skill 包在原目录改名前停止。"""
        self.files["SKILL.md"] = b"---\nname: another-skill\n---\n"
        self.write_archive()
        with self.assertRaisesRegex(ValueError, "asr-transcription"):
            update_skill(self.archive, self.installed, tasks_finished=True)
        self.assertTrue((self.installed / "old-resource.txt").is_file())

    def test_windows_ambiguous_components_stop_before_writing(self):
        """拒绝 Windows 会规范化或保留的路径组件，保持暂存目录外无写入。"""
        entries = (
            "scripts/.. /.. /escape.txt", "scripts/trailing./file.py", "scripts/trailing /file.py",
            "scripts/CON/file.py", "scripts/NUL.txt/file.py", "scripts/bad\x00/file.py",
            "scripts/bad\x01/file.py", "scripts/bad\x7f/file.py",
        )
        for entry in entries:
            with self.subTest(entry=entry):
                self.write_archive([(entry, b"outside")])
                with self.assertRaisesRegex(ValueError, "ZIP 含不支持的发行路径"):
                    update_skill(self.archive, self.installed, tasks_finished=True)
                self.assertTrue((self.installed / "old-resource.txt").is_file())
                self.assertEqual(list(self.installed.parent.iterdir()), [self.installed])
                self.assertEqual(list(self.temporary_root.rglob("escape.txt")), [])

    def test_corrupt_archive_preserves_original(self):
        """下载内容损坏时由 ZIP 的 CRC 校验阻止资源替换。"""
        self.write_archive()
        content = self.archive.read_bytes()
        self.archive.write_bytes(content.replace(b"print('new entry')", b"print('bad entry')", 1))
        with self.assertRaises(BadZipFile):
            update_skill(self.archive, self.installed, tasks_finished=True)
        self.assertTrue((self.installed / "old-resource.txt").is_file())
        self.assertEqual(list(self.installed.parent.iterdir()), [self.installed])

    def test_replacement_failure_restores_original(self):
        """新目录接管失败时恢复原目录并清理暂存资源。"""
        self.write_archive()
        original_rename = Path.rename

        def rename(path, destination):
            """模拟新目录接管安装位置时的文件系统错误。"""
            if path.name == "candidate":
                raise PermissionError("synthetic failure")
            return original_rename(path, destination)

        with patch.object(Path, "rename", rename), self.assertRaises(PermissionError):
            update_skill(self.archive, self.installed, tasks_finished=True)
        self.assertTrue((self.installed / "old-resource.txt").is_file())
        self.assertEqual(list(self.installed.parent.iterdir()), [self.installed])

    def test_failed_rollback_retains_backup(self):
        """回滚受阻时保留原资源副本并指出恢复位置。"""
        self.write_archive()
        original_rename = Path.rename

        def rename(path, destination):
            """模拟替换与回滚两次目录改名均受阻。"""
            if path.name in ("candidate", "previous"):
                raise PermissionError("synthetic failure")
            return original_rename(path, destination)

        with patch.object(Path, "rename", rename), self.assertRaisesRegex(RuntimeError, "原 Skill 保留在"):
            update_skill(self.archive, self.installed, tasks_finished=True)
        previous = next(self.installed.parent.glob(".asr-transcription-update-*/previous"))
        self.assertTrue((previous / "old-resource.txt").is_file())

    def test_interruption_after_original_rename_restores_original(self):
        """验证旧目录刚改名后中断仍恢复安装位置并清理候选资源。"""
        self.write_archive()
        original_rename = Path.rename

        def interrupt_after_original(path, destination):
            """完成旧目录改名后立即模拟Ctrl+C。"""
            result = original_rename(path, destination)
            if path == self.installed:
                raise KeyboardInterrupt()
            return result

        with patch.object(Path, "rename", interrupt_after_original), self.assertRaises(KeyboardInterrupt):
            update_skill(self.archive, self.installed, tasks_finished=True)
        self.assertTrue((self.installed / "old-resource.txt").is_file())
        self.assertEqual(list(self.installed.parent.iterdir()), [self.installed])
        self.assertEqual({path: path.read_bytes() for path in self.user_data}, self.user_data)

    def test_interruption_before_candidate_rename_restores_original(self):
        """验证候选目录接管前中断仍恢复旧目录。"""
        self.write_archive()
        original_rename = Path.rename

        def interrupt_candidate(path, destination):
            """在候选目录改名前模拟Ctrl+C，其余改名照常执行。"""
            if path.name == "candidate":
                raise KeyboardInterrupt()
            return original_rename(path, destination)

        with patch.object(Path, "rename", interrupt_candidate), self.assertRaises(KeyboardInterrupt):
            update_skill(self.archive, self.installed, tasks_finished=True)
        self.assertTrue((self.installed / "old-resource.txt").is_file())
        self.assertEqual(list(self.installed.parent.iterdir()), [self.installed])
        self.assertEqual({path: path.read_bytes() for path in self.user_data}, self.user_data)

    def test_interruption_after_candidate_rename_keeps_new_directory_and_backup(self):
        """验证候选资源已接管后中断不覆盖新目录，保留旧副本并报告未完成。"""
        self.write_archive()
        original_rename = Path.rename

        def interrupt_after_candidate(path, destination):
            """完成候选目录改名后立即模拟Ctrl+C。"""
            result = original_rename(path, destination)
            if path.name == "candidate":
                raise KeyboardInterrupt()
            return result

        with patch.object(Path, "rename", interrupt_after_candidate), \
                self.assertRaisesRegex(RuntimeError, "安装位置已有资源，未覆盖"):
            update_skill(self.archive, self.installed, tasks_finished=True)
        self.assertEqual((self.installed / "scripts/asr.py").read_bytes(), self.files["scripts/asr.py"])
        self.assertFalse((self.installed / "old-resource.txt").exists())
        previous = next(self.installed.parent.glob(".asr-transcription-update-*/previous"))
        self.assertTrue((previous / "old-resource.txt").is_file())
        self.assertEqual({path: path.read_bytes() for path in self.user_data}, self.user_data)

    def test_archive_inside_installation_is_preserved(self):
        """拒绝使用位于将被替换目录中的原 ZIP。"""
        self.write_archive()
        nested = self.installed / "new.zip"
        shutil.copyfile(self.archive, nested)
        with self.assertRaisesRegex(ValueError, "安装目录之外"):
            update_skill(nested, self.installed, tasks_finished=True)
        self.assertTrue(nested.is_file())

    def test_cli_returns_actionable_failure(self):
        """CLI 把缺少任务结束确认转换为可读 JSON 回执。"""
        self.write_archive()
        with patch("builtins.print") as output:
            result = main(["--zip", str(self.archive), "--skill-dir", str(self.installed)])
        self.assertEqual(result, 1)
        report = json.loads(output.call_args.args[0])
        self.assertEqual(report["status"], "failed")
        self.assertIn("--tasks-finished", report["message"])
