"""媒体安装内部入口，由asr.py在有界子进程中调用。"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from asr_agent.environment import Project, SetupError
from asr_agent.media_setup import install_media_in_worker

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        report = install_media_in_worker(Project(ROOT))
    except (SetupError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
    print(json.dumps(report, ensure_ascii=False))
