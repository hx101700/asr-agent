# 产品与代码审查

更新：2026-10-02。对象为dev分支的现行实现。执行回执、事实解释及异常定位已修正，记录恢复等产品能力仍未提供。源码版本以Git记录为准，当前包摘要见[STATUS](STATUS.md)，剩余问题见[ISSUES](ISSUES.md)。

## 结论与证据范围

当前项目已有适合学习的职责边界：Codex负责理解意图和调用工具，本机网页负责交互，Python负责确定性用例，BL负责云端流程。已修正的执行问题说明了失败事实的重要性；剩余不足在记录恢复、用户找回能力、发行识别和真实使用验证。继续增加架构层或删除所有检查，都不能解决这些不足。

审查覆盖入口、用例、工具、前端状态与传输、安装/打包、Skill和开发/使用文档。执行状态故障注入已转为回归测试。最终复核完成了全量回归、新空目录联网安装、发行环境中的本机合约和Edge网页检查；准确范围见[ACCEPTANCE](ACCEPTANCE.md)。真实登录、云端识别、原生窗口可见性、完整键盘可用性及Office逐页视觉仍需各自验收。

函数说明统一为正面描述动作和结果的简短中文句子，调用者需要的返回约定随简介保留，具体实现原因放在代码旁。注释修改与执行逻辑修改分别核对。文件数量、行数和测试数量都不作为复杂度或产品质量评分；用户体验与识别准确率仍需要各自的证据。

2026-10-02发行一致性复核已同步AGENTS、Skill与使用说明中的记录失败、JSON目标路径及重导前提，删除login后的重复状态查询示例，并清理两个闲置字段。随后在增强文本专项验证中复现了BL对--前缀上下文的解析问题，已改为原生--context=值；字符保真及检查范围见[ACCEPTANCE](ACCEPTANCE.md)。

## 从用户目标向下审查

| 用户此刻要解决的问题 | 当前入口与责任 | 评价及不足 |
| --- | --- | --- |
| 拿到ZIP后开始使用 | release/README、项目Skill、bootstrap | 已明确本机运行时、Tk组件、等待方式和BL冲突目录边界；安装期间仍缺少阶段反馈 |
| 知道当前环境是否可用 | diagnostics.doctor | 能检查Python、Node、依赖和BL；缺少Tk组件诊断，且诊断成功不能证明GUI在当前桌面可见 |
| 选择账号、音频和增强内容 | static/app、model、view；Session | 单文件、热词/上下文并用、Key显示与执行分开，符合当前需求；实际键盘、焦点、窗口交互仍需验收 |
| 核对并保存本次设置 | Session.validate/confirm、job_files.publish_config | 确认快照与上传授权分开，旧预览失效有实际意义；未保存草稿不持久化是已说明的取舍 |
| 让Codex开始识别 | Skill、CLI、transcription.transcribe | 同一进程回执能明确连接网页与命令；丢失job_id后没有受支持的查找入口 |
| 等待且理解失败 | tools.bailian、transcription、error_catalog | 没有重复实现上传/轮询，官方错误有依据；现已分开报告执行事实、错误阶段与记录写入失败 |
| 取得可阅读的文件 | results、delivery、documents | JSON解析与各格式写入分开；单格式失败保留其它成果，逻辑合理；结构回读不等于阅读效果好 |
| 以后重导或定位问题 | export、job-status、HELP | 重导不需Key/音频/词表且不再识别；有效JSON与状态记录分离时没有普通用户可用的恢复路径 |
| 向维护者报告故障 | doctor、状态回执、发行ZIP | 异常已有阶段/类型；仍缺少项目发行身份，维护者难以把报告对应到源码 |

用户要完成的核心任务是“把一份录音转换成可信、可找到、可使用的文本”。因此产品完成标准需要同时考虑首次使用、失败后的下一步和日后找回，不应只统计成功路径的文件数量。

## 已修正的执行问题与剩余边界

以下问题曾由故障注入或异常分支确认，随后按现有业务边界修正。故障注入证明代码路径的问题，不证明用户历史运行发生过这些故障。没有据此增加自动恢复系统、重试或新架构层。

### R1：记录写入失败仍须保留已经取得的结果

位置：[transcription.py](../src/asr_agent/application/transcription.py)的_save_status、transcribe及export_job。

原问题是JSON已在内存形成JSON_READY，随后状态写入失败却直接上抛，丢失当次成功回执。现在_save_status只尝试写入一次，I/O失败或中断写入独立record_error；transcribe保留JSON_READY/result_received、路径和摘要，明确本次未进入文档导出。停止状态无法保存时也保留原始错误。

回归测试以合成音频、真实本地配置和JSON、BL进程替身验证：JSON_READY写入失败仍得到结果路径与对应摘要；BL只调用一次，状态不重写，未触发导出。还移除了JSON成功解析后的冗余is_file探测，避免诊断检查的异常覆盖成功事实。

剩余边界：磁盘仍可能为RUNNING，export继续要求已保存的JSON_READY及摘要。本轮没有增加记录恢复入口；应保留本次回执及JSON，不能自动补摘要、删除占用或再次上传。

学习点：单文件原子写入可以防止半份记录，但不能使“外部进程完成”和“本地成功记录”成为同一个原子操作。两件事之间的失败必须有准确的解释。

### R2：BL尚未启动时必须明确未上传

位置：[transcription.py](../src/asr_agent/application/transcription.py)的transcribe。

原问题是RUNNING写入失败后，通用异常分支留下unknown，实际BL调用为0。现在PREPARING或RUNNING写入失败立即返回STOPPED/not_started，保留record_error，不再尝试写状态或启动BL。两处失败点均已有回归测试。

RUNNING仍在启动前保守落盘，以处理启动后进程崩溃的未知范围；当前调用与后续读取旧记录的证据不同。这里通过明确的顺序和返回值解决，没有引入状态机框架。

### R3：异常说明必须能定位阶段和原因类别

位置：[transcription.py](../src/asr_agent/application/transcription.py)的transcribe；解释原则与[delivery.py](../src/asr_agent/application/delivery.py)保持一致。

原分支把程序异常、中断和普通文件错误都提示为检查配置/权限/空间。现在本地执行异常保留固定phase与error_type，区分已知输入、I/O、中断和未知程序错误；BL错误保留已有说明并增加phase。未知异常正文不输出。

对应测试核对了未启动/结果检查阶段、具体解释与私有正文不进入回执。阶段定义见[ERRORS](ERRORS.md)，没有新建通用异常框架。

## 值得补齐的产品能力

这些是建议，不是现有功能已实现的声明，也不全部属于代码bug。

| 能力 | 代码证据与用户影响 | 最小可交付改进及验证 |
| --- | --- | --- |
| 安装可观察性 | [bootstrap.py](../src/asr_agent/application/bootstrap.py)中pip/npm没有总超时；[environment.py](../src/asr_agent/tools/environment.py)收集输出，失败返回后才写日志。慢网络期间没有可见阶段 | 输出“检查环境/安装Python依赖/安装BL/完成”事件；安装输出直接进入项目本地日志，不向聊天回显原始第三方内容。验证中断时仍有已产生的诊断，不增加自动重试或虚构百分比 |
| 失败安装的人工修复 | bootstrap拒绝覆盖非空或不完整BL目录，HELP只要求先检查 | 给出准确的失败位置、保留范围与用户显式修复步骤；不得擅自删除凭据、原始文件或正常安装 |
| 任务找回 | [__main__.py](../src/asr_agent/__main__.py)仅接受确切job_id，Skill禁止猜最新，符合安全边界；目前没有列出候选的命令 | 增加只读jobs入口，列编号、时间、源文件名和已有本地状态，由用户选择。文件名也可能敏感，按需本机显示；不输出正文/增强内容，不加数据库，不查云端 |
| 发行身份 | [build_zip.py](../scripts/build_zip.py)返回路径和文件表；唯一项目版本0.1.0在不发布的pyproject中，doctor不报告项目版本 | 一处维护项目版本，doctor及构建回执可识别；需要区分同版本未提交构建时，再报告发行内容摘要。HEAD单独不能标识当前工作区 |
| Tk诊断 | HELP要求tkinter，但doctor未检查；缺少组件要等点击目录按钮才发现 | 用户主动doctor时报告组件可用性；窗口是否可见仍做实际交互验证，不把自检加到每次转写前 |
| 用户与Agent验收 | 前端单元测试覆盖状态；发行环境中已检查Edge实际DOM、文件添加、回执、刷新及响应布局；完整独立对话未完成 | 继续检查原生目录选择、键盘操作、实际Codex编排和云端效果；记录行为而不仅记录文件存在 |

识别质量还需要与流程质量分开。现有实现能检查原JSON到成品的内容保真，不能证明识别文本、说话人划分正确。要比较热词/上下文效果，需少量已授权并有人工参考稿的固定样本；对同一输入比较错误及业务术语识别，先约定评估口径，不用“调用成功”证明精度提高。

## 设计模式与风格是否合理

当前后端是轻量的用例分层，以函数组织多步骤流程；前端是MVP式职责分离。可以准确地按以下实现理解，无需给每个模块附会一种设计模式：

| 实现 | 合理性 | 应保持的边界 |
| --- | --- | --- |
| CLI/HTTP入口分派 | 入口表达协议，便于定位请求去向 | 多步骤业务放application；单一登录/状态/模板操作直接调用工具即可 |
| session / transcription / delivery | 分别拥有本机配置、外部执行、本地交付生命周期 | 不把三者合为巨型服务，也不逐行拆出只转发一次的类 |
| tools.bailian及媒体/文档工具 | 将不稳定的外部格式与进程能力集中在少数位置 | BL公开能力直接调用，JSON只解析一次；不用SDK/HTTP再建第二套云端流程 |
| rules与冻结数据类 | 规则不执行I/O，共享数据清楚 | 只有稳定共享概念进入models；不要把所有dict马上改成模型框架 |
| 前端model / view / app / api | 状态、DOM、事件编排、HTTP传输分开 | 普通表单留DOM，Key不入Model；权限不能由disabled反推 |
| 三writer的函数列表 | 少量格式选择直观，新增格式位置明确 | 无需工厂、插件注册器或writer继承层 |

风格总体统一：无状态能力以模块函数实现；Session、DirectoryPicker等真实生命周期用类；每个命名函数/方法有简短职责说明，关键外部约束有中文注释。本轮统一了异常解释与状态事实，见R1–R3。

分层不是严格的隔离架构：入口已有单一工具直接调用，job_files也认识项目配置和状态协议。这些实现有实际用途。DEVELOPMENT已按代码修正文案，避免以后为了满足图上的每一层而添加转发代码。[结构测试](../tests/test_architecture.py)只能证明它检查的导入方向和旧模块不存在，不能证明职责全部合理。

## 冗余与必要复杂度

在本次审查的运行路径中，没有发现第二套云端上传、轮询或结果下载实现，也没有理由增加BaseTool、Repository、DI容器、队列、数据库或额外LLM。现有单文件范围不足以支持这些成本。

以下重复出现的操作有不同消费者或时点，不应直接按名称删除：

- 预览读媒体事实、确认核对size/mtime、执行比对音频SHA：分别服务用户核对、快速发现变化和实际上传一致性；原始媒体只探测一次，新FLAC必须单独检查。
- 前端即时反馈与后端输入规则：前者改善交互，后者才是执行边界；数值应由后端description提供，避免双份常量漂移。
- Session短锁与目录选择器取消机制：解决已有并发请求与窗口生命周期；不是为了未来多用户系统。
- 执行状态与导出状态：防止“文档失败”被解释为“需要重新识别”；各轮导出保留自己的结果。
- 开发AGENTS与发行AGENTS：面对不同使用者，保留发行模板有价值；修改用户契约时应同时检查Skill/HELP/发行模板，避免漂移。

存在三个应明确代价的取舍：一次占用覆盖未启动BL的本地准备失败；未保存草稿不跨服务恢复；保存响应未知时冻结。它们符合现行要求，可暂时保留。若以后改善恢复体验，应先定义哪些事实可信、由谁显式操作，再改变行为，不因不便就绕过占用或自动重试。

## 公开工程经验如何用于本项目

以下是公开资料与本项目的对应建议，不是对这些公司全部内部流程的推断，也不是厂商认证。

| 官方资料 | 公开原则 | 本项目的应用 |
| --- | --- | --- |
| [Google代码审查关注点](https://google.github.io/eng-practices/review/reviewer/looking-for.html) | 审查设计、用户影响、可理解性及有效测试，避免为猜测需求泛化 | 每个新模块都说明当前消费者；修实际失败语义；UI必须有使用证据 |
| [Google小规模变更](https://google.github.io/eng-practices/review/developer/small-cls.html) | 变更应自包含、可审查，重构与行为变化尽量分开，包含相关测试 | 后续安装反馈、发行身份分别提交可核查变更，避免和目录重排混在一起 |
| [Meta Fix Fast](https://engineering.fb.com/2021/02/17/developer-tools/fix-fast/) | 尽早得到准确、可行动的故障信号，减少噪声及定位成本 | 固定阶段、异常类型、发行身份帮助定位；无需复制大型检测平台 |
| [OpenAI Skill评估](https://developers.openai.com/blog/eval-skills) | 分别观察产出、操作过程、风格和效率，使用少量必要检查 | 验证Skill触发、同进程回执、没有重复识别及正确解释失败；Python测试不能覆盖这些行为 |
| [OpenAI Skill构建](https://learn.chatgpt.com/docs/build-skills) | 描述应清楚限定触发范围，按需加载正文；仓库级技能有明确发现位置 | 现有项目内技能范围合理；保留短入口与按需HELP，不把全部开发文档塞进Skill |

应用这些经验不要求复杂基础设施。当前仓库未发现.github、.gitlab-ci.yml、azure-pipelines.yml或Jenkinsfile；不据此断言项目外没有CI。若建立自动检查，先把现有Python、Node和打包边界检查在Windows环境中跑起来，并与具体源码/包对应，真实云端和桌面验收仍单独执行。

## 建议的改进顺序与通过标准

| 顺序 | 一次变更只解决什么 | 可核查的完成标准 |
| --- | --- | --- |
| 已完成 | 修执行事实、结果回执与错误解释 | 对应故障测试通过；状态不自动重写，BL不重提，敏感正文不输出；R1的后续记录恢复仍未提供 |
| 2 | 补安装阶段与可用诊断 | 等待时可知道当前步骤；中断前输出保留到本地；失败修复说明具体；不自动重装/换源 |
| 3 | 建立发行身份 | 源码、doctor、构建回执及测试记录能对应同一份包；凭据/开发文档仍不入包 |
| 4 | 补只读任务找回，单独决定本地记录恢复 | 丢失回执可显式选择已有编号；不按最新猜任务，不重新上传；缺摘要不能静默补签 |
| 5 | 完成当前ZIP的真实用户旅程验证 | 新目录、新对话安装与使用；Agent按约定行动，失败后说明准确；三格式内容与实际阅读效果分别验证 |

建议只在每项改动的失败机制和验收条件明确后写代码，不先建立一套为未来问题准备的框架。Git操作与发行交付情况查看当前STATUS及实际Git元数据。

## 作为学习样本的阅读路径

1. 从[Skill](../.agents/skills/asr-agent/SKILL.md)和[HELP](HELP.md)读出谁授权、谁上传、谁解释结果，对照[UML设计视图](UML.md)追踪调用关系。
2. 读[CLI](../src/asr_agent/__main__.py)、[web](../src/asr_agent/web.py)和[Session](../src/asr_agent/application/session.py)，追踪一次确认；说明upload_id、预览ID与job_id为何不同。
3. 读[inputs](../src/asr_agent/application/inputs.py)、[rules](../src/asr_agent/application/rules.py)、[models](../src/asr_agent/models.py)，区分读取事实、判断规则和共享数据。
4. 读[transcription](../src/asr_agent/application/transcription.py)与[bailian](../src/asr_agent/tools/bailian.py)，逐步标出有副作用的位置，回答“此处失败，哪些事情已经发生”。用R1/R2作故障练习。
5. 读[results](../src/asr_agent/tools/results.py)、[delivery](../src/asr_agent/application/delivery.py)与[documents](../src/asr_agent/tools/documents.py)，解释识别成功、内容保真、三格式交付和识别质量为何是不同判断。
6. 读测试与[build_zip](../scripts/build_zip.py)，为一个具体修改选最小有效测试，并确认源码、文档和发行包同时一致。

例如调整一个已支持参数时，应能明确指出rules的规则、Session的确认快照、bailian的参数映射及前端反馈是否需要变化；只有实际变化处才改代码。能追踪这条责任链，比背诵设计模式名称更有助于维护。

## 本轮验证与交付边界

- 已执行：执行故障的针对性回归、命名函数说明检查、最终全量回归、空目录安装和发行环境检查。项目只在ACCEPTANCE集中维护最新测试范围及结果，避免多处计数漂移。
- 排除的怀疑：HTTP关闭等待目录窗口导致必然卡住。实际ThreadingHTTPServer.daemon_threads为True，探针中server_close未被等待请求阻塞，取消事件已发出；不登记为bug，也未更改此代码。
- 发行清单仍为44个文件，doc只含HELP、ERRORS、REFERENCES。本文及其它开发文档不发布；当前包核对情况见[STATUS](STATUS.md)。
- 未执行：新对话中的完整Codex使用、原生目录窗口交互、Office逐页视觉与真实云端识别；不能据本轮结论宣称这些已通过。
- 当前实现与最近修改范围以[STATUS](STATUS.md)为准，验证证据以[ACCEPTANCE](ACCEPTANCE.md)为准。
