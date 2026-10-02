中文 | [English](https://github.com/hx101700/asr-agent/blob/v0.1.0/release/NOTES.en.md)

### 新增

- **录音转写**：在 Codex 中调用阿里云百炼，将单个本地音频转成文字，支持时间戳和说话人区分。
- **精度增强**：导入 Excel 热词表、填写上下文参考文本，两种方式可同时使用。
- **文档导出**：同时保存 Word、Excel、Markdown 和原始 JSON；支持从已有任务在本地重新生成文档。
- **网页配置**：选择音频、调整识别选项、核对信息并指定保存位置。
- **双语文档**：提供中英文 README 与 Agent 使用规则。

### 安装

下载 Assets 中的 **asr-agent.zip**，解压后用 Codex 打开 `asr-agent` 文件夹。环境准备和首次使用见[README](https://github.com/hx101700/asr-agent/blob/v0.1.0/README.md)。

支持 Windows 10/11 x64。语音识别由[阿里云百炼](https://help.aliyun.com/zh/model-studio/what-is-model-studio)提供，通过官方 [BL CLI](https://github.com/modelstudioai/cli) 调用。
