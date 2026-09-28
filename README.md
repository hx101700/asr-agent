# asr-agent

面向 Codex 的本地非实时语音转写工具，计划通过阿里云百炼 CLI 固定调用 `qwen-audio-3.0-asr-flash-filetrans`。

> 当前已提供本地配置网页，可直接选择音频/Excel、同时使用热词和上下文、校验并保存配置。尚未接入云端识别、三种成品导出或发行ZIP。

首版范围：Windows 10/11、Codex 桌面端、单文件输入、临时 OSS、带时间戳的 Excel / Word / Markdown 三种成品，以及本地 JSON 结果。说话人区分默认开启、可关闭；开启时多声道将合并为单声道，网页会在确认前提示，原文件保留。

- 开发者从 [文档索引](doc/README.md) 和 [当前状态](doc/STATUS.md) 开始。
- 用户流程见 [使用说明](doc/HELP.md)，阶段验收见 [验收计划](doc/ACCEPTANCE.md)。
- Codex 项目协作规则见 [AGENTS.md](AGENTS.md)。
- 已实现命令与验证结果见 [S1验证记录](doc/S1_VERIFICATION.md)。媒体处理使用PyAV预编译wheel，不需要安装独立FFmpeg程序。
- 网页与文件流程见 [S2验证记录](doc/S2_VERIFICATION.md)。地域固定北京，热词使用即时模式。

已有Windows Python 3.12+和Node.js 18.17+时，可在项目根目录运行：

```powershell
python scripts/asr.py bootstrap
.venv\Scripts\python.exe scripts/asr.py doctor
.venv\Scripts\python.exe scripts/asr.py probe-bl
.venv\Scripts\python.exe scripts/asr.py serve
```

`serve`打开本机网页；如由Codex内置浏览器打开，可加`--no-browser`并使用启动时的会话链接。网页中的确认只保存本地配置，不发送阿里云。`doctor`发现缺失环境会返回非零退出码。使用API Key时，先在项目`.env`填写`DASHSCOPE_API_KEY`，可用`api-key-status`检查本地配置，密钥不会回显。完整说明见[HELP.md](doc/HELP.md)。

测试数据、凭据和转写结果仅在本地保存，不进入 Git 和发布包。
