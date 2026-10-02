中文 | [English](https://github.com/hx101700/memoflow/blob/v0.1.0/release/NOTES.en.md)

MemoFlow 的目标是将录音整理为符合你的习惯和指定格式的会议纪要，并从你确认的修改中持续改进。这份 v0.1.0 开发预览完成了第一阶段：通过 `asr-transcription` Skill 转写录音，生成 Word、Excel 和 Markdown 供你检查和校对。

### 功能

- 添加单个录音，调整语言、发言人区分和保存位置。
- 在中文与英文界面间切换，选择浅色、深色或跟随系统外观。
- 从 Excel 导入热词并填写上下文，两种增强方式可以同时使用。
- 使用百炼控制台授权，或在页面填写自己的 API Key；检查时自动保存到工作目录，由官方 BL CLI 完成识别。
- 保存原始 JSON 和三种文档，支持从已有任务在本机重新导出。

这次更新修正了热词 Excel 中图表工作表的错误提示，让 Word 的复杂文字（如阿拉伯语）沿用统一字号，并修复了导出记录损坏时状态查询可能报错的问题。

### 安装与文件保存

Skill 可以独立安装，录音任务、凭据和依赖保存在你选择的工作目录。保存位置会避开 Skill 程序目录，方便分别管理工具和转写文件。

### 开始使用

下载 [asr-transcription.zip](https://github.com/hx101700/memoflow/releases/download/v0.1.0/asr-transcription.zip) 后交给 Codex，要求安装为 Skill，并阅读其中的 `SKILL.md`。选择独立的工作目录后，Codex 会按说明准备环境并打开配置网页，再按所选方式引导认证。

当前支持 Windows 10/11 x64，需要 Python 3.12 x64、Node.js 18.17+ 与 npm。识别使用北京地域的 `qwen-audio-3.0-asr-flash-filetrans`，上传及识别可能产生调用费用。个性化纪要、样式偏好和反馈学习将在第二阶段实现。

详细操作见[项目 README](https://github.com/hx101700/memoflow/blob/v0.1.0/README.md)。遇到问题欢迎提交 [Issue](https://github.com/hx101700/memoflow/issues)。
