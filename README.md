# asr-agent

面向 Codex 的本地非实时语音转写工具，计划通过阿里云百炼 CLI 固定调用 `qwen-audio-3.0-asr-flash-filetrans`。

> 当前处于需求与方案设计阶段，尚未提供可运行的转写功能或安装包。

首版范围：Windows 10/11、Codex 桌面端、单文件输入、临时 OSS、带时间戳的 Excel / Word / Markdown 三种成品，以及本地 JSON 结果。说话人区分默认开启、可关闭；开启时多声道将合并为单声道，网页会在确认前提示，原文件保留。

- 开发者从 [文档索引](doc/README.md) 和 [当前状态](doc/STATUS.md) 开始。
- 用户流程见 [使用说明](doc/HELP.md)，阶段验收见 [验收计划](doc/ACCEPTANCE.md)。
- Codex 项目协作规则见 [AGENTS.md](AGENTS.md)。

测试数据、凭据和转写结果仅在本地保存，不进入 Git 和发布包。
