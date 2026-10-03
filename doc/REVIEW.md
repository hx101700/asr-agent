# 代码审查

日期：2026-10-03。范围为本仓库维护的Skill源码、前端、依赖声明、开发脚本、相关测试、使用文档及UML。采用全文阅读、沿调用者追踪数据和写入位置、合成复现与回归验证；检索用于修改后的引用核对。当前版本的验证结果记录在[ACCEPTANCE](ACCEPTANCE.md)。

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

## 本轮确认与修正

| 位置 | 问题与处理 |
| --- | --- |
| `SKILL.md` / `references/usage.md` | 新任务启动曾被理解为先询问录音路径；现在复用当前工作目录，明确先打开网页、在页面选文件 |
| `web.py::serve` | 默认浏览器的返回值未进入回执，调用方容易将启动请求当作页面已显示；现在分别报告监听与浏览器请求状态，失败时保留可访问服务，输出失败时释放服务 |
| `utils/hotwords.py` | Excel的图表工作表也会出现在sheetnames中。读取行列前检查Worksheet类型，沿既有字段错误链返回中英文提示 |
| `utils/job_files.py` | 损坏交付记录的files为列表时会触发AttributeError；在现有记录解析入口识别该类型错误，返回OUTCOME_UNKNOWN并保留已知JSON结果 |
| `utils/documents.py` | Word模板的复杂文字字号可独立继承，原设置只覆盖普通文字字号；现在统一设置w:szCs和复杂文字粗体，与标题20磅、正文等样式10磅保持一致 |
| `frontend/i18n.ts` | 删除两种语言中无消费者的saved文案键，并重新构建网页资源 |
| `tests/test_web.py` | 负向认证测试向已拒绝的连接继续发送正文，在Windows偶发连接中止；改为验证正文读取前即返回403，生产HTTP逻辑保持原有行为 |
| `doc/uml/02-install.*` | 将当前进程内check_python与本机检查/安装子进程分开表达，重绘PNG；其余九份图稿与当前调用、状态协议一致 |

上述修正复用现有解析、样式和错误处理入口；没有增加新的运行校验层或兼容入口。STATUS与ACCEPTANCE统一描述当前版本，移除重复堆叠的迁移与验收叙述。

## 职责判断

保留一个录音转写Skill。它是一个明确用户任务，Codex负责流程选择与授权；utils/bailian.py是官方CLI适配模块，映射参数、准备子进程、解释错误。BL负责鉴权、临时上传、提交、轮询和结果下载。本机JSON解析与文档排版由本项目完成。

现在没有第二项独立BL业务用例需要跨Skill交接认证或工作目录。出现真实的新用例时，再根据共同消费者提取共享调用代码；不为未知能力增加通用Agent、动态工具注册或新的云客户端。

安装下载的恢复策略独立于云端任务。安装器只比较两个固定来源的短时文件吞吐、安排下载和本机安装；完整文件下载、续传与摘要验证直接使用锁定pip的公开CLI。安装失败的有限换源不影响转写的一次执行约束。

utils是Python包内的能力分组。application协调步骤，utils执行具体操作；没有反向导入用例。通用安装/诊断进程与BL进程在凭据、输出和生命周期上不同，保持各自入口有实际依据。

Vue 组件负责呈现和浏览器操作，useTranscription编排页面用例，model管理纯状态规则，api处理本机会话HTTP；界面偏好与任务配置分开。Python TypedDict和TypeScript接口说明现有数据协议，静态检查放在开发环境，用户ZIP交付运行代码和构建资源。

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

对照[OpenAI Skill 文档](https://learn.chatgpt.com/docs/build-skills)和[技能指令写作建议](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)，入口保留触发范围、工作目录、主流程和交付判定；安装细节、错误分支与模型资料按需进入 references。Skill 描述当前可执行的转写能力，项目的个性化纪要目标写入产品文档。

独立审查完整阅读 Skill 与引用资料，并核对实际 CLI 帮助和代码。入口与实现一致，条件分支明确以下操作：

- 网页保存成功而终端回执丢失时，通过同一网页或用户保留的确切任务编号及 `job-status` 核对，避免继续无条件等待或猜测最新任务。
- 控制台模式复用当前工作目录的 BL 模型凭据；以 `configured` 区分模型 Key 与单独的控制台登录状态。
- 虚拟环境解释器不可运行时，使用首次准备环境的 CPython 3.12 执行 `doctor`。
- 新录音从本机网页文件选择器进入；先取得监听回执，再通过宿主浏览器工具打开并核对页面。工作目录与录音路径分别处理。

格式校验和情境评审用于核对指令明确性与实现一致性；完整使用效果仍需目标用户环境验证。
