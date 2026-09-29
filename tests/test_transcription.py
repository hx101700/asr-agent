"""S3用例：使用真实网页配置和媒体处理，只替代BL进程边界。"""

import hashlib
import io
import json
import threading
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from asr_agent import MODEL
from asr_agent.auth import read_api_key
from asr_agent.bailian import BailianFailure
from asr_agent.environment import SetupError
from asr_agent.media import probe_audio
from asr_agent.session import Session
from asr_agent.transcription import job_status, transcribe
from tests.support import ProjectTestCase


def transcript_result(*texts):
    return {"transcripts": [
        {"channel_id": channel, "text": text, "sentences": [
            {"text": text, "begin_time": 100, "end_time": 900, "speaker_id": 0}
        ]}
        for channel, text in enumerate(texts or ("合成测试转写。",))
    ]}


class TranscriptionTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.secret = "asr-agent-synthetic-transcription-key"
        self.project.path(".env").write_text(
            f"DASHSCOPE_API_KEY={self.secret}\n", encoding="utf-8"
        )
        # 用例测试不安装或运行另一个CLI；参数长度检查仍走生产实现。
        command = patch("asr_agent.bailian.bl_command", side_effect=lambda project, args: [
            "node", str(project.bl_entry), *args, "--quiet"
        ])
        command.start()
        self.addCleanup(command.stop)
        execution = patch("asr_agent.transcription.run_recognition", side_effect=self.write_result)
        self.cli = execution.start()
        self.addCleanup(execution.stop)

    def make_job(self, *, channels=1, diarization=True, enhancement="none", **options):
        session = Session(self.project)
        audio_bytes = io.BytesIO()
        with wave.open(audio_bytes, "wb") as audio:
            audio.setnchannels(channels)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\0" * 32000 * channels)
        content = audio_bytes.getvalue()
        upload = session.upload("audio", "合成录音.wav", io.BytesIO(content), len(content))
        payload = {
            "auth_mode": "api_key", "audio_upload_id": upload["upload_id"],
            "diarization_enabled": diarization, "enhancement_mode": enhancement,
            "hotwords_upload_id": "", "context": "",
            "json_directory": "outputs", "document_directory": "outputs",
            **options,
        }
        if enhancement in ("hotwords", "both"):
            workbook = Workbook()
            workbook.active.append(["text", "weight"])
            workbook.active.append(["合成术语", 5])
            workbook.active.append(["Qwen", 50])
            stream = io.BytesIO()
            workbook.save(stream)
            workbook.close()
            data = stream.getvalue()
            words = session.upload("hotwords", "合成热词.xlsx", io.BytesIO(data), len(data))
            payload["hotwords_upload_id"] = words["upload_id"]
        if enhancement in ("context", "both"):
            payload["context"] = "讨论合成术语与Qwen的识别效果。"
        try:
            preview = session.validate(payload)
            receipt = session.confirm(preview["validation_id"])
            config = json.loads(Path(receipt["config_path"]).read_text(encoding="utf-8"))
            return receipt["job_id"], config
        finally:
            session.cleanup()

    @staticmethod
    def output_path(arguments):
        return Path(arguments[arguments.index("--out") + 1])

    def write_result(self, project, command, private):
        self.output_path(command.argv).write_text(
            json.dumps(transcript_result(), ensure_ascii=False), encoding="utf-8"
        )

    def test_saved_configuration_requires_separate_upload_authorization(self):
        job_id, _ = self.make_job()
        with self.assertRaises(SetupError):
            transcribe(self.project, job_id)
        self.cli.assert_not_called()
        self.assertFalse(self.project.path(f".state/jobs/{job_id}/execution").exists())
        self.assertFalse(job_status(self.project, job_id)["execution_authorized"])

    def test_confirmation_checksum_matches_the_saved_utf8_bytes(self):
        job_id, _ = self.make_job(enhancement="both")
        path = self.project.path(f".state/jobs/{job_id}/config.json")
        checksum = path.with_suffix(".sha256").read_text(encoding="ascii").strip()
        self.assertEqual(checksum, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_modified_snapshot_is_rejected_before_execution_is_claimed(self):
        for changed in ("context", "vocabulary", "audio_metadata", "recognition_options"):
            with self.subTest(changed=changed):
                job_id, config = self.make_job(enhancement="both")
                if changed == "context":
                    config["enhancement"]["context"] = "保存后修改的上下文。"
                elif changed == "vocabulary":
                    config["enhancement"]["hotwords"]["vocabulary"] = {"替换后的词": 5}
                elif changed == "audio_metadata":
                    config["audio"]["metadata"]["sample_rate"] = 8000
                else:
                    config["recognition_options"]["language_hints"] = ["en"]
                path = self.project.path(f".state/jobs/{job_id}/config.json")
                path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
                with self.assertRaisesRegex(SetupError, "配置发生变化"):
                    transcribe(self.project, job_id, authorize_upload=True)
                self.assertFalse(path.parent.joinpath("execution").exists())
                self.cli.assert_not_called()

    def test_legacy_configuration_without_checksum_is_not_automatically_accepted(self):
        job_id, _ = self.make_job()
        path = self.project.path(f".state/jobs/{job_id}/config.sha256")
        path.unlink()
        with self.assertRaisesRegex(SetupError, "缺少确认摘要"):
            transcribe(self.project, job_id, authorize_upload=True)
        self.assertFalse(path.exists())
        self.assertFalse(path.parent.joinpath("execution").exists())
        self.cli.assert_not_called()

    def test_success_records_json_only_and_never_reexecutes_the_saved_job(self):
        job_id, _ = self.make_job()
        report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "JSON_READY")
        self.assertEqual(report["cloud_outcome"], "result_received")
        self.assertFalse(report["documents_ready"])
        self.assertIsNone(report["task_id"])
        self.assertTrue(Path(report["json_path"]).is_file())
        self.assertEqual(job_status(self.project, job_id), report)
        self.assertEqual(transcribe(self.project, job_id, authorize_upload=True), report)
        self.cli.assert_called_once()
        config_text = self.project.path(f".state/jobs/{job_id}/config.json").read_text(encoding="utf-8")
        self.assertFalse(json.loads(config_text)["execution_authorized"])
        self.assertNotIn(self.secret, config_text + json.dumps(report))

    def test_saved_uploads_execute_after_web_session_cleanup(self):
        # make_job在返回前已调用Session.cleanup；执行只依赖持久配置及已确认副本。
        job_id, config = self.make_job(channels=2, enhancement="both")
        audio = Path(config["audio"]["path"])
        hotwords = Path(config["enhancement"]["hotwords"]["path"])
        self.assertTrue(audio.is_file())
        self.assertTrue(hotwords.is_file())
        report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "JSON_READY")
        self.assertEqual(report["cloud_outcome"], "result_received")
        self.assertTrue(audio.is_file())
        self.assertTrue(hotwords.is_file())
        self.cli.assert_called_once()

    def test_unchanged_snapshot_avoids_excel_parsing_and_original_audio_probe(self):
        job_id, config = self.make_job(enhancement="both", language_hint="zh", speaker_count=3)
        # 原文件已通过S2检查；这里任何再次打开媒体或解析Excel都应暴露为回归。
        with patch("asr_agent.validation.probe_audio", side_effect=AssertionError("重复探测原音频")), \
                patch("asr_agent.media.probe_audio", side_effect=AssertionError("重复探测原音频")), \
                patch("asr_agent.validation.load_workbook", side_effect=AssertionError("重复解析Excel")):
            report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "JSON_READY")
        arguments = self.cli.call_args.args[1].argv
        self.assertEqual(arguments[arguments.index("--context") + 1], config["enhancement"]["context"])
        self.assertEqual(json.loads(arguments[arguments.index("--vocabulary") + 1]),
                         config["enhancement"]["hotwords"]["vocabulary"])

    def test_api_key_is_read_once_for_the_prepared_command(self):
        job_id, _ = self.make_job()
        with patch("asr_agent.auth.read_api_key", wraps=read_api_key) as read_key:
            report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "JSON_READY")
        read_key.assert_called_once_with(self.project)
        command = self.cli.call_args.args[1]
        self.assertEqual(command.env["DASHSCOPE_API_KEY"], self.secret)
        self.assertNotIn(self.secret, repr(command))

    def test_console_execution_does_not_run_auth_status_or_read_dotenv(self):
        job_id, _ = self.make_job(auth_mode="console")
        with patch("asr_agent.bailian.console_status", side_effect=AssertionError("重复查询鉴权状态")), \
                patch("asr_agent.bailian._run_bl", side_effect=AssertionError("执行识别前启动了额外BL命令")), \
                patch("asr_agent.auth.read_api_key", side_effect=AssertionError("控制台模式读取了.env")):
            report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "JSON_READY")
        self.assertNotIn("DASHSCOPE_API_KEY", self.cli.call_args.args[1].env)
        self.cli.assert_called_once()

    def test_concurrent_execution_enters_bl_only_once(self):
        job_id, _ = self.make_job()
        entered, release = threading.Event(), threading.Event()

        def block_cli(*args):
            entered.set()
            if not release.wait(5):
                raise AssertionError("测试未释放BL边界")
            self.write_result(*args)

        self.cli.side_effect = block_cli
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(transcribe, self.project, job_id, authorize_upload=True)
            try:
                self.assertTrue(entered.wait(5))
                second = pool.submit(transcribe, self.project, job_id, authorize_upload=True)
                observed = second.result(timeout=5)
                self.assertEqual(observed["status"], "RUNNING")
                self.assertEqual(self.cli.call_count, 1)
            finally:
                release.set()
            self.assertEqual(first.result(timeout=5)["status"], "JSON_READY")

    def test_crashed_execution_marker_prevents_resubmission(self):
        job_id, _ = self.make_job()
        self.project.path(f".state/jobs/{job_id}/execution").mkdir()
        report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "OUTCOME_UNKNOWN")
        self.assertEqual(report["cloud_outcome"], "unknown")
        self.cli.assert_not_called()

    def test_changed_audio_or_hotwords_are_rejected_before_bl(self):
        for changed in ("audio", "hotwords"):
            with self.subTest(changed=changed):
                job_id, config = self.make_job(enhancement="both")
                record = config["audio"] if changed == "audio" else config["enhancement"]["hotwords"]
                path = Path(record["path"])
                path.write_bytes(path.read_bytes() + b"changed after confirmation")
                report = transcribe(self.project, job_id, authorize_upload=True)
                self.assertEqual(report["status"], "STOPPED")
                self.assertEqual(report["cloud_outcome"], "not_started")
                self.cli.assert_not_called()

    def test_missing_key_after_confirmation_stops_without_cloud_request(self):
        job_id, _ = self.make_job()
        self.project.path(".env").write_text("DASHSCOPE_API_KEY=\n", encoding="utf-8")
        report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "STOPPED")
        self.assertEqual(report["cloud_outcome"], "not_started")
        self.cli.assert_not_called()

    def test_stereo_is_converted_once_and_original_copy_is_preserved(self):
        job_id, config = self.make_job(channels=2)
        original = Path(config["audio"]["path"])
        original_bytes = original.read_bytes()
        report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "JSON_READY")
        arguments = self.cli.call_args.args[1].argv
        uploaded = Path(arguments[arguments.index("--url") + 1])
        self.assertNotEqual(uploaded, original)
        self.assertEqual(uploaded.suffix, ".flac")
        metadata = probe_audio(uploaded)
        self.assertEqual(metadata.channels, 1)
        self.assertEqual(metadata.sample_rate, 16000)
        self.assertAlmostEqual(metadata.duration_seconds, 1.0)
        self.assertEqual(original.read_bytes(), original_bytes)
        self.assertEqual(probe_audio(original).channels, 2)

    def test_mono_or_disabled_diarization_uses_existing_audio(self):
        for channels, diarization in ((1, True), (2, False)):
            with self.subTest(channels=channels, diarization=diarization):
                self.cli.reset_mock()
                job_id, config = self.make_job(channels=channels, diarization=diarization)
                report = transcribe(self.project, job_id, authorize_upload=True)
                self.assertEqual(report["status"], "JSON_READY")
                arguments = self.cli.call_args.args[1].argv
                self.assertEqual(arguments[arguments.index("--url") + 1], config["audio"]["path"])
                self.assertEqual("--diarization" in arguments, diarization)
                self.assertNotIn("--speaker-count", arguments)
                self.assertFalse(self.project.path(f".state/jobs/{job_id}/execution/mono.flac").exists())

    def test_actual_upload_size_limit_applies_after_mono_conversion(self):
        job_id, _ = self.make_job(channels=2)
        # 降低阈值以覆盖超限，不创建1GB测试文件；探测和FLAC转换仍真实执行。
        with patch("asr_agent.validation.MAX_UPLOAD_BYTES", 1):
            report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "STOPPED")
        self.assertEqual(report["cloud_outcome"], "not_started")
        converted = self.project.path(f".state/jobs/{job_id}/execution/mono.flac")
        self.assertEqual(probe_audio(converted).channels, 1)
        self.cli.assert_not_called()

    def test_dual_enhancement_and_recognition_options_reach_the_same_request(self):
        job_id, config = self.make_job(enhancement="both", language_hint="zh", speaker_count=3)
        report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "JSON_READY")
        _, command, private = self.cli.call_args.args
        arguments = command.argv
        self.assertEqual(command.env["DASHSCOPE_API_KEY"], self.secret)
        values = lambda flag: arguments[arguments.index(flag) + 1]
        self.assertEqual(values("--model"), MODEL)
        self.assertEqual(values("--language"), "zh")
        self.assertEqual(values("--speaker-count"), "3")
        self.assertEqual(values("--context"), config["enhancement"]["context"])
        self.assertEqual(json.loads(values("--vocabulary")), {"合成术语": 5, "Qwen": 50})
        self.assertIn("合成术语", private)
        self.assertIn(config["enhancement"]["context"], private)
        self.assertNotIn(self.secret, json.dumps(arguments))

    def test_existing_json_is_preserved_without_starting_bl(self):
        job_id, config = self.make_job()
        destination = Path(config["json_directory"]) / "transcription.json"
        destination.parent.mkdir(parents=True)
        destination.write_text("previous result", encoding="utf-8")
        report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "STOPPED")
        self.assertEqual(report["cloud_outcome"], "not_started")
        self.assertEqual(destination.read_text(encoding="utf-8"), "previous result")
        self.cli.assert_not_called()

    def test_exit_zero_requires_usable_json_and_keeps_unusable_files(self):
        empty_sentences = {"transcripts": [{"sentences": []}]}
        cases = [None, "", "not json", "[]", json.dumps([transcript_result()]),
                 json.dumps({"transcripts": []}), json.dumps(empty_sentences),
                 json.dumps(transcript_result("   "))]
        for content in cases:
            with self.subTest(content=content):
                self.cli.reset_mock()
                job_id, config = self.make_job()

                def save_unusable(project, command, private):
                    if content is not None:
                        self.output_path(command.argv).write_text(content, encoding="utf-8")

                self.cli.side_effect = save_unusable
                report = transcribe(self.project, job_id, authorize_upload=True)
                self.assertEqual(report["status"], "STOPPED")
                self.assertEqual(report["cloud_outcome"], "unknown")
                self.assertFalse(report["documents_ready"])
                self.cli.assert_called_once()
                path = Path(config["json_directory"]) / "transcription.json"
                self.assertEqual(path.exists(), content is not None)
                if content is not None:
                    self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_invalid_sentence_timestamps_do_not_become_success(self):
        for begin, end in ((True, 900), (100, 99), (-1, 900), (0, 1.5)):
            with self.subTest(begin=begin, end=end):
                job_id, _ = self.make_job()
                result = transcript_result()
                result["transcripts"][0]["sentences"][0].update(begin_time=begin, end_time=end)

                def write_invalid(project, command, private):
                    self.output_path(command.argv).write_text(json.dumps(result), encoding="utf-8")

                self.cli.side_effect = write_invalid
                report = transcribe(self.project, job_id, authorize_upload=True)
                self.assertEqual(report["status"], "STOPPED")
                self.assertTrue(Path(report["json_path"]).is_file())

    def test_multiple_result_tracks_are_kept_without_normalization(self):
        job_id, _ = self.make_job()
        result = transcript_result("第一音轨。", "第二音轨。")
        result["provider_extension"] = {"preserve": True}
        text = json.dumps(result, ensure_ascii=False, indent=4) + "\n"

        def write_tracks(project, command, private):
            self.output_path(command.argv).write_text(text, encoding="utf-8")

        self.cli.side_effect = write_tracks
        report = transcribe(self.project, job_id, authorize_upload=True)
        self.assertEqual(report["status"], "JSON_READY")
        self.assertEqual(report["result"]["audio_tracks"], 2)
        self.assertEqual(report["result"]["sentences"], 2)
        self.assertEqual(Path(report["json_path"]).read_text(encoding="utf-8"), text)

    def test_bl_start_failure_and_interrupted_wait_have_distinct_outcomes(self):
        for started, code in ((False, "LOCAL_PROCESS_START_FAILED"), (True, "LOCAL_WAIT_INTERRUPTED")):
            with self.subTest(started=started):
                self.cli.reset_mock()
                job_id, _ = self.make_job()
                self.cli.side_effect = BailianFailure(
                    {"source": "local", "code": code, "explanation": "合成的BL边界故障"},
                    started=started,
                )
                report = transcribe(self.project, job_id, authorize_upload=True)
                self.assertEqual(report["status"], "STOPPED")
                self.assertEqual(report["cloud_outcome"], "unknown" if started else "not_started")
                self.assertEqual(report["error"]["code"], code)
                self.assertIsNone(report["task_id"])
                self.assertEqual(transcribe(self.project, job_id, authorize_upload=True), report)
                self.cli.assert_called_once()
