"""源码目录入口；无需先向全局 Python 安装本项目。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from asr_agent.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
