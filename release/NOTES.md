中文 | [English](https://github.com/hx101700/asr-agent/blob/v0.1.0/release/NOTES.en.md)

asr-agent 的首个版本现已发布。把安装包交给 Codex，就可以在本机网页中配置录音转写，完成后得到 Word、Excel 和 Markdown。

### 新增

- **网页配置**：添加单个录音，调整语言、说话人区分和参考人数，选择保存位置。
- **热词与上下文**：从 Excel 导入热词，填写上下文参考文本，也可以同时使用两种增强方式。
- **百炼认证**：支持官方网页授权登录，以及使用项目 `.env` 中的 API Key。
- **文档生成**：保存带时间戳的三种文档及原始 JSON，支持从已有任务重新导出。

### 开始使用

下载 [asr-agent.zip](https://github.com/hx101700/asr-agent/releases/download/v0.1.0/asr-agent.zip)，将 ZIP 和 [README 中的安装提示](https://github.com/hx101700/asr-agent/blob/v0.1.0/README.md#agent-安装推荐)一起发给 Codex。安装完成后，说一句“帮我转写这段录音”，按提示完成认证和网页设置即可。

当前支持 **Windows 10/11 x64**，使用北京地域的 `qwen-audio-3.0-asr-flash-filetrans`。语音识别由[阿里云百炼](https://help.aliyun.com/zh/model-studio/what-is-model-studio)提供，通过官方 [BL CLI](https://github.com/modelstudioai/cli) 调用，可能产生调用费用。

欢迎通过 [Issues](https://github.com/hx101700/asr-agent/issues)反馈使用中遇到的问题。
