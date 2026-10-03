# 代码审查

日期：2026-10-04。本轮重新从入口到具体实现阅读全文，并分别检查前端交互、后端记录和文件操作、安装更新、Skill指令及UML。用独立复现确认问题后修改，再运行回归；没有把已有检测脚本的通过当作源码审查。实际结果见[ACCEPTANCE](ACCEPTANCE.md)，历史修正通过Git追溯。

## 阅读覆盖

Python 代码路径相对于 `skills/asr-transcription/`；前端与开发配置路径相对于仓库根。阅读范围按模块职责记录，避免把文件数量当作审查充分性的依据。

| 范围 | 完整阅读的文件 |
| --- | --- |
| 入口与共享定义 | scripts/asr.py、update_skill.py；scripts/asr_runtime下的__init__.py、__main__.py、models.py、error_catalog.json |
| 应用用例 | application下的__init__、bootstrap、diagnostics、inputs、rules、session、transcription、delivery |
| 本机能力 | utils下的__init__、environment、installation、auth、bailian、files、job_files、results、media、hotwords、documents、directory_picker、_directory_dialog、i18n |
| 网页 | web.py；frontend下的App.vue、main.ts、useTranscription.ts、model.ts、api.ts、types.ts、preferences.ts、i18n.ts、style.css、index.html，以及UploadField、KeyDisplay、ReviewPanel、HotwordEditor组件 |
| 技能与依赖 | SKILL.md、agents/openai.yaml、assets/env.example、references全部；scripts/requirements.txt、bailian/package.json和package-lock.json全部锁项 |
| 开发与交付 | scripts/build_zip.py、probe_bl.py、console-browser.cts及其构建产物；前端package/lock、vite/tsconfig配置和Python静态检查配置；README/AGENTS双语、doc文档、全部11份UML源稿与图、Release说明；相关运行、权限、媒体、文档、HTTP、更新、前端和打包测试 |

第三方BL及Python依赖按锁定版本使用。本审查核对其公开接口、安装边界和实际调用，不把对项目源码的审查称为第三方全部代码审计。

## 本次发现与处理

| 位置 | 问题与处理 |
| --- | --- |
| `documents.publish_document` / `files.write_json_atomic` | 固定临时文件名会让同时导出或写记录的两个调用互相覆盖，出现文件已生成但回执失败。改用同目录的独立临时文件，仍替换固定目标并清理自身临时文件；没有增加导出锁或队列 |
| `Session.description` / `useTranscription.restoreForm` | 撤回已完成但HTTP响应中断后，刷新会丢失恢复入口。现有会话缓存通过GET返回，页面启动和点击修改共用恢复函数；不重复撤回，也不持久化未保存编辑 |
| `App.vue` / `i18n.ts` | 多行上下文错误在窄窗口与提示文字重叠；保存页还会在转写开始后静态声称音频未上传。使用Element Plus原生inline-message布局，保存页改为引导到Codex查看进度 |
| `HotwordEditor.vue` | 删除第二页的行会因数组变化退回第一页。删除无条件重置的监听，只在页数缩小时限制当前页；校验失败仍主动定位错误行 |
| `update_skill.update_skill` | 两次目录改名之间的KeyboardInterrupt未进入旧回滚分支，可能留下空安装位置。统一异常和中断恢复边界，仅安装位置空缺时恢复旧副本；已接管或恢复受阻时保留原副本并说明路径 |
| 更新器依赖比较 | any生成器在Python锁变化时提前返回，漏读缺少的BL锁。先完整读取两种依赖锁，再归并变化结果；缺失时在替换前报错 |
| 旧接口与无调用者字段 | 音频登记仍带通用kind、上传查找仍允许热词、错误字段仍使用hotwords_upload_id；前端还保留全局行级错误列表及无消费者的返回字段。改为uploaded_audio和hotword_rows，删除这些旧分支与重复展示 |
| 文档与UML | 纠正关闭浏览器等同结束服务、保存回执等同实时状态、重复调用无条件返回旧状态、浏览器测试只能用合成数据，以及更新检查保证任意ZIP完整可用等不准确说明；同步受影响的四张图 |

改动沿用既有会话、执行占用、原子文件替换和Element Plus组件。没有新增依赖、云端调用层、后台轮询、任务状态或兼容分支。旧热词接口的删除由实际消费者范围确定；历史任务保留真实模型标签仍是必要的数据含义。

标准发行ZIP由固定清单构建并逐文件核对。更新器只核对名称、入口、路径、CRC及依赖锁；将标准包重新封装并删除其它运行模块时，更新器可能接受但安装后无法运行。该范围明确为不支持的输入，没有为每个模块追加一次性检查或另建包验证框架。

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

本轮按本机skill-creator指导核对指令与实现，并读取当前[OpenAI Skill文档](https://learn.chatgpt.com/docs/build-skills)及[脚本使用建议](https://developers.openai.com/plugins/build/skills)。当前结构包含必需的SKILL.md及name/description，scripts、references、assets按用途组织；agents/openai.yaml是可选展示元数据，隐式调用保持默认开启。

格式符合要求与分发方式分别判断：当前官方推荐用[Plugin](https://developers.openai.com/plugins/build/plugins)分发可复用Skill。Codex自动发现本地Skill变化不等于从远端自动下载新版，也不代表运行进程热更新。本机官方skill-installer的`_copy_skill`在目标存在时拒绝安装，没有覆盖更新参数。项目的update_skill.py服务于用户明确要求的ZIP更新和活动任务保护，是本项目工具而非OpenAI标准机制；本轮保持既定ZIP范围，未引入Plugin或另一套包管理。

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
