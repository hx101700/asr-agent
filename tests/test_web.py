import http.client
import io
import json
import threading
import wave
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from unittest.mock import patch

from openpyxl import Workbook, load_workbook

from asr_agent.validation import ValidationError
from asr_agent.web import Session, create_server, output_directory
from tests.support import ProjectTestCase


class WebFixture(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.audio = self.project.path("data/audio/录音.wav")
        self.audio.parent.mkdir(parents=True)
        with wave.open(str(self.audio), "wb") as audio:
            audio.setnchannels(2)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\0" * 64000)
    def payload_for(self, session):
        content = self.audio.read_bytes()
        uploaded = session.upload("audio", self.audio.name, io.BytesIO(content), len(content))
        return {"auth_mode": "console", "audio_upload_id": uploaded["upload_id"],
                        "diarization_enabled": True, "enhancement_mode": "none",
                        "hotwords_upload_id": "", "context": "", "json_directory": "outputs",
                        "document_directory": "outputs/documents"}


class SessionTests(WebFixture):
    def setUp(self):
        super().setUp()
        self.session = Session(self.project)
        self.payload = self.payload_for(self.session)

    def test_preview_performs_no_conversion_or_job_write(self):
        result = self.session.validate(self.payload)
        self.assertTrue(result["summary"]["audio"]["requires_mono"])
        self.assertEqual(result["summary"]["region"], "华北2（北京）")
        self.assertFalse(self.project.path(".state/jobs").exists())
        self.assertFalse(self.project.path("outputs").exists())

    def test_confirm_is_idempotent_even_with_concurrent_requests(self):
        preview = self.session.validate(self.payload)
        with ThreadPoolExecutor(max_workers=2) as pool:
            receipts = list(pool.map(self.session.confirm, [preview["validation_id"]] * 2))
        self.assertEqual(receipts[0], receipts[1])
        self.assertEqual(len(list(self.project.path(".state/jobs").iterdir())), 1)
        with open(receipts[0]["config_path"], encoding="utf-8") as file:
            config = json.load(file)
        self.assertFalse(config["execution_authorized"])
        self.assertFalse(receipts[0]["execution_started"])
        self.assertEqual(config["region"], "cn-beijing")

    def test_failed_revalidation_invalidates_old_preview(self):
        previous = self.session.validate(self.payload)
        with self.assertRaises(ValidationError):
            self.session.validate({**self.payload, "audio_upload_id": "missing"})
        with self.assertRaises(ValidationError):
            self.session.confirm(previous["validation_id"])

    def test_file_changed_after_preview_cannot_be_confirmed(self):
        preview = self.session.validate(self.payload)
        uploaded = Path(self.session.uploaded(self.payload["audio_upload_id"], "audio")["path"])
        uploaded.write_bytes(uploaded.read_bytes() + b"changed")
        with self.assertRaises(ValidationError):
            self.session.confirm(preview["validation_id"])
        self.assertFalse(self.project.path(".state/jobs").exists())

    def test_api_key_is_not_written_to_config(self):
        secret = "synthetic-local-key"
        self.project.path(".env").write_text("DASHSCOPE_API_KEY=" + secret, encoding="utf-8")
        preview = self.session.validate({**self.payload, "auth_mode": "api_key"})
        receipt = self.session.confirm(preview["validation_id"])
        with open(receipt["config_path"], encoding="utf-8") as file:
            text = file.read()
        self.assertNotIn(secret, text)
        self.assertNotIn(secret, json.dumps(preview))

    def test_api_key_change_invalidates_confirmation(self):
        path = self.project.path(".env")
        path.write_text("DASHSCOPE_API_KEY=synthetic-key", encoding="utf-8")
        preview = self.session.validate({**self.payload, "auth_mode": "api_key"})
        path.write_text("DASHSCOPE_API_KEY=another-synthetic-key", encoding="utf-8")
        with self.assertRaises(ValidationError):
            self.session.confirm(preview["validation_id"])

    def test_session_and_console_do_not_read_dotenv(self):
        with patch("asr_agent.web.api_key_status", side_effect=AssertionError("must not read")):
            self.session.description()
            self.session.auth_status("console")
            self.session.validate(self.payload)

    def test_hotwords_snapshot_is_bound_to_excel_fingerprint(self):
        path = self.project.path("data/热词.xlsx")
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "热词"
        sheet.append(["text", "weight"])
        sheet.append(["术语", 50])
        workbook.save(path)
        workbook.close()
        content = path.read_bytes()
        uploaded = self.session.upload("hotwords", path.name, io.BytesIO(content), len(content))
        payload = {**self.payload, "enhancement_mode": "both", "hotwords_upload_id": uploaded["upload_id"],
                   "context": "会议涉及测试术语"}
        preview = self.session.validate(payload)
        self.assertEqual(preview["summary"]["enhancement"]["count"], 1)
        self.assertEqual(preview["summary"]["enhancement"]["context_chars"], len(payload["context"]))
        copy = Path(self.session.uploaded(uploaded["upload_id"], "hotwords")["path"])
        copy.write_bytes(copy.read_bytes() + b"change")
        with self.assertRaises(ValidationError):
            self.session.confirm(preview["validation_id"])

    def test_outputs_cannot_target_source_or_outside_project(self):
        for path in ("data/audio", "../outside", "outputs/../.git", "outputs/.private"):
            with self.subTest(path=path), self.assertRaises(ValidationError):
                output_directory(self.project, path, "json_directory")

    def test_unknown_fields_and_multiple_audio_values_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.session.validate({**self.payload, "model": "other-model"})
        with self.assertRaises(ValidationError):
            self.session.validate({**self.payload, "audio_upload_id": ["a", "b"]})

    def test_browser_source_is_not_read_again_after_upload(self):
        preview = self.session.validate(self.payload)
        self.audio.write_bytes(b"source changed outside local upload")
        receipt = self.session.confirm(preview["validation_id"])
        self.assertTrue(receipt["ok"])

    def test_reselection_invalidates_preview_and_replaces_only_own_copy(self):
        preview = self.session.validate(self.payload)
        old_copy = Path(self.session.uploaded(self.payload["audio_upload_id"], "audio")["path"])
        content = self.audio.read_bytes()
        self.session.upload("audio", "another.wav", io.BytesIO(content), len(content))
        self.assertFalse(old_copy.exists())
        self.assertTrue(self.audio.is_file())
        with self.assertRaises(ValidationError):
            self.session.confirm(preview["validation_id"])

    def test_incomplete_upload_removes_partial_copy(self):
        with self.assertRaises(ValidationError):
            self.session.upload("audio", "short.wav", io.BytesIO(b"short"), 10)
        self.assertFalse(list(self.session.upload_directory.glob("*.part")))

    def test_upload_id_cannot_be_used_by_another_session(self):
        with self.assertRaises(ValidationError):
            Session(self.project).validate(self.payload)


class WebServerTests(WebFixture):
    def setUp(self):
        super().setUp()
        self.server = create_server(self.project)
        self.payload = self.payload_for(self.server.session)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    def request(self, method, path, payload=None, *, token=True, headers=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        supplied = {"Origin": self.origin}
        if token:
            supplied["X-ASR-Token"] = self.server.session.token
        if headers:
            supplied.update(headers)
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            supplied["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=supplied)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_static_page_has_no_key_field_and_does_not_expose_files(self):
        status, headers, body = self.request("GET", "/", token=False)
        self.assertEqual(status, 200)
        self.assertNotIn(b'type="password"', body)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("GET", "/.env")[0], 404)

    def test_token_host_and_origin_are_enforced(self):
        self.assertEqual(self.request("GET", "/api/session", token=False)[0], 403)
        self.assertEqual(self.request("GET", "/api/session", headers={"X-ASR-Token": "é"})[0], 403)
        self.assertEqual(self.request("GET", "/api/session", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request("POST", "/api/validate", self.payload,
                                      headers={"Origin": "https://evil.example"})[0], 403)

    def test_second_server_cannot_reuse_live_port(self):
        with self.assertRaises(OSError):
            create_server(self.project, self.server.server_port)

    def test_cookie_restores_receipt_without_browser_storage(self):
        status, headers, _ = self.request("GET", "/api/session")
        self.assertEqual(status, 200)
        cookie = headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertNotIn("Max-Age", cookie)
        preview = json.loads(self.request("POST", "/api/validate", self.payload)[2])
        receipt = json.loads(self.request("POST", "/api/confirm", {"validation_id": preview["validation_id"]})[2])
        status, _, body = self.request("GET", "/api/session", token=False, headers={"Cookie": cookie.split(";", 1)[0]})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["confirmed"]["job_id"], receipt["job_id"])

    def test_direct_upload_and_template(self):
        status, _, body = self.request("POST", "/api/upload-audio", body=self.audio.read_bytes(),
                                      headers={"Content-Type": "application/octet-stream",
                                               "X-File-Name": quote(self.audio.name)})
        self.assertEqual(status, 200)
        uploaded = json.loads(body)
        self.assertEqual(uploaded["name"], self.audio.name)
        self.assertEqual(self.request("POST", "/api/validate",
                                      {**self.payload, "audio_upload_id": uploaded["upload_id"]})[0], 200)
        self.assertEqual(self.request("GET", "/api/files?directory=data/audio")[0], 404)
        status, _, body = self.request("GET", "/api/hotwords-template")
        self.assertEqual(status, 200)
        workbook = load_workbook(io.BytesIO(body))
        self.assertEqual(workbook["热词"]["A1"].value, "text")
        workbook.close()

    def test_upload_filename_cannot_supply_a_path(self):
        status, _, _ = self.request("POST", "/api/upload-audio", body=b"synthetic",
                                   headers={"Content-Type": "application/octet-stream",
                                            "X-File-Name": quote("../escape.wav")})
        self.assertEqual(status, 422)
        self.assertFalse(self.project.path("escape.wav").exists())

    def test_api_key_error_does_not_return_contents(self):
        status, _, body = self.request("POST", "/api/auth-status", {"auth_mode": "api_key"})
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["configured"])
        self.assertEqual(self.request("POST", "/api/validate", {**self.payload, "auth_mode": "api_key"})[0], 422)
