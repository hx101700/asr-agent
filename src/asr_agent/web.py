"""本机HTTP入口：协议检查、静态资源和用例结果到响应的转换。"""

import hmac
import io
import json
import os
import socket
import webbrowser
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from openpyxl import Workbook

from .environment import Project, SetupError
from .session import Session
from .validation import ValidationError

STATIC = Path(__file__).parent / "static"
MAX_REQUEST_BYTES = 32 * 1024


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
                      "/app.mjs": ("app.mjs", "text/javascript; charset=utf-8"),
                      "/model.mjs": ("model.mjs", "text/javascript; charset=utf-8"),
                      "/view.mjs": ("view.mjs", "text/javascript; charset=utf-8")}
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
                elif path == "/api/api-key":
                    self.json(200, session.api_key_display())
                elif path == "/api/select-directory":
                    self.json(200, session.select_directory(payload.get("kind"), payload.get("picker_id")))
                elif path == "/api/cancel-directory":
                    self.json(200, session.cancel_directory(payload.get("picker_id")))
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
