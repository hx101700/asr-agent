# 当前状态

更新：2026-10-03。

## 产品

MemoFlow 的目标是把语音输入整理为符合用户习惯、重点要求和指定格式的会议纪要，并从用户确认的范例与修改反馈中持续学习。当前已实现第一阶段 `asr-transcription`：通过 BL 2.1.0 调用北京地域的固定模型，交付原始 JSON、Word、Excel 和 Markdown 校对稿。个性化纪要与反馈学习属于尚待实现的第二阶段。

## 当前工作

配置页面已采用 Vue 3、TypeScript 和 Element Plus，提供中文/English 切换及跟随系统、浅色、深色主题。API Key 可直接在网页填写、修改，在检查时保存到当前工作目录；转写执行继续从该固定文件读取。Python 已补充共享协议类型和开发阶段静态检查。前端源码放在仓库 `frontend/`，通过 Vite 构建为 Skill 内的网页资源，用户 ZIP 只包含构建结果。

Vue 页面与 Python 类型改动已完成既有回归。本次对照官方 Skill 写作建议及实际代码完成独立情境复核，补充保存回执恢复、工作目录凭据范围和基础解释器诊断指引；新增终端回执丢失场景验证通过。详细证据见[ACCEPTANCE](ACCEPTANCE.md)。

内部 Python 执行包统一为 `asr_runtime`，与对外 Skill `asr-transcription` 区分。入口、导入、测试、构建清单和 UML 路径已同步；类型检查、13 项包与结构检查、真实 Edge 配置场景通过。现有命令、任务目录和业务协议保持一致。

本地包：`dist/asr-transcription.zip`，42个文件、268497字节，SHA-256：`c199794834510a741936f67977465290b73b5a09f303755834a238d059528d03`。CRC、固定清单、每文件内容与 Skill 源码均核对通过；包内没有 TypeScript/Vue 源码、开发工具、测试、UML 或用户数据。

## 实现

- Skill源位于skills/asr-transcription，代码按入口→application→utils组织。BL保持公开CLI适配模块，不另设BL Skill。
- 用户工作目录显式传入--workspace；程序资源、私有运行目录与输出位置有明确边界。
- 运行根与Skill重叠、原生选择/默认及最终输出写入Skill均被拒绝；Python检查和安装进程使用-I隔离工作目录模块。
- Vue组件、页面用例、HTTP协议与Python业务边界已按实现核对，审查依据见[REVIEW](REVIEW.md)。

## 版本与远端

GitHub 仓库已重命名为 [hx101700/memoflow](https://github.com/hx101700/memoflow)，默认分支为 `dev`，本地 origin 已同步。项目版本保持 `0.1.0`；仅通过验收并发布到 `master` 时才变更项目版本，开发提交沿用当前版本。

包名调整提交 `827c15fd30ae69fa9d124ade08e9de472b154886` 已同步到 `dev`，现有 [v0.1.0](https://github.com/hx101700/memoflow/releases/tag/v0.1.0) 开发预览已替换为新的 ZIP。公开下载与本地包逐字节一致，包中仅含新的内部路径。项目版本号仍为 `0.1.0`；`master` 保持 `6c8371135d92b9f9d3bd52ca9ee246747f0c7f5e`，本次未合并。

## 接续

先核对Git与本文件，沿[DEVELOPMENT](DEVELOPMENT.md)了解职责与协议；实际限制见[ISSUES](ISSUES.md)。使用入口为Skill内SKILL.md；开发脚本、测试和UML不进入用户ZIP。
