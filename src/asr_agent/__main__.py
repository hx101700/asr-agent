"""S1公开入口：检查、局部安装与无音频合约探针。"""

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
    parser = argparse.ArgumentParser(description="asr-agent S1工具；尚不执行转写。")
    parser.add_argument("command", choices=("doctor", "bootstrap", "probe-bl", "api-key-status"))
    args = parser.parse_args(argv)
    project = Project(Path(__file__).resolve().parents[2])
    try:
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
