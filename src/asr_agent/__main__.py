"""本地配置、明确授权的BL转写，以及仅查看本地执行记录的入口。"""

import argparse
import json
import sys
from pathlib import Path

from .application.bootstrap import bootstrap
from .application.diagnostics import doctor, probe
from .tools.auth import api_key_status
from .tools.environment import Project, SetupError
from .tools.bailian import BailianFailure, console_status, login_console


def main(argv: list[str] | None = None) -> int:
    """分派项目命令并输出JSON回执，按已知错误和交付状态确定退出码。"""
    # Windows重定向输出时也保持UTF-8，使Codex和JSON解析器正确读取中文。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="asr-agent本地工具；转写须明确授权上传。")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "bootstrap", "probe-bl", "api-key-status", "console-status", "login"):
        commands.add_parser(name)
    serve_parser = commands.add_parser("serve", help="打开本地配置网页")
    serve_parser.add_argument("--port", type=int, default=0, help="本地网页端口，默认自动选择")
    serve_parser.add_argument("--no-browser", action="store_true", help="不自动打开系统浏览器")
    for name in ("transcribe", "export", "job-status"):
        command = commands.add_parser(name)
        command.add_argument("--job", required=True, help="网页保存回执中的设置编号")
        if name == "transcribe":
            command.add_argument("--authorize-upload", action="store_true", help="用户明确同意将本次音频及所选增强内容发送至阿里云")
    args = parser.parse_args(argv)
    project = Project(Path(__file__).resolve().parents[2])
    try:
        if args.command == "serve":
            from .web import serve
            serve(project, port=args.port, open_browser=not args.no_browser)
            return 0
        if args.command == "transcribe":
            from .application.transcription import transcribe
            report = transcribe(project, args.job, authorize_upload=args.authorize_upload)
        elif args.command == "export":
            from .application.transcription import export_job
            report = export_job(project, args.job)
        elif args.command == "job-status":
            from .application.transcription import job_status
            report = job_status(project, args.job)
        else:
            if args.command == "login":
                print(json.dumps({"status": "WAITING_FOR_LOGIN", "message": "请在最后打开的阿里云官方页面完成授权。Windows可能先出现一个缺少参数的页面，程序会接收BL的完整备用链接并打开一次。最多等待15分钟；未打开时可按Ctrl+C停止。"}, ensure_ascii=False), flush=True)
            actions = {
                "doctor": doctor, "bootstrap": bootstrap, "api-key-status": api_key_status,
                "console-status": console_status, "login": login_console, "probe-bl": probe,
            }
            report = actions[args.command](project)
    except BailianFailure as exc:
        print(json.dumps({"status": "STOPPED", "error": exc.report}, ensure_ascii=False))
        return 1
    except (SetupError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if (report.get("issues") or report.get("configured") is False
                 or report.get("status") in ("STOPPED", "OUTCOME_UNKNOWN")
                 or (report.get("status") == "JSON_READY" and not report.get("documents_ready"))) else 0


if __name__ == "__main__":
    raise SystemExit(main())
