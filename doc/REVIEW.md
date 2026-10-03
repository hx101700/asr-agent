# 代码审查

日期：2026-10-04。下表保留当前版本的整体源码审查范围；本轮沿用户实际词表和对话，追踪导入、行级错误展示、上下文检查、保存后返回修改及ZIP更新边界。实际结果见[ACCEPTANCE](ACCEPTANCE.md)，历史修正通过Git追溯。

## 阅读覆盖

Python 代码路径相对于 `skills/asr-transcription/`；前端与开发配置路径相对于仓库根。阅读范围按模块职责记录，避免把文件数量当作审查充分性的依据。

| 范围 | 完整阅读的文件 |
| --- | --- |
| 入口与共享定义 | scripts/asr.py；scripts/asr_runtime下的__init__.py、__main__.py、models.py、error_catalog.json |
| 应用用例 | application下的__init__、bootstrap、diagnostics、inputs、rules、session、transcription、delivery |
| 本机能力 | utils下的__init__、environment、installation、auth、bailian、files、job_files、results、media、hotwords、documents、directory_picker、_directory_dialog、i18n |
| 网页 | web.py；frontend下的App.vue、main.ts、useTranscription.ts、model.ts、api.ts、types.ts、preferences.ts、i18n.ts、style.css、index.html，以及UploadField、KeyDisplay、ReviewPanel组件 |
| 技能与依赖 | SKILL.md、agents/openai.yaml、assets/env.example、references全部；scripts/requirements.txt、bailian/package.json和package-lock.json全部锁项 |
| 开发与交付 | scripts/build_zip.py、probe_bl.py；前端package/lock、vite/tsconfig配置和Python静态检查配置；README/AGENTS双语、doc文档、UML源稿与图、Release说明；运行、权限、媒体、文档、HTTP、前端和打包相关测试 |

第三方BL及Python依赖按锁定版本使用。本审查核对其公开接口、安装边界和实际调用，不把对项目源码的审查称为第三方全部代码审计。

## 本次发现与处理

| 位置 | 问题与处理 |
| --- | --- |
| `App.vue` / `HotwordEditor.vue` | 后端已经返回热词行号，但顶部Alert与自动聚焦后的字段区域分离，用户只看到通用提示。改为在表格行和单元格内显示原因；错误内容保留供修改，支持直接填写 |
| `inputs.import_hotwords` / `rules.build_vocabulary` | Excel只作导入来源，最终检查使用编辑后的行；导入、检查词表及预览共用唯一规则。真实公式与普通字符串分别处理，避免新增未经依据的内容限制 |
| `validate_context` / `checkRequiredInputs` | 本轮没有已复现的语义故障案例，核对官方400字符规则；提示明确空白、字符总数/超出数及不可传输字符位置，保留原文 |
| `Session.reopen` / Skill回执处理 | 原页面保存后只有只读回执，再次打开也不能修改。新增撤回操作，复用一次执行占用阻止旧编号上传；恢复原表单，再次确认产生新编号，已开始任务拒绝覆盖 |
| `asr.py` / `update_skill.py` | ZIP更新复用同一Skill，标准库脚本暂存并整体替换，失败回滚。真实Windows测试证明入口只读句柄阻止运行期间目录改名；旧版无此保护，指令要求核对原会话 |

新增编辑表格直接使用Element Plus公开组件；协议JSON请求上限调整为512KiB以容纳2000条词表及行号。没有新增云端客户端、电子表格执行引擎、进程注册表或数据迁移层。更新器的Windows路径拒绝规则来自隔离目录的实际文件操作结果，相关回归保留在测试中。

## 职责判断

保留一个录音转写Skill。它是一个明确用户任务，Codex负责流程选择与授权；utils/bailian.py是官方CLI适配模块，映射参数、准备子进程、解释错误。BL负责鉴权、临时上传、提交、轮询和结果下载。本机JSON解析与文档排版由本项目完成。

现在没有第二项独立BL业务用例需要跨Skill交接认证或工作目录。出现真实的新用例时，再根据共同消费者提取共享调用代码；不为未知能力增加通用Agent、动态工具注册或新的云客户端。

安装下载的恢复策略独立于云端任务。安装器只比较两个固定来源的短时文件吞吐、安排下载和本机安装；完整文件下载、续传与摘要验证直接使用锁定pip的公开CLI。安装失败的有限换源不影响转写的一次执行约束。

utils是Python包内的能力分组。application协调步骤，utils执行具体操作；没有反向导入用例。通用安装/诊断进程与BL进程在凭据、输出和生命周期上不同，保持各自入口有实际依据。

Vue 组件负责呈现和浏览器操作，useTranscription编排页面用例，model管理纯状态规则，api处理本机会话HTTP；界面偏好与任务配置分开。Python TypedDict和TypeScript接口说明现有数据协议，静态检查放在开发环境，用户ZIP交付运行代码和构建资源。

以下检查有当前消费者，保留在各自边界：

- 登录后的`auth status`区分模型凭据存在与单纯进程退出；固定BL闲置超时也可能退出0。Windows浏览器适配在第一次开页前转交完整URL，保留原BL授权会话。
- 预览SHA建立用户确认基线，确认只检查文件属性，执行SHA确认实际上传内容；重导使用配置及原JSON摘要。热词执行不再读取Excel。
- 前端输入检查提供即时定位，后端约束HTTP输入；上传与目录请求的短锁、请求编号用于实际并发和取消。
- Excel/Word运行时回读是现有交付判定的一部分，验证库实际写入的内容；删除它会改变交付语义，不作为无行为变化的精简处理。

## 写入与执行边界

| 场景 | 当前约束 |
| --- | --- |
| 私有运行目录与Skill重叠 | Runtime在构造及解析运行根时拒绝两者任意方向重叠，常规项目内Skill布局仍可用 |
| 原生选择Skill为输出目录 | 在选择探测前、预览和最终JSON/文档创建前复用check_output_path拒绝，保留用户选择其它目录的能力 |
| 工作目录同名Python模块 | 版本检查、依赖检查、ensurepip和pip使用-I；真实子进程回归确认工作目录中的json.py/sysconfig.py不参与这些操作 |
| 凭据与上传 | 用户在密码输入框编辑Key，检查时按需通过专用接口保存到工作目录私有.env；转写执行读取该文件，console独立使用BL配置；网页保存与云端执行授权分开，失败不自动重试 |
| 文件与原文 | 上传由会话ID引用；预览/确认/执行的摘要用途各不重复；导出失败保留已有目标，记录失败保留当次已知事实 |

这些是本工具入口的路径和进程约束，不代替Windows文件系统ACL；本地管理员仍拥有操作系统授予的权限。调用时若操作系统拒绝写入，程序报告实际失败，不修改系统权限。

## 变量与接口

- Runtime.workspace是用户工作目录，skill_root是程序资源；root是私有运行目录，output_root是默认结果位置。
- audio_tracks/channel_id描述音轨，channels描述音轨内声道；单声道转换使用已确认AudioInfo，没有混用。
- config是已确认输入，execution是执行记录，delivery是文档交付。job-status读取记录，不能表示云端实时状态或进程仍存活。
- export_documents(runtime, config, transcript)自行派生任务目录，避免调用者同时传入可能不一致的运行上下文与任务根。
- result_path(config)负责解析和读取位置；实际写入位置在prepare_result/prepare_documents检查，不增加重复写权限层。
- 前端Language与Theme描述界面偏好，FormValues.language描述音频语言，配置中的region固定cn-beijing；切换界面语言不会改变识别参数或文档格式。
- Key仅由KeyDisplay组件的局部ref持有，通过ViewEffects在需要读取或保存时传递；Model只记录凭据状态，localStorage只保存语言与主题。

## 验证

针对性复现、安装、完整回归与发行核对的实际结果集中记录在[ACCEPTANCE](ACCEPTANCE.md)。未覆盖的真实云端、原生桌面和Office人工场景见[ISSUES](ISSUES.md)。

## Skill 指令审查

本轮核对[Agent Skills格式规范](https://agentskills.io/specification)、[OpenAI Skill文档](https://learn.chatgpt.com/docs/build-skills)和[指令写作建议](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)。当前结构符合必需的SKILL.md及name/description格式，scripts、references、assets按用途组织；agents/openai.yaml是OpenAI支持的可选展示元数据，隐式调用保持默认开启。

参考方向限定为带本机脚本或外部CLI的任务型Skill：

| 官方范例 | 借鉴点 | 本项目取舍 |
| --- | --- | --- |
| [transcribe](https://github.com/openai/skills/blob/main/skills/.curated/transcribe/SKILL.md) | 描述对应录音转写意图，固定脚本入口，说明输出和引用资料 | 保留BL与网页选文件；不采用其OpenAI模型、默认参数或重复识别策略 |
| [gh-fix-ci](https://github.com/openai/skills/blob/main/skills/.curated/gh-fix-ci/SKILL.md) | 使用现有CLI，给出输入默认值、任务边界及可操作结果 | 认证按本项目已知状态选择，避免每次重复检查；不引入其计划审批流程 |

入口先区分新录音与已有任务，正常路径保留必要的回执、授权及人工交接；安装、错误修复和模型限制按需加载。交付使用json_path和各READY文件的path，减少额外查找。范例用于设计参照，不表示外部Skill的全部规定都适用于本项目。

独立审查完整阅读 Skill 与引用资料，并核对实际 CLI 帮助和代码。入口与实现一致，条件分支明确以下操作：

- 网页保存成功而终端回执丢失时，通过同一网页或用户保留的确切任务编号及 `job-status` 核对，避免继续无条件等待或猜测最新任务。
- 控制台模式复用当前工作目录的 BL 模型凭据；以 `configured` 区分模型 Key 与单独的控制台登录状态。
- 虚拟环境解释器不可运行时，使用首次准备环境的 CPython 3.12 执行 `doctor`。
- 新录音从本机网页文件选择器进入；取得监听回执后通过宿主打开一次URL，立即让用户操作。computer-use和页面自动检查不属于正常使用依赖；工作目录与录音路径分别处理。

格式校验和情境评审用于核对指令明确性与实现一致性；完整使用效果仍需目标用户环境验证。
