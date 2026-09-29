"""按已保存配置执行一次转写；云端流程完全交给BL。"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from . import MODEL
from .bailian import BEIJING_BASE_URL, WAIT_SECONDS, BailianFailure, PreparedCommand, prepare_command, run_recognition
from .environment import Project, SetupError
from .results import Transcript, load_transcript
from .delivery import export_documents, latest_delivery
from .media import MediaError, convert_to_mono
from .validation import ValidationError, check_audio_limits, file_fingerprint


def job_directory(project: Project, job_id: str) -> Path:
    if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise SetupError("设置编号应为网页回执中的32位小写十六进制编号。")
    directory = project.path(f".state/jobs/{job_id}")
    if directory != project.root.resolve() / ".state/jobs" / job_id:
        raise SetupError("任务目录不能重定向。")
    return directory


def read_config(project: Project, job_id: str) -> dict:
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


def _save_status(directory: Path, report: dict) -> None:
    report["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = directory / "status.json.tmp"
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(directory / "status.json")


def job_status(project: Project, job_id: str) -> dict:
    """仅查看本地记录，不向云端查询，也不由记录推断进程仍然存活。"""
    root = job_directory(project, job_id)
    execution = root / "execution"
    if execution.resolve() != execution:
        raise SetupError("执行记录目录不能重定向。")
    if not execution.exists():
        read_config(project, job_id)
        return {"job_id": job_id, "status": "CONFIGURED", "execution_authorized": False,
                "message": "设置已保存，尚未授权执行。"}
    try:
        report = json.loads((execution / "status.json").read_text(encoding="utf-8"))
        if (not isinstance(report, dict) or report.get("job_id") != job_id
                or report.get("status") not in ("PREPARING", "RUNNING", "STOPPED", "JSON_READY")):
            raise ValueError("invalid status")
    except (OSError, ValueError):
        return {"job_id": job_id, "status": "OUTCOME_UNKNOWN", "cloud_outcome": "unknown",
                "message": "任务已被占用但执行记录不可读，不能重新提交。请检查本地进程和记录。"}
    if report["status"] in ("PREPARING", "RUNNING"):
        report["message"] = "这是最近保存的执行状态，不代表进程仍存活。请检查原执行进程，勿重新提交。"
    return _with_delivery(root, report)


def _with_delivery(root: Path, report: dict) -> dict:
    delivery = latest_delivery(root)
    if delivery is not None:
        _attach_delivery(report, delivery)
    return report


def _attach_delivery(report: dict, delivery: dict) -> dict:
    report.update(delivery=delivery, documents_ready=delivery["status"] == "COMPLETE",
                  message=delivery["message"])
    return report


def _deliver(project: Project, config: dict, transcript: Transcript, report: dict) -> dict:
    try:
        delivery = export_documents(job_directory(project, config["job_id"]), config, transcript)
    except (OSError, SetupError, KeyboardInterrupt) as exc:
        # 即使状态文件也无法写入，仍把已保存的JSON交给调用者，不能误报识别失败。
        delivery = {"status": "OUTCOME_UNKNOWN", "error_type": type(exc).__name__,
                    "message": "本地导出中断或记录无法保存。JSON及已生成文件已保留，请检查目录权限、空间和文件；未重新识别。"}
    # 返回本次调用的轮次；并行发起的另一轮不能替换本调用的回执。
    return _attach_delivery(report, delivery)


def export_job(project: Project, job_id: str) -> dict:
    """已有结果的显式本地导出入口；不读取Key、原音频或热词，也不调用BL。"""
    config = read_config(project, job_id)
    report = job_status(project, job_id)
    if report["status"] != "JSON_READY":
        raise SetupError("任务尚无通过检查的JSON，不能导出；不会自动重新识别。")
    transcript = load_transcript(_output_path(config))
    expected = report.get("result", {}).get("sha256")
    if expected is not None and transcript.sha256 != expected:
        raise SetupError("转写JSON在验收后发生变化，未导出；请先检查原结果。")
    return _deliver(project, config, transcript, report)


def _check_input(project: Project, record: dict) -> Path:
    path = Path(record["path"])
    base = project.path(".state/web-uploads")
    if (not path.is_absolute() or not path.is_relative_to(base)
            or len(path.relative_to(base).parts) != 2 or path.resolve() != path):
        raise SetupError("输入文件不是网页保存的本机会话副本，请重新选择。")
    if file_fingerprint(path) != record["fingerprint"]:
        raise SetupError("保存设置后的输入文件已改变，请重新选择并确认；未上传。")
    return path


def _output_path(config: dict) -> Path:
    directory = Path(config["json_directory"])
    if (not directory.is_absolute() or directory.name != "json"
            or directory.parent.name != config["job_id"] or directory.resolve() != directory):
        raise SetupError("JSON保存位置发生变化或不是已确认的任务目录。")
    return directory / "transcription.json"


def prepare_input(project: Project, config: dict, execution: Path) -> tuple[PreparedCommand, list[str], Path]:
    """复用未变更的S2快照；只复核输入指纹，并验收新生成的音频副本。"""
    mode = config["auth_mode"]
    if mode not in ("console", "api_key"):
        raise SetupError("配置的鉴权方式无效。")
    audio_record = config["audio"]
    source = _check_input(project, audio_record)
    options = config["recognition_options"]
    languages = options["language_hints"]
    if not isinstance(languages, list) or len(languages) > 1:
        raise SetupError("当前BL仅支持一个语言提示，请重新配置。")
    prepared = execution / "mono.flac" if audio_record["requires_mono"] else source
    destination = _output_path(config)
    arguments = ["speech", "recognize", "--config", "default", "--model", MODEL, "--url", str(prepared),
                 "--base-url", BEIJING_BASE_URL, "--out", str(destination),
                 "--timeout", str(WAIT_SECONDS), "--poll-interval", "5", "--output", "json"]
    if config["diarization_enabled"]:
        arguments.append("--diarization")
    if languages:
        arguments.extend(["--language", languages[0]])
    if options["speaker_count"] is not None:
        arguments.extend(["--speaker-count", str(options["speaker_count"])])
    enhancement = config["enhancement"]
    enhancement_mode = enhancement["mode"]
    if enhancement_mode not in ("none", "hotwords", "context", "both"):
        raise SetupError("增强方式无效。")
    private = [str(source), audio_record.get("name", source.name)]
    hotwords = enhancement["hotwords"]
    if (hotwords is not None) != (enhancement_mode in ("hotwords", "both")):
        raise SetupError("热词配置不完整，请重新确认。")
    if hotwords is not None:
        _check_input(project, hotwords)
        arguments.extend(["--vocabulary", json.dumps(hotwords["vocabulary"], ensure_ascii=False, separators=(",", ":"))])
        private.extend(hotwords["vocabulary"])
    context = enhancement["context"]
    if (context is not None) != (enhancement_mode in ("context", "both")):
        raise SetupError("上下文配置不完整，请重新确认。")
    if context is not None:
        arguments.extend(["--context", context])
        private.append(context)
    command = prepare_command(project, arguments, mode)
    # 先拒绝不可启动的参数；通过后才做可能耗时的本地声道合并。
    if audio_record["requires_mono"]:
        converted = convert_to_mono(source, prepared)
        check_audio_limits(converted, True)
        if file_fingerprint(source) != audio_record["fingerprint"]:
            raise SetupError("声道处理期间源文件改变，未上传。")
    destination.parent.mkdir(parents=True, exist_ok=False)
    return command, private, destination


def transcribe(project: Project, job_id: str, *, authorize_upload: bool = False) -> dict:
    if not authorize_upload:
        raise SetupError("保存设置不等于授权上传。需用户明确同意后，使用--authorize-upload执行本次任务。")
    config = read_config(project, job_id)
    execution = job_directory(project, job_id) / "execution"
    try:
        # 目录是一次执行的持久占用标记，成功、失败、崩溃后都不删除或自动重试。
        execution.mkdir(exist_ok=False)
    except FileExistsError:
        return job_status(project, job_id)
    report = {"job_id": job_id, "status": "PREPARING", "execution_authorized": True,
              "authorization_source": "explicit_cli_flag", "cloud_outcome": "not_started",
              "started_at": datetime.now(timezone.utc).isoformat(), "task_id": None,
              "executor_pid": os.getpid(), "documents_ready": False}
    _save_status(execution, report)
    destination = None
    try:
        project.prepare()
        command, private, destination = prepare_input(project, config, execution)
        report.update(status="RUNNING", cloud_outcome="unknown", message="BL正在执行上传、识别、等待及结果保存。")
        _save_status(execution, report)
        run_recognition(project, command, private)
        transcript = load_transcript(destination)
        result = transcript.summary()
        report.update(status="JSON_READY", cloud_outcome="result_received", json_path=str(destination), result=result,
                      message="BL已结束，转写JSON已保存并通过结构检查；等待本地导出。")
    except BailianFailure as exc:
        outcome = "unknown" if report["status"] == "RUNNING" and exc.started else "not_started"
        message = ("BL执行已停止，云端结果未知；未自动重试，也未取消云端任务。" if outcome == "unknown"
                   else "BL识别尚未启动，音频未上传；未自动重试。")
        report.update(status="STOPPED", cloud_outcome=outcome,
                      error=exc.report, message=message)
    except (SetupError, ValidationError, MediaError, OSError, ValueError, KeyError, TypeError, KeyboardInterrupt) as exc:
        message = str(exc) if isinstance(exc, (SetupError, ValidationError, MediaError)) else "本地准备或结果检查未完成，请检查配置、文件权限和磁盘空间。"
        report.update(status="STOPPED", message=message,
                      error={"source": "local", "code": "LOCAL_EXECUTION_STOPPED", "explanation": message})
    if destination is not None and destination.is_file():
        report["json_path"] = str(destination)
    _save_status(execution, report)
    if report["status"] == "JSON_READY":
        # 云端成功先独立落盘。导出失败不得改写为识别失败或触发第二次BL执行。
        return _deliver(project, config, transcript, report)
    return report
