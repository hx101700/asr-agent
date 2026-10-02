"""管理本机会话的文件上传、配置预览和确认流程。"""

import secrets
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .. import MODEL
from ..utils.auth import read_api_key
from ..utils.directory_picker import DirectoryPicker
from ..utils.environment import Runtime, SetupError
from ..utils.files import FileError, check_file_unchanged, resolve_input
from ..utils.hotwords import MAX_XLSX_BYTES
from ..utils.job_files import publish_config
from .inputs import load_hotwords, validate_audio
from .rules import (
    AUDIO_SUFFIXES, ValidationError, validate_context, LANGUAGES, validate_options,
    MAX_CONTEXT_CHARS, MIN_SPEAKERS, MAX_SPEAKERS, MAX_UPLOAD_BYTES,
    MAX_DURATION_SECONDS, MAX_HOTWORDS,
)

MAX_LOCAL_AUDIO_BYTES = 2_000_000_000


def output_directory(runtime: Runtime, value: str, field: str, approved: Path | None = None) -> Path:
    """解析并校验本次会话的保存目录。"""
    try:
        if value == "default":
            base = runtime.output_root
            if base.resolve() != base:
                raise ValidationError("默认保存目录不能重定向到其他目录。", field)
            if base.exists() and not base.is_dir():
                raise ValidationError("默认保存位置存在同名文件，请选择其他文件夹。", field)
        else:
            if approved is None or value != str(approved):
                raise ValidationError("请点击“选择文件夹”设置保存位置。", field)
            if approved.resolve() != approved or not approved.is_dir():
                raise ValidationError("所选文件夹已不存在，请重新选择。", field)
            base = approved
        runtime.check_output_path(base)
        return base
    except SetupError as exc:
        raise ValidationError(str(exc), field) from exc
    except OSError as exc:
        raise ValidationError("此文件夹无法保存文件，请选择其他位置。", field) from exc


class Session:
    def __init__(self, runtime: Runtime):
        """初始化会话令牌、上传登记和目录选择器。"""
        self.runtime = runtime
        self.token = secrets.token_urlsafe(32)
        self._state_lock = threading.Lock()
        self.draft = None
        self.receipt = None
        self.upload_directory = runtime.root.resolve() / ".state/web-uploads" / uuid.uuid4().hex
        self.uploads = {}
        self.output_directories = {}
        self._picker = DirectoryPicker()
        self._closed = threading.Event()
        self._pending_uploads = set()

    def _require_open(self) -> None:
        """检查会话是否处于开放状态。"""
        if self._closed.is_set():
            raise ValidationError("当前会话已关闭。", "session")

    def _require_editable(self) -> None:
        """检查当前会话的配置编辑权限。"""
        self._require_open()
        if self.receipt:
            raise ValidationError("本会话已保存配置，请新建任务。", "session")

    def _require_uploads_complete(self) -> None:
        """检查上传完成状态，报告仍在接收的文件类型。"""
        if self._pending_uploads:
            kind = next(iter(self._pending_uploads))
            raise ValidationError("文件仍在添加，请稍候。", f"{kind}_upload_id")

    def select_directory(self, kind: str, picker_id: str | None = None) -> dict:
        """打开原生目录窗口，校验并登记所选保存位置。"""
        if kind not in ("json", "document"):
            raise ValidationError("未知的保存位置。", "directory")
        request_id = picker_id if picker_id is not None else uuid.uuid4().hex
        with self._state_lock:
            self._require_editable()
            initial = self.output_directories.get(kind, self.runtime.output_root)
        while not initial.exists():
            initial = initial.parent
        try:
            selected = self._picker.select(initial, request_id)
        except SetupError as exc:
            raise ValidationError(str(exc), f"{kind}_directory") from exc
        if selected is None:
            return {"ok": True, "cancelled": True}
        path = selected  # 选择器已核对现有目录；这里只检查一次实际可写性。
        try:
            self.runtime.check_output_path(path)
            # 选择时检查一次可写性；预览和确认不反复创建探针文件。
            with tempfile.TemporaryFile(dir=path):
                pass
        except SetupError as exc:
            raise ValidationError(str(exc), f"{kind}_directory") from exc
        except OSError as exc:
            raise ValidationError("此文件夹无法保存文件，请选择其他位置。", f"{kind}_directory") from exc
        with self._state_lock:
            self._require_editable()
            self.output_directories[kind] = path
            self.draft = None
        return {"ok": True, "cancelled": False, "path": str(path)}

    def cancel_directory(self, picker_id: str) -> dict:
        """取消指定请求的目录选择等待。"""
        # 取消仅经过选择器自己的短锁，不等待文件接收、指纹或Excel校验。
        try:
            self._picker.cancel(picker_id)
        except SetupError as exc:
            raise ValidationError(str(exc), "directory") from exc
        return {"ok": True}

    def api_key_display(self) -> dict:
        """读取工作目录中的API Key，返回本机页面所需的显示数据。"""
        try:
            return {"ok": True, "value": read_api_key(self.runtime)}
        except (SetupError, OSError, UnicodeError) as exc:
            message = str(exc) if isinstance(exc, SetupError) else "无法读取 .env 文件。"
            raise ValidationError(message, "auth_mode") from exc

    def description(self) -> dict:
        """返回模型信息、表单选项、默认目录和确认回执。"""
        with self._state_lock:
            return {"model": MODEL, "region": "华北2（北京）",
                    "output_defaults": {"json": str(self.runtime.output_root),
                                        "document": str(self.runtime.output_root)},
                    "languages": LANGUAGES,
                    "audio_suffixes": sorted(AUDIO_SUFFIXES),
                    "limits": {"audio_bytes": MAX_LOCAL_AUDIO_BYTES, "hotwords_bytes": MAX_XLSX_BYTES,
                               "upload_bytes": MAX_UPLOAD_BYTES, "audio_seconds": MAX_DURATION_SECONDS,
                               "hotwords_count": MAX_HOTWORDS,
                               "context_chars": MAX_CONTEXT_CHARS, "speaker_min": MIN_SPEAKERS,
                               "speaker_max": MAX_SPEAKERS},
                    "confirmed": self.receipt}

    def upload(self, kind: str, name: str, source, size: int) -> dict:
        """接收文件字节，保存会话副本并返回上传编号。"""
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
            self._pending_uploads.add(kind)
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
                    self._pending_uploads.remove(kind)
                    if self._closed.is_set():
                        self._remove_empty_upload_directory()

    def uploaded(self, identifier, kind: str) -> dict:
        """按会话上传编号查找指定用途的已完成副本。"""
        if not isinstance(identifier, str) or identifier not in self.uploads:
            raise ValidationError("请选择音频文件。" if kind == "audio" else "请选择热词文件。", f"{kind}_upload_id")
        record = self.uploads[identifier]
        if record["kind"] != kind:
            raise ValidationError("文件类型与所选用途不符。", f"{kind}_upload_id")
        return record

    def _remove_empty_upload_directory(self) -> None:
        """移除上传结束后的空会话目录。"""
        if (not self._pending_uploads and self.upload_directory.exists()
                and not any(self.upload_directory.iterdir())):
            self.upload_directory.rmdir()

    def cleanup(self) -> None:
        """关闭会话和目录窗口，清理临时副本并保留已确认音频。"""
        # 与发布上传结果使用同一短锁，不能在“检查开放→发布”之间插入关闭标记。
        with self._state_lock:
            self._closed.set()
        self._picker.close()
        with self._state_lock:
            keep = set()
            if self.receipt and self.draft:
                config = self.draft["config"]
                keep.add(config["audio"]["path"])
            if self.upload_directory.resolve() != self.upload_directory:
                return
            for record in self.uploads.values():
                if record["path"] not in keep:
                    Path(record["path"]).unlink(missing_ok=True)
            self._remove_empty_upload_directory()

    def validate(self, payload: dict) -> dict:
        """读取已上传内容并应用规则，生成确认快照和面向网页的预览。"""
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
            diarization = payload.get("diarization_enabled")
            recognition_options = validate_options(payload, diarization)
            source = self.uploaded(payload.get("audio_upload_id"), "audio")
            audio = validate_audio(self.upload_directory, source["path"], diarization)
            audio["name"] = source["name"]
            enhancement = payload.get("enhancement_mode")
            warnings = list(audio["warnings"])
            hotwords = None
            context = None
            if enhancement not in ("none", "hotwords", "context", "both"):
                raise ValidationError("请选择有效的识别增强方式。", "enhancement_mode")
            if enhancement in ("hotwords", "both"):
                source = self.uploaded(payload.get("hotwords_upload_id"), "hotwords")
                hotwords = load_hotwords(self.upload_directory, source["path"])
                warnings.extend(hotwords["warnings"])
            if enhancement in ("context", "both"):
                context = validate_context(payload.get("context"))

            job_id = uuid.uuid4().hex
            json_base = output_directory(self.runtime, payload.get("json_directory"), "json_directory", self.output_directories.get("json"))
            document_base = output_directory(self.runtime, payload.get("document_directory"), "document_directory", self.output_directories.get("document"))
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
                "auth_mode": mode,
                "audio": {"name": audio["name"], **{
                    field: audio["metadata"][field] for field in (
                        "channels", "sample_rate", "duration_seconds", "size_bytes", "format_name")}},
                "enhancement": {"mode": enhancement, "count": hotwords["count"] if hotwords else 0,
                                "context_chars": len(context) if context else 0},
                "json_directory": config["json_directory"], "document_directory": config["document_directory"],
                "warnings": warnings,
            }
            self.draft = {"id": secrets.token_urlsafe(24), "config": config}
            return {"ok": True, "validation_id": self.draft["id"], "summary": summary}

    def confirm(self, validation_id: str) -> dict:
        """保存指定预览的配置快照并返回任务回执。"""
        with self._state_lock:
            self._require_open()
            self._require_uploads_complete()
            if not self.draft or validation_id != self.draft["id"]:
                raise ValidationError("转写设置已变更，请重新检查并预览。", "confirmation")
            if self.receipt:
                return self.receipt  # 同一个确认重复送达时，不创建第二项任务。
            config = self.draft["config"]
            try:
                # 确认保存预览快照；完整音频摘要留到执行前比对，热词直接使用已解析词表。
                audio = config["audio"]
                path = resolve_input(self.upload_directory, audio["path"], AUDIO_SUFFIXES)
                check_file_unchanged(path, audio["fingerprint"])
                config["confirmed_at"] = datetime.now(timezone.utc).isoformat()
                destination = publish_config(self.runtime, config)
            except FileError as exc:
                self.draft = None
                raise ValidationError(str(exc), "audio_path") from exc
            except (OSError, SetupError, ValidationError):
                self.draft = None
                raise
            self.receipt = {"ok": True, "job_id": config["job_id"], "config_path": str(destination),
                            "auth_mode": config["auth_mode"],
                            "json_directory": config["json_directory"],
                            "document_directory": config["document_directory"], "execution_started": False}
            return self.receipt
