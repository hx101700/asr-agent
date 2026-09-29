"""用事件控制文件读取和目录等待，验证取消与上传的真实并发边界。"""

import io
import threading
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from asr_agent.session import Session
from asr_agent.validation import ValidationError, validate_audio
from tests.support import ProjectTestCase


class PausedInput(io.BytesIO):
    def __init__(self, content):
        super().__init__(content)
        self.read_started = threading.Event()
        self.release = threading.Event()

    def read(self, size=-1):
        self.read_started.set()
        if not self.release.wait(timeout=5):
            raise AssertionError("测试未释放文件读取")
        return super().read(size)


class SessionConcurrencyTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.session = Session(self.project)
        content = io.BytesIO()
        with wave.open(content, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\0" * 32000)
        self.audio = content.getvalue()
        uploaded = self.session.upload("audio", "original.wav", io.BytesIO(self.audio), len(self.audio))
        self.payload = {
            "auth_mode": "console", "audio_upload_id": uploaded["upload_id"],
            "diarization_enabled": True, "enhancement_mode": "none",
            "hotwords_upload_id": "", "context": "",
            "json_directory": "outputs", "document_directory": "outputs",
        }

    def tearDown(self):
        self.session.cleanup()
        super().tearDown()

    def test_cancel_directory_completes_while_upload_read_is_paused(self):
        source = PausedInput(self.audio)
        picker_started = threading.Event()
        picker_events = []

        def wait_for_cancel(_initial, *, cancel_event):
            picker_events.append(cancel_event)
            picker_started.set()
            if not cancel_event.wait(timeout=5):
                raise AssertionError("目录选择未收到取消")
            return None

        with patch("asr_agent.directory_picker.choose_directory", side_effect=wait_for_cancel), \
             ThreadPoolExecutor(max_workers=3) as pool:
            selecting = pool.submit(self.session.select_directory, "json", "during-upload")
            try:
                self.assertTrue(picker_started.wait(timeout=2))
                uploading = pool.submit(self.session.upload, "audio", "replacement.wav", source, len(self.audio))
                self.assertTrue(source.read_started.wait(timeout=2))
                cancelling = pool.submit(self.session.cancel_directory, "during-upload")
                self.assertTrue(cancelling.result(timeout=1)["ok"])
                self.assertTrue(picker_events[0].is_set())
                self.assertTrue(selecting.result(timeout=1)["cancelled"])
                self.assertFalse(source.release.is_set())
                self.assertFalse(uploading.done())
            finally:
                source.release.set()
                self.session.cancel_directory("during-upload")
            self.assertTrue(uploading.result(timeout=2)["ok"])

    def test_same_kind_concurrent_upload_is_rejected_without_reading_it(self):
        source = PausedInput(self.audio)
        other = io.BytesIO(self.audio)
        with ThreadPoolExecutor(max_workers=2) as pool:
            uploading = pool.submit(self.session.upload, "audio", "replacement.wav", source, len(self.audio))
            try:
                self.assertTrue(source.read_started.wait(timeout=2))
                duplicate = pool.submit(self.session.upload, "audio", "duplicate.wav", other, len(self.audio))
                with self.assertRaisesRegex(ValidationError, "正在添加"):
                    duplicate.result(timeout=1)
                self.assertEqual(other.tell(), 0)
            finally:
                source.release.set()
            self.assertTrue(uploading.result(timeout=2)["ok"])
        self.assertEqual(len(self.session.uploads), 1)
        self.assertFalse(list(self.session.upload_directory.glob("*.part")))

    def test_audio_and_hotwords_can_receive_independently(self):
        audio = PausedInput(self.audio)
        hotwords = PausedInput(b"synthetic Excel bytes; no parsing in upload")
        with ThreadPoolExecutor(max_workers=2) as pool:
            audio_upload = pool.submit(self.session.upload, "audio", "replacement.wav", audio, len(self.audio))
            try:
                self.assertTrue(audio.read_started.wait(timeout=2))
                words_upload = pool.submit(self.session.upload, "hotwords", "words.xlsx", hotwords, len(hotwords.getvalue()))
                self.assertTrue(hotwords.read_started.wait(timeout=2))
                # 音频还在接收时，热词已经可以独立发布完整副本。
                hotwords.release.set()
                words_result = words_upload.result(timeout=1)
                self.assertEqual(self.session.uploaded(words_result["upload_id"], "hotwords")["name"], "words.xlsx")
                self.assertFalse(audio_upload.done())
            finally:
                audio.release.set()
                hotwords.release.set()
            self.assertTrue(audio_upload.result(timeout=2)["ok"])
        self.assertEqual({entry["kind"] for entry in self.session.uploads.values()}, {"audio", "hotwords"})

    def test_pending_upload_rejects_validation_and_confirmation(self):
        preview = self.session.validate(self.payload)
        source = PausedInput(self.audio)
        with ThreadPoolExecutor(max_workers=3) as pool:
            uploading = pool.submit(self.session.upload, "audio", "replacement.wav", source, len(self.audio))
            try:
                self.assertTrue(source.read_started.wait(timeout=2))
                validating = pool.submit(self.session.validate, self.payload)
                confirming = pool.submit(self.session.confirm, preview["validation_id"])
                for action in (validating, confirming):
                    with self.assertRaisesRegex(ValidationError, "仍在添加"):
                        action.result(timeout=1)
                self.assertIsNone(self.session.draft)
                self.assertIsNone(self.session.receipt)
                self.assertFalse(self.project.path(".state/jobs").exists())
            finally:
                source.release.set()
            uploading.result(timeout=2)

    def test_cleanup_returns_before_late_upload_and_prevents_publication(self):
        source = PausedInput(self.audio)
        with ThreadPoolExecutor(max_workers=2) as pool:
            uploading = pool.submit(self.session.upload, "audio", "late.wav", source, len(self.audio))
            try:
                self.assertTrue(source.read_started.wait(timeout=2))
                self.assertEqual(len(list(self.session.upload_directory.glob("*.part"))), 1)
                closing = pool.submit(self.session.cleanup)
                closing.result(timeout=1)
                self.assertFalse(uploading.done())
                # 活动上传拥有.part的清理责任，关闭线程不删除另一个线程打开的文件。
                self.assertEqual(len(list(self.session.upload_directory.glob("*.part"))), 1)
            finally:
                source.release.set()
            with self.assertRaisesRegex(ValidationError, "会话已关闭"):
                uploading.result(timeout=2)
        self.assertFalse(self.session.upload_directory.exists())
        self.assertFalse(any(record["name"] == "late.wav" for record in self.session.uploads.values()))
        with self.assertRaisesRegex(ValidationError, "会话已关闭"):
            self.session.validate(self.payload)

    def test_failed_replacement_preserves_old_file_but_not_old_preview(self):
        preview = self.session.validate(self.payload)
        original = self.session.uploaded(self.payload["audio_upload_id"], "audio").copy()
        with self.assertRaisesRegex(ValidationError, "不完整"):
            self.session.upload("audio", "incomplete.wav", io.BytesIO(b"short"), 100)
        self.assertEqual(self.session.uploaded(self.payload["audio_upload_id"], "audio"), original)
        self.assertEqual(Path(original["path"]).read_bytes(), self.audio)
        self.assertEqual(list(self.session.upload_directory.iterdir()), [Path(original["path"])])
        self.assertIsNone(self.session.draft)
        with self.assertRaises(ValidationError):
            self.session.confirm(preview["validation_id"])
        self.assertNotEqual(self.session.validate(self.payload)["validation_id"], preview["validation_id"])

    def test_publish_failure_removes_new_destination_and_keeps_original(self):
        preview = self.session.validate(self.payload)
        original = Path(self.session.uploaded(self.payload["audio_upload_id"], "audio")["path"])
        unlink = Path.unlink

        def refuse_original_delete(path, *args, **kwargs):
            if path == original:
                raise PermissionError("synthetic file is in use")
            return unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", refuse_original_delete):
            with self.assertRaises(PermissionError):
                self.session.upload("audio", "replacement.wav", io.BytesIO(self.audio), len(self.audio))
        self.assertEqual(list(self.session.upload_directory.iterdir()), [original])
        self.assertEqual(original.read_bytes(), self.audio)
        self.assertIsNone(self.session.draft)
        with self.assertRaises(ValidationError):
            self.session.confirm(preview["validation_id"])
        # 最终发布失败也必须撤销“正在添加”，让用户可以重新检查旧文件。
        self.assertTrue(self.session.validate(self.payload)["ok"])

    def test_cancel_directory_does_not_wait_for_audio_validation(self):
        picker_started = threading.Event()
        validation_started = threading.Event()
        release_validation = threading.Event()
        picker_events = []

        def wait_for_cancel(_initial, *, cancel_event):
            picker_events.append(cancel_event)
            picker_started.set()
            if not cancel_event.wait(timeout=5):
                raise AssertionError("目录选择未收到取消")
            return None

        def paused_validation(*args):
            validation_started.set()
            if not release_validation.wait(timeout=5):
                raise AssertionError("测试未释放音频校验")
            return validate_audio(*args)

        with patch("asr_agent.directory_picker.choose_directory", side_effect=wait_for_cancel), \
             patch("asr_agent.session.validate_audio", side_effect=paused_validation), \
             ThreadPoolExecutor(max_workers=3) as pool:
            selecting = pool.submit(self.session.select_directory, "json", "during-validation")
            try:
                self.assertTrue(picker_started.wait(timeout=2))
                validating = pool.submit(self.session.validate, self.payload)
                self.assertTrue(validation_started.wait(timeout=2))
                cancelling = pool.submit(self.session.cancel_directory, "during-validation")
                self.assertTrue(cancelling.result(timeout=1)["ok"])
                self.assertTrue(picker_events[0].is_set())
                self.assertTrue(selecting.result(timeout=1)["cancelled"])
                self.assertFalse(validating.done())
            finally:
                release_validation.set()
                self.session.cancel_directory("during-validation")
            self.assertTrue(validating.result(timeout=2)["ok"])
