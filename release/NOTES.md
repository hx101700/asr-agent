中文 | [English](https://github.com/hx101700/asr-agent/blob/v0.1.0/release/NOTES.en.md)

asr-transcription v0.1.0 提供录音转写 Skill。安装后，告诉 Codex 你需要转写录音，在本机网页完成配置，便可得到 Word、Excel 和 Markdown 供检查和校对。

### 功能

- 添加单个录音，调整语言、发言人区分和保存位置。
- 从 Excel 导入热词并填写上下文，两种增强方式可以同时使用。
- 使用百炼控制台授权或自己的 API Key，由官方 BL CLI 完成识别。
- 保存原始 JSON 和三种文档，支持从已有任务在本机重新导出。

### 安装与文件保存

Skill 可以独立安装，录音任务、凭据和依赖保存在你选择的工作目录。保存位置会避开 Skill 程序目录，方便分别管理工具和转写文件。

### 开始使用

下载 [asr-transcription.zip](https://github.com/hx101700/asr-agent/releases/download/v0.1.0/asr-transcription.zip) 后交给 Codex，要求安装为 Skill，并阅读其中的 `SKILL.md`。选择独立的工作目录后，Codex 会按说明准备环境并打开配置网页，再按所选方式引导认证。

当前支持 Windows 10/11 x64，需要 Python 3.12 x64、Node.js 18.17+ 与 npm。识别使用北京地域的 `qwen-audio-3.0-asr-flash-filetrans`，上传及识别可能产生调用费用。第一阶段提供转写与校对文档；会议总结属于后续阶段。

详细操作见[项目 README](https://github.com/hx101700/asr-agent/blob/v0.1.0/README.md)。遇到问题欢迎提交 [Issue](https://github.com/hx101700/asr-agent/issues)。
