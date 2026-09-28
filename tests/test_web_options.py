import http.client
import io
import json
import threading
import wave
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from openpyxl import Workbook

from asr_agent.environment import Project
from asr_agent.validation import ValidationError
from asr_agent.web import Session, create_server
from tests.support import ProjectTestCase


class OptionsFixture(ProjectTestCase):
    def setUp(self):
        super().setUp()
        # 用工作区内同一临时根的兄弟目录模拟用户选中项目外的保存位置。
        temporary_root = self.project.root
        self.project = Project(temporary_root / "agent")
        self.project.root.mkdir()
        self.selected = temporary_root / "selected"
        self.selected.mkdir()
        self.other = temporary_root / "other"
        self.other.mkdir()

    def payload_for(self, session):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\0" * 32000)
        content = buffer.getvalue()
        uploaded = session.upload("audio", "synthetic.wav", io.BytesIO(content), len(content))
        return {
            "auth_mode": "console", "audio_upload_id": uploaded["upload_id"],
            "diarization_enabled": True, "enhancement_mode": "none",
            "hotwords_upload_id": "", "context": "",
            "json_directory": "outputs", "document_directory": "outputs",
        }

    def select(self, session, kind, destination):
        with patch("asr_agent.web.choose_directory", return_value=destination) as picker:
            result = session.select_directory(kind)
        picker.assert_called_once()
        return result


class DirectoryOptionTests(OptionsFixture):
    def setUp(self):
        super().setUp()
        self.session = Session(self.project)
        self.payload = self.payload_for(self.session)

    def test_selected_external_directory_is_saved_without_producing_outputs(self):
        for kind in ("json", "document"):
            result = self.select(self.session, kind, self.selected)
            self.assertEqual(result["path"], str(self.selected))
            self.assertFalse(result["cancelled"])
        preview = self.session.validate({
            **self.payload, "json_directory": str(self.selected),
            "document_directory": str(self.selected),
        })
        receipt = self.session.confirm(preview["validation_id"])
        config = json.loads(Path(receipt["config_path"]).read_text(encoding="utf-8"))
        for field in ("json_directory", "document_directory"):
            self.assertTrue(Path(config[field]).is_relative_to(self.selected))
        self.assertFalse(config["execution_authorized"])
        self.assertFalse(receipt["execution_started"])
        self.assertEqual(list(self.selected.iterdir()), [])
        self.assertFalse(self.project.path("outputs").exists())

    def test_browser_cannot_register_external_directory_by_submitting_path(self):
        with self.assertRaises(ValidationError):
            self.session.validate({**self.payload, "json_directory": str(self.selected)})
        self.assertEqual(self.session.output_directories, {})
        self.assertEqual(list(self.selected.iterdir()), [])

    def test_directory_approval_is_bound_to_kind_and_exact_directory(self):
        self.select(self.session, "json", self.selected)
        for changes in (
            {"document_directory": str(self.selected)},
            {"json_directory": str(self.other)},
            {"json_directory": str(self.selected / "child")},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.session.validate({**self.payload, **changes})

    def test_cancel_keeps_selected_directory_and_existing_preview(self):
        self.select(self.session, "json", self.selected)
        preview = self.session.validate({**self.payload, "json_directory": str(self.selected)})
        result = self.select(self.session, "json", None)
        self.assertTrue(result["cancelled"])
        self.assertEqual(self.session.output_directories["json"], self.selected)
        self.assertEqual(self.session.draft["id"], preview["validation_id"])
        self.assertTrue(self.session.confirm(preview["validation_id"])["ok"])

    def test_switching_directory_invalidates_existing_preview(self):
        self.select(self.session, "json", self.selected)
        preview = self.session.validate({**self.payload, "json_directory": str(self.selected)})
        self.select(self.session, "json", self.other)
        self.assertEqual(self.session.output_directories["json"], self.other)
        with self.assertRaises(ValidationError):
            self.session.confirm(preview["validation_id"])
        self.assertFalse(self.project.path(".state/jobs").exists())

    def test_cancel_waiting_picker_keeps_previous_preview_and_releases_lock(self):
        preview = self.session.validate(self.payload)
        started = threading.Event()

        def blocked_picker(_initial, *, cancel_event):
            started.set()
            self.assertTrue(cancel_event.wait(timeout=3))
            return self.selected  # 即使同时收到结果，也不能把已取消的选择登记下来。

        with patch("asr_agent.web.choose_directory", side_effect=blocked_picker):
            with ThreadPoolExecutor(max_workers=1) as pool:
                selected = pool.submit(self.session.select_directory, "json", "picker-current")
                self.assertTrue(started.wait(timeout=3))
                self.session.cancel_directory("picker-old")
                self.assertFalse(self.session.picker_cancel_event.is_set())
                self.session.cancel_directory("picker-current")
                self.assertTrue(selected.result(timeout=3)["cancelled"])
        self.assertEqual(self.session.output_directories, {})
        self.assertEqual(self.session.draft["id"], preview["validation_id"])
        self.assertFalse(self.session.picker_lock.locked())
        self.assertFalse(self.select(self.session, "json", self.selected)["cancelled"])

    def test_cancel_arriving_before_open_prevents_window_but_not_next_request(self):
        self.session.cancel_directory("early-cancel")
        with patch("asr_agent.web.choose_directory", return_value=self.selected) as picker:
            self.assertTrue(self.session.select_directory("json", "early-cancel")["cancelled"])
            picker.assert_not_called()
            self.assertFalse(self.session.select_directory("json", "next-request")["cancelled"])
            picker.assert_called_once()

    def test_language_speakers_and_combined_enhancement_survive_confirmation(self):
        workbook = Workbook()
        workbook.active.append(["text", "weight"])
        workbook.active.append(["测试术语", 4])
        buffer = io.BytesIO()
        workbook.save(buffer)
        workbook.close()
        content = buffer.getvalue()
        uploaded = self.session.upload("hotwords", "synthetic.xlsx", io.BytesIO(content), len(content))
        preview = self.session.validate({
            **self.payload, "language_hint": "zh", "speaker_count": 3,
            "enhancement_mode": "both", "hotwords_upload_id": uploaded["upload_id"],
            "context": "本次会议讨论测试术语。",
        })
        expected = {"language_hints": ["zh"], "speaker_count": 3}
        self.assertEqual(preview["summary"]["recognition_options"], expected)
        self.assertEqual(preview["summary"]["enhancement"]["mode"], "both")
        receipt = self.session.confirm(preview["validation_id"])
        config = json.loads(Path(receipt["config_path"]).read_text(encoding="utf-8"))
        self.assertEqual(config["recognition_options"], expected)
        self.assertEqual(config["enhancement"]["hotwords"]["count"], 1)
        self.assertEqual(config["enhancement"]["context"], "本次会议讨论测试术语。")
        self.assertFalse(config["execution_authorized"])


class ProtectedOptionsEndpointTests(OptionsFixture):
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

    def request(self, method, path, payload=None, *, token=True, origin=None):
        headers = {"Origin": origin or self.origin}
        if token:
            headers["X-ASR-Token"] = self.server.session.token
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_directory_route_uses_native_selection_and_ignores_browser_path(self):
        with patch("asr_agent.web.choose_directory", return_value=self.selected) as picker:
            status, _, body = self.request("POST", "/api/select-directory", {
                "kind": "document", "path": str(self.other),
            })
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["path"], str(self.selected))
        self.assertEqual(self.server.session.output_directories["document"], self.selected)
        picker.assert_called_once()
        self.assertEqual(list(self.selected.iterdir()), [])
        self.assertEqual(list(self.other.iterdir()), [])

    def test_new_routes_require_token_and_correct_origin_before_any_action(self):
        with patch("asr_agent.web.choose_directory") as picker, \
             patch("asr_agent.web.read_api_key") as read_key:
            for route, payload in (("/api/select-directory", {"kind": "json"}), ("/api/api-key", {}),
                                   ("/api/cancel-directory", {"picker_id": "protected-picker"})):
                with self.subTest(route=route):
                    self.assertEqual(self.request("POST", route, payload, token=False)[0], 403)
                    self.assertEqual(self.request("POST", route, payload, origin="https://example.invalid")[0], 403)
        picker.assert_not_called()
        read_key.assert_not_called()

    def test_key_is_returned_only_by_dedicated_post_and_never_saved(self):
        secret = "synthetic-display-key"
        self.project.path(".env").write_text("DASHSCOPE_API_KEY=" + secret, encoding="utf-8")
        status, headers, body = self.request("POST", "/api/api-key", {})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["value"], secret)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.request("GET", "/api/api-key")[0], 404)

        for method, route, payload in (
            ("GET", "/api/session", None),
            ("POST", "/api/auth-status", {"auth_mode": "api_key"}),
        ):
            status, _, body = self.request(method, route, payload)
            self.assertEqual(status, 200)
            self.assertNotIn(secret.encode("utf-8"), body)

        status, _, body = self.request("POST", "/api/validate", {**self.payload, "auth_mode": "api_key"})
        self.assertEqual(status, 200)
        self.assertNotIn(secret.encode("utf-8"), body)
        preview = json.loads(body)
        status, _, body = self.request("POST", "/api/confirm", {"validation_id": preview["validation_id"]})
        self.assertEqual(status, 200)
        self.assertNotIn(secret.encode("utf-8"), body)
        config = Path(json.loads(body)["config_path"]).read_text(encoding="utf-8")
        self.assertNotIn(secret, config)
        self.assertNotIn(secret.encode("utf-8"), self.request("GET", "/api/session")[2])
