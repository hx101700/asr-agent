"""按独立轮次导出三种文档并记录交付结果。"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..tools.documents import DocumentError, publish_document, write_docx, write_markdown, write_xlsx
from ..tools.environment import SetupError
from ..tools.job_files import prepare_documents, reserve_export, save_record
from ..models import Transcript


def export_documents(job_root: Path, config: dict, transcript: Transcript) -> dict:
    """生成本轮Excel、Word和Markdown，汇总各格式交付结果。"""
    export_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ-") + uuid.uuid4().hex[:8]
    state = reserve_export(job_root, export_id)
    report = {"job_id": config["job_id"], "export_id": export_id, "status": "EXPORTING",
              "source_sha256": transcript.sha256, "sentences": len(transcript.sentences),
              "files": {}, "message": "正在本地生成文档。"}
    save_record(state, report)
    try:
        destination = prepare_documents(config, export_id)
    except (OSError, SetupError, KeyError, TypeError) as exc:
        report.update(status="FAILED", message="无法创建文档目录，请检查已确认的保存位置、权限和磁盘空间；JSON已保留。",
                      error_type=type(exc).__name__)
        save_record(state, report)
        return report

    # 格式之间没有成功依赖；某一项失败后仍可完成其余格式，但不重试失败项。
    for extension, writer in (("xlsx", write_xlsx), ("docx", write_docx), ("md", write_markdown)):
        final = destination / f"transcription.{extension}"
        try:
            size = publish_document(writer, transcript, final, source_name=config["audio"]["name"], job_id=config["job_id"])
            report["files"][extension] = {"status": "READY", "path": str(final),
                                          "bytes": size}
        except Exception as exc:
            # 第三方序列化器可能在异常中携带正文。仅公开自有错误说明及异常类型。
            if isinstance(exc, DocumentError):
                message = str(exc)
            elif isinstance(exc, OSError):
                message = "文件保存失败，请检查目录权限、磁盘空间及文件占用；未自动重试。"
            else:
                message = f"导出程序发生异常，类型：{type(exc).__name__}；未自动重试，请联系开发者检查。"
            report["files"][extension] = {"status": "FAILED", "message": message,
                                          "error_type": type(exc).__name__}
        save_record(state, report)
    ready = sum(item["status"] == "READY" for item in report["files"].values())
    report.update(status="COMPLETE" if ready == 3 else "PARTIAL" if ready else "FAILED",
                  message="Excel、Word和Markdown已保存，Excel和Word已回读核验。" if ready == 3 else "部分或全部文档未完成；JSON及已完成文件已保留，未自动重试。")
    save_record(state, report)
    return report
