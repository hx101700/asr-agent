中文 | [English](https://github.com/hx101700/memoflow/blob/v0.1.0/release/NOTES.en.md)

MemoFlow 希望把录音整理成符合你习惯和格式要求的会议纪要。这份 v0.1.0 开发预览先做好第一步：让 Codex 帮你转写录音，生成带时间戳的 Word、Excel 和 Markdown，交给你检查和校对。

### 功能特性

- **网页配置**：添加单个录音，按需调整语言、发言人区分和保存位置；支持中文、英文及浅色、深色外观。
- **精度增强**：在表格中填写热词，或导入 Excel 后直接修改。错误会标在对应行，重复词需确认保留一行；热词和上下文可同时使用。
- **百炼识别**：使用 Qwen-Audio-3.1-ASR-Flash-Filetrans，由官方 BL CLI 完成上传和识别。可选择控制台授权，也可在网页填写并保存自己的北京地域 API Key。
- **文档交付**：保留原始 JSON，并生成三种转写文件；已有成功任务可以直接在本机重新导出。

### 使用体验

保存设置后，回到 Codex 发送“继续”即可接着操作。发现设置填错时，可在转写开始前返回修改。若撤回请求的响应中断，刷新原页面可以恢复同一服务仍保留的确认内容；之后未保存的编辑不会保留。

这次整理修复了热词表翻页后的删行跳页、窄窗口错误提示重叠和本地导出的临时文件冲突。页面、Skill 说明和开发图稿也已按实际行为核对。

### 开始使用

先注册阿里云账号，按平台指引完成实名认证及百炼服务准备。下载 [asr-transcription.zip](https://github.com/hx101700/memoflow/releases/download/v0.1.0/asr-transcription.zip)，连同下面这句话发给 Codex：

> 请解压 ZIP，阅读其中的 SKILL.md，帮我安装并配置 asr-transcription。

安装完成后说“帮我转写录音”，在打开的网页中添加文件和设置即可。

当前支持 Windows 10/11 x64，需要 Python 3.12 x64、Node.js 18.17+ 与 npm。识别使用百炼北京地域，可能产生调用费用。个性化纪要与反馈学习属于后续阶段。

使用方法见[README](https://github.com/hx101700/memoflow/blob/v0.1.0/README.md)，遇到问题欢迎提交[Issue](https://github.com/hx101700/memoflow/issues)。
