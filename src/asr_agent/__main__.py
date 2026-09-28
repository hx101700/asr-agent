"""项目工具入口；serve只打开S2本地配置页面。"""

import argparse
import json
import sys
from pathlib import Path

from .bootstrap import bootstrap
from .auth import api_key_status
from .environment import Project, SetupError, doctor
from .probe import probe


def main(argv: list[str] | None = None) -> int:
    # Windows重定向输出时也保持UTF-8，使Codex和JSON解析器正确读取中文。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="asr-agent本地工具；当前尚不执行云端转写。")
    parser.add_argument("command", choices=("doctor", "bootstrap", "probe-bl", "api-key-status", "serve"))
    parser.add_argument("--port", type=int, default=0, help="本地网页端口，默认自动选择")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开系统浏览器")
    args = parser.parse_args(argv)
    project = Project(Path(__file__).resolve().parents[2])
    try:
        if args.command == "serve":
            from .web import serve
            serve(project, port=args.port, open_browser=not args.no_browser)
            return 0
        actions = {
            "doctor": doctor,
            "bootstrap": bootstrap,
            "api-key-status": api_key_status,
            "probe-bl": probe,
        }
        action = actions[args.command]
        report = action(project)
    except (SetupError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report.get("issues") or report.get("configured") is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
