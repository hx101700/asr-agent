"""启动录音转写Skill的本机工具。"""

import sys

# 技能目录作为只读资源使用，编译缓存留在执行进程内。
sys.dont_write_bytecode = True

from asr_transcription.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
