"""按已保存配置执行一次转写；云端流程完全交给BL。"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from . import MODEL
from .auth import api_key_status
from .bailian import BEIJING_BASE_URL, WAIT_SECONDS, BailianFailure, check_command_length, console_status, run_recognition
from .environment import Project, SetupError, bl_command
from .media import MediaError, convert_to_mono
from .validation import MAX_UPLOAD_BYTES, ValidationError, file_fingerprint, load_hotwords, validate_audio, validate_context, validate_options


def job_directory(project: Project, job_id: str) -> Path:
    if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise SetupError("设置编号应为网页回执中的32位小写十六进制编号。")
    directory = project.path(f".state/jobs/{job_id}")
    if directory != project.root.resolve() / ".state/jobs" / job_id:
        raise SetupError("任务目录不能重定向。")
    return directory


def read_config(project: Project, job_id: str) -> dict:
    path = job_directory(project, job_id) / "config.json"
    if path.is_symlink():
        raise SetupError("任务配置不能使用符号链接。")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
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
    return report


def _upload_root(project: Project, record: dict) -> Project:
    path = Path(record["path"])
    base = project.path(".state/web-uploads")
    if (not path.is_absolute() or not path.is_relative_to(base)
            or len(path.relative_to(base).parts) != 2 or path.resolve() != path):
        raise SetupError("输入文件不是网页保存的本机会话副本，请重新选择。")
    return Project(path.parent)


def _output_path(config: dict) -> Path:
    directory = Path(config["json_directory"])
    if (not directory.is_absolute() or directory.name != "json"
            or directory.parent.name != config["job_id"] or directory.resolve() != directory):
        raise SetupError("JSON保存位置发生变化或不是已确认的任务目录。")
    return directory / "transcription.json"


def prepare_input(project: Project, config: dict, execution: Path) -> tuple[list[str], list[str], Path]:
    """复用S2校验；不信任旧媒体元信息，也不静默省略增强参数。"""
    mode = config["auth_mode"]
    if mode not in ("console", "api_key"):
        raise SetupError("配置的鉴权方式无效。")
    status = api_key_status(project) if mode == "api_key" else console_status(project)
    if not status["configured"]:
        raise SetupError(status["message"])
    audio_record = config["audio"]
    upload_root = _upload_root(project, audio_record)
    audio = validate_audio(upload_root, audio_record["path"], config["diarization_enabled"])
    if audio["fingerprint"] != audio_record["fingerprint"]:
        raise SetupError("保存设置后的音频已改变，请重新选择并确认；未上传。")
    options = config["recognition_options"]
    languages = options["language_hints"]
    if not isinstance(languages, list) or len(languages) > 1:
        raise SetupError("当前BL仅支持一个语言提示，请重新配置。")
    validate_options({"language_hint": languages[0] if languages else None,
                      "speaker_count": options["speaker_count"]}, config["diarization_enabled"])
    source = Path(audio["path"])
    prepared = execution / "mono.flac" if audio["requires_mono"] else source
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
        words = load_hotwords(_upload_root(project, hotwords), hotwords["path"])
        if words["fingerprint"] != hotwords["fingerprint"]:
            raise SetupError("保存设置后的词表已改变，请重新选择并确认；未上传。")
        arguments.extend(["--vocabulary", json.dumps(words["vocabulary"], ensure_ascii=False, separators=(",", ":"))])
        private.extend(words["vocabulary"])
    context = enhancement["context"]
    if (context is not None) != (enhancement_mode in ("context", "both")):
        raise SetupError("上下文配置不完整，请重新确认。")
    if context is not None:
        arguments.extend(["--context", validate_context(context)])
        private.append(context)
    check_command_length(bl_command(project, arguments))
    # 先拒绝不可启动的参数；通过后才做可能耗时的本地声道合并。
    if audio["requires_mono"]:
        convert_to_mono(source, prepared)
        converted = validate_audio(Project(execution), prepared, True)
        if converted["metadata"]["channels"] != 1 or converted["metadata"]["size_bytes"] > MAX_UPLOAD_BYTES:
            raise SetupError("单声道副本检查不通过，未上传。")
        if file_fingerprint(source) != audio["fingerprint"]:
            raise SetupError("声道处理期间源文件改变，未上传。")
    destination.parent.mkdir(parents=True, exist_ok=False)
    return arguments, private, destination


def inspect_result(path: Path) -> dict:
    """只检查官方句子结构；保留全部音轨，不提前实施导出或猜测字段别名。"""
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(result, dict) or not isinstance(result["transcripts"], list):
            raise ValueError("unexpected document")
        sentences = 0
        nonempty = 0
        for track in result["transcripts"]:
            if not isinstance(track, dict) or not isinstance(track["sentences"], list):
                raise ValueError("unexpected track")
            for sentence in track["sentences"]:
                begin, end = sentence["begin_time"], sentence["end_time"]
                if (type(begin) is not int or type(end) is not int or not 0 <= begin <= end
                        or not isinstance(sentence["text"], str)):
                    raise ValueError("unexpected sentence")
                speaker = sentence.get("speaker_id")
                if speaker is not None and (type(speaker) is not int or speaker < 0):
                    raise ValueError("unexpected speaker")
                sentences += 1
                nonempty += bool(sentence["text"].strip())
        if not nonempty:
            raise ValueError("no usable transcript")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SetupError("BL未生成可用的转写JSON，或结果结构不符合已核实契约。已保留现有文件；未推断失败原因，未重新识别。") from exc
    return {"audio_tracks": len(result["transcripts"]), "sentences": sentences,
            "json_bytes": path.stat().st_size}


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
        arguments, private, destination = prepare_input(project, config, execution)
        report.update(status="RUNNING", cloud_outcome="unknown", message="BL正在执行上传、识别、等待及结果保存。")
        _save_status(execution, report)
        run_recognition(project, arguments, config["auth_mode"], private)
        result = inspect_result(destination)
        report.update(status="JSON_READY", cloud_outcome="result_received", json_path=str(destination), result=result,
                      message="BL已结束，转写JSON已保存并通过结构检查；Excel、Word和Markdown导出尚未接入。")
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
    return report
