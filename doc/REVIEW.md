# 设计审查

本文记录当前实现的职责划分、必要取舍和维护关注点。它不替代测试结果，也不将本机验证视为云端或人工验收。验证证据见[验收记录](ACCEPTANCE.md)，未解决事项见[当前问题与限制](ISSUES.md)。

## 审查范围

审查围绕用户的完整任务：安装项目、配置一份录音、明确授权上传、理解执行结果、取得三种文档，并在需要时重新导出。代码证据包括 CLI 与 HTTP 入口、application、tools、前端、项目 Skill 和固定发行清单。

当前实现采用轻量用例分层和前端 MVP 式职责划分。设计重点是明确副作用发生的位置、保存可解释的执行事实，并直接复用 BL 公开能力。类主要用于具有生命周期的会话与窗口；无状态能力使用模块函数。

## 责任划分

| 设计 | 当前实现与理由 | 维护边界 |
| --- | --- | --- |
| 入口分派 | [CLI](../src/asr_agent/__main__.py) 与 [HTTP](../src/asr_agent/web.py) 处理协议和回执 | 多步骤业务放在 application；单一工具操作可以直接分派 |
| 用例分离 | [Session](../src/asr_agent/application/session.py)、[transcription](../src/asr_agent/application/transcription.py)、[delivery](../src/asr_agent/application/delivery.py) 分别管理配置、执行和导出生命周期 | 保持各自状态的所有者清楚，避免多个模块同时改变同一业务状态 |
| 外部能力集中 | [bailian](../src/asr_agent/tools/bailian.py) 包装公开 CLI；[results](../src/asr_agent/tools/results.py) 集中解析官方转写结果 JSON | 参数与返回结构变化在调用边界处理，继续复用 BL 的鉴权、上传、轮询和下载 |
| 规则与数据分离 | [rules](../src/asr_agent/application/rules.py) 表达无 I/O 规则，[models](../src/asr_agent/models.py) 保存共享不可变数据 | 只把多个模块共享的稳定概念放入 models |
| 前端职责分离 | [model](../src/asr_agent/static/model.mjs) 管状态与权限，view 管 DOM，app 管事件编排，api 管传输 | 普通表单留 DOM；Key 不进入 model；操作权限由状态派生 |
| 简单导出策略 | [delivery](../src/asr_agent/application/delivery.py) 使用固定 writer 列表调用三格式 | 格式逻辑位于 writer，轮次和部分成功处理位于 delivery |

分层约束有明确范围：`tools` 包含项目文件协议，并非纯通用工具集合；入口也允许直接调用单一工具。[结构测试](../tests/test_architecture.py) 检查已约定的导入方向和旧模块清理，不替代职责审查。

## 关键取舍

### 区分配置保存与上传授权

网页确认保存一个可核对的配置快照，`execution_authorized` 保持 `false`。转写命令必须显式携带上传授权。配置回执从原 `serve` 进程交给 Codex，避免按“最新任务”猜测用户选择。

代价是使用者需要保留明确的 `job_id`。目前没有列出历史任务的入口；该限制记录在 ISSUES。

### 按实际阶段检查输入

预览读取媒体信息并建立 SHA 基线，确认只检查路径和 size/mtime，执行前比对实际音频大小与 SHA。热词 Excel 在预览时解析，后续使用配置中的词典。Key 在网页显示和执行时分别读取。

这些检查各自服务不同的使用时点。修改时应先说明检查的消费者，避免重新加入确认阶段的完整 SHA、执行阶段的 Excel 读取或预览阶段的凭据绑定。实现见 [inputs](../src/asr_agent/application/inputs.py)、[Session.confirm](../src/asr_agent/application/session.py) 和 [prepare_input](../src/asr_agent/application/transcription.py)。

### 一次执行占用

`execution` 目录从本地准备开始占用。进程结束后保留占用，防止结果未知时再次提交。该约束包含缺 Key、转换失败等尚未启动 BL 的情形。

这是当前产品取舍，不是云端幂等保证。若未来允许修复后继续，应先定义“确定未启动”的证据和显式操作语义，再修改占用规则。当前代码没有自动重试或恢复执行入口。

### 分开记录外部结果与本地交付

`JSON_READY` 表示原始 JSON 已通过结构检查；导出轮次的 `COMPLETE` 才表示三种文档完成。单格式导出失败保留其他文件，重新导出读取已有 JSON，不再识别音频。

外部进程完成与本地记录保存不能组成一个原子操作。`_save_status` 在记录写入失败时为回执附加 `record_error`：未启动 BL 的情形保持 `not_started`；已经取得 JSON 的情形保留路径、摘要和 `result_received`。磁盘记录可能滞后，当前仍缺少记录恢复入口。

### 保持有限的并发控制

会话短锁保护上传登记与发布；接收文件字节在锁外进行。目录窗口在独立子进程中运行，取消请求使用选择器自己的同步机制。前端用输入版本识别迟到预览，保存结果未知时暂停重复提交。

这些机制服务当前浏览器并发请求和原生窗口生命周期。普通表单、文件和本地任务仍使用直接的数据结构与函数调用。

## 维护检查点

| 修改范围 | 首先核对 | 对应检查 |
| --- | --- | --- |
| 模型参数或输入限制 | 官方资料、固定 BL 版本、规则和参数映射 | 参数边界测试及本机 BL 合约测试；必要时执行已授权云端验证 |
| 执行或错误处理 | 副作用发生顺序、`cloud_outcome`、`phase`、记录失败语义 | 故障注入与一次执行回归 |
| 网页交互 | model 权限、迟到响应、焦点和原生窗口 | 前端测试与实际浏览器交互 |
| 文档导出 | 原文、时间戳、格式限制、部分交付 | 内容回读测试与 Office 实际阅读检查 |
| 安装或发行 | 依赖锁、文件清单、中英文模板、相对链接 | 新目录安装及包边界检查 |
| 调用关系或状态协议 | application 与 tools 的责任分配 | 相关测试、DEVELOPMENT 和 UML 同步 |

维护时优先让失败位置和返回语义明确。新增层次、依赖或校验前，应能指出当前消费者和具体失败机制；已有工具可以直接满足要求时继续复用。

## 仍需关注的产品能力

当前主要不足是安装过程缺少阶段反馈、任务编号丢失后缺少查询入口、结果与记录分离后的恢复能力，以及尚未完成的独立用户旅程和实际文档视觉验收。具体影响、可用处理方式与代码位置集中维护在 [ISSUES.md](ISSUES.md)。

识别质量与流程正确性分别评估。结构检查和文档回读可以证明约定范围内的内容传递，不能证明词语识别或说话人划分准确。精度增强效果需要带人工参考稿的已授权录音进行评估。

## 代码阅读入口

1. 阅读 [使用指南](HELP.md) 与[项目 Skill](../.agents/skills/asr-agent/SKILL.md)，确认人、网页、Codex 和 BL 各自的职责。
2. 对照 [UML](UML.md) 跟踪 Session 的上传、预览与确认，区分 `upload_id`、`validation_id` 和 `job_id`。
3. 跟踪 `transcription` 与 `bailian` 的调用顺序，判断每个失败点已经发生的本地和外部副作用。
4. 阅读 `results`、`delivery` 和 `documents`，区分 JSON 有效、文档交付、内容保真和识别准确率。
5. 查看对应测试和[构建器](../scripts/build_zip.py)，确认修改范围与发行范围一致。
