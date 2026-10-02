# 当前状态

更新：2026-10-03。

## 产品与实现

MemoFlow 旨在把语音输入整理为符合用户习惯和指定格式的会议纪要，并从确认后的范例与修改中改善后续结果。当前完成第一阶段 `asr-transcription` Skill：配置一个录音，经官方 BL CLI 转写，交付原始 JSON、Word、Excel 和 Markdown 供用户校对。个性化纪要与反馈学习尚待第二阶段实现。

- Skill 源码：`skills/asr-transcription/`；CLI 入口：`scripts/asr.py`；内部 Python 包：`scripts/asr_runtime/`。
- 代码保持入口 → application → utils；BL 负责鉴权、上传、提交、轮询与下载，本项目负责本机配置、媒体准备和文档生成。
- Vue 3、TypeScript、Element Plus 页面提供中英文、系统/浅色/深色主题，以及网页 API Key 编辑。运行环境、凭据与任务保存在用户工作目录，Skill 资源保持只读。

## 当前交付

完整审查覆盖手写运行代码、前端、依赖声明、测试、使用与开发文档、UML及发行清单。修复了图表工作表输入导致热词解析异常、损坏交付记录导致状态查询异常，以及 Word 复杂文字字号未遵循统一设置的问题；删除了一项无消费者的前端文案。安装 UML 已区分当前解释器检查与安装子进程。

新空目录联网安装成功；实际 ZIP 解压代码的 291 项 Python 回归全部通过、无跳过。34 项前端测试、1 项真实 Edge 集成场景、Python 与 Vue 类型检查、Skill 格式及包边界检查通过。具体证据、首次测试发现和人工验收范围见 [ACCEPTANCE](ACCEPTANCE.md)，职责审查见 [REVIEW](REVIEW.md)。

本地发行包：`dist/asr-transcription.zip`，42 个文件，268948 字节。SHA-256：`f67d3c19aabbeeca89ce41f373234ec4738ae2f8819b07221b88c285e053c86c`。包仅包含独立 Skill 所需文件；开发文档、UML、测试、构建工具、运行环境和用户数据留在包外。

## 分支与发布

仓库：[hx101700/memoflow](https://github.com/hx101700/memoflow)，默认分支为 `dev`，项目版本保持 `0.1.0`。本轮按用户要求覆盖现有 [v0.1.0 开发预览](https://github.com/hx101700/memoflow/releases/tag/v0.1.0)，远端结果在实际发布和下载核对后补充。

`master` 基线为 `6c8371135d92b9f9d3bd52ca9ee246747f0c7f5e`；本轮不合并。版本号仅在通过验收并正式发布到 `master` 时变更。

## 下一步

在目标 Windows 的新 Codex 对话中完成完整使用验收，补齐真实云端、原生目录窗口和 Office 视觉证据后，再决定第一阶段的 `master` 里程碑。当前限制见 [ISSUES](ISSUES.md)；模块与协议见 [DEVELOPMENT](DEVELOPMENT.md)，图示见 [UML](UML.md)。
