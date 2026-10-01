"""从项目源码目录启动asr-agent命令行。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from asr_agent.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
