# 状态与错误说明

> 核验日期：2026-09-29；CLI源码基线：`8bbbbc722d70fb200641ef22b6f6d033aeae9f74`。运行时解释的唯一字典为[error_catalog.json](../src/asr_agent/error_catalog.json)，包含核验日期、CLI版本、官方来源及中文含义。本文解释适用边界，不另维护一份运行时映射。

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

当前BL 2.1.0完整命令不会向包装器持续暴露这些状态，且CANCELED/UNKNOWN仍轮询到超时。上述是状态解释，不是当前Python能即时识别全部终态的承诺；S3采用有界等待并记录未知结果，详见REFERENCES。

## HTTP/API 错误

### 百炼通用错误

以下映射来自[百炼错误码](https://www.alibabacloud.com/help/zh/model-studio/error-code)（页面更新于2026-09-25）。错误码、HTTP状态与message需一起解释；同名错误的具体原因可能不同。

具体code及中文含义见[字典的api_codes](../src/asr_agent/error_catalog.json)。HTTP状态取BL实际返回值，不从退出码推断。

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

数值、官方常量及中文解释见[字典的cli_exit_codes](../src/asr_agent/error_catalog.json)。未列值按未知退出码解释，不能冒充服务端API错误码。

**映射限制**：当前[API错误映射](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/errors/api.ts)可能把HTTP错误统一归为`GENERAL=1`，并保留 `httpStatus/apiCode/requestId`。不能从401推断退出3，也不能从429推断退出4。错误JSON通常在stderr，解析位置见[error-handler.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/runtime/src/error-handler.ts)。

进程被终止、无法启动或收到未列数值时，单独记录平台/进程状态，不强塞到上述官方常量。CLI版本升级时复核。

## 项目自定义状态与错误

### S2本机网页HTTP状态

以下来自本项目[web.py](../src/asr_agent/web.py)，不是阿里云返回码：200表示本地操作完成；400表示JSON/请求格式错误；403表示Host、Origin或会话认证不符；404表示没有此静态资源或接口；422表示输入校验或本地文件操作未完成。界面同时显示字段与Excel行错误，不能把本机200解释为云端识别成功。

确认返回明确4xx时可修改输入、重新检查；网络结果未知时不自动重发，刷新只查询保存回执。配置本身始终带execution_authorized=false，S3需要新的云端执行授权。

### S3本地执行记录

| 状态 | 含义 |
| --- | --- |
| CONFIGURED | 已保存设置，未授权执行 |
| PREPARING | 已占用本次执行，正在本地准备；记录不保证进程仍存活 |
| RUNNING | 最近进入BL执行阶段，不能据此细分上传/排队/识别/下载 |
| JSON_READY | BL结束且JSON通过本地结构检查，三种文档尚未生成 |
| STOPPED | 本地准备、BL执行或JSON检查停止；失败不重试 |
| OUTCOME_UNKNOWN | 执行已被占用但记录不可读，不得重新启动 |

cloud_outcome分别记录not_started、unknown、result_received，不将本地成功等同于已核实所有云端子状态。完整BL模式未稳定暴露task_id，保持null；本地job_id不能代填云端task_id。

实际LOCAL错误来自[本项目进程适配器](../src/asr_agent/bailian.py)与[执行用例](../src/asr_agent/transcription.py)：

| code | 含义 |
| --- | --- |
| LOCAL_PROCESS_START_FAILED | 本地BL进程无法启动，识别未开始 |
| LOCAL_WAIT_INTERRUPTED | 本机等待超时、中断或管道故障，进程已停止；不能当作云端取消 |
| LOCAL_EXECUTION_STOPPED | 本地输入/媒体/路径准备或结果检查未完成，具体原因见中文说明 |

命令入口参数/配置错误也可能直接返回failed及message，没有伪造阿里云code。任何已有execution目录都会阻止重新启动，包括本地准备失败；用户修正后须新建配置，不自动恢复未知云端任务。

## 错误记录字段

已实现的CLI错误字段：source、cli_exit_code、http_status、code（服务端api_code）、脱敏message、explanation、request_id、source_url。只保留BL实际暴露的值，不补造cause/hint/stack或失败所在云端阶段。非JSON stderr不原样透传，保留实际退出码和通用说明。

本机status.json包含任务编号、最近状态/时间、执行器PID、授权来源、cloud_outcome、task_id（当前通常为空）、JSON位置及可用性计数；不包含转写正文、Key、上下文或热词。状态位于.state/jobs/ID/execution，BL原始JSON位于用户选择的JSON目录，均排除Git。未识别的官方code保留脱敏拼写，并明确字典未收录，不借用Paraformer含义。
