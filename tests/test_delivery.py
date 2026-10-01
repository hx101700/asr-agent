"""验证本地导出轮次、格式失败和保存位置。"""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from asr_agent import MODEL
from asr_agent.tools.job_files import latest_delivery
from asr_agent.tools.documents import DocumentError
from asr_agent.tools.environment import SetupError
from asr_agent.tools.results import load_transcript
from asr_agent.tools.documents import timestamp
from asr_agent.application.transcription import export_job, job_status, transcribe
from tests.support import ProjectTestCase


class DeliveryTests(ProjectTestCase):
    def setUp(self):
        """准备已保存任务、合成JSON和文档目录。"""
        super().setUp()
        self.job_id = "a" * 32
        self.root = self.project.path(f".state/jobs/{self.job_id}")
        (self.root / "execution").mkdir(parents=True)
        base = self.project.path(f"outputs/{self.job_id}")
        self.config = {"schema_version": 1, "job_id": self.job_id, "model": MODEL,
                       "region": "cn-beijing", "status": "CONFIGURED",
                       "execution_authorized": False, "confirmed_at": "synthetic-time",
                       "json_directory": str(base / "json"),
                       "document_directory": str(base / "documents"),
                       "audio": {"name": "合成录音.wav"}}
        self.save_config()
        self.json_path = base / "json/transcription.json"
        self.json_path.parent.mkdir(parents=True)
        self.json_path.write_text(json.dumps({
            "file_url": "https://example.invalid/private-result?signature=synthetic-secret",
            "transcripts": [{"channel_id": 0, "sentences": [
                {"text": "合成文本。", "begin_time": 1, "end_time": 1501, "speaker_id": 0},
                {"text": "", "begin_time": 1501, "end_time": 1501},
            ]}, {"channel_id": 2, "sentences": [
                {"text": "=HYPERLINK(\"https://example.invalid\")", "begin_time": 0, "end_time": 1234},
            ]}]
        }, ensure_ascii=False), encoding="utf-8")
        self.save_execution()
        cloud = patch("asr_agent.application.transcription.run_recognition", side_effect=AssertionError("local export must not call BL"))
        self.cloud = cloud.start()
        self.addCleanup(cloud.stop)

    def save_config(self):
        """保存合成任务配置及对应内容摘要。"""
        content = json.dumps(self.config, ensure_ascii=False).encode("utf-8")
        (self.root / "config.json").write_bytes(content)
        (self.root / "config.sha256").write_text(hashlib.sha256(content).hexdigest(), encoding="ascii")

    def save_execution(self, **changes):
        """保存测试用执行状态与结果摘要。"""
        report = {"job_id": self.job_id, "status": "JSON_READY", "documents_ready": False,
                  "cloud_outcome": "result_received", "json_path": str(self.json_path),
                  "result": load_transcript(self.json_path).summary()}
        report.update(changes)
        (self.root / "execution/status.json").write_text(json.dumps(report), encoding="utf-8")

    def test_existing_json_exports_without_key_audio_or_bl_and_preserves_source(self):
        """验证已有JSON独立导出并保留原结果。"""
        original = self.json_path.read_bytes()
        report = export_job(self.project, self.job_id)
        self.assertTrue(report["documents_ready"])
        self.assertEqual(report["delivery"]["status"], "COMPLETE")
        self.assertEqual(set(report["delivery"]["files"]), {"xlsx", "docx", "md"})
        for record in report["delivery"]["files"].values():
            content = Path(record["path"]).read_bytes()
            self.assertEqual(len(content), record["bytes"])
            self.assertNotIn("sha256", record)
        self.assertEqual(report["delivery"]["source_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(self.json_path.read_bytes(), original)
        self.cloud.assert_not_called()
        self.assertEqual(job_status(self.project, self.job_id), report)

    def test_one_format_failure_retains_other_formats_and_never_retries(self):
        """验证单格式失败保留其他成品且各格式调用一次。"""
        with patch("asr_agent.application.delivery.write_docx", side_effect=RuntimeError("private transcript in exception")) as writer:
            report = export_job(self.project, self.job_id)
        writer.assert_called_once()
        self.assertFalse(report["documents_ready"])
        self.assertEqual(report["status"], "JSON_READY")
        self.assertEqual(report["cloud_outcome"], "result_received")
        self.assertEqual(report["delivery"]["status"], "PARTIAL")
        self.assertEqual(report["delivery"]["files"]["docx"]["error_type"], "RuntimeError")
        self.assertIn("程序发生异常", report["delivery"]["files"]["docx"]["message"])
        self.assertNotIn("磁盘", report["delivery"]["files"]["docx"]["message"])
        self.assertNotIn("private transcript", json.dumps(report))
        for extension in ("xlsx", "md"):
            self.assertTrue(Path(report["delivery"]["files"][extension]["path"]).is_file())
        self.assertEqual(transcribe(self.project, self.job_id, authorize_upload=True), report)
        self.cloud.assert_not_called()

    def test_known_document_error_and_filesystem_error_have_specific_messages(self):
        """验证格式错误和文件系统错误有对应说明。"""
        for error, message in ((DocumentError("已知格式限制"), "已知格式限制"),
                               (OSError("private path"), "目录权限")):
            with self.subTest(error=type(error).__name__), \
                 patch("asr_agent.application.delivery.write_docx", side_effect=error):
                report = export_job(self.project, self.job_id)
            failure = report["delivery"]["files"]["docx"]
            self.assertIn(message, failure["message"])
            self.assertNotIn("private path", json.dumps(report))
            self.assertEqual(report["delivery"]["status"], "PARTIAL")

    def test_unexpected_serializer_error_is_not_reported_as_disk_failure(self):
        """验证序列化异常返回对应的程序错误说明。"""
        with patch("asr_agent.tools.documents.Workbook.save", side_effect=ValueError("private transcript")):
            report = export_job(self.project, self.job_id)
        failure = report["delivery"]["files"]["xlsx"]
        self.assertEqual(failure["error_type"], "ValueError")
        self.assertIn("程序发生异常", failure["message"])
        self.assertNotIn("目录", failure["message"])
        self.assertNotIn("private transcript", json.dumps(report))
        self.assertEqual(report["delivery"]["status"], "PARTIAL")

    def test_explicit_reexport_uses_new_directory_and_preserves_first_round(self):
        """验证显式重导建立新目录且保留上一轮。"""
        first = export_job(self.project, self.job_id)["delivery"]
        second = export_job(self.project, self.job_id)["delivery"]
        self.assertNotEqual(first["export_id"], second["export_id"])
        for extension, record in first["files"].items():
            self.assertTrue(Path(record["path"]).is_file())
            self.assertNotEqual(record["path"], second["files"][extension]["path"])
        self.assertEqual(latest_delivery(self.root), second)

    def test_changed_json_after_recognition_is_rejected(self):
        """验证识别后JSON内容改变时拒绝导出。"""
        self.json_path.write_bytes(self.json_path.read_bytes() + b"\n")
        with self.assertRaisesRegex(SetupError, "发生变化"):
            export_job(self.project, self.job_id)
        self.assertFalse((self.root / "exports").exists())

    def test_result_without_digest_is_not_exported_or_resubmitted(self):
        """验证结果摘要缺失时返回导出来源错误。"""
        self.save_execution(result={"audio_tracks": 2, "sentences": 3})
        with self.assertRaisesRegex(SetupError, "缺少结果JSON摘要"):
            export_job(self.project, self.job_id)
        self.assertFalse((self.root / "exports").exists())
        self.cloud.assert_not_called()

    def test_no_export_when_recognition_did_not_finish(self):
        """验证识别进行中拒绝导出。"""
        self.save_execution(status="RUNNING")
        with self.assertRaisesRegex(SetupError, "尚无"):
            export_job(self.project, self.job_id)
        self.assertFalse((self.root / "exports").exists())

    def test_unwritable_output_is_local_failure_and_preserves_json(self):
        """验证保存目录写入失败时保留JSON并报告导出失败。"""
        Path(self.config["document_directory"]).write_text("existing file", encoding="utf-8")
        report = export_job(self.project, self.job_id)
        self.assertEqual(report["delivery"]["status"], "FAILED")
        self.assertEqual(report["status"], "JSON_READY")
        self.assertFalse(report["documents_ready"])
        self.assertTrue(self.json_path.is_file())

    def test_unknown_latest_round_does_not_claim_previous_success(self):
        """验证最新导出记录异常时返回结果未知状态。"""
        export_job(self.project, self.job_id)
        (self.root / "exports" / "99999999-incomplete").mkdir()
        report = job_status(self.project, self.job_id)
        self.assertEqual(report["delivery"]["status"], "OUTCOME_UNKNOWN")
        self.assertFalse(report["documents_ready"])

    def test_status_write_failure_still_reports_saved_json_without_reidentification(self):
        """验证状态写入失败仍说明JSON已保存。"""
        with patch("asr_agent.application.delivery.save_record", side_effect=OSError("synthetic disk full")):
            report = export_job(self.project, self.job_id)
        self.assertEqual(report["status"], "JSON_READY")
        self.assertEqual(report["cloud_outcome"], "result_received")
        self.assertEqual(report["delivery"]["status"], "OUTCOME_UNKNOWN")
        self.assertFalse(report["documents_ready"])
        self.assertTrue(Path(report["json_path"]).is_file())
        self.cloud.assert_not_called()

    def test_call_returns_its_own_delivery_even_if_another_round_starts(self):
        """验证并发导出返回当前调用自己的轮次。"""
        expected = {"status": "EXPORTING", "message": "synthetic", "export_id": "this-call"}
        with patch("asr_agent.application.transcription.export_documents", return_value=expected), \
             patch("asr_agent.application.transcription.latest_delivery", side_effect=AssertionError("重导不读取上一轮交付")):
            report = export_job(self.project, self.job_id)
        self.assertEqual(report["delivery"], expected)

    def test_loader_preserves_order_empty_sentence_ids_and_precise_milliseconds(self):
        """验证JSON解析保留原顺序、空句和毫秒时间。"""
        transcript = load_transcript(self.json_path)
        self.assertEqual([s.begin_ms for s in transcript.sentences], [1, 1501, 0])
        self.assertEqual([s.channel_id for s in transcript.sentences], [0, 0, 2])
        self.assertEqual([s.track_index for s in transcript.sentences], [1, 1, 2])
        self.assertEqual(transcript.sentences[1].text, "")
        self.assertIsNone(transcript.sentences[1].speaker_id)
        self.assertEqual(timestamp(25 * 3600000 + 1501), "25:00:01.501")

    def test_channel_or_sentence_schema_errors_are_not_guessed(self):
        """验证异常结果字段返回结构检查错误。"""
        for change in ({"channel_id": True, "sentences": []}, {"sentences": [None]},
                       {"sentences": [{"text": "text", "start": 0, "end": 1}]}):
            self.json_path.write_text(json.dumps({"transcripts": [change]}), encoding="utf-8")
            with self.assertRaises(SetupError):
                load_transcript(self.json_path)
