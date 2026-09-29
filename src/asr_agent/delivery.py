"""本地文档交付：每次显式导出独立留档，逐项成功，不触发云端操作。"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .documents import DocumentError, write_docx, write_markdown, write_xlsx
from .environment import SetupError
from .results import Transcript


def _save_report(directory: Path, report: dict) -> None:
    temporary = directory / "status.json.tmp"
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(directory / "status.json")


def latest_delivery(job_root: Path) -> dict | None:
    directory = job_root / "exports"
    if not directory.exists():
        return None
    # 每轮使用带时间的独立目录；并发导出互不覆盖，最新发起的一轮代表当前交付。
    try:
        if directory.resolve() != directory:
            raise ValueError("redirected report")
        rounds = sorted(directory.iterdir(), reverse=True)
        if not rounds:
            return None
        if rounds[0].resolve() != rounds[0]:
            raise ValueError("redirected report")
        report = json.loads((rounds[0] / "status.json").read_text(encoding="utf-8"))
        if (not isinstance(report, dict) or report.get("job_id") != job_root.name
                or report.get("status") not in ("EXPORTING", "COMPLETE", "PARTIAL", "FAILED")
                or not isinstance(report.get("message"), str)):
            raise ValueError("invalid report")
        if report["status"] == "COMPLETE":
            files = report.get("files", {})
            if (set(files) != {"xlsx", "docx", "md"}
                    or any(not isinstance(record, dict) or record.get("status") != "READY"
                           or not record.get("path") for record in files.values())):
                raise ValueError("incomplete delivery")
        if report["status"] == "EXPORTING":
            report["message"] = "这是最近保存的导出状态，不代表进程仍在运行。请检查原进程和已完成文件；不会自动重试。"
        return report
    except (OSError, ValueError, TypeError):
        return {"status": "OUTCOME_UNKNOWN", "message": "本地导出记录不可读，请检查已有文件；不会重新识别或自动导出。"}


def export_documents(job_root: Path, config: dict, transcript: Transcript) -> dict:
    export_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ-") + uuid.uuid4().hex[:8]
    state = job_root / "exports" / export_id
    if state.resolve() != state:
        raise SetupError("导出记录目录不能重定向。")
    state.mkdir(parents=True, exist_ok=False)
    report = {"job_id": config["job_id"], "export_id": export_id, "status": "EXPORTING",
              "source_sha256": transcript.sha256, "sentences": len(transcript.sentences),
              "files": {}, "message": "正在本地生成文档。"}
    _save_report(state, report)
    try:
        base = Path(config["document_directory"])
        if (not base.is_absolute() or base.name != "documents"
                or base.parent.name != config["job_id"] or base.resolve() != base):
            raise SetupError("文档保存位置发生变化或不是已确认的任务目录。")
        destination = base / export_id
        destination.mkdir(parents=True, exist_ok=False)
    except (OSError, SetupError, KeyError, TypeError) as exc:
        report.update(status="FAILED", message="无法创建文档目录，请检查已确认的保存位置、权限和磁盘空间；JSON已保留。",
                      error_type=type(exc).__name__)
        _save_report(state, report)
        return report

    # 格式之间没有成功依赖；某一项失败后仍可完成其余格式，但不重试失败项。
    for extension, writer in (("xlsx", write_xlsx), ("docx", write_docx), ("md", write_markdown)):
        final = destination / f"transcription.{extension}"
        temporary = destination / f"transcription.partial.{extension}"
        try:
            writer(transcript, temporary, source_name=config["audio"]["name"], job_id=config["job_id"])
            digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
            temporary.replace(final)
            report["files"][extension] = {"status": "READY", "path": str(final),
                                          "bytes": final.stat().st_size, "sha256": digest}
        except Exception as exc:
            # 第三方序列化器可能在异常中携带正文。仅公开自有错误说明及异常类型。
            message = str(exc) if isinstance(exc, DocumentError) else "文件生成或检查失败，请检查目录权限、磁盘空间及本地依赖。"
            report["files"][extension] = {"status": "FAILED", "message": message,
                                          "error_type": type(exc).__name__}
        _save_report(state, report)
    ready = sum(item["status"] == "READY" for item in report["files"].values())
    report.update(status="COMPLETE" if ready == 3 else "PARTIAL" if ready else "FAILED",
                  message="Excel、Word和Markdown已保存并通过内容检查。" if ready == 3 else "部分或全部文档未完成；JSON及已完成文件已保留，未自动重试。")
    _save_report(state, report)
    return report
