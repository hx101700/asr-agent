# asr-agent

基于阿里云百炼的录音转写 Agent，在 Codex 中使用。

中文 · [English](README.en.md) · [下载](https://github.com/hx101700/asr-agent/releases) · [使用文档](doc/HELP.md) · [百炼 CLI](https://github.com/modelstudioai/cli)

会议、访谈、课程录音，转写为带时间戳和说话人信息的 Word、Excel、Markdown。你在网页中选择文件和识别选项，Codex 完成转写并给出文档位置。

## 功能特性

- **录音转写** — 支持 MP3、WAV、M4A、FLAC 等格式，每次处理一个音频文件。
- **精度增强** — 从 Excel 导入热词，配合上下文参考文本，辅助识别专业词汇。
- **说话人区分** — 默认开启，可设置参考人数。
- **多格式导出** — 同时生成 Word、Excel、Markdown，保留原始 JSON，支持本地重新导出。
- **可视化配置** — 在浏览器中选择文件、调整设置、预览信息和选择保存位置。

<!-- SCREENSHOT: overview
在此放实际页面全景：添加音频、转写设置和信息栏。
建议文件：doc/images/01-transcription-overview.png
配文：在一个页面中完成录音选择与转写设置。隐藏密钥和私人路径。
-->

## 安装

需要 **Windows 10/11 x64、Codex 桌面端、Python 3.12 x64 和 Node.js 18.17.0+（含 npm）**。Python 需包含 tkinter；安装依赖需要联网。

从 [Releases](https://github.com/hx101700/asr-agent/releases) 下载 **asr-agent.zip**，解压后用 Codex 打开其中的 `asr-agent` 文件夹，然后输入：

> 请安装 asr-agent，并打开录音转写页面。

首次使用需要配置百炼账号：按提示完成控制台登录，或使用自己的北京地域 API Key。[安装与账号配置](doc/HELP.md)介绍了具体操作。

## 快速开始

安装完成后，直接告诉 Codex 你要做什么：

| 场景 | 可以这样说 |
| --- | --- |
| 转写录音 | 帮我转写一段会议录音，区分发言人。 |
| 添加专业词汇 | 这段录音有专业术语，我想添加热词和上下文再转写。 |
| 重新生成文档 | 请把刚才的转写结果重新生成 Word、Excel 和 Markdown。 |

网页打开后，选择音频，按需调整设置，点击**检查并预览**和**保存设置**，再返回 Codex 确认开始转写。完成后，Codex 会给出文档保存位置。

识别使用你自己的百炼账号，可能产生调用费用；录音及启用的增强内容会在确认转写后发送到百炼。

## 热词与上下文

热词用来指定重点识别的词语，可从 Excel 导入；上下文补充录音中可能出现的专业术语和参考文本。两种方式可以同时使用。[了解百炼精度增强](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy)。

<!-- SCREENSHOT: enhancement
在此放热词与上下文同时启用的实际截图。
建议文件：doc/images/02-accuracy-enhancement.png
配文：为专业词汇添加识别参考。使用公开术语，不展示真实人名或私人内容。
-->

## 转写结果

Word 用于阅读和校对，Excel 便于逐段查看与筛选，Markdown 可直接用于笔记和归档。三种文档保留时间戳，开启说话人区分时包含说话人编号。

<!-- SCREENSHOT: outputs
在此放 Word、Excel、Markdown 的实际成品截图。
建议文件：doc/images/03-transcription-outputs.png
配文：同一份录音，三种文档格式。使用可公开的样本。
-->

重新导出在本机完成，会更新同一组文档；如需保留手工修改，请先另存副本。文件要求、保存规则和问题处理见[使用文档](doc/HELP.md)。

## 基于阿里云百炼

[阿里云百炼](https://help.aliyun.com/zh/model-studio/what-is-model-studio)提供云端语音识别服务，[官方 BL CLI](https://github.com/modelstudioai/cli)负责登录、上传与识别调用。asr-agent 在此基础上提供本机配置页面和文档导出。

当前使用 `qwen-audio-3.0-asr-flash-filetrans`，地域固定北京。

[百炼控制台](https://bailian.console.aliyun.com/) · [百炼文档](https://help.aliyun.com/zh/model-studio/) · [BL CLI 官网](https://bailian.console.aliyun.com/cli) · [BL CLI 源码](https://github.com/modelstudioai/cli)

## 参与贡献

问题反馈和改进建议欢迎提交到 [Issues](https://github.com/hx101700/asr-agent/issues)。开发资料见[文档中心](doc/README.md)，代码结构见[UML](doc/UML.md)。

[Apache-2.0](LICENSE)
