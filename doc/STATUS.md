# 当前状态

更新：2026-10-03。

## 产品与实现

MemoFlow 的目标是将语音输入整理为符合用户习惯和指定格式的会议纪要，并从确认后的范例与修改中改善后续结果。当前完成第一阶段 `asr-transcription` Skill：配置单个录音，经官方 BL CLI 转写，交付原始 JSON、Word、Excel 和 Markdown 供用户校对。个性化纪要与反馈学习尚待第二阶段实现。

Skill 位于 `skills/asr-transcription/`，CLI 入口为 `scripts/asr.py`，Python 执行包为 `scripts/asr_runtime/`。代码保持入口 → application → utils；前端为 Vue 3、TypeScript、Element Plus。运行环境、凭据与任务写入用户工作目录，Skill 资源保持只读。

## 当前工作：依赖下载恢复

已完成并发布安装器改进：

- 安装前并行采样 PyPI 与阿里云镜像的文件前缀，优先选择较快来源。
- 使用摘要锁定的 pip 26.2.1，业务依赖的中断恢复由 pip 处理；每来源一次下载流程，失败后尝试另一个来源。
- 完整 wheel 保存在私有工作目录，下载成功后再从本机文件安装；本机安装错误不触发换源。
- 安装进程持续输出进度并同步写日志，没有下载总耗时上限。
- 云端转写继续保持失败不自动重试，npm 安装仍为单次尝试。

相关代码为 `application/bootstrap.py` 和 `utils/installation.py`。Skill、使用说明、开发规则和安装 UML 已同步。

本轮在新空目录完成联网安装，PyAV 27.6 MB 完整下载，Python 依赖及 BL 2.1.0 安装成功，doctor 的 issues 为空。发行 ZIP 解压代码执行 306 项 Python 回归通过、无跳过，包含真实 pip 的断流/续传、重新下载与摘要拒绝，以及 BL 本机合约；mypy 检查 29 个文件通过。实际范围见 [ACCEPTANCE](ACCEPTANCE.md)。

发行包：`dist/asr-transcription.zip`，43 个文件，272860 字节。SHA-256：`3f8cf2ba1221b6d8ca84ca2948974376e00c69291c13d2513fc839a99a03d745`。仅新增必要的安装工具模块，开发文档、UML、测试、安装环境、wheel 缓存和用户数据均在包外。

## 分支与发布

仓库为 [hx101700/memoflow](https://github.com/hx101700/memoflow)，开发分支为 `dev`。安装器实现提交 `3df8d2166e9d1a9de02f359fe6740850be7f2ca7` 已推送。现有 [v0.1.0 开发预览](https://github.com/hx101700/memoflow/releases/tag/v0.1.0) 已更新中英文说明及 ZIP，旧附件已替换，公开下载与上述本地包逐字节一致；远端代码、文档和图稿的完整文件树核对通过。

远端只保留一个 `v0.1.0` 标签和一个开发预览。项目版本保持 `0.1.0`，只有正式发布到 `master` 时才变更；`master` 保持 `6c8371135d92b9f9d3bd52ca9ee246747f0c7f5e`，本轮未合并。

## 下一步

从 Release 下载新 ZIP 并更新安装测试所用的 Skill 副本，验证目标网络中的安装体验。完整第一阶段验收仍需目标 Windows 的新 Codex 对话、真实云端识别、原生目录窗口与 Office 视觉证据；随后再决定 `master` 里程碑。限制见 [ISSUES](ISSUES.md)，模块见 [DEVELOPMENT](DEVELOPMENT.md)，图示见 [UML](UML.md)。
