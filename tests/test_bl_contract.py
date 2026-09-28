"""真实BL发布包+本机模拟服务；不向阿里云提交任务，不使用用户音频/凭据。"""

import json
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from asr_agent import MODEL
from asr_agent.auth import bailian_environment
from asr_agent.environment import Project, bl_command
from asr_agent.probe import SYNTHETIC_AUDIO_URL
from tests.support import ROOT, ProjectTestCase


@unittest.skipUnless(Project(ROOT).bl_entry.is_file(), "需要先安装项目内BL才能运行合约测试")
class BailianContractTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.calls = []
        self.mode = "success"
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, status, payload):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                owner.authorization = self.headers.get("Authorization")
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                owner.calls.append(("POST", self.path, body))
                if owner.mode in ("submit_401", "submit_500"):
                    self.reply(int(owner.mode[-3:]), {"code": "TestFailure", "message": "synthetic failure"})
                else:
                    self.reply(200, {"output": {"task_id": "local-test-task", "task_status": "PENDING"}})

            def do_GET(self):
                owner.calls.append(("GET", self.path, None))
                if self.path == "/result.json":
                    self.reply(200, {"transcripts": [{"text": "本地模拟转写", "sentences": [{
                        "text": "本地模拟转写", "begin_time": 0, "end_time": 1000, "speaker_id": 0,
                    }]}]})
                    return
                if owner.mode == "query_500":
                    self.reply(500, {"code": "TestFailure", "message": "synthetic failure"})
                    return
                status = {"task_failed": "FAILED", "canceled": "CANCELED", "unknown": "UNKNOWN"}.get(owner.mode, "SUCCEEDED")
                result = {
                    "subtask_status": "FAILED" if owner.mode == "subtask_failed" else "SUCCEEDED",
                    "transcription_url": f"{owner.base_url}/result.json",
                    "file_url": SYNTHETIC_AUDIO_URL,
                    "message": "synthetic subtask failure",
                }
                self.reply(200, {"output": {"task_id": "local-test-task", "task_status": status,
                    "message": "synthetic task status", "results": [result]}})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    def invoke(self, mode="success"):
        self.mode = mode
        self.project.prepare()
        self.project.path(".env").write_text(
            "DASHSCOPE_API_KEY=asr-agent-synthetic-test-key\n", encoding="utf-8")
        env = bailian_environment(self.project, "api_key")
        output = self.project.path("result.json")
        arguments = [
            "speech", "recognize", "--model", MODEL, "--url", SYNTHETIC_AUDIO_URL,
            "--base-url", self.base_url, "--diarization", "--out", str(output),
            "--timeout", "1", "--poll-interval", "0.1", "--output", "json",
        ]
        # 这里运行真实CLI；Python HTTP代码仅为测试fixture，不属于产品运行路径。
        result = subprocess.run(
            bl_command(Project(ROOT), arguments), cwd=self.project.root, env=env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
            timeout=30, shell=False, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result, output

    def test_full_cli_flow_saves_json_without_exposing_task_id(self):
        result, output = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        transcript = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(transcript["transcripts"][0]["text"], "本地模拟转写")
        self.assertNotIn("local-test-task", result.stdout)
        self.assertEqual([call[0] for call in self.calls], ["POST", "GET", "GET"])
        submitted = self.calls[0][2]
        self.assertEqual(submitted["model"], MODEL)
        self.assertTrue(submitted["parameters"]["diarization_enabled"])
        self.assertEqual(self.authorization, "Bearer " + "asr-agent-synthetic-test-key")

    def test_submit_401_is_not_retried(self):
        result, output = self.invoke("submit_401")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(output.exists())

    def test_submit_500_is_not_retried(self):
        result, output = self.invoke("submit_500")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(output.exists())

    def test_query_error_stops_without_resubmission(self):
        result, output = self.invoke("query_500")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([call[0] for call in self.calls], ["POST", "GET"])
        self.assertFalse(output.exists())

    def test_task_failure_stops(self):
        result, output = self.invoke("task_failed")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.calls), 2)
        self.assertFalse(output.exists())

    def test_subtask_failure_can_exit_zero_with_empty_result(self):
        result, output = self.invoke("subtask_failed")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), [])
        self.assertIn("[FAILED]", result.stdout)
        self.assertEqual(len(self.calls), 2)

    def test_canceled_task_times_out_without_resubmission(self):
        result, output = self.invoke("canceled")
        self.assertEqual(result.returncode, 5, result.stderr)
        self.assertGreaterEqual(sum(call[0] == "GET" for call in self.calls), 2)
        self.assertEqual(sum(call[0] == "POST" for call in self.calls), 1)
        self.assertFalse(output.exists())

    def test_unknown_task_times_out_without_resubmission(self):
        result, output = self.invoke("unknown")
        self.assertEqual(result.returncode, 5, result.stderr)
        self.assertGreaterEqual(sum(call[0] == "GET" for call in self.calls), 2)
        self.assertEqual(sum(call[0] == "POST" for call in self.calls), 1)
        self.assertFalse(output.exists())
