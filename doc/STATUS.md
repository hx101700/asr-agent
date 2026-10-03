# 当前状态

更新：2026-10-03。

## 产品与实现

MemoFlow 的目标是把录音整理为符合用户习惯和指定格式的会议纪要，并从用户确认的范例与修改中改善后续结果。当前第一阶段 `asr-transcription` 提供本机网页配置、BL 转写及 JSON、Word、Excel、Markdown 校对稿；个性化纪要与反馈学习属于后续阶段。

Skill 位于 `skills/asr-transcription/`，入口为 `scripts/asr.py`，执行包为 `scripts/asr_runtime/`。代码保持入口 → application → utils，前端为 Vue 3、TypeScript、Element Plus。

## 当前工作：页面启动与选择录音

本轮修正真实使用中出现的启动误导：

- 新转写先打开网页，录音由网页文件选择器接收；工作目录优先复用会话约定，否则采用当前任务目录。
- 有宿主浏览器工具时使用 `serve --no-browser`，打开完整启动 URL，并依据实际页面或用户反馈确认显示。
- `serve` 输出 `event=listening` 及 `browser_request`，分别表示端口监听和系统打开请求结果。系统调用失败时保留本机服务，启动回执写入失败时关闭服务。
- 宿主没有页面查看能力时请用户确认，不为检查网页额外扫描或控制桌面应用。本机配置页与 BL 授权页分开说明。

定向启动、HTTP与打包检查共51项通过，mypy检查29个文件通过，官方Skill格式校验通过。新候选包在本对话实际显示，用户已确认；另在用户指定的agent对话启动同一候选代码，主对话通过浏览器接口核对该实例的页面和截图。实际证据与范围见[ACCEPTANCE](ACCEPTANCE.md)。

前端构建文件始终包含在ZIP中；本轮只修改启动代码与指引，静态HTML、JavaScript和CSS保持原有内容。

## 清理与用户当前操作

用户指定测试位置中的旧ZIP、旧运行目录和用户级asr-transcription Skill已删除。agent对话复测产生的空白临时副本也已清理，原始MP3保留。

用户随后在本项目 `.runtime/browser-startup-case/work` 的页面自行添加真实录音并完成本机预览。该页面、服务和工作目录已保留，未执行云端识别；后续清理须先确认用户已结束操作。这个目录用于本轮页面验证，复用开发Python依赖，不代表已完成其独立工作区的BL环境准备。

## 分支与发布

开发分支为 `dev`，项目版本保持 `0.1.0`。网页启动修正已推送，源码提交为`7192c2d4ec13dd3a2cedaa4031395b8562cfa0f6`。现有[v0.1.0开发预览](https://github.com/hx101700/memoflow/releases/tag/v0.1.0)已更新附件和中英文发布说明，远端仍只有一个标签和一个Release，`master`保持不变。

已发布ZIP：`dist/asr-transcription.zip`，43个文件、274650字节，SHA-256：`03756c1cd8a0f645713bc399f30a250f5ccde22c2944f92fb63bff460ee6f706`。公开下载与本机包逐字节一致，远端完整Git树与本机提交一致。仅包含Skill运行所需文件；开发文档、UML、测试、运行环境及用户数据不入包。

原Windows红色错误弹窗的具体错误码未保留，原因仍未确认。已验证的修复范围是网页启动指引、回执语义，以及通过宿主浏览器打开页面。后续完整使用、BL授权和真实识别按用户需求单独验收。
