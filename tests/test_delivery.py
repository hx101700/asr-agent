"""本地恢复、部分失败和已确认保存位置的交付边界。"""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from asr_agent import MODEL
from asr_agent.delivery import latest_delivery
from asr_agent.environment import SetupError
from asr_agent.results import load_transcript, timestamp
from asr_agent.transcription import export_job, job_status, transcribe
from tests.support import ProjectTestCase


class DeliveryTests(ProjectTestCase):
    def setUp(self):
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
        cloud = patch("asr_agent.transcription.run_recognition", side_effect=AssertionError("local export must not call BL"))
        self.cloud = cloud.start()
        self.addCleanup(cloud.stop)

    def save_config(self):
        content = json.dumps(self.config, ensure_ascii=False).encode("utf-8")
        (self.root / "config.json").write_bytes(content)
        (self.root / "config.sha256").write_text(hashlib.sha256(content).hexdigest(), encoding="ascii")

    def save_execution(self, **changes):
        report = {"job_id": self.job_id, "status": "JSON_READY", "documents_ready": False,
                  "cloud_outcome": "result_received", "json_path": str(self.json_path),
                  "result": load_transcript(self.json_path).summary()}
        report.update(changes)
        (self.root / "execution/status.json").write_text(json.dumps(report), encoding="utf-8")

    def test_existing_json_exports_without_key_audio_or_bl_and_preserves_source(self):
        original = self.json_path.read_bytes()
        report = export_job(self.project, self.job_id)
        self.assertTrue(report["documents_ready"])
        self.assertEqual(report["delivery"]["status"], "COMPLETE")
        self.assertEqual(set(report["delivery"]["files"]), {"xlsx", "docx", "md"})
        for record in report["delivery"]["files"].values():
            content = Path(record["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), record["sha256"])
            self.assertEqual(len(content), record["bytes"])
        self.assertEqual(self.json_path.read_bytes(), original)
        self.cloud.assert_not_called()
        self.assertEqual(job_status(self.project, self.job_id), report)

    def test_one_format_failure_retains_other_formats_and_never_retries(self):
        with patch("asr_agent.delivery.write_docx", side_effect=RuntimeError("private transcript in exception")) as writer:
            report = export_job(self.project, self.job_id)
        writer.assert_called_once()
        self.assertFalse(report["documents_ready"])
        self.assertEqual(report["status"], "JSON_READY")
        self.assertEqual(report["cloud_outcome"], "result_received")
        self.assertEqual(report["delivery"]["status"], "PARTIAL")
        self.assertEqual(report["delivery"]["files"]["docx"]["error_type"], "RuntimeError")
        self.assertNotIn("private transcript", json.dumps(report))
        for extension in ("xlsx", "md"):
            self.assertTrue(Path(report["delivery"]["files"][extension]["path"]).is_file())
        self.assertEqual(transcribe(self.project, self.job_id, authorize_upload=True), report)
        self.cloud.assert_not_called()

    def test_explicit_reexport_uses_new_directory_and_preserves_first_round(self):
        first = export_job(self.project, self.job_id)["delivery"]
        second = export_job(self.project, self.job_id)["delivery"]
        self.assertNotEqual(first["export_id"], second["export_id"])
        for extension, record in first["files"].items():
            self.assertTrue(Path(record["path"]).is_file())
            self.assertNotEqual(record["path"], second["files"][extension]["path"])
        self.assertEqual(latest_delivery(self.root), second)

    def test_changed_json_after_s3_is_rejected(self):
        self.json_path.write_bytes(self.json_path.read_bytes() + b"\n")
        with self.assertRaisesRegex(SetupError, "发生变化"):
            export_job(self.project, self.job_id)
        self.assertFalse((self.root / "exports").exists())

    def test_real_s3_legacy_result_without_digest_can_be_exported(self):
        self.save_execution(result={"audio_tracks": 2, "sentences": 3})
        report = export_job(self.project, self.job_id)
        self.assertEqual(report["delivery"]["source_sha256"], hashlib.sha256(self.json_path.read_bytes()).hexdigest())

    def test_no_export_when_recognition_did_not_finish(self):
        self.save_execution(status="RUNNING")
        with self.assertRaisesRegex(SetupError, "尚无"):
            export_job(self.project, self.job_id)
        self.assertFalse((self.root / "exports").exists())

    def test_unwritable_output_is_local_failure_and_preserves_json(self):
        Path(self.config["document_directory"]).write_text("existing file", encoding="utf-8")
        report = export_job(self.project, self.job_id)
        self.assertEqual(report["delivery"]["status"], "FAILED")
        self.assertEqual(report["status"], "JSON_READY")
        self.assertFalse(report["documents_ready"])
        self.assertTrue(self.json_path.is_file())

    def test_unknown_latest_round_does_not_claim_previous_success(self):
        export_job(self.project, self.job_id)
        (self.root / "exports" / "99999999-incomplete").mkdir()
        report = job_status(self.project, self.job_id)
        self.assertEqual(report["delivery"]["status"], "OUTCOME_UNKNOWN")
        self.assertFalse(report["documents_ready"])

    def test_status_write_failure_still_reports_saved_json_without_reidentification(self):
        with patch("asr_agent.delivery._save_report", side_effect=OSError("synthetic disk full")):
            report = export_job(self.project, self.job_id)
        self.assertEqual(report["status"], "JSON_READY")
        self.assertEqual(report["cloud_outcome"], "result_received")
        self.assertEqual(report["delivery"]["status"], "OUTCOME_UNKNOWN")
        self.assertFalse(report["documents_ready"])
        self.assertTrue(Path(report["json_path"]).is_file())
        self.cloud.assert_not_called()

    def test_call_returns_its_own_delivery_even_if_another_round_starts(self):
        expected = {"status": "EXPORTING", "message": "synthetic", "export_id": "this-call"}
        with patch("asr_agent.transcription.export_documents", return_value=expected), \
             patch("asr_agent.transcription.latest_delivery", return_value={
                 "status": "FAILED", "message": "another round", "export_id": "other-call"}):
            report = export_job(self.project, self.job_id)
        self.assertEqual(report["delivery"], expected)

    def test_loader_preserves_order_empty_sentence_ids_and_precise_milliseconds(self):
        transcript = load_transcript(self.json_path)
        self.assertEqual([s.begin_ms for s in transcript.sentences], [1, 1501, 0])
        self.assertEqual([s.channel_id for s in transcript.sentences], [0, 0, 2])
        self.assertEqual([s.track_index for s in transcript.sentences], [1, 1, 2])
        self.assertEqual(transcript.sentences[1].text, "")
        self.assertIsNone(transcript.sentences[1].speaker_id)
        self.assertEqual(timestamp(25 * 3600000 + 1501), "25:00:01.501")

    def test_channel_or_sentence_schema_errors_are_not_guessed(self):
        for change in ({"channel_id": True, "sentences": []}, {"sentences": [None]},
                       {"sentences": [{"text": "text", "start": 0, "end": 1}]}):
            self.json_path.write_text(json.dumps({"transcripts": [change]}), encoding="utf-8")
            with self.assertRaises(SetupError):
                load_transcript(self.json_path)
