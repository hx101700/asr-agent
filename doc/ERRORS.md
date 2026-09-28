# 状态与错误说明

> 核验日期：2026-09-28；CLI 源码基线：`8bbbbc722d70fb200641ef22b6f6d033aeae9f74`。本文件是首版错误字典的设计依据，机器可读字典在实现阶段生成并与本文件校验一致。

## 适用范围

本项目采用异步“提交—轮询—获取结果”，默认由BL内置流程执行，不建设公网回调服务或Python轮询器。用户所说的回调状态在本项目中分为任务状态、HTTP/API错误、CLI退出码和本地错误，不能共用一张没有来源的状态码表。官方含义用于解释BL实际提供的信息，不为获取未暴露字段另发请求。

官方资料可能建议重试；本项目遵从用户要求：**失败后不自动重试**。正常排队/运行中的查询不是重试失败请求。用户手动恢复也必须说明恢复哪一步，不能把重新提交识别藏在“继续”按钮后面。

## 云端任务状态

| 状态 | 官方含义/适用范围 | 向用户说明与项目行为 |
| --- | --- | --- |
| `PENDING` | 已提交，排队中 | “已提交，正在排队”；按间隔正常查询 |
| `RUNNING` | 正在运行 | “正在识别”；不重新上传或提交 |
| `SUCCEEDED` | 顶层任务成功 | 继续检查子任务，再下载JSON；此时不宣称三种文档已完成 |
| `FAILED` | 任务失败 | 保存原因，停止；不自动重提 |
| `CANCELED` | 通用任务系统的已取消状态 | 停止等待；不等同于用户关闭网页；本版不承诺取消正在运行的ASR |
| `UNKNOWN` | 通用任务系统中不存在或状态未知 | 报告未知，检查原ID/地域；不得据此自动重提 |

`PENDING/RUNNING/FAILED` 见[本模型系列 SDK 状态说明](https://help.aliyun.com/zh/model-studio/funauidio-asr-recorded-speech-recognition-python-sdk)；顶层及子任务结果见[Filetrans HTTP API](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api)；`CANCELED/UNKNOWN` 见[异步任务管理](https://help.aliyun.com/zh/model-studio/manage-asynchronous-tasks)。后者为通用状态，不声称固定模型每次都会产生全部状态。

出现文档未列出的状态时保留原值，停止自动推进并提示“任务状态未被当前版本识别”。不能用默认分支把未知状态当成功。

## HTTP/API 错误

### 百炼通用错误

以下映射来自[百炼错误码](https://www.alibabacloud.com/help/zh/model-studio/error-code)（页面更新于2026-09-25）。错误码、HTTP状态与message需一起解释；同名错误的具体原因可能不同。

| HTTP | code | 简明解释 | 建议用户动作 |
| --- | --- | --- | --- |
| 400 | `InvalidParameter` | 参数不符合要求 | 根据具体message检查本模型参数 |
| 401 | `InvalidApiKey` / `invalid_api_key` | Key或鉴权配置有误 | 检查Key、地域和endpoint，重新验证 |
| 401 | `NOT AUTHORIZED` | 账号/业务空间未授权 | 检查实际权限与空间归属 |
| 403 | `AccessDenied` | 访问被拒 | 结合message确认原因 |
| 403 | `Model.AccessDenied` | 没有模型访问权限 | 检查模型开通与授权 |
| 404 | `WorkSpaceNotFound` | 业务空间不可用/配置错误 | 检查Workspace配置 |
| 429 | `Throttling` / `Throttling.RateQuota` | 请求频率受限 | 停止；由用户决定何时恢复 |
| 429 | `Throttling.Concurrency` | 并发受限 | 检查同账号其他任务 |
| 429 | `BudgetLimitExceeded` | 预算触发停止调用 | 用户检查预算设置 |
| 500 | `InternalError` | 服务内部错误 | 保存request_id，按需联系支持 |
| 500 | `InternalError.FileUpload` | 文件上传失败 | 检查message与上传阶段 |
| 500/503 | `ServiceUnavailable` | 服务暂不可用/容量不足 | 停止，保留诊断信息 |

这些是通用错误的初始子集，不声称完整枚举所有ASR错误。文档给出的“稍后重试”等建议只转述为用户可选择的下一步，不触发程序重试。

### 固定模型系列的明确示例

| code | 证据范围 | 解释 |
| --- | --- | --- |
| `FILE_DOWNLOAD_FAILED` | [Filetrans HTTP失败响应示例](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api) | 云端获取输入音频失败；检查资源有效期及访问条件 |
| `InvalidFile.DownloadFailed` | [本模型系列SDK失败示例](https://help.aliyun.com/zh/model-studio/funauidio-asr-recorded-speech-recognition-python-sdk) | 输入文件下载失败；保留原始拼写，不假设与另一code在所有接口等价 |

总错误页中明确标为 Paraformer 的 `FILE_*`、`ASR_RESPONSE_HAVE_NO_WORDS`、`SUCCESS_WITH_NO_VALID_FRAGMENT` 等说明，不自动纳入固定 Qwen 模型字典。不据此套用别的模型格式或时长限制。

### 未知错误模板

“在【失败阶段】收到错误【原code】。当前官方映射未确认，原始信息为【脱敏message】。已停止，未自动重试。任务ID【若有】，请求ID【若有】。已保存【文件清单】。建议先检查【有证据的检查项】。”

不得把未知错误推断为余额不足、音频损坏或权限问题；只有message和官方来源支持时才能给出对应解释。

## CLI 退出码

以下取自[官方退出码定义](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/errors/codes.ts)。

| 数值 | 常量 | 用户可读说明 |
| --- | --- | --- |
| 0 | `SUCCESS` | CLI进程正常结束，仍需检查业务结果 |
| 1 | `GENERAL` | 一般错误，读取结构化错误详情 |
| 2 | `USAGE` | 命令或参数使用错误 |
| 3 | `AUTH` | CLI鉴权类别错误 |
| 4 | `QUOTA` | CLI配额类别错误 |
| 5 | `TIMEOUT` | CLI等待或请求超时 |
| 6 | `NETWORK` | CLI网络类别错误 |
| 7 | `CONFIRMATION_REQUIRED` | 命令要求确认 |
| 10 | `CONTENT_FILTER` | 内容过滤类别错误 |

**映射限制**：当前[API错误映射](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/errors/api.ts)可能把HTTP错误统一归为`GENERAL=1`，并保留 `httpStatus/apiCode/requestId`。不能从401推断退出3，也不能从429推断退出4。错误JSON通常在stderr，解析位置见[error-handler.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/runtime/src/error-handler.ts)。

进程被终止、无法启动或收到未列数值时，单独记录平台/进程状态，不强塞到上述官方常量。CLI版本升级时复核。

## 项目自定义错误（设计）

下表使用 `LOCAL_` 前缀，明确不是阿里云状态码。最终是否需要独立退出数值在实现阶段决定，当前不编造已存在的命令协议。

| 自定义code | 含义 | 恢复边界 |
| --- | --- | --- |
| `LOCAL_ENVIRONMENT_INVALID` | 依赖/版本/入口不符合要求 | 修复环境，不发云端请求 |
| `LOCAL_AUDIO_INVALID` | 本地媒体探测或限制不通过 | 换文件/修改选择后再确认 |
| `LOCAL_HOTWORDS_INVALID` | Excel结构或热词规则错误 | 按行修改，不自动删词 |
| `LOCAL_CONTEXT_INVALID` | 上下文为空或超过所选模式限制 | 用户修改，不自动截断 |
| `LOCAL_OUTPUT_UNWRITABLE` | 输出目录不可写 | 修改目录后重新确认 |
| `LOCAL_APPROVAL_STALE` | 确认后的输入发生变化 | 重新校验与确认 |
| `LOCAL_SUBMISSION_UNCERTAIN` | 提交结果未知 | 不重提；先核实原任务 |
| `LOCAL_WAIT_INTERRUPTED` | 进程/有界等待中断 | 有task_id时可人工恢复查询 |
| `LOCAL_RESULT_SCHEMA_INVALID` | 返回JSON无法按已核实契约解释 | 保留原始JSON，修复映射，不重跑识别 |
| `LOCAL_EXPORT_FAILED` | 一种或多种导出失败 | 保留已完成结果，只重新导出 |
| `LOCAL_CLEANUP_FAILED` | 本任务词表清理未完成 | 单独列出待清理ID；不重跑识别 |

## 错误记录字段

计划保存：`stage`、`source`（cli/http/task/local）、`cli_exit_code`、`http_status`、`code`、脱敏`message`、`task_id`、`request_id`、时间、`source_url`、`applicability`、已保存文件和明确下一步。云端字段只记录BL实际暴露的值，未暴露则为空/未知，不补造，也不增加网络请求。`http/task`表示错误来源，不表示Python承担HTTP调用。运行记录在`.state/`，BL保存的转写JSON在`outputs/`，均排除Git。

将字典与用户说明做成同一份数据的生成结果，避免代码和文档维护两套含义。每个官方条目必须有URL和核验版本/日期；测试至少包含未知code、stderr JSON、退出0但子任务失败和状态未知四类情况。
