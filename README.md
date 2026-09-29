# asr-agent

面向 Codex 的本地非实时语音转写工具，计划通过阿里云百炼 CLI 固定调用 `qwen-audio-3.0-asr-flash-filetrans`。

> 当前已提供本地配置网页和明确授权后的BL转写入口，可保存并检查JSON。已通过本机合约及一次API Key单样本真实云端验收；控制台登录尚未真实验收，三种成品导出和发行ZIP尚未实现。

首版范围：Windows 10/11、Codex 桌面端、单文件输入、临时 OSS、带时间戳的 Excel / Word / Markdown 三种成品，以及本地 JSON 结果。说话人区分默认开启、可关闭；开启时多声道将合并为单声道，网页会在确认前提示，原文件保留。

- 开发者从 [文档索引](doc/README.md) 和 [当前状态](doc/STATUS.md) 开始。
- 用户流程见 [使用说明](doc/HELP.md)，阶段验收见 [验收计划](doc/ACCEPTANCE.md)。
- Codex 项目协作规则见 [AGENTS.md](AGENTS.md)。
- 已实现命令与验证结果见 [S1验证记录](doc/S1_VERIFICATION.md)。媒体处理使用PyAV预编译wheel，不需要安装独立FFmpeg程序。
- 网页与文件流程见 [S2验证记录](doc/S2_VERIFICATION.md)。地域固定北京，热词使用即时模式。
- 执行、错误与一次性任务记录见 [S3验证记录](doc/S3_VERIFICATION.md)。正式执行前需明确本次文件与上传授权。

已有Windows Python 3.12+和Node.js 18.17+时，可在项目根目录运行：

```powershell
python scripts/asr.py bootstrap
.venv\Scripts\python.exe scripts/asr.py doctor
.venv\Scripts\python.exe scripts/asr.py probe-bl
.venv\Scripts\python.exe scripts/asr.py serve
```

`serve`打开本机网页；如由Codex内置浏览器打开，可加`--no-browser`并使用启动时的会话链接。原生目录窗口需要正常Windows交互桌面。网页确认只保存本地配置，不发送阿里云。`doctor`发现依赖缺失或版本不匹配会返回非零；完整环境再次执行bootstrap会跳过安装。API Key预填项目`.env`，`api-key-status`只返回脱敏状态；网页在勾选指定Key后可只读查看。完整说明见[HELP.md](doc/HELP.md)。

代码采用前端MVP、后端应用服务与本地能力边界。实际模块职责见[开发文档](doc/DEVELOPMENT.md)，审查整改记录见[代码审查](doc/CODE_REVIEW.md)。

测试数据、凭据和转写结果仅在本地保存，不进入 Git 和发布包。
