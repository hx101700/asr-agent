"""验证保存后修改设置及旧任务停止的真实文件协议。"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import threading
from unittest.mock import patch

from asr_runtime.application.rules import ValidationError
from asr_runtime.application.session import Session
from asr_runtime.application.transcription import job_status, transcribe
from asr_runtime.utils.job_files import reserve_execution, save_record
from tests.test_web import WebFixture


class ReconfigureTests(WebFixture):
    def setUp(self):
        """保存带可编辑词表和上下文的本机配置。"""
        super().setUp()
        self.session = Session(self.runtime)
        self.addCleanup(self.session.cleanup)
        self.form = {**self.payload_for(self.session), "enhancement_mode": "both",
                     "hotword_rows": [{"row": 2, "text": "Kubernetes", "weight": "4"}],
                     "context": "录音讨论 Kubernetes。"}
        preview = self.session.validate(self.form)
        self.receipt = self.session.confirm(preview["validation_id"])

    def test_reopen_preserves_inputs_and_stops_old_receipt_before_upload(self):
        """验证返回修改保留原输入、使旧编号停止，并允许新配置保存。"""
        old_id = self.receipt["job_id"]
        restored = self.session.reopen(old_id)
        self.assertEqual(restored["configuration"], self.form)
        self.assertEqual(restored["audio"]["upload_id"], self.form["audio_upload_id"])
        self.assertIsNone(self.session.description()["confirmed"])
        with patch("asr_runtime.application.transcription.run_recognition") as run:
            result = transcribe(self.runtime, old_id, authorize_upload=True)
        run.assert_not_called()
        self.assertEqual(result["status"], "STOPPED")
        self.assertEqual(result["error"]["code"], "LOCAL_CONFIG_REOPENED")
        self.assertEqual(result["cloud_outcome"], "not_started")
        revised = {**restored["configuration"], "context": "修改后的参考文本"}
        preview = self.session.validate(revised)
        receipt = self.session.confirm(preview["validation_id"])
        self.assertNotEqual(receipt["job_id"], old_id)
        config = json.loads(Path(receipt["config_path"]).read_text(encoding="utf-8"))
        self.assertEqual(config["enhancement"]["context"], revised["context"])
        self.assertTrue(Path(config["audio"]["path"]).exists())
        self.assertEqual(job_status(self.runtime, old_id)["status"], "STOPPED")

    def test_started_task_keeps_its_receipt_and_execution_record(self):
        """验证任务开始后返回修改被拒绝，原任务状态和页面回执保留。"""
        execution = reserve_execution(self.runtime, self.receipt["job_id"])
        report = {"job_id": self.receipt["job_id"], "status": "RUNNING", "cloud_outcome": "unknown"}
        save_record(execution, report)
        before = (execution / "status.json").read_bytes()
        with self.assertRaisesRegex(ValidationError, "已进入执行流程"):
            self.session.reopen(self.receipt["job_id"])
        self.assertEqual(self.session.receipt, self.receipt)
        self.assertEqual((execution / "status.json").read_bytes(), before)

    def test_reopen_can_restore_again_when_first_response_was_lost(self):
        """验证撤回已生效而响应丢失时，同一编号可再次取得恢复数据。"""
        first = self.session.reopen(self.receipt["job_id"])
        second = self.session.reopen(self.receipt["job_id"])
        self.assertEqual(second, first)
        self.assertEqual(second["configuration"], self.form)
        self.assertEqual(job_status(self.runtime, self.receipt["job_id"])["status"], "STOPPED")

    def test_new_preview_ends_the_previous_reopen_recovery(self):
        """验证开始新的预览后不再返回旧撤回数据。"""
        self.session.reopen(self.receipt["job_id"])
        self.session.validate(self.form)
        with self.assertRaises(ValidationError):
            self.session.reopen(self.receipt["job_id"])

    def test_reopen_and_execution_reservation_have_one_winner(self):
        """验证网页撤回与终端执行同时到达时共用一次执行占用。"""
        barrier = threading.Barrier(2)

        def reopen():
            """同步发起网页撤回并返回是否取得占用。"""
            barrier.wait()
            try:
                self.session.reopen(self.receipt["job_id"])
                return True
            except ValidationError:
                return False

        def execute():
            """同步申请终端执行占用并返回是否取得。"""
            barrier.wait()
            try:
                reserve_execution(self.runtime, self.receipt["job_id"])
                return True
            except FileExistsError:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(reopen)
            second = pool.submit(execute)
            self.assertEqual(sum((first.result(timeout=5), second.result(timeout=5))), 1)

    def test_unknown_receipt_cannot_withdraw_saved_task(self):
        """验证错误编号不能撤回当前页面的任务。"""
        with self.assertRaises(ValidationError):
            self.session.reopen("0" * 32)
        self.assertEqual(job_status(self.runtime, self.receipt["job_id"])["status"], "CONFIGURED")
