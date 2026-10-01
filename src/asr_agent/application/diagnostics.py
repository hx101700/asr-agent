"""检查本机运行环境与BL公开命令契约。"""

import json
import sys

from .. import BAILIAN_VERSION, MODEL
from ..tools.bailian import bl_command, installed_bl_version, verify_bl_installation
from ..tools.environment import (
    Project, SetupError, check_node, check_python, installed_python_versions,
    locked_python_versions, run_process,
)

SYNTHETIC_AUDIO_URL = "https://example.invalid/asr-agent-probe.wav"


def doctor(project: Project) -> dict:
    """检查本机运行时及项目依赖，返回环境诊断报告。"""
    report = {
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "project": str(project.root),
        "issues": [],
    }
    try:
        check_python()
    except SetupError as exc:
        report["issues"].append(str(exc))
    try:
        node, version = check_node(project)
        report["node"] = {"path": str(node), "version": version}
    except SetupError as exc:
        report["issues"].append(str(exc))
    try:
        version = installed_bl_version(project)
        report["bailian"] = {"version": version, "expected": BAILIAN_VERSION, "entry": str(project.bl_entry)}
        if version != BAILIAN_VERSION or not project.bl_entry.is_file():
            report["issues"].append("项目内BL尚未安装或版本不匹配。")
        else:
            verify_bl_installation(project)
    except SetupError as exc:
        report["issues"].append(str(exc))
    venv_python = project.path(".venv/Scripts/python.exe")
    report["venv_python"] = str(venv_python) if venv_python.is_file() else None
    if not venv_python.is_file():
        report["issues"].append("项目虚拟环境尚未创建或不完整。")
    else:
        try:
            expected = locked_python_versions(project)
            installed = installed_python_versions(project, expected)
            if installed is None:
                report["issues"].append("Python运行依赖缺失或无法加载，请运行bootstrap。")
            else:
                report["python_packages"] = installed
                for name, version in expected.items():
                    if installed[name] != version:
                        report["issues"].append(f"Python依赖{name}版本不匹配：需要{version}，实际{installed[name]}。")
        except SetupError as exc:
            report["issues"].append(str(exc))
    report["note"] = "仅检查本地环境；不读取凭据，不验证账号权限，不执行转写。"
    return report


def probe(project: Project) -> dict:
    """核对BL公开帮助及请求参数映射，保存合约检查报告。"""
    project.prepare()
    # 探针与将来的真实登录配置分开；不读取或复用任何既存凭据。
    config = project.path(".state/bailian-probe")
    config.mkdir(parents=True, exist_ok=True)
    if any((config / name).exists() for name in ("config.json", "credentials.json")):
        raise SetupError("探针配置目录含配置/凭据文件，停止探针；未读取或覆盖。")
    observations = []
    checks = [
        ("version", ["--version"]),
        ("recognize_help", ["speech", "recognize", "--help"]),
        ("login_help", ["auth", "login", "--help"]),
        ("speech_help", ["speech", "--help"]),
    ]
    for name, arguments in checks:
        result = run_process(project, bl_command(project, arguments), probe_mode=True)
        if result.returncode:
            raise SetupError(f"BL探针失败：{name}，退出码{result.returncode}，未重试。")
        if name == "version" and result.stdout.strip() != f"bl {BAILIAN_VERSION}":
            raise SetupError("BL实际执行版本与锁定版本不一致。")
        if name.endswith("_help") and "Usage:" not in result.stdout + result.stderr:
            raise SetupError(f"BL未返回预期的公开帮助：{name}。")
        observations.append({"name": name, "stdout": result.stdout, "stderr": result.stderr})

    # BL的本地文件dry-run可能先上传；这里始终使用保留域名且不给文件路径入口。
    arguments = [
        "speech", "recognize", "--model", MODEL, "--url", SYNTHETIC_AUDIO_URL,
        "--diarization", "--speaker-count", "3", "--language", "zh",
        "--context=本地合约探针", "--vocabulary", '{"测试术语":4}',
        "--dry-run", "--output", "json",
    ]
    result = run_process(project, bl_command(project, arguments), probe_mode=True)
    if result.returncode:
        raise SetupError(f"BL请求构造探针失败，退出码{result.returncode}，未重试。")
    try:
        payload = json.loads(result.stdout)
        request = payload["request"]
        valid = (
            request["model"] == MODEL
            and request["input"]["file_urls"] == [SYNTHETIC_AUDIO_URL]
            and request["parameters"]["diarization_enabled"] is True
            and request["parameters"]["speaker_count"] == 3
            and request["parameters"]["language_hints"] == ["zh"]
            and request["parameters"]["vocabulary"] == {"测试术语": 4}
            and request["input"]["context"][0]["content"][0]["text"] == "本地合约探针"
        )
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise SetupError("BL dry-run输出结构与核实契约不一致。") from exc
    if not valid:
        raise SetupError("BL未按预期构造固定模型、语言、说话人或增强参数。")
    report = {
        "version": BAILIAN_VERSION,
        "model": MODEL,
        "status": "passed",
        "scope": "CLI公开帮助与虚构URL请求构造；非真实识别验收",
        "observations": observations,
        "request_preview": payload,
    }
    path = project.path(".state/bl-probe.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "passed", "report": str(path), "scope": report["scope"]}
