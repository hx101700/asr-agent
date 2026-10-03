"""启动录音转写Skill的本机工具。"""

import sys

# 技能目录作为只读资源使用，编译缓存留在执行进程内。
sys.dont_write_bytecode = True

if __name__ == "__main__":
    # Windows 的只读文件句柄阻止安装目录被改名，任务结束后才允许整体更新。
    with open(__file__, "rb"):
        from asr_runtime.__main__ import main

        raise SystemExit(main())
