# 开发说明

本文说明 MemoFlow 的产品边界、当前 Skill 的模块职责和任务协议。操作说明集中在 [usage.md](../skills/asr-transcription/references/usage.md)，对象与调用关系见 [UML](UML.md)，实际验证见 [ACCEPTANCE](ACCEPTANCE.md)。

## 业务与角色

MemoFlow 是整个产品，目标是从语音输入生成符合用户习惯、重点要求和指定格式的会议纪要，并根据用户提供的范例与确认的修改反馈持续改善。`asr-transcription` 是当前已实现的第一阶段 Skill，承担录音转写与校对稿交付；项目名称与这个具体能力的名称分开维护。

| 名称 | 作用与位置 |
| --- | --- |
| `MemoFlow` | 项目与产品名称 |
| `asr-transcription` | Codex 使用的录音转写 Skill，位于 `skills/asr-transcription/` |
| `asr_runtime` | Skill 内部的 Python 执行包，位于 `scripts/asr_runtime/`，由 `scripts/asr.py` 调用 |

第一阶段将单个本地录音转为原始 JSON、Excel、Word、Markdown，交给用户检查。模型固定为 `qwen-audio-3.0-asr-flash-filetrans`，北京地域，通过 BL 的临时 OSS 上传。

Codex 读取 Skill，选择工作目录、执行工具并解释回执。网页接收本机文件、编辑选项并保存配置。BL 负责鉴权、上传、提交、轮询、下载和原始 JSON 落盘。Python 负责本机文件、媒体处理、结果解析与文档生成。

第二阶段处于规划中，将以用户校对稿、文档范例、格式要求、重点说明及确认后的修改反馈为输入，生成个性化会议纪要。“学习”指从这些材料中提取并应用用户认可的偏好；偏好的保存方式与反馈采纳规则在该阶段设计，当前尚未实现。

当前重新导出仍从原始转写 JSON 生成文档，会覆盖同名成品；用户校对修改应另存，作为后续会议纪要阶段的输入。

## 资源与工作目录

```text
frontend/                     # 开发时维护的 Vue / TypeScript 前端
├── App.vue                   # 页面与交互区域
├── components/               # 上传、凭据输入与核对面板
├── useTranscription.ts       # 页面用例编排
├── api.ts / model.ts         # HTTP 与纯状态规则
├── types.ts                  # 前端输入和回执协议
└── preferences.ts / i18n.ts  # 界面偏好与中英文文案

skills/asr-transcription/       # 独立安装的 Skill，运行时只读
├── SKILL.md                   # 触发范围与任务操作
├── agents/openai.yaml         # Codex 展示信息
├── scripts/
│   ├── asr.py                 # CLI 入口
│   ├── requirements.txt       # Python 固定版本与摘要
│   ├── bailian/               # BL npm 依赖锁
│   └── asr_runtime/           # Python 模块与网页
├── references/                # 按需读取的操作、模型、错误说明
├── assets/env.example         # 空 Key 配置模板
└── LICENSE

用户选择的工作目录/
├── .asr-transcription/        # 私有运行文件
│   ├── .env
│   ├── .venv/
│   ├── .tools/bailian/
│   ├── .runtime/
│   └── .state/
└── transcriptions/            # 默认结果保存根
```

`Runtime(workspace, skill_root)` 传递这两种目录的边界：`resource(relative)` 读取 Skill 内的文件，`path(relative)` 定位私有运行目录中的文件，`output_root` 给出默认结果目录，`check_output_path(path)` 检查输出位置。Skill优先复用会话中已约定的工作目录，否则采用当前任务目录；该目录须已存在且位于Skill安装目录之外。私有运行目录与 Skill 目录互不包含。CLI仍显式接收`--workspace`，按该参数定位文件。录音输入由网页选择，不作为工作目录选择或服务启动的前提。

同一 Skill 可以服务不同工作目录。凭据和任务按工作目录分开，Skill 移动不改变既有工作目录里的任务文件。这里的“私有运行目录”表示当前工作区单独使用的存储位置；实际读写仍受 Windows 文件权限和执行工具权限约束。

## Skill结构与Codex元数据

`SKILL.md` 的 name、description 和任务指令构成技能入口，scripts、references 与 assets 按实际用途提供代码、按需资料和模板。`agents/openai.yaml` 是 OpenAI 支持的可选元数据，由 Codex 读取显示名称、简短说明和默认提示词。仓库的 `AGENTS.md` 维护开发规则。依据见[官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills#optional-metadata)。

Python 包内的 `utils/` 集中提供文件、媒体、文档和 CLI 操作，application 编排多步骤用例。安装与诊断进程返回版本或安装输出，BL 执行进程管理凭据、用户登录和识别等待；两者分别保持适合其生命周期的调用函数。

## BL 能力边界

当前只有“录音转写并交付校对文档”这一项完整用户任务，因此由一个 Skill 提供入口，`utils/bailian.py` 集中适配官方 CLI。认证、临时上传、任务提交、轮询、结果下载和原始 JSON 落盘由 BL 完成；Python 读取本机配置、准备媒体、解析结果并生成文档。热词与上下文的本地检查服务于网页反馈，参数序列化服务于 CLI 调用，云端权限由 BL 验证。

只有新增了可独立触发的 BL 用户任务，且确实需要自己的使用指令、输入和交付标准时，才评估建立另一个 Skill；多个已实现用例需要相同进程能力时再提取共享代码。第二阶段的模型、Skill 划分与调用方式按会议纪要和反馈学习的实际需求确定。

## 模块职责

Python 运行模块位于 `skills/asr-transcription/scripts/asr_runtime/`。多步骤用例按入口 → application → utils 组织，单一操作允许入口直接分派。下表中 `frontend/` 路径相对于仓库根目录，其余代码路径相对于 Python 包目录。

| 模块 | 职责 |
| --- | --- |
| `__main__.py` / `web.py` | 分派 CLI 与 HTTP 请求，创建 Runtime，输出回执 |
| `application/bootstrap.py` / `diagnostics.py` | 根据 Skill 的依赖锁准备工作目录环境，检查本机运行条件 |
| `application/session.py` | 管理本次网页上传、保存目录、预览、确认与清理 |
| `application/inputs.py` / `rules.py` | 读取输入事实、应用模型规则；rules 不执行 I/O |
| `application/transcription.py` | 编排一次执行、已知结果与重新导出 |
| `application/delivery.py` | 顺序调用三格式 writer 并汇总交付状态 |
| `utils/environment.py` / `auth.py` | 提供 Runtime、子进程环境、依赖检查及本机凭据读取 |
| `utils/installation.py` | 固定安装工具与来源、比较文件采样速度、持续记录安装进度并回收子进程 |
| `utils/bailian.py` | 映射公开 CLI 参数，启动 BL，转交登录链接并解释脱敏错误 |
| `utils/files.py` / `job_files.py` | 文件身份、原子状态写入、配置发布及任务目录协议 |
| `utils/hotwords.py` / `media.py` | Excel 模板与读取，音频探测与单声道副本 |
| `utils/results.py` / `documents.py` | 官方结果 JSON 的唯一解析边界，三种格式生成与目标替换 |
| `utils/directory_picker.py` / `_directory_dialog.py` | 原生目录窗口子进程、选择、取消与回收 |
| `models.py` | 媒体与转写 dataclass，以及配置、执行、导出的 TypedDict 协议 |
| `utils/i18n.py` | 按当前 HTTP 请求语言查找本机提示，结束后恢复语言上下文 |
| `frontend/App.vue` / `components/` | 页面、Element Plus 控件及上传、Key 输入、核对信息组件 |
| `frontend/useTranscription.ts` / `model.ts` | 页面用例编排与纯状态规则，管理上传、预览、保存及操作可用性 |
| `frontend/api.ts` / `types.ts` | HTTP 传输和端点输入、回执类型 |
| `frontend/preferences.ts` / `i18n.ts` | 界面语言、系统/浅色/深色主题及中英文显示文案 |

有生命周期的 `Session` 和 `DirectoryPicker` 使用类；无状态能力使用模块函数。Runtime 管理资源边界。PreparedCommand 只服务一次 BL 调用，包含私有参数与环境，保留在内存中。

Python 的 TypedDict 描述已有 JSON 字段和允许的状态，数据在运行时保持普通字典；业务规则和外部输入仍由现有解析边界检查。TypeScript 定义表单、页面状态、端点回执和组件接口，开发时通过 `vue-tsc` 核对 Vue 单文件组件及脚本。类型声明与实际验证各自承担明确职责。

## 页面与界面偏好

`serve`持续运行并输出`event=listening`、URL、PID及`browser_request`。`skipped`表示由宿主浏览器工具打开；`requested`表示系统接受打开请求；`failed`表示返回失败或抛出浏览器异常。浏览器失败时仍保持HTTP服务供调用方打开同一URL；启动输出失败时关闭服务器。是否实际显示页面，由浏览器工具状态或用户反馈确认。

有浏览器工具时，Codex使用`serve --no-browser`并打开返回的完整URL；只有系统浏览器可用时才调用默认打开方式。新转写从配置页的文件选择器开始。本机配置页与BL的阿里云授权页是两个阶段：确认配置后再按认证方式和已有凭据决定是否执行login。

`App.vue` 组合 Element Plus 控件及三个视图组件。`useTranscription()` 保存页面用例所需的响应式状态，`model.ts` 计算操作权限、构造配置并处理预览与回执；`ReviewPanel.vue` 从同一表单或已检查快照派生摘要。`ViewEffects` 将焦点、模板下载和 Key 控件读写留在视图侧。

`main.ts` 从启动 URL 取得会话令牌后清理地址栏，并把令牌保留在 `createApi()` 的闭包中。HTTP 请求携带当前界面语言，后端以 `language_scope()` 为每次请求设置语言；公共校验提示和已登记的本机消息按该语言返回，CLI 默认使用中文。语音识别的语言参数仍由转写设置决定。

`usePreferences()` 使用浏览器语言作为默认界面语言、系统配色作为默认主题。页面通过 Element Plus 的 ConfigProvider 和 `html.dark` 类同步组件语言与配色；localStorage 中的 `asr-ui-preferences` 只保存语言、主题。保存作用域是当前网页来源，随机端口变化时可能使用新的默认偏好。

切换界面语言保留音频引用与输入，并使已检查预览失效；用户重新检查后取得当前语言的提示。上传、凭据处理、目录选择、检查和保存期间按状态限制语言切换，主题选择独立工作。配置、音频、Key 和增强正文不写入浏览器持久存储。

实现依据：[Vue 的 TypeScript 支持](https://vuejs.org/guide/typescript/overview.html)、[Element Plus 国际化](https://element-plus.org/en-US/guide/i18n.html)及[深色模式](https://element-plus.org/en-US/guide/dark-mode.html)。

## 输入与确认

| 阶段 | 检查与读取 | 产出 |
| --- | --- | --- |
| 添加文件 | 文件用途、文件名、大小和接收字节数 | 会话副本与 `upload_id` |
| 预览 | 音频探测、SHA 基线、Excel 解析、选项及上下文规则、保存目录 | 内存 draft 与 `validation_id` |
| 确认 | 复用 draft，核对音频 size/mtime | `config.json`、`config.sha256` 与 `job_id` |
| 执行 | 配置协议与摘要、音频实际大小与 SHA、执行时凭据 | 执行记录与原始 JSON |
| 重导 | 配置、已保存成功记录、原始 JSON 摘要 | 固定任务目录的三种成品 |

热词在预览时转为即时 `vocabulary` 保存到配置，执行不再依赖原 Excel。上下文与热词可同时使用。API Key 独立于任务快照：检查时按需保存已修改的 Key，正式执行读取当时的 `.env`；配置确认不绑定 Key 值或文件时间。

配置写入临时文件和相同内容的 SHA 后发布；摘要用于发现已确认内容发生变化。网页保存不授权上传，配置中 `execution_authorized=false`。Codex 从同一 `serve` 进程的 `event=configured` 回执取得编号，根据本次上传授权执行。

## 凭据与参数

bootstrap 从 Skill 的 `assets/env.example` 复制空模板到私有运行目录 `.env`，保留已存在的文件。网页允许用户填写或修改 `DASHSCOPE_API_KEY`，在“检查并预览”时保存到该固定文件。Key 模式复用非空与内部空白检查，执行时读取并注入 BL 环境。控制台模式复用工作目录内的 BL 配置，首次或明确重新登录时才调用 `login`。

Python 安装、虚拟环境核对与依赖加载检查使用 `-I` 隔离模式，从指定虚拟环境加载包，避免工作目录中的同名 Python 文件参与安装或检查。执行命令所需的路径来自 Runtime，用户选定的保存目录只用于输出。

网页通过受保护的 `POST /api/api-key` 读取已有 Key，缺失时返回空值；通过 `POST /api/save-api-key` 保存输入。`KeyDisplay.vue` 使用局部状态绑定密码输入框，与可提交表单分开。检查并预览先完成本机必填检查，再按需保存凭据，最后请求配置预览；凭据保存成功与任务配置确认是独立结果。保存 Key 的短暂阶段使用 `auth.status=saving`，暂停认证方式与 Key 编辑，等待原请求结束后继续。切换认证方式、配置保存成功或组件关闭时清空控件。Key 不进入任务配置、浏览器持久存储、日志或聊天。`console-status` 报告本机凭据存在性，不代表在线权限验证。

`recognition_arguments` 集中映射选项。热词用 JSON 序列化形成单个参数值，上下文使用单个 `--context=<原文>`，避免以 `--` 开头的文本被 BL 误识别为命令选项。`prepare_command` 构造一次 argv、核对一次 Windows 命令长度并读取执行 Key；进程使用 `shell=False`。来源与限制见 [model.md](../skills/asr-transcription/references/model.md)。

## 生命周期与状态

Session 短锁保护上传登记与发布，文件字节接收在锁外完成，同类上传不能并发。目录窗口在独立子进程中运行，取消使用选择器自己的信号，没有用户选择总时限。正常服务退出清理未确认副本和 Excel 副本，保留已确认音频。关闭浏览器不等于关闭服务。

前端用输入 revision 作废迟到预览。确认返回明确 4xx 后恢复编辑；保存结果未知时暂停重复保存。默认输出目录由 Runtime 提供，自选目录只能经本机会话原生窗口批准。选择目录时在试写前、预览时在接受目录前调用 `check_output_path()`；创建 JSON 或文档目录前再次通过同一方法检查，确保实际写入目标位于 Skill 之外。

开启发言人区分且多声道时，用已确认 AudioInfo 调用 PyAV 生成单声道 FLAC。保留采样率，核对源文件变化及新副本的声道、采样率、时长与实际上传大小。转换失败停止，不自动更换编码或切片。

任务独占创建 `execution` 目录后，取得一次执行占用。本地准备失败、识别失败或结果未知均保留占用；重复调用返回既有状态。这限制本地尝试次数，不是云端恰好一次保证。提交超时或本机进程结束均不能证明云端未受理或已取消。

| 状态或字段 | 含义 |
| --- | --- |
| `CONFIGURED` | 确认配置已保存，尚未执行 |
| `PREPARING` | 取得执行占用，正在本机准备 |
| `RUNNING` | 已保存启动前的保守记录，云端结果按未知处理 |
| `STOPPED` | 当次执行停止，按 `phase` 和 `cloud_outcome` 解释 |
| `JSON_READY` | 原始 JSON 已保存并通过结构检查 |
| `documents_ready=true` | 当次导出记录为 COMPLETE，三格式均完成 |
| `OUTCOME_UNKNOWN` | 本机记录无法确定当前结果 |
| `record_error` | 执行记录保存失败，磁盘可能滞后于回执 |

记录保存失败时保留当次已知事实；成功 JSON 记录写入失败则在导出前返回，已有 JSON 保留。当前没有记录恢复或补签摘要入口。`job-status` 只读本机执行与交付记录，不检查进程存活、不查询云端、不重新核验成品。

## 文档交付

results 解析原始 JSON 后，三个 writer 共享 Transcript。delivery 顺序尝试 Excel、Word、Markdown 各一次，单格式失败后仍尝试其余格式。各格式先写 partial 文件，成功后替换目标；失败保留该格式原目标。Excel、Word 在替换前回读，Markdown 编码保真由测试验证。

重新导出核对确认配置、磁盘 JSON_READY 和原始 JSON 摘要，复用相同 writer 与目标，不读取音频、原 Excel 或 Key，不调用 BL。每个任务只有一份 `delivery/status.json`，记录 EXPORTING、COMPLETE、PARTIAL 或 FAILED。手工校对的文档需另存，同一任务等待当前导出结束后再执行下一次。

- 三格式标题：`源文件名（不含扩展名） 录音转写`，不另列“音频”信息行。
- Excel：等线、黑白无填充色；标题和任务说明左对齐，第三行直接表头；表头及非正文列居中，正文左对齐且自动换行；保留筛选、冻结，真实存储限制不截断。
- Word：等线；标题 20 磅，正文、元信息、时间标签、页码 10 磅；普通文字和复杂文字采用相同字号与粗体设置；正文左对齐，时间标签不用圆点，标签随下一段。

| 数据 | 位置 |
| --- | --- |
| Key / BL 配置 | `<workspace>/.asr-transcription/.env` / `<workspace>/.asr-transcription/.state/bailian/` |
| 暂存输入 | 私有运行目录下 `.state/web-uploads/<session_id>/` |
| 配置及摘要 | 私有运行目录下 `.state/jobs/<job_id>/config.json`、`config.sha256` |
| 执行 / 导出记录 | 同一任务的 `execution/status.json` / `delivery/status.json` |
| 原始 JSON | `<json_root>/<job_id>/json/transcription.json` |
| 成品 | `<document_root>/<job_id>/documents/transcription.{xlsx,docx,md}` |

JSON 与文档保存根默认均为 `<workspace>/transcriptions/`，可分别通过原生窗口选择。结果原文、时间戳、结构检查与识别质量、Office 视觉效果分别验收。

## 构建与维护

### 运行依赖准备

`bootstrap`仅在业务依赖缺失或版本不匹配时准备下载。`rank_python_indexes()`并行采样PyPI与阿里云镜像上同一个锁定pip wheel的前缀，按收到字节与耗时排序；这不是全程速度保证。安装工具pip 26.2.1的文件路径与摘要直接维护在`utils/installation.py`，业务依赖仍以`requirements.txt`为来源。

安装器先通过现有pip下载并安装锁定的新pip，再由新版pip下载业务依赖。每阶段按排序后的两个来源各启动至多一次下载；连接重试与中断恢复使用pip公开选项。已下载的完整wheel保存在私有`.runtime/wheels`，全部下载成功后才用`--no-index`进行本机安装。SHA校验由pip承担；不自行拼接断点、不修改摘要，也不在本机安装失败后重复切源。

`run_installer()`为pip/npm长进程持续转发stderr进度并写日志，stdout保留CLI最终JSON；安装没有总耗时限制。`run_process()`继续服务版本、平台等短检查。两者复用同一个隔离子进程环境；安装进程中断时回收自身子进程。BL的npm安装保持单次尝试，云端转写策略保持不变。

### 前端与发行包

前端由 Vite 在开发阶段构建到 Skill 的 `scripts/asr_runtime/static/`，固定输出 `index.html`、`app.js` 和 `app.css`，并提供 `favicon.svg` 与 `THIRD_PARTY_LICENSES.txt`。Python 本机服务直接提供这些产物，用户安装和使用时无需安装前端构建依赖。源码在 `frontend/`，锁定的 Vue、Element Plus、Vite、TypeScript 及检查工具在仓库根 `package.json`、`package-lock.json`；构建行为见 [Vite 官方说明](https://vite.dev/guide/build.html)。

开发构建需要 Node.js `^20.19.0 || >=22.12.0`，与 Skill 运行时 BL 所需的 Node.js 18.17+ 分别管理。前端开发命令在仓库根执行：

```powershell
npm ci
npm run check:web
npm run test:web
npm run build:web
npm run test:browser
```

`build:web` 先执行类型检查再构建。`test:browser` 使用开发依赖 Playwright、本机 Edge 和真实 Python 本机服务；测试只使用合成数据，完成后清理自己的工作目录。Python 静态检查工具与配置也仅用于开发，具体命令见 [ACCEPTANCE](ACCEPTANCE.md)。

`scripts/build_zip.py` 以固定逐文件清单构建 `asr-transcription.zip`，归档根直接为 Skill 内容。包只含 SKILL、展示 metadata、运行代码、前端构建资源、运行依赖锁、参考说明、空配置模板和 LICENSE。仓库 README、AGENTS、开发文档、UML、测试、开发探针、TypeScript/Vue 源码、构建工具、node_modules、运行环境和用户数据都不进入包。

使用仓库中 `skills/asr-transcription/scripts/asr.py` 的绝对路径和明确工作目录准备运行环境；开发测试命令见 [ACCEPTANCE](ACCEPTANCE.md)。开发探针在仓库 `scripts/probe_bl.py`，固定虚构 URL，不进入 Skill。修改模块时沿当前职责定位消费者，同时维护清单、相称测试与相关 UML，实际结果再写验证记录。

## 版本与分支

开发阶段的仓库默认分支为 `dev`，承载日常开发、修复和开发预览，当前项目版本保持 `0.1.0`。只有通过验收并正式发布到 `master` 时才变更项目版本，同时更新根 `package.json`、`package-lock.json` 中的项目版本、Git 标签和发布说明，正式标签指向对应的 `master` 提交。

开发期间经用户授权可更新现有 `v0.1.0` 开发预览及附件，沿用当前版本。向 `dev` 推送或更新预览不触发 `master` 合并。第三方依赖版本由各自锁文件维护，与项目版本分别管理。
