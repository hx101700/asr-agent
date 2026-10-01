"""本机HTTP入口：协议检查、静态资源和用例结果到响应的转换。"""

import hmac
import json
import os
import socket
import webbrowser
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .tools.environment import Project, SetupError
from .tools.hotwords import hotwords_template
from .application.session import Session
from .application.rules import ValidationError

STATIC = Path(__file__).parent / "static"
MAX_REQUEST_BYTES = 32 * 1024


def create_server(project: Project, port: int = 0) -> ThreadingHTTPServer:
    """建立绑定127.0.0.1的HTTP服务与独立配置会话。"""
    session = Session(project)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            """关闭默认HTTP访问日志。"""
            # 请求URL和请求头可能携带会话令牌。
            pass

        def setup(self):
            """初始化连接并设置网络读写超时。"""
            super().setup()
            self.connection.settimeout(10)

        def send(self, status: int, data: bytes, content_type: str = "application/json; charset=utf-8", cookie=False):
            """发送响应内容及缓存控制头，按需设置会话Cookie。"""
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
            """将用例回执编码为UTF-8 JSON响应。"""
            self.send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), cookie=cookie)

        def allowed(self, authenticated=True) -> bool:
            """核对本机请求来源及必要的会话令牌，拒绝时直接回复403。"""
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
            """分派静态资源、会话描述和热词模板的读取请求。"""
            path = urlsplit(self.path)
            static = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/app.css": ("app.css", "text/css; charset=utf-8"),
                      "/app.mjs": ("app.mjs", "text/javascript; charset=utf-8"),
                      "/api.mjs": ("api.mjs", "text/javascript; charset=utf-8"),
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
            """将字段错误或本机文件失败转换为网页可呈现的响应。"""
            if isinstance(exc, ValidationError):
                self.json(422, {"ok": False, "error": str(exc), "field": exc.field, "details": exc.details})
            else:
                self.json(422, {"ok": False, "error": "本地文件操作未完成，请检查路径与访问权限。"})

        def do_POST(self):
            """解析受保护请求，调用会话用例并输出确认事件。"""
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
                    receipt = session.confirm(payload.get("validation_id"))
                    try:
                        # Codex等待此进程回执继续同一任务，不扫描“最新”配置或输出敏感输入。
                        print(json.dumps({"event": "configured", **receipt}, ensure_ascii=False), flush=True)
                    except OSError:
                        pass  # 输出通道断开不改变已保存事实，网页仍须收到成功回执。
                    self.json(200, receipt)
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
            """独占绑定本机HTTP端口。"""
            # Windows默认复用地址可能让两个预览进程同时占用同一端口。
            if os.name == "nt":
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()

        def server_close(self):
            """关闭监听并清理本次会话，取消仍在等待的目录窗口。"""
            super().server_close()
            session.cleanup()

    server = LocalServer(("127.0.0.1", port), Handler)
    server.session = session
    return server


def serve(project: Project, *, port=0, open_browser=True) -> None:
    """持续提供配置网页与进程回执，退出时释放本次服务资源。"""
    server = create_server(project, port)
    url = f"http://127.0.0.1:{server.server_port}/#token={server.session.token}"
    # 仅在调用方的本地终端交付会话链接，不写Git或HTTP访问日志。
    print(json.dumps({"url": url, "pid": os.getpid()}, ensure_ascii=False), flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
