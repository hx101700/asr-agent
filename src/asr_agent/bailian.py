"""BL的进程边界：不实现上传、鉴权请求、轮询或下载协议。"""

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .auth import bailian_environment
from .environment import Project, SetupError, bl_command

BEIJING_BASE_URL = "https://dashscope.aliyuncs.com"
WAIT_SECONDS = 3600
PROCESS_SECONDS = WAIT_SECONDS + 300


@dataclass(frozen=True)
class PreparedCommand:
    """一次准备的实际命令与环境；repr也不能包含Key、上下文或热词。"""

    argv: tuple[str, ...] = field(repr=False)
    env: dict[str, str] = field(repr=False)


def prepare_command(project: Project, arguments: list[str], auth_mode: str) -> PreparedCommand:
    argv = bl_command(project, arguments)
    check_command_length(argv)
    return PreparedCommand(tuple(argv), bailian_environment(project, auth_mode))


class BailianFailure(Exception):
    def __init__(self, report: dict, *, started: bool):
        super().__init__(report["explanation"])
        self.report = report
        self.started = started


def check_command_length(argv: list[str]) -> None:
    # CreateProcessW的32767限制包含终止NUL；按Python实际Windows引号规则计算。
    length = len(subprocess.list2cmdline(argv).encode("utf-16-le")) // 2 + 1
    if length > 32767:
        raise SetupError(
            f"识别命令共{length}个UTF-16单元，超过Windows的32767上限。"
            "请减少热词或缩短路径后重新配置；未截断热词、未启动BL。"
        )


def redact_message(value: str, private_values: list[str]) -> str:
    for private in sorted(set(private_values), key=len, reverse=True):
        if private:
            value = value.replace(private, "[已隐藏]")
    value = re.sub(r"(?:https?|oss)://[^\s\"<>]+", "[URL已隐藏]", value)
    value = re.sub(r"\b(?:sk-[A-Za-z0-9._-]+|LTAI[A-Za-z0-9]+)\b", "[凭据已隐藏]", value)
    value = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [已隐藏]", value)
    return " ".join(value.split())[:800]


def explain_cli_error(returncode: int, stderr: str, private_values: list[str]) -> dict:
    """只读取官方结构化错误的标量字段；不回传cause、hint或整段stderr。"""
    catalog = json.loads(Path(__file__).with_name("error_catalog.json").read_text(encoding="utf-8"))
    try:
        error = json.loads(stderr)["error"]
        if not isinstance(error, dict):
            error = {}
    except (ValueError, KeyError, TypeError):
        error = {}
    api_code = error.get("api_code")
    if not isinstance(api_code, str):
        api_code = None
    request_id = error.get("request_id")
    if not isinstance(request_id, str):
        request_id = None
    http_status = error.get("http_status")
    if type(http_status) is not int:
        http_status = None
    cli = catalog["cli_exit_codes"].get(str(returncode))
    api = catalog["api_codes"].get(api_code or "")
    explanation = cli["meaning"] if cli else "BL返回未收录的进程退出码。"
    source = catalog["cli_source"] if cli else None
    if api:
        explanation = api["meaning"]
        source = api.get("source_url", catalog["api_source"])
    elif api_code:
        explanation += " 当前官方字典未收录此API错误码，不能据此推断具体原因。"
    message = error.get("message")
    return {
        "source": "cli", "cli_exit_code": returncode, "http_status": http_status,
        "code": redact_message(api_code, private_values) if api_code else None,
        "request_id": redact_message(request_id, private_values) if request_id else None,
        "message": redact_message(message, private_values) if isinstance(message, str) else "CLI未提供可解析的结构化错误信息。",
        "explanation": explanation, "source_url": source,
    }


def _run_bl(project: Project, command: PreparedCommand,
            private_values: list[str], *, timeout: float, capture_stdout: bool = False) -> str:
    private_values = [*private_values, command.env.get("DASHSCOPE_API_KEY", "")]
    try:
        process = subprocess.Popen(
            command.argv, cwd=project.root, env=command.env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture_stdout else subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except OSError as exc:
        raise BailianFailure({"source": "local", "code": "LOCAL_PROCESS_START_FAILED",
                              "explanation": "无法启动BL进程，尚未执行云端操作。"}, started=False) from exc
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt, OSError) as exc:
        process.kill()
        process.communicate()
        # 这里只说明进程中断；是否已提交识别，由调用用例解释。
        raise BailianFailure({"source": "local", "code": "LOCAL_WAIT_INTERRUPTED",
                              "explanation": "BL进程等待已中断，未自动重试。"},
                             started=True) from exc
    if process.returncode:
        raise BailianFailure(explain_cli_error(process.returncode, stderr, private_values), started=True)
    return stdout or ""


def run_recognition(project: Project, command: PreparedCommand,
                    private_values: list[str]) -> None:
    _run_bl(project, command, private_values, timeout=PROCESS_SECONDS)


def console_status(project: Project) -> dict:
    project.prepare()
    command = prepare_command(project, ["auth", "status", "--config", "default", "--output", "json"], "console")
    output = _run_bl(project, command, [], timeout=60, capture_stdout=True)
    try:
        status = json.loads(output)
        if not isinstance(status, dict):
            raise ValueError("invalid status")
    except ValueError as exc:
        raise SetupError("BL未返回可解析的本地登录状态。") from exc
    # authenticated也可能只代表控制台token/AK，识别必须存在模型API Key。
    configured = isinstance(status.get("api_key"), dict)
    return {"mode": "console", "configured": configured, "verified_online": False,
            "message": "已配置项目内模型凭据。" if configured else "项目内尚无模型凭据，请先运行login完成百炼控制台登录。"}


def login_console(project: Project) -> dict:
    project.prepare()
    command = prepare_command(project, ["auth", "login", "--console", "--console-site", "domestic",
                                        "--config", "default", "--output", "json"], "console")
    _run_bl(project, command, [], timeout=15 * 60 + 30)
    # BL登录空等超时也可能退出0，必须再核对公开的本地状态命令。
    return console_status(project)
