# asr-agent

中文 | [English](README.en.md)

**在 Codex 中，将录音转成带时间戳的 Word、Excel 和 Markdown。**

asr-agent 适合处理会议、访谈、课程等已经录制好的音频。在 Codex 中提出需求，在本机网页选择文件和设置，完成后获得三种转写文档及原始识别 JSON。

语音识别由[阿里云百炼](https://help.aliyun.com/zh/model-studio/what-is-model-studio)北京地域的 `qwen-audio-3.0-asr-flash-filetrans` 提供，通过官方 [BL CLI](https://github.com/modelstudioai/cli) 调用。支持 Windows 10/11 x64，每次处理一个文件，支持时间戳、发言人区分，以及热词和上下文同时使用。

## 开始之前

适用于 Windows 10/11 x64。本机需有 Windows x64 CPython 3.12（含 venv、ensurepip、tkinter）、Node.js 18.17.0 或更高版本及配套 npm。ZIP 不附带运行时或依赖包；安装需要网络。

请准备可正常使用的 Codex 桌面端，以及具备该模型调用权限的阿里云账号或北京地域的百炼 API Key。识别使用你自己的阿里云服务，可能产生模型调用费用。

## 第一次使用

### 1. 安装并打开页面

解压后，用 Codex 打开 `asr-agent` 文件夹，在项目对话中输入：

> 请安装 asr-agent，并打开录音转写页面。

Codex 会安装项目依赖和阿里云百炼 CLI，再打开本机网页。首次使用请等待下载完成；后续在同一项目中说“帮我转写录音”即可。

### 2. 选择账号使用方式

- **控制台登录**：保持“使用指定 API Key”未勾选，首次使用时按 Codex 提示在阿里云官方页面完成授权。
- **指定 API Key**：将 `.env.example` 复制为 `.env`，在 `DASHSCOPE_API_KEY=` 后填写自己的 Key，再勾选网页中的“使用指定 API Key”。密钥从本机读取，请勿发送到聊天。

### 3. 添加录音并保存设置

1. 选择或拖入一个音频，支持 MP3、WAV、M4A、FLAC 等格式。
2. 选择音频语言，按需调整发言人区分和参考人数。
3. 按需下载模板、填写并导入热词 Excel，或填写与录音相关的参考文本；热词和上下文可以同时启用。
4. 通过“选择文件夹”指定 JSON 与文档保存位置，默认保存在项目 `outputs` 中。
5. 点击“检查并预览”，核对信息后点击“保存设置”。多声道录音需要合并时，页面会提示，原文件保留。

阿里云的[精度增强说明](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy)中，即时热词随请求提供词语及权重，上下文用于提供包含待识别原词的参考文本。本项目分别通过 Excel 和文本输入配置，两者可同时使用。

### 4. 返回 Codex 开始转写

> 同意将这次录音及所选热词、上下文发送到阿里云百炼北京进行转写，请开始。

完成后，Codex 会告诉你文件保存在哪里。页面可以关闭，转写期间请保持电脑和执行进程运行。文件添加与设置保存都在本机完成，确认开始转写后才发送云端。

## 输出文件

| 文件 | 用途 |
| --- | --- |
| `transcription.docx` | 分段阅读和编辑，包含时间标签与说话人信息 |
| `transcription.xlsx` | 按时间、说话人及正文查看或筛选内容 |
| `transcription.md` | 在 Markdown 编辑器和笔记中阅读与归档 |
| `transcription.json` | 保留原始识别结果，供本地重新导出使用 |

文档标题为“录音文件名 录音转写”。默认文档保存在 `outputs/任务编号/documents/`，原始 JSON 保存在 `outputs/任务编号/json/`，具体路径由 Codex 告知。

需要重新生成文档时，保留项目文件夹与原始 JSON，告诉 Codex：“请为任务 `<任务编号>` 重新导出三种文档。”文档会覆盖该任务的同名成品，无需再次识别录音。如果手动编辑过成品，请先另存一份。仅有一份 JSON 文件不足以恢复完整任务。

## 使用说明

- 当前每次处理一个已有音频，不支持实时录音、批处理、翻译或自动摘要。
- 转写失败后会停止并说明已知原因，不会自动再次提交识别；已生成文件保留。
- 录音、密钥和转写内容属于用户数据，请勿提交到公开仓库。
- [详细使用说明](doc/HELP.md)：手动安装命令、文件要求、保存位置和退出方法。
- [状态与错误说明](doc/ERRORS.md)：遇到失败时如何处理。
- [官方能力依据](doc/REFERENCES.md)：模型参数与输入限制。

## 服务与上游项目

阿里云百炼提供云端语音识别服务，官方 BL CLI 负责账号登录、上传与识别调用；asr-agent 提供本机设置页面和文档导出。项目安装流程会配置所需的 CLI 版本。

- [百炼控制台](https://bailian.console.aliyun.com/)：配置账号与 API Key。
- [百炼官方文档](https://help.aliyun.com/zh/model-studio/)：模型和接口说明。
- [BL CLI 官网](https://bailian.console.aliyun.com/cli) · [BL CLI GitHub 源码](https://github.com/modelstudioai/cli)。

本项目采用 [Apache-2.0](LICENSE) 许可证。
