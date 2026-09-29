"""本地配置用例与会话状态；不依赖HTTP处理器或浏览器元素。"""

import hashlib
import json
import os
import secrets
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import MODEL
from .auth import api_key_status, read_api_key
from .directory_picker import DirectoryPicker
from .environment import Project, SetupError
from .validation import (
    AUDIO_SUFFIXES, MAX_XLSX_BYTES, ValidationError, file_fingerprint, load_hotwords,
    resolve_input, validate_audio, validate_context, LANGUAGES, validate_options,
    MAX_CONTEXT_CHARS, MIN_SPEAKERS, MAX_SPEAKERS,
)

MAX_LOCAL_AUDIO_BYTES = 2_000_000_000


def output_directory(project: Project, value: str, field: str, approved: Path | None = None) -> Path:
    """默认目录留在项目内；外部目录必须来自本会话的系统选择窗口。"""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("请输入输出目录。", field)
    base = project.root.resolve() / "outputs"
    try:
        if base.resolve() != base:
            raise ValidationError("outputs根目录不能重定向到其他目录。", field)
        path = (project.root / value).resolve()
        chosen = approved is not None and path == approved and approved.resolve() == approved
        if not chosen and (not path.is_relative_to(base) or any(part.startswith(".") for part in path.relative_to(base).parts)):
            raise ValidationError("请点击“选择文件夹”设置保存位置。", field)
        if chosen and not path.is_dir():
            raise ValidationError("所选文件夹已不存在，请重新选择。", field)
        if any(Path(part).is_reserved() for part in path.parts):
            raise ValidationError("输出目录包含系统保留名称。", field)
        parent = path
        while not parent.exists():
            parent = parent.parent
        if not parent.is_dir():
            raise ValidationError("输出路径或其上级已存在同名文件。", field)
        with tempfile.TemporaryFile(dir=parent):
            pass
        return path
    except (OSError, SetupError) as exc:
        raise ValidationError("此文件夹无法保存文件，请选择其他位置。", field) from exc


class Session:
    def __init__(self, project: Project):
        self.project = project
        self.token = secrets.token_urlsafe(32)
        self._state_lock = threading.RLock()
        self.draft = None
        self.receipt = None
        self.upload_directory = project.root.resolve() / ".state/web-uploads" / uuid.uuid4().hex
        self.uploads = {}
        self.output_directories = {}
        self._picker = DirectoryPicker()
        self._closed = threading.Event()
        self._pending_uploads = {}

    def _require_open(self) -> None:
        if self._closed.is_set():
            raise ValidationError("当前会话已关闭。", "session")

    def _require_editable(self) -> None:
        self._require_open()
        if self.receipt:
            raise ValidationError("本会话已保存配置，请新建任务。", "session")

    def _require_uploads_complete(self) -> None:
        if self._pending_uploads:
            kind = next(iter(self._pending_uploads))
            raise ValidationError("文件仍在添加，请稍候。", f"{kind}_upload_id")

    def select_directory(self, kind: str, picker_id: str | None = None) -> dict:
        if kind not in ("json", "document"):
            raise ValidationError("未知的保存位置。", "directory")
        request_id = picker_id if picker_id is not None else uuid.uuid4().hex
        with self._state_lock:
            self._require_editable()
            initial = self.output_directories.get(kind, self.project.root / "outputs")
        while not initial.exists():
            initial = initial.parent
        try:
            selected = self._picker.select(initial, request_id)
        except SetupError as exc:
            raise ValidationError(str(exc), f"{kind}_directory") from exc
        if selected is None:
            return {"ok": True, "cancelled": True}
        path = output_directory(self.project, str(selected), f"{kind}_directory", approved=selected)
        with self._state_lock:
            self._require_editable()
            self.output_directories[kind] = path
            self.draft = None
        return {"ok": True, "cancelled": False, "path": str(path)}

    def cancel_directory(self, picker_id: str) -> dict:
        # 取消仅经过选择器自己的短锁，不等待文件接收、指纹或Excel校验。
        try:
            self._picker.cancel(picker_id)
        except SetupError as exc:
            raise ValidationError(str(exc), "directory") from exc
        return {"ok": True}

    def api_key_display(self) -> dict:
        """用户选择指定Key后，仅向受保护的本机页面提供；不写配置和日志。"""
        try:
            return {"ok": True, "value": read_api_key(self.project)}
        except (SetupError, OSError, UnicodeError) as exc:
            message = str(exc) if isinstance(exc, SetupError) else "无法读取 .env 文件。"
            raise ValidationError(message, "auth_mode") from exc

    def auth_status(self, mode: str) -> dict:
        if mode == "api_key":
            return api_key_status(self.project)
        if mode == "console":
            return {"configured": None, "verified_online": False,
                    "message": "已选择账号登录。此预览版暂不发起登录。"}
        raise ValidationError("请选择有效的鉴权方式。", "auth_mode")

    def description(self) -> dict:
        with self._state_lock:
            return {"model": MODEL, "region": "华北2（北京）", "stage": "S2",
                    "project_name": self.project.root.name,
                    "output_defaults": {"json": str(self.project.root.resolve() / "outputs"),
                                        "document": str(self.project.root.resolve() / "outputs")},
                    "languages": LANGUAGES,
                    "limits": {"audio_bytes": MAX_LOCAL_AUDIO_BYTES, "hotwords_bytes": MAX_XLSX_BYTES,
                               "context_chars": MAX_CONTEXT_CHARS, "speaker_min": MIN_SPEAKERS,
                               "speaker_max": MAX_SPEAKERS},
                    "auth": {"console": self.auth_status("console"),
                             "api_key": {"configured": None, "message": "选择后检查 API Key 设置。"}},
                    "confirmed": self.receipt}

    def upload(self, kind: str, name: str, source, size: int) -> dict:
        """短锁登记、锁外接收、短锁发布；每类文件同时只接收一次。"""
        if kind not in ("audio", "hotwords"):
            raise ValidationError("不支持的文件用途。", "upload")
        field = f"{kind}_upload_id"
        suffixes = AUDIO_SUFFIXES if kind == "audio" else {".xlsx"}
        maximum = MAX_LOCAL_AUDIO_BYTES if kind == "audio" else MAX_XLSX_BYTES
        if (not name or len(name) > 255 or any(char in name for char in "/\\\0")
                or any(ord(char) < 32 for char in name) or Path(name).suffix.lower() not in suffixes):
            raise ValidationError("所选文件名或格式不符合要求。", field)
        if not 0 < size <= maximum:
            raise ValidationError("文件为空或超过本机接收上限。", field)
        identifier = uuid.uuid4().hex
        destination = self.upload_directory / (identifier + Path(name).suffix.lower())
        partial = destination.with_suffix(destination.suffix + ".part")
        with self._state_lock:
            self._require_editable()
            if kind in self._pending_uploads:
                raise ValidationError("此类文件正在添加，请稍候。", field)
            if self.upload_directory.resolve() != self.upload_directory:
                raise ValidationError("本地文件暂存目录不能重定向。", field)
            self.upload_directory.mkdir(parents=True, exist_ok=True)
            # 在关闭标记和暂存文件之间保持原子登记；cleanup不删除活动上传拥有的文件。
            output = partial.open("xb")
            self._pending_uploads[kind] = identifier
            self.draft = None
        published = False
        try:
            with output:
                remaining = size
                while remaining:
                    self._require_open()
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValidationError("传入的文件不完整，请重新选择。", field)
                    output.write(chunk)
                    remaining -= len(chunk)
            with self._state_lock:
                self._require_editable()
                if self._pending_uploads.get(kind) != identifier:
                    raise ValidationError("上传状态已失效，请重新选择文件。", field)
                partial.replace(destination)
                # 新文件完整后再替换旧副本；失败也不会恢复已废弃的旧预览。
                for old_id, old in list(self.uploads.items()):
                    if old["kind"] == kind:
                        Path(old["path"]).unlink(missing_ok=True)
                        del self.uploads[old_id]
                self.uploads[identifier] = {"path": str(destination), "name": name, "kind": kind}
                published = True
            return {"ok": True, "upload_id": identifier, "name": name, "size_bytes": size}
        finally:
            try:
                if not published:
                    partial.unlink(missing_ok=True)
                    destination.unlink(missing_ok=True)
            finally:
                with self._state_lock:
                    if self._pending_uploads.get(kind) == identifier:
                        del self._pending_uploads[kind]
                    if self._closed.is_set():
                        self._remove_empty_upload_directory()

    def uploaded(self, identifier, kind: str) -> dict:
        if not isinstance(identifier, str) or identifier not in self.uploads:
            raise ValidationError("请选择音频文件。" if kind == "audio" else "请选择热词文件。", f"{kind}_upload_id")
        record = self.uploads[identifier]
        if record["kind"] != kind:
            raise ValidationError("文件类型与所选用途不符。", f"{kind}_upload_id")
        return record

    def _remove_empty_upload_directory(self) -> None:
        if (not self._pending_uploads and self.upload_directory.exists()
                and not any(self.upload_directory.iterdir())):
            self.upload_directory.rmdir()

    def cleanup(self) -> None:
        """先关闭会话，阻止迟到上传发布；活动上传负责清理自身文件。"""
        # 与发布上传结果使用同一短锁，不能在“检查开放→发布”之间插入关闭标记。
        with self._state_lock:
            self._closed.set()
        self._picker.close()
        with self._state_lock:
            keep = set()
            if self.receipt and self.draft:
                config = self.draft["config"]
                keep.add(config["audio"]["path"])
                if config["enhancement"]["hotwords"]:
                    keep.add(config["enhancement"]["hotwords"]["path"])
            if self.upload_directory.resolve() != self.upload_directory:
                return
            for record in self.uploads.values():
                if record["path"] not in keep:
                    Path(record["path"]).unlink(missing_ok=True)
            self._remove_empty_upload_directory()

    def _credential_stamp(self, mode: str):
        if mode != "api_key":
            return None
        status = api_key_status(self.project)
        if not status["configured"]:
            raise ValidationError(status["message"], "auth_mode")
        stamp = self.project.path(".env").stat()
        # 只在当前会话内比较文件元信息，不保存密钥或密钥摘要。
        return stamp.st_size, stamp.st_mtime_ns, stamp.st_ino

    def validate(self, payload: dict) -> dict:
        with self._state_lock:
            self._require_editable()
            self._require_uploads_complete()
            self.draft = None  # 即使新校验失败，旧预览也不再可确认。
            allowed = {"auth_mode", "audio_upload_id", "diarization_enabled", "enhancement_mode",
                       "hotwords_upload_id", "context", "json_directory", "document_directory",
                       "language_hint", "speaker_count"}
            if set(payload) - allowed:
                raise ValidationError("请求含不支持的配置字段。", "form")
            mode = payload.get("auth_mode")
            if mode not in ("console", "api_key"):
                raise ValidationError("请选择有效的鉴权方式。", "auth_mode")
            credential_stamp = self._credential_stamp(mode)
            diarization = payload.get("diarization_enabled")
            recognition_options = validate_options(payload, diarization)
            source = self.uploaded(payload.get("audio_upload_id"), "audio")
            upload_project = Project(self.upload_directory)
            audio = validate_audio(upload_project, source["path"], diarization)
            audio["name"] = source["name"]
            enhancement = payload.get("enhancement_mode")
            warnings = list(audio["warnings"])
            hotwords = None
            context = None
            if enhancement not in ("none", "hotwords", "context", "both"):
                raise ValidationError("请选择有效的识别增强方式。", "enhancement_mode")
            if enhancement in ("hotwords", "both"):
                source = self.uploaded(payload.get("hotwords_upload_id"), "hotwords")
                hotwords = load_hotwords(upload_project, source["path"])
                hotwords["name"] = source["name"]
                warnings.extend(hotwords["warnings"])
            if enhancement in ("context", "both"):
                context = validate_context(payload.get("context"))

            job_id = uuid.uuid4().hex
            json_base = output_directory(self.project, payload.get("json_directory"), "json_directory", self.output_directories.get("json"))
            document_base = output_directory(self.project, payload.get("document_directory"), "document_directory", self.output_directories.get("document"))
            config = {
                "schema_version": 1, "job_id": job_id, "model": MODEL, "region": "cn-beijing",
                "auth_mode": mode, "audio": audio, "diarization_enabled": diarization,
                "recognition_options": recognition_options,
                "enhancement": {"mode": enhancement, "hotwords": hotwords, "context": context},
                "json_directory": str(json_base / job_id / "json"),
                "document_directory": str(document_base / job_id / "documents"),
                "status": "CONFIGURED", "execution_authorized": False,
            }
            summary = {
                "model": MODEL, "region": "华北2（北京）", "auth_mode": mode,
                "recognition_options": recognition_options,
                "audio": {"name": audio["name"], **audio["metadata"],
                          "format": audio["metadata"]["format_name"], "requires_mono": audio["requires_mono"]},
                "enhancement": {"mode": enhancement, "count": hotwords["count"] if hotwords else 0,
                                "context_chars": len(context) if context else 0},
                "json_directory": config["json_directory"], "document_directory": config["document_directory"],
                "warnings": warnings,
            }
            self.draft = {"id": secrets.token_urlsafe(24), "config": config, "credential_stamp": credential_stamp,
                          "json_base": str(json_base), "document_base": str(document_base)}
            return {"ok": True, "validation_id": self.draft["id"], "summary": summary}

    def confirm(self, validation_id: str) -> dict:
        with self._state_lock:
            self._require_open()
            self._require_uploads_complete()
            if not self.draft or validation_id != self.draft["id"]:
                raise ValidationError("转写设置已变更，请重新检查并预览。", "confirmation")
            if self.receipt:
                return self.receipt  # 同一个确认重复送达时，不创建第二项任务。
            draft = self.draft
            config = draft["config"]
            try:
                if self._credential_stamp(config["auth_mode"]) != draft["credential_stamp"]:
                    raise ValidationError("账号设置已变更，请重新检查。", "auth_mode")
                inputs = [(config["audio"], "audio_path", AUDIO_SUFFIXES)]
                if config["enhancement"]["hotwords"]:
                    inputs.append((config["enhancement"]["hotwords"], "hotwords_path", {".xlsx"}))
                for record, field, suffixes in inputs:
                    path = resolve_input(Project(self.upload_directory), record["path"], suffixes, field)
                    if file_fingerprint(path) != record["fingerprint"]:
                        raise ValidationError("文件已变更，请重新检查后保存。", field)
                output_directory(self.project, draft["json_base"], "json_directory", self.output_directories.get("json"))
                output_directory(self.project, draft["document_base"], "document_directory", self.output_directories.get("document"))
                relative = f".state/jobs/{config['job_id']}"
                directory = self.project.path(relative)
                if directory != self.project.root.resolve() / relative:
                    raise ValidationError("任务状态目录不能重定向。", "confirmation")
                directory.mkdir(parents=True, exist_ok=False)
                config["confirmed_at"] = datetime.now(timezone.utc).isoformat()
                temporary = directory / "config.json.tmp"
                destination = directory / "config.json"
                content = (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                with temporary.open("xb") as output:
                    output.write(content)
                    output.flush()
                    os.fsync(output.fileno())
                # 先保存确认摘要，再发布配置；S3据此复用本次已校验快照。
                with (directory / "config.sha256").open("x", encoding="ascii") as checksum:
                    checksum.write(hashlib.sha256(content).hexdigest() + "\n")
                    checksum.flush()
                    os.fsync(checksum.fileno())
                temporary.replace(destination)
            except (OSError, SetupError, ValidationError):
                self.draft = None
                raise
            self.receipt = {"ok": True, "job_id": config["job_id"], "config_path": str(destination),
                            "json_directory": config["json_directory"],
                            "document_directory": config["document_directory"], "execution_started": False}
            return self.receipt
