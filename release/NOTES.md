中文 | [English](https://github.com/hx101700/asr-agent/blob/v0.1.1/release/NOTES.en.md)

这次更新主要整理了转写完成后的文件保存方式。之前每次重新导出都会多出一个目录，同一段录音的文档容易散在不同位置。现在，一个任务对应一组 Word、Excel 和 Markdown 文件，重新导出后仍然到同一个地方找。

## 文件保存更直接

三种文档直接放在任务的 `documents` 文件夹下：

```text
documents/
├── transcription.docx
├── transcription.xlsx
└── transcription.md
```

重新导出会更新这三个同名文件。它读取已保存的识别结果，在本机生成文档，不会重新上传录音或发起识别。如果某种格式写入失败，已有文件会保留，其他格式仍会继续处理。

## 使用时需要留意

如果已经手工修改过 Word 或 Excel，并希望保留这些修改，请在重新导出前另存副本。旧版本产生的目录和文件会留在原位置，可以按需要自行整理。

中英文使用说明、Agent 规则和 UML 也已跟随这次改动更新，文档里的保存路径与程序一致。

## 下载与开始使用

下载 Assets 中的 **asr-agent.zip**，解压后用 Codex 打开 `asr-agent` 文件夹，输入“请安装 asr-agent，并打开录音转写页面”。环境准备与账号配置见[使用说明](https://github.com/hx101700/asr-agent/blob/v0.1.1/README.md)。

语音识别由[阿里云百炼](https://help.aliyun.com/zh/model-studio/what-is-model-studio)提供，通过官方 [BL CLI](https://github.com/modelstudioai/cli) 调用。asr-agent 负责把本机选择文件、配置增强和保存文档这些步骤串起来。
