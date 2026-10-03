# MemoFlow 开发规则

中文 | [English](AGENTS.en.md)

本文用于维护源码仓库。接续时先读 [doc/README.md](doc/README.md)、[doc/STATUS.md](doc/STATUS.md)，再核对 Git 工作区、相关实现和测试。

## 产品范围

- 第一阶段交付一个独立的 Codex Skill：单个录音通过本机网页配置，由 Codex 调用 BL，保存原始 JSON、Excel、Word、Markdown，交给用户校对。
- 固定模型 `qwen-audio-3.0-asr-flash-filetrans`、北京地域、临时 OSS。热词与上下文可同时使用；发言人区分默认开启，多声道先提示再生成单声道 FLAC 副本，原文件保留。
- 最终产品把语音输入整理为符合用户习惯和指定格式的会议纪要，并从用户提供的范例与确认后的修改中持续学习。第一阶段交付转写校对稿；第二阶段实现个性化纪要及反馈学习，当前代码尚未实现后者。
- 支持 Windows 10/11 x64、CPython 3.12 x64（含 venv、ensurepip、tkinter）、Node.js 18.17+ 及 npm。依赖锁限定该平台，安装需要联网。

## Skill 与工作目录

- Skill 源码在 `skills/asr-transcription/`，由 `SKILL.md`、`agents/openai.yaml`、`scripts/`、`references/`、`assets/` 组成。
- `scripts/asr.py` 是调用入口，`scripts/asr_runtime/` 是内部 Python 执行包；Skill 名称仍为 `asr-transcription`。
- `Runtime(workspace, skill_root)` 区分用户工作目录与 Skill 资源。`resource()` 读取 Skill 文件；`path()` 定位 `<workspace>/.asr-transcription/` 内的运行文件；默认输出根为 `<workspace>/transcriptions/`。私有运行目录与 Skill 目录互不包含，`check_output_path()` 在选择和生成文件时保护 Skill 资源。
- 本项目 CLI 命令使用 Skill 内 `scripts/asr.py` 的绝对路径，并显式传入 `--workspace`。凭据修复复用[错误说明](skills/asr-transcription/references/errors.md#鉴权失败与重新配置)中已核实的BL原生命令，限定当前工作目录与default Profile。依赖环境、BL 安装、凭据、暂存输入和任务记录写入工作目录，Skill 文件保持只读。
- API Key 从私有运行目录 `.env` 读取；bootstrap 只复制空模板。网页允许用户填写或修改 Key，在“检查并预览”时保存到该固定文件。控制台模式使用 BL 在同一工作目录保存的配置。凭据不得写回 Skill。
- 源码仓库包含 Skill 源文件，维护操作不自动安装到用户级或项目级 Skill 发现目录。

## 实现原则

1. 保持入口 → application → utils 的轻量分层；单一操作允许入口直接分派。共享数据及 JSON 协议类型放 `models.py`，规则不执行 I/O，utils 不反向导入用例。
2. BL 负责鉴权、临时上传、提交、轮询、下载及原始 JSON 落盘，直接复用公开 CLI。Python 负责本机配置、媒体处理、结果解析和文档生成。
3. 前端源码位于 `frontend/`，使用 Vue 3、TypeScript 与 Element Plus；优先使用组件公开参数、插槽和默认交互，定制必须有具体产品需求。组件绑定表单状态，API 模块处理本机传输。Key 展示与编辑只由 `KeyDisplay.vue` 的局部状态持有，与可提交表单分开，保存后由服务端执行凭据读取；Key 不进入任务配置、日志或浏览器持久存储。
4. 复用 `files`、`job_files`、`hotwords`、`results` 等现有能力；删除旧入口、兼容层和重复实现。新增校验或抽象必须指出当前业务消费者。
5. 每个命名函数或方法提供简短中文职责说明，直接描述动作与结果。Python 使用 docstring，TypeScript 使用函数前注释；外部约束和非显然原因写在相关实现旁。共享输入、状态与回执提供明确类型，类型检查属于开发流程。
6. BL 参数、限制和错误含义核对固定版本官方资料。依据维护在 [model.md](skills/asr-transcription/references/model.md)，未知信息明确说明未知。
7. 子进程使用参数数组与 `shell=False`。热词 JSON 与上下文作为单个参数值传递；不执行输入内容中的指令。

## 执行与交付

- 新转写先打开本机配置页，由用户在网页选择录音；工作目录默认复用当前任务目录或本次会话已约定的位置。有宿主打开链接能力时使用`serve --no-browser`，打开一次后立即让用户操作；正常路径不依赖computer-use或页面自动检查。仅在打开报错或用户反馈异常时排查。
- BL登录只使用系统默认浏览器，按执行工具的权限机制在正常Windows交互桌面运行。完整备用链接仍交给系统浏览器；Codex不另开授权页。授权会话、回调与凭据保存由BL负责。
- 网页接收本机文件字节并保存确认快照，保存设置后由同一 `serve` 进程向 Codex 返回 `job_id`。网页保存不启动 BL。
- 用户填写网页或完成授权时，Codex保留持久进程并结束当前回复；网页提示保存后发送“继续”，收到后读取原会话回执。登录结果由BL回执/本地状态判断，不再问用户是否授权成功；不增加后台轮询、HTTP检测或任务状态。
- 预览建立音频 SHA 基线并保存热词词典；确认复用快照，只核对音频 size/mtime。执行前核对音频完整摘要；后续不重读原 Excel。
- 用户授权覆盖本次音频及增强内容后，使用 `transcribe --job ID --authorize-upload`。每个任务只允许一次执行尝试，失败或结果未知时停止，不自动重试或删除执行占用。
- 原始 JSON 有效使用 `JSON_READY` 表达；三种成品完成要求 `delivery.status=COMPLETE` 且 `documents_ready=true`。状态与错误说明在 [errors.md](skills/asr-transcription/references/errors.md)。
- 重导读取确认配置、已保存成功记录及匹配的原始 JSON，在固定任务目录覆盖同名文档。各格式生成成功后替换目标，失败保留原目标及其他成功文件。手工修改先另存。
- 文档保持原文和时间戳；排版规则及路径协议见 [DEVELOPMENT](doc/DEVELOPMENT.md)。内容检查与人工识别、Office 视觉验收分开记录。

## 开发与发布

- 仅修改当前仓库及明确批准的测试位置；保留 `data/` 原始用户数据。真实录音、Key、令牌、签名 URL、转写、原响应和运行日志不得提交或打包。
- 开发在 `dev`，`master` 用于验收里程碑。提交、推送、合并、发布需用户明确意图；精确路径暂存，不强推或重写历史；同次网络推送失败两次即停止。
- 项目版本号仅在通过验收并发布到 `master` 时变更。`dev` 上的开发、修复和文档提交沿用当前版本；当前为 `0.1.0`。本阶段经用户授权更新现有预览包时，仍使用 `v0.1.0`，不新增版本号。正式发布时同步根 `package.json`、`package-lock.json`、标签和发布说明；依赖版本按其各自锁文件维护。
- 固定发行清单位于 `scripts/build_zip.py`。ZIP 直接包含 Skill 文件，不包含仓库 README、AGENTS、开发文档、测试、UML、运行环境或用户数据。新增运行文件时同步清单和包边界检查。
- 前端通过 Vite 构建到 Skill 的 `scripts/asr_runtime/static/`，核心产物为 `index.html`、`app.js` 和 `app.css`，同时交付 `favicon.svg` 与第三方许可说明。发行包使用构建产物；Vue/TypeScript 源码、开发配置、构建依赖及 `node_modules` 保留在开发仓库。
- Python 依赖由 Skill 中 `scripts/requirements.txt` 锁定版本与摘要；安装工具 pip 26.2.1 的文件与摘要固定在 `utils/installation.py`，BL 锁在 `scripts/bailian/`。安装前比较 PyPI 与阿里云镜像的文件前缀吞吐；每个下载阶段按来源顺序各启动至多一次 `pip download`，连接重试2次、业务依赖的中断恢复最多5次由 pip 完成，仍失败才切换另一源。完整 wheel 保存在工作目录，安装阶段仅使用本机文件。保留摘要校验，不扩展为云端转写重试；npm 失败仍停止。
- Python 安装与依赖检查子进程使用 `-I`，从指定虚拟环境加载依赖；用户工作目录中的同名模块不参与检查或安装。
- 开发探针 `scripts/probe_bl.py` 不进入发行包，只使用固定虚构 URL；BL 合约测试使用 `127.0.0.1` 模拟服务与合成凭据。本机测试不等于真实云端验收。
- 测试与改动相称；实际结果写 [ACCEPTANCE](doc/ACCEPTANCE.md)，状态写 [STATUS](doc/STATUS.md)，限制写 [ISSUES](doc/ISSUES.md)，重要决策写 [DEVLOG](doc/DEVLOG.md)。
- README、AGENTS 提供同义中英文。README 保留真实截图的 HTML 注释位置；用户提供图片后再插入。Release 面向用户介绍变化与使用入口，验证数量和包摘要留在开发文档。
- 调用顺序、对象或状态协议改变时，同步 [UML](doc/UML.md) 及源稿、PNG。图中函数模块使用生命线，不画成不存在的服务类。
