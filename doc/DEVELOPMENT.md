# 开发说明

本文说明当前模块职责、数据协议和维护约束。使用方法见[使用指南](HELP.md)，调用关系见[UML 设计视图](UML.md)，验证范围见[验收记录](ACCEPTANCE.md)。

## 业务边界

asr-agent 将单个本地录音转换为原始 JSON、Excel、Word 和 Markdown。模型固定为 `qwen-audio-3.0-asr-flash-filetrans`，地域固定为北京，音频通过 BL 的临时 OSS 能力上传。

网页负责接收本机文件、检查输入和保存配置。Codex 取得配置回执后，根据用户的上传授权调用独立转写命令。BL 负责鉴权、上传、提交、轮询、下载和原始 JSON 落盘；Python 负责本机媒体处理、结果解析和文档导出。

热词和上下文可以同时启用。热词使用随请求发送的即时 `vocabulary`。开启发言人区分时，多声道录音先生成单声道 FLAC 副本；原文件保留。

## 代码结构

多步骤用例按“入口 → application → tools”组织。登录、凭据状态和模板生成等单一工具操作由入口直接分派。`models.py` 只保存共享不可变数据。

```text
src/asr_agent/
├── __main__.py、web.py        # CLI 与 HTTP 入口
├── models.py                 # AudioInfo、Sentence、Transcript、HotwordRow
├── application/
│   ├── bootstrap.py、diagnostics.py
│   ├── session.py
│   ├── inputs.py、rules.py
│   └── transcription.py、delivery.py
├── tools/
│   ├── environment.py、auth.py、bailian.py
│   ├── files.py、job_files.py、hotwords.py
│   ├── media.py、results.py、documents.py
│   └── directory_picker.py、_directory_dialog.py
├── static/                   # model、view、app、api 及页面样式
└── error_catalog.json
```

| 模块 | 职责 |
| --- | --- |
| [__main__.py](../src/asr_agent/__main__.py) / [web.py](../src/asr_agent/web.py) | 分派命令或 HTTP 请求，转换输入与回执；网页确认后向同一 `serve` 进程输出回执 |
| [bootstrap.py](../src/asr_agent/application/bootstrap.py) / [diagnostics.py](../src/asr_agent/application/diagnostics.py) | 安排项目依赖安装与复用，提供环境诊断和公开 CLI 合约探针 |
| [session.py](../src/asr_agent/application/session.py) | 管理上传登记、目录选择、预览、确认和会话清理 |
| [inputs.py](../src/asr_agent/application/inputs.py) | 读取文件事实并应用规则，形成预览数据与字段错误 |
| [rules.py](../src/asr_agent/application/rules.py) | 表达固定模型的输入规则、选项规则和热词词典规则 |
| [transcription.py](../src/asr_agent/application/transcription.py) | 核对授权，管理一次执行与状态转移，编排媒体准备、BL 调用和本地导出 |
| [delivery.py](../src/asr_agent/application/delivery.py) | 向任务的固定目录导出三种文档，汇总完整或部分交付结果 |
| [environment.py](../src/asr_agent/tools/environment.py) / [auth.py](../src/asr_agent/tools/auth.py) | 管理项目路径、子进程环境、依赖事实及 `.env` 凭据读取 |
| [bailian.py](../src/asr_agent/tools/bailian.py) | 映射公开 CLI 参数，执行 BL，转交登录链接并解释脱敏错误 |
| [files.py](../src/asr_agent/tools/files.py) / [job_files.py](../src/asr_agent/tools/job_files.py) | 提供文件身份、原子状态写入、配置发布、任务占用与输出路径协议 |
| [hotwords.py](../src/asr_agent/tools/hotwords.py) / [media.py](../src/asr_agent/tools/media.py) | 读取 Excel、生成模板，以及探测音频和生成单声道副本 |
| [results.py](../src/asr_agent/tools/results.py) / [documents.py](../src/asr_agent/tools/documents.py) | 解析官方结果 JSON，写入并发布三种文档 |
| [directory_picker.py](../src/asr_agent/tools/directory_picker.py) / [_directory_dialog.py](../src/asr_agent/tools/_directory_dialog.py) | 管理原生目录窗口的子进程、取消和返回协议 |
| [model.mjs](../src/asr_agent/static/model.mjs) / [view.mjs](../src/asr_agent/static/view.mjs) / [app.mjs](../src/asr_agent/static/app.mjs) / [api.mjs](../src/asr_agent/static/api.mjs) | 分别处理交互状态、DOM、事件编排和 HTTP 传输 |

`tools` 同时包含外部能力调用和项目文件协议，依赖方向止于工具层。`rules` 不执行 I/O。`Session` 和 `DirectoryPicker` 用类管理生命周期，无状态能力使用模块函数。`Project` 包含文件系统行为，位于环境工具；`PreparedCommand` 仅服务 BL 调用，位于 BL 工具。

## 输入与确认协议

| 阶段 | 读取与检查 | 产出 |
| --- | --- | --- |
| 添加文件 | 核对用途、文件名、大小和接收字节数 | 会话副本与 `upload_id` |
| 预览 | 探测音频并建立 SHA 基线；解析所选 Excel；检查选项、上下文和保存目录 | 内存中的配置快照及 `validation_id` |
| 确认 | 复用快照，核对音频路径及 size/mtime | `config.json`、`config.sha256` 和 `job_id` |
| 执行 | 核对配置协议与摘要；建立执行占用；核对音频大小与完整 SHA，读取执行凭据 | BL 执行回执及原始 JSON |
| 重导 | 核对确认配置、已保存的 `JSON_READY` 记录及结果 JSON 摘要 | 新的一轮文档 |

每次预览解析当次选择的音频和词表；确认及执行复用预览保存的词典。重新导入词表或修改设置后，需要重新预览。配置中保存增强内容和识别选项，API Key 在运行时单独读取。

`job_files.publish_config` 独占创建任务目录，将配置写入临时文件，保存同一内容的 SHA，再发布 `config.json`。摘要用于发现内容变化，不是签名。读取端要求既有摘要，不为缺失摘要补签。

`tools.files.write_json_atomic` 是执行与导出记录共用的原子写入入口。配置、音频和结果 JSON 的摘要各有消费者；文档成品记录保存位置与大小。

## 凭据与命令参数

API Key 模式从项目 `.env` 读取 `DASHSCOPE_API_KEY`，只检查非空和内部空白。网页显示和正式执行分别读取；预览与确认不绑定凭据。Key 通过受会话保护的本机 POST 返回到只读密码控件，并在切换鉴权方式或保存后清空。

控制台模式使用项目内 BL 配置，不读取 `.env`。`login` 用于首次登录或用户明确要求重新登录；`console-status` 报告本地模型 Key 和控制台凭据的存在性，不代表在线权限验证。

`recognition_arguments` 集中映射已确认选项。热词通过 JSON 序列化形成一个参数值，上下文通过单个 `--context=<原文>` 传递，避免 BL 2.1.0 把 `--help`、`--version` 或其他 `--` 前缀文本识别为命令选项。

`prepare_command` 构造一次完整参数数组、检查 Windows 命令长度并准备凭据环境。进程使用 `shell=False`，引用和反斜杠由 `subprocess` 处理。`PreparedCommand` 含凭据环境，只在内存中传递。参数依据及传递保真验证见[官方资料与能力边界](REFERENCES.md)。

## 会话、媒体与执行生命周期

### 本机会话

`Session` 使用普通 `Lock` 保护上传、预览、确认和关闭状态。上传在短锁内登记，锁外接收字节，再在短锁内发布；同类上传不能并发。关闭后迟到的结果不能发布。目录选择器使用独立短锁和取消事件，取消请求不等待会话的文件 I/O。

浏览器用 `revision` 作废迟到的预览结果。保存收到明确的 4xx 拒绝时恢复编辑；网络中断或不明确的服务端错误进入 `save_unknown`，暂停重复保存。普通表单值留在 DOM，操作权限从 model 派生，Key 不进入 model。

保存目录可以使用默认 `outputs`，或由本机会话原生窗口选择。自选目录按用途登记精确路径，选择时试写一次，预览时核对目录仍有效。浏览器不能通过任意路径字符串批准其他目录。

关闭浏览器不等于关闭服务。正常服务退出清理未确认副本与词表副本，保留已确认音频；强制退出不保证完成清理或恢复草稿。

### 媒体准备

开启发言人区分且音频为多声道时，`convert_to_mono` 使用已确认的 `AudioInfo` 生成单声道 FLAC。转换保留采样率，逐帧处理音频，并核对源文件转换期间的变化以及新副本的声道、采样率和有效样本时长。新 FLAC 还需通过实际上传大小与时长限制。转换失败即停止执行。

### 一次执行

任务通过独占创建 `execution` 目录取得一次执行占用。占用从本地准备开始，包括缺少 Key、转换失败等 BL 尚未启动的情形。成功、失败或进程中断后均保留占用；再次调用同一任务返回本地状态。

这项约束限制同一 job 的执行尝试次数，不能保证云端恰好执行一次。BL 提交超时或本地进程结束，也不能证明云端未受理或已取消。

## 状态与结果语义

| 字段或状态 | 含义 |
| --- | --- |
| `CONFIGURED` | 配置已确认；`execution_authorized=false` |
| `PREPARING` | 本地准备已开始；BL 尚未启动 |
| `RUNNING` | 已在调用 BL 前保存保守状态；云端结果按未知处理 |
| `STOPPED` | 本次执行停止；结合 `cloud_outcome` 和错误阶段判断已知范围 |
| `JSON_READY` | 原始 JSON 已保存并通过结构检查 |
| `OUTCOME_UNKNOWN` | 本地记录缺失、损坏或不可读，无法从记录确定结果 |
| `documents_ready=true` | 当前导出记录中的三种文档全部完成 |
| `json_path` | 结果目标位置；字段存在不证明结果已取得 |
| `record_error` | 执行记录保存失败；磁盘状态可能落后于本次回执 |

执行记录每次只尝试写入一次。`PREPARING` 或 `RUNNING` 写入失败时返回 `not_started` 并停止启动 BL。成功结果记录写入失败时，回执保留 `JSON_READY`、`result_received`、路径及摘要，停止于文档导出之前。已有执行错误也不会被记录错误覆盖。

本地异常使用固定 `phase` 和必要的 `error_type` 定位；第三方未知异常只公开类型。官方错误解释集中在 `error_catalog.json`，状态解释见[错误与状态说明](ERRORS.md)。

`job-status` 读取本地执行记录和任务的固定导出记录，不检查进程存活、不查询云端、不重新验证成品。

## 文档交付

`tools.results` 是官方转写结果 JSON 的唯一解析入口。`application.delivery` 顺序生成 Excel、Word 和 Markdown，目标为已确认的任务文档目录中的三个固定文件名。各格式之间没有成功依赖；单个 writer 失败后仍尝试其余格式一次。记录保存失败或中断可能结束当次交付，已生成文件保留。

各格式先写入同目录临时文件，成功后替换目标文件；失败保留已有目标。Excel 和 Word 在替换前回读核对，Markdown 直接编码写入，编码保真由测试覆盖。每个任务只有一份导出记录：运行时为 `EXPORTING`，完成后为 `COMPLETE`、`PARTIAL` 或 `FAILED`。当次命令返回本次结果，`read_delivery` 直接读取该任务的固定记录。

显式 `export` 核对确认配置、已保存的 `JSON_READY` 执行记录及匹配的结果摘要，重新生成并覆盖该任务的同名成品。重导不读取 Key、音频或原 Excel，也不调用 BL。手工修改过的文档应先另存；同一任务等待当前导出命令结束后再发起下一次。结构与内容保真检查不代表识别准确率或 Office 排版已通过人工验收。

升级保留旧版本已生成的文件，不自动迁移、删除或扫描旧导出记录。已有任务明确重新导出后，成品和状态使用下表中的固定位置。

| 数据 | 位置 |
| --- | --- |
| Key 与 BL 配置 | `.env`、`.state/bailian/` |
| 暂存输入 | `.state/web-uploads/<session_id>/` |
| 确认配置 | `.state/jobs/<job_id>/config.json` 与 `config.sha256` |
| 执行记录 | `.state/jobs/<job_id>/execution/status.json` |
| 原始 JSON | `<json_root>/<job_id>/json/transcription.json` |
| 导出记录 | `.state/jobs/<job_id>/delivery/status.json` |
| 文档成品 | `<document_root>/<job_id>/documents/transcription.{xlsx,docx,md}` |

## 维护与发行

命名函数和方法使用简短中文职责说明：Python 使用 docstring，JavaScript 使用函数前注释。说明面向调用者，交代动作、结果及必要的返回约定；实现原因和外部限制写在对应代码旁。

修改行为时，沿当前职责定位消费者：输入限制在 `rules`，确认快照在 `Session`，CLI 映射在 `bailian`，结果解析在 `results`，导出编排在 `delivery`。调用顺序或状态协议改变时，同步对应 UML 源稿和渲染图。

[`scripts/build_zip.py`](../scripts/build_zip.py) 使用固定逐文件清单，当前清单为 46 个文件。运行代码、静态页面、错误字典、入口、依赖锁、Skill、LICENSE 和 `.env.example` 进入 ZIP。根目录 README、AGENTS 的中英文版本及 `.gitignore` 来自 `release/` 中的明确模板映射；包内 `doc/` 仅含 HELP、ERRORS、REFERENCES。

中文 `AGENTS.md` 是指令入口，`AGENTS.en.md` 为同一规则的英文对照。README 与发行模板同步维护两种语言。仓库 README 的页面概览、精度增强、输出结果三处使用 HTML 注释预留真实截图位置；截图尚待提供，当前发行清单不收录展示截图。

测试、构建器、pyproject、开发文档和 UML 保留在仓库。运行环境、下载文件、凭据、录音、转写结果和日志不发布。新增运行文件时更新发行清单及包边界测试；新增静态资源时同时检查 HTTP 路由。

```powershell
python -S -X utf8 scripts/build_zip.py
.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -t . -v
node --test tests/test_frontend.mjs
```

构建器拒绝覆盖同名 ZIP。验证应与改动相称，实际结果集中记录在 [ACCEPTANCE.md](ACCEPTANCE.md)，当前工作与发行状态维护在 [STATUS.md](STATUS.md)。
