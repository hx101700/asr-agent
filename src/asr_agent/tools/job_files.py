"""管理任务配置、执行占用、状态记录和输出目录。"""

import hashlib
import json
import os
import re
from pathlib import Path

from .. import MODEL
from .environment import Project, SetupError
from .files import write_json_atomic


def job_directory(project: Project, job_id: str) -> Path:
    """核对回执编号与路径归属，返回任务目录。"""
    if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise SetupError("设置编号应为网页回执中的32位小写十六进制编号。")
    path = project.path(f".state/jobs/{job_id}")
    if path != project.root.resolve() / ".state/jobs" / job_id:
        raise SetupError("任务目录不能重定向。")
    return path


def publish_config(project: Project, config: dict) -> Path:
    """保存确认配置及其内容摘要，完成写入后发布配置文件。"""
    directory = job_directory(project, config["job_id"])
    directory.mkdir(parents=True, exist_ok=False)
    temporary = directory / "config.json.tmp"
    destination = directory / "config.json"
    content = (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with temporary.open("xb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    with (directory / "config.sha256").open("x", encoding="ascii") as checksum:
        checksum.write(hashlib.sha256(content).hexdigest() + "\n")
        checksum.flush()
        os.fsync(checksum.fileno())
    temporary.replace(destination)
    return destination


def read_config(project: Project, job_id: str) -> dict:
    """读取已确认配置，并核对保存协议与内容摘要。"""
    path = job_directory(project, job_id) / "config.json"
    checksum = path.with_suffix(".sha256")
    if path.resolve() != path or checksum.resolve() != checksum:
        raise SetupError("任务配置不能使用符号链接。")
    if not checksum.is_file():
        raise SetupError("此设置缺少确认摘要，请在当前网页重新检查并保存；不会自动补签或上传。")
    try:
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != checksum.read_text(encoding="ascii").strip():
            raise SetupError("已保存的配置发生变化，请重新检查并确认；未执行转写。")
        config = json.loads(content)
        valid = (config["schema_version"] == 1 and config["job_id"] == job_id
                 and config["model"] == MODEL and config["region"] == "cn-beijing"
                 and config["status"] == "CONFIGURED"
                 and config["execution_authorized"] is False and bool(config["confirmed_at"]))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SetupError("无法读取已确认的配置，请通过网页重新检查并保存。") from exc
    if not valid:
        raise SetupError("任务配置与当前模型、地域或保存协议不符，未执行。")
    return config


def reserve_execution(project: Project, job_id: str) -> Path:
    """独占创建执行目录，登记本任务的一次执行占用。"""
    path = job_directory(project, job_id) / "execution"
    path.mkdir(exist_ok=False)
    return path


def read_execution(root: Path) -> dict | None:
    """读取执行记录；已占用任务的记录缺失或损坏时返回结果未知。"""
    execution = root / "execution"
    if execution.resolve() != execution:
        raise SetupError("执行记录目录不能重定向。")
    if not execution.exists():
        return None
    try:
        report = json.loads((execution / "status.json").read_text(encoding="utf-8"))
        if (not isinstance(report, dict) or report.get("job_id") != root.name
                or report.get("status") not in ("PREPARING", "RUNNING", "STOPPED", "JSON_READY")):
            raise ValueError("invalid status")
        return report
    except (OSError, ValueError):
        return {"job_id": root.name, "status": "OUTCOME_UNKNOWN", "cloud_outcome": "unknown",
                "message": "任务已被占用但执行记录不可读，不能重新提交。请检查本地进程和记录。"}


def latest_delivery(root: Path) -> dict | None:
    """读取最近一轮本地导出记录并核对记录结构。"""
    directory = root / "exports"
    if not directory.exists():
        return None
    try:
        if directory.resolve() != directory:
            raise ValueError("redirected report")
        rounds = sorted(directory.iterdir(), reverse=True)
        if not rounds:
            return None
        if rounds[0].resolve() != rounds[0]:
            raise ValueError("redirected report")
        report = json.loads((rounds[0] / "status.json").read_text(encoding="utf-8"))
        if (not isinstance(report, dict) or report.get("job_id") != root.name
                or report.get("status") not in ("EXPORTING", "COMPLETE", "PARTIAL", "FAILED")
                or not isinstance(report.get("message"), str)):
            raise ValueError("invalid report")
        if report["status"] == "COMPLETE":
            files = report.get("files", {})
            if (set(files) != {"xlsx", "docx", "md"}
                    or any(not isinstance(record, dict) or record.get("status") != "READY"
                           or not record.get("path") for record in files.values())):
                raise ValueError("incomplete delivery")
        return report
    except (OSError, ValueError, TypeError):
        return {"status": "OUTCOME_UNKNOWN", "message": "本地导出记录不可读，请检查已有文件；不会重新识别或自动导出。"}


def reserve_export(root: Path, export_id: str) -> Path:
    """独占创建本轮导出记录目录，保留历史轮次。"""
    state = root / "exports" / export_id
    if state.resolve() != state:
        raise SetupError("导出记录目录不能重定向。")
    state.mkdir(parents=True, exist_ok=False)
    return state


def result_path(config: dict) -> Path:
    """解析已确认的JSON保存路径，并核对任务目录归属。"""
    directory = Path(config["json_directory"])
    if (not directory.is_absolute() or directory.name != "json"
            or directory.parent.name != config["job_id"] or directory.resolve() != directory):
        raise SetupError("JSON保存位置发生变化或不是已确认的任务目录。")
    return directory / "transcription.json"


def prepare_result(path: Path) -> None:
    """独占创建JSON结果文件的保存目录。"""
    path.parent.mkdir(parents=True, exist_ok=False)


def prepare_documents(config: dict, export_id: str) -> Path:
    """核对已确认保存位置，为本轮三格式成品新建目录。"""
    base = Path(config["document_directory"])
    if (not base.is_absolute() or base.name != "documents"
            or base.parent.name != config["job_id"] or base.resolve() != base):
        raise SetupError("文档保存位置发生变化或不是已确认的任务目录。")
    destination = base / export_id
    destination.mkdir(parents=True, exist_ok=False)
    return destination


def save_record(directory: Path, report: dict) -> None:
    """原子保存本目录的执行或导出状态记录。"""
    write_json_atomic(directory / "status.json", report)
