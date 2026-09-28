"""仅供本机使用的S2配置页面；没有云端执行入口。"""

import hmac
import io
import json
import os
import secrets
import socket
import tempfile
import threading
import uuid
import webbrowser
from datetime import datetime, timezone
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from openpyxl import Workbook

from . import MODEL
from .auth import api_key_status
from .environment import Project, SetupError
from .validation import (
    AUDIO_SUFFIXES, MAX_XLSX_BYTES, ValidationError, file_fingerprint, load_hotwords,
    resolve_input, validate_audio, validate_context,
)

STATIC = Path(__file__).parent / "static"
MAX_REQUEST_BYTES = 32 * 1024
MAX_LOCAL_AUDIO_BYTES = 2_000_000_000


def output_directory(project: Project, value: str, field: str) -> Path:
    """S2只允许项目outputs下的目录；不创建成品或覆盖用户文件。"""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("请输入输出目录。", field)
    base = project.root.resolve() / "outputs"
    try:
        if base.resolve() != base:
            raise ValidationError("outputs根目录不能重定向到其他目录。", field)
        path = project.path(value)
        if not path.is_relative_to(base) or any(part.startswith(".") for part in path.relative_to(base).parts):
            raise ValidationError("当前输出目录只支持项目outputs及其非隐藏子目录。", field)
        if any(Path(part).is_reserved() for part in path.relative_to(base).parts):
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
        raise ValidationError("输出目录不可写或超出项目范围，请检查路径。", field) from exc


class Session:
    def __init__(self, project: Project):
        self.project = project
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.draft = None
        self.receipt = None
        self.upload_directory = project.root.resolve() / ".state/web-uploads" / uuid.uuid4().hex
        self.uploads = {}

    def auth_status(self, mode: str) -> dict:
        if mode == "api_key":
            return api_key_status(self.project)
        if mode == "console":
            return {"configured": None, "verified_online": False,
                    "message": "本页仅保存登录方式，正式执行前由BL完成控制台登录。"}
        raise ValidationError("请选择有效的鉴权方式。", "auth_mode")

    def description(self) -> dict:
        with self.lock:
            return {"model": MODEL, "region": "华北2（北京）", "stage": "S2",
                    "project_name": self.project.root.name,
                    "auth": {"console": self.auth_status("console"),
                             "api_key": {"configured": None, "message": "选择后检查项目.env。"}},
                    "confirmed": self.receipt}

    def upload(self, kind: str, name: str, source, size: int) -> dict:
        """浏览器只把所选文件传给本机；服务端从不按客户端路径读取磁盘。"""
        with self.lock:
            if kind not in ("audio", "hotwords"):
                raise ValidationError("不支持的文件用途。", "upload")
            if self.receipt:
                raise ValidationError("本会话已保存配置，请启动新会话。", "session")
            self.draft = None
            field = "audio_upload_id" if kind == "audio" else "hotwords_upload_id"
            suffixes = AUDIO_SUFFIXES if kind == "audio" else {".xlsx"}
            maximum = MAX_LOCAL_AUDIO_BYTES if kind == "audio" else MAX_XLSX_BYTES
            if (not name or len(name) > 255 or any(char in name for char in "/\\\0")
                    or any(ord(char) < 32 for char in name) or Path(name).suffix.lower() not in suffixes):
                raise ValidationError("所选文件名或格式不符合要求。", field)
            if not 0 < size <= maximum:
                raise ValidationError("文件为空或超过本机接收上限。", field)
            if self.upload_directory.resolve() != self.upload_directory:
                raise ValidationError("本地文件暂存目录不能重定向。", field)
            self.upload_directory.mkdir(parents=True, exist_ok=True)
            # 每类只保留当前选择；这些是本程序生成的副本，不是用户源文件。
            for identifier, old in list(self.uploads.items()):
                if old["kind"] == kind:
                    Path(old["path"]).unlink(missing_ok=True)
                    del self.uploads[identifier]
            identifier = uuid.uuid4().hex
            destination = self.upload_directory / (identifier + Path(name).suffix.lower())
            partial = destination.with_suffix(destination.suffix + ".part")
            try:
                with partial.open("xb") as output:
                    remaining = size
                    while remaining:
                        chunk = source.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValidationError("传入的文件不完整，请重新选择。", field)
                        output.write(chunk)
                        remaining -= len(chunk)
                partial.replace(destination)
            except (OSError, ValidationError):
                partial.unlink(missing_ok=True)
                raise
            self.uploads[identifier] = {"path": str(destination), "name": name, "kind": kind}
            return {"ok": True, "upload_id": identifier, "name": name, "size_bytes": size}

    def uploaded(self, identifier, kind: str) -> dict:
        if not isinstance(identifier, str) or identifier not in self.uploads:
            raise ValidationError("请先选择文件并等待传入本机完成。", f"{kind}_upload_id")
        record = self.uploads[identifier]
        if record["kind"] != kind:
            raise ValidationError("文件类型与所选用途不符。", f"{kind}_upload_id")
        return record

    def cleanup(self) -> None:
        """会话结束时清理未确认副本；已保存配置引用的文件继续保留。"""
        with self.lock:
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
            if self.upload_directory.exists() and not any(self.upload_directory.iterdir()):
                self.upload_directory.rmdir()

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
        with self.lock:
            if self.receipt:
                raise ValidationError("本会话已保存配置，请启动新会话准备另一项任务。", "session")
            self.draft = None  # 即使新校验失败，旧预览也不再可确认。
            allowed = {"auth_mode", "audio_upload_id", "diarization_enabled", "enhancement_mode",
                       "hotwords_upload_id", "context", "json_directory", "document_directory"}
            if set(payload) - allowed:
                raise ValidationError("请求含不支持的配置字段。", "form")
            mode = payload.get("auth_mode")
            if mode not in ("console", "api_key"):
                raise ValidationError("请选择有效的鉴权方式。", "auth_mode")
            credential_stamp = self._credential_stamp(mode)
            diarization = payload.get("diarization_enabled")
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
                hotwords = load_hotwords(upload_project, source["path"], allow_super=True)
                hotwords["name"] = source["name"]
                warnings.extend(hotwords["warnings"])
            if enhancement in ("context", "both"):
                context = validate_context(payload.get("context"))

            job_id = uuid.uuid4().hex
            json_base = output_directory(self.project, payload.get("json_directory"), "json_directory")
            document_base = output_directory(self.project, payload.get("document_directory"), "document_directory")
            config = {
                "schema_version": 1, "job_id": job_id, "model": MODEL, "region": "cn-beijing",
                "auth_mode": mode, "audio": audio, "diarization_enabled": diarization,
                "enhancement": {"mode": enhancement, "hotwords": hotwords, "context": context},
                "json_directory": str(json_base / job_id / "json"),
                "document_directory": str(document_base / job_id / "documents"),
                "status": "CONFIGURED", "execution_authorized": False,
            }
            summary = {
                "model": MODEL, "region": "华北2（北京）", "auth_mode": mode,
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
        with self.lock:
            if not self.draft or validation_id != self.draft["id"]:
                raise ValidationError("预览已失效，请重新检查配置。", "confirmation")
            if self.receipt:
                return self.receipt  # 同一个确认重复送达时，不创建第二项任务。
            draft = self.draft
            config = draft["config"]
            try:
                if self._credential_stamp(config["auth_mode"]) != draft["credential_stamp"]:
                    raise ValidationError("鉴权配置已变化，请重新检查。", "auth_mode")
                inputs = [(config["audio"], "audio_path", AUDIO_SUFFIXES)]
                if config["enhancement"]["hotwords"]:
                    inputs.append((config["enhancement"]["hotwords"], "hotwords_path", {".xlsx"}))
                for record, field, suffixes in inputs:
                    path = resolve_input(Project(self.upload_directory), record["path"], suffixes, field)
                    if file_fingerprint(path) != record["fingerprint"]:
                        raise ValidationError("文件已变化，请重新检查配置后确认。", field)
                output_directory(self.project, draft["json_base"], "json_directory")
                output_directory(self.project, draft["document_base"], "document_directory")
                relative = f".state/jobs/{config['job_id']}"
                directory = self.project.path(relative)
                if directory != self.project.root.resolve() / relative:
                    raise ValidationError("任务状态目录不能重定向。", "confirmation")
                directory.mkdir(parents=True, exist_ok=False)
                config["confirmed_at"] = datetime.now(timezone.utc).isoformat()
                temporary = directory / "config.json.tmp"
                destination = directory / "config.json"
                with temporary.open("x", encoding="utf-8") as output:
                    json.dump(config, output, ensure_ascii=False, indent=2)
                    output.write("\n")
                    output.flush()
                    os.fsync(output.fileno())
                temporary.replace(destination)
            except (OSError, SetupError, ValidationError):
                self.draft = None
                raise
            self.receipt = {"ok": True, "job_id": config["job_id"], "config_path": str(destination),
                            "json_directory": config["json_directory"],
                            "document_directory": config["document_directory"], "execution_started": False}
            return self.receipt


def hotwords_template() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "热词"
    sheet.append(["text", "weight"])
    sheet.append(["示例术语", 4])
    sheet.column_dimensions["A"].width = 32
    sheet.column_dimensions["B"].width = 12
    sheet.freeze_panes = "A2"
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def create_server(project: Project, port: int = 0) -> ThreadingHTTPServer:
    session = Session(project)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # 请求头/查询串可能携带本地会话信息，不写访问日志。

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def send(self, status: int, data: bytes, content_type: str = "application/json; charset=utf-8", cookie=False):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            if cookie:
                self.send_header("Set-Cookie", f"asr_ui_{self.server.server_port}={session.token}; Path=/; HttpOnly; SameSite=Strict")
            self.end_headers()
            self.wfile.write(data)

        def json(self, status: int, payload: dict, cookie=False):
            self.send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), cookie=cookie)

        def allowed(self, authenticated=True) -> bool:
            expected_host = f"127.0.0.1:{self.server.server_port}"
            origin = self.headers.get("Origin")
            if self.headers.get("Host") != expected_host or (origin is not None and origin != f"http://{expected_host}"):
                self.json(403, {"ok": False, "error": "请求来源不被允许。"})
                return False
            if self.command == "POST" and origin != f"http://{expected_host}":
                self.json(403, {"ok": False, "error": "缺少有效的本地页面来源。"})
                return False
            if authenticated:
                token = self.headers.get("X-ASR-Token", "")
                if not token:
                    try:
                        cookies = SimpleCookie(self.headers.get("Cookie", ""))
                        value = cookies.get(f"asr_ui_{self.server.server_port}")
                        token = value.value if value else ""
                    except CookieError:
                        token = ""
                if not hmac.compare_digest(token.encode("utf-8"), session.token.encode("ascii")):
                    self.json(403, {"ok": False, "error": "会话无效，请从Codex重新打开本地页面链接。"})
                    return False
            return True

        def do_GET(self):
            path = urlsplit(self.path)
            static = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/app.css": ("app.css", "text/css; charset=utf-8"),
                      "/app.js": ("app.js", "text/javascript; charset=utf-8")}
            if not self.allowed(authenticated=path.path not in static):
                return
            try:
                if path.path in static:
                    name, kind = static[path.path]
                    self.send(200, (STATIC / name).read_bytes(), kind)
                elif path.path == "/api/session":
                    self.json(200, session.description(), cookie=True)
                elif path.path == "/api/hotwords-template":
                    self.send(200, hotwords_template(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    self.json(404, {"ok": False, "error": "未找到此页面或接口。"})
            except (ValidationError, SetupError, OSError) as exc:
                self.error_response(exc)

        def error_response(self, exc):
            if isinstance(exc, ValidationError):
                self.json(422, {"ok": False, "error": str(exc), "field": exc.field, "details": exc.details})
            else:
                self.json(422, {"ok": False, "error": "本地文件操作未完成，请检查路径与访问权限。"})

        def do_POST(self):
            if not self.allowed():
                return
            try:
                path = urlsplit(self.path).path
                if path in ("/api/upload-audio", "/api/upload-hotwords"):
                    if self.headers.get("Transfer-Encoding") or self.headers.get_content_type() != "application/octet-stream":
                        raise ValidationError("请选择文件后传入本机。", "upload")
                    size = int(self.headers.get("Content-Length", "0"))
                    name = unquote(self.headers.get("X-File-Name", ""), errors="strict")
                    kind = "audio" if path == "/api/upload-audio" else "hotwords"
                    self.json(200, session.upload(kind, name, self.rfile, size))
                    return
                if self.headers.get("Transfer-Encoding") or self.headers.get_content_type() != "application/json":
                    raise ValidationError("请求必须为JSON。", "request")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_REQUEST_BYTES:
                    raise ValidationError("请求为空或超过本地大小限制。", "request")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValidationError("请求格式不正确。", "request")
                if path == "/api/validate":
                    self.json(200, session.validate(payload))
                elif path == "/api/confirm":
                    self.json(200, session.confirm(payload.get("validation_id")))
                elif path == "/api/auth-status":
                    self.json(200, session.auth_status(payload.get("auth_mode")))
                else:
                    self.json(404, {"ok": False, "error": "未找到此接口。"})
            except (ValidationError, SetupError, OSError) as exc:
                self.error_response(exc)
            except (ValueError, TypeError):
                self.json(400, {"ok": False, "error": "请求格式不正确。"})

    class LocalServer(ThreadingHTTPServer):
        allow_reuse_address = False

        def server_bind(self):
            # Windows默认复用地址可能让两个预览进程同时占用同一端口。
            if os.name == "nt":
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()

        def server_close(self):
            super().server_close()
            session.cleanup()

    server = LocalServer(("127.0.0.1", port), Handler)
    server.session = session
    return server


def serve(project: Project, *, port=0, open_browser=True) -> None:
    server = create_server(project, port)
    url = f"http://127.0.0.1:{server.server_port}/#token={server.session.token}"
    # 仅在调用方的本地终端交付会话链接，不写Git或HTTP访问日志。
    print(json.dumps({"stage": "S2", "url": url, "pid": os.getpid(), "execution_available": False}, ensure_ascii=False), flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
