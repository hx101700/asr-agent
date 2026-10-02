# asr-agent

中文 | [English](README.en.md)

在 Codex 中转写录音，并生成 Word、Excel 和 Markdown。语音识别由[阿里云百炼](https://help.aliyun.com/zh/model-studio/what-is-model-studio)提供，通过官方 [BL CLI](https://github.com/modelstudioai/cli) 调用。

## 功能特性

- **录音转写** — 将本地音频转成文字，支持时间戳和说话人区分。
- **精度增强** — 从 Excel 导入热词，添加上下文参考文本，两种方式可以同时使用。
- **可视化配置** — 在浏览器中添加录音、调整转写设置并选择保存位置。
- **文档导出** — 同时生成 Word、Excel 和 Markdown，保留原始 JSON，支持本地重新导出。

## Agent 安装（推荐）

使用前，请先[注册阿里云账号](https://help.aliyun.com/zh/account/step-1-register-an-alibaba-cloud-account)，按[官方指引](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)完成实名认证、开通百炼服务等准备。

从 [Releases](https://github.com/hx101700/asr-agent/releases) 下载 **asr-agent.zip**，把 ZIP 和下面这句话发给 Codex，它会根据本机环境，按项目说明完成安装与校验：

```text
请将 ZIP 解压到独立项目文件夹，阅读其中的 AGENTS.md，并按照说明帮我安装和配置 asr-agent。
```

当前支持 Windows 10/11 x64。本机需安装 Python 3.12 x64 和 Node.js 18.17+（含 npm）；环境要求见[使用说明](doc/HELP.md)。

## 快速开始

安装完成后，直接告诉 Codex 你需要转写录音：

```text
帮我转写这段录音。
```

Codex 会引导你完成百炼认证，可选择：

- **控制台登录（推荐）**：在阿里云官方网页完成授权，由 BL 管理登录凭据。
- **API Key**：使用已有的北京地域百炼 Key，按提示填入项目 `.env`，在转写页面选择“使用指定 API Key”。

随后，Codex 会打开转写网页。按页面提示添加录音，调整语言、说话人区分等设置，并选择保存位置。

<!-- SCREENSHOT: overview
在此放实际转写页面截图，展示添加录音、转写设置和保存位置。
建议文件：doc/images/01-transcription-overview.png
配文：添加录音，按需调整转写设置。隐藏密钥和私人路径。
-->

需要提高专业词汇的识别准确率时，可以导入热词表，或填写上下文参考文本。热词指定重点识别的词语，上下文提供包含相关词语的参考文本；两种方式可以同时使用。

<!-- SCREENSHOT: enhancement
在此放热词与上下文同时启用的实际截图。
建议文件：doc/images/02-accuracy-enhancement.png
配文：为识别提供热词和上下文参考。使用公开术语和可公开的示例内容。
-->

核对并保存设置后，返回 Codex 确认开始转写。Codex 会调用 BL 完成转写，自动生成排版后的 Word、Excel 和 Markdown，并告知保存位置。

转写会将录音及启用的增强内容发送到百炼，可能产生调用费用。

## 参与贡献

欢迎提交 [Issue](https://github.com/hx101700/asr-agent/issues)、功能建议和 PR。代码结构、开发约定与验证方法见[开发文档](doc/README.md)。

## 相关链接

| 资源 | 链接 |
| --- | --- |
| 阿里云百炼 | [控制台](https://bailian.console.aliyun.com/) · [官方文档](https://help.aliyun.com/zh/model-studio/) |
| 百炼 CLI | [官方主页](https://bailian.console.aliyun.com/cli) · [GitHub](https://github.com/modelstudioai/cli) |
| 识别精度增强 | [热词与上下文说明](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy) |
| asr-agent | [使用说明](doc/HELP.md) · [版本下载](https://github.com/hx101700/asr-agent/releases) |

本项目采用 [Apache-2.0](LICENSE) 许可证。
