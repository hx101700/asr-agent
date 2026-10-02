# 状态与错误说明

先根据页面或 Codex 返回的提示定位问题。发生失败时，保留当前回执和已经生成的文件；处理完成前不要反复提交同一录音。

## 常见问题处理

| 现象 | 处理方法 |
| --- | --- |
| 安装期间没有新输出 | 等待同一次安装结束。只有返回失败后，才按提示检查网络、版本或日志；不要并行启动另一份安装。 |
| 安装提示目录冲突 | 让 Codex 检查提示中的安装目录及已有文件。保留凭据和用户数据，确认残留内容后再决定修复方式。 |
| 登录完成后仍提示配置不足 | 让 Codex 查看本地登录状态，确认模型调用凭据是否存在。页面登录成功不等于模型权限已验证。 |
| 文件或增强内容检查失败 | 按页面定位的字段修改。热词错误按 Excel 行处理；修改后重新导入、检查并保存。 |
| 选择文件夹后没有出现窗口 | 检查任务栏和被遮挡的窗口。仍无窗口时点击网页的“取消等待”，让 Codex 检查网页服务所在的桌面环境。 |
| 保存设置时断开连接或结果不明确 | 保留页面，返回 Codex 检查同一网页服务的保存回执。确认结果前不要重建或再次提交设置。 |
| 转写失败、超时或等待中断 | 让 Codex 说明停止阶段和已知结果。结果未知时不要重新提交；本机停止不代表云端已取消。 |
| 仅部分文档生成失败 | 先使用已保存的文件。任务成功记录和原 JSON 完整时，可明确要求 Codex 重新导出，生成新一轮文档。 |
| 提示执行记录无法保存 | 保留这次回执和文件，检查提示中的权限、空间或中断原因。后续状态查询可能是旧记录，不应据此再次识别。 |
| 错误原因未收录 | 保留脱敏的错误码和请求编号，参阅百炼官方错误说明或向服务方查询；不能仅凭状态码推断余额或权限问题。 |

提交问题反馈时，提供使用步骤、环境版本和脱敏错误信息，去除 API Key、登录链接、音频正文及私人路径。

## 状态字段参考

本节供排障和 Agent 解释回执使用。上游CLI/API错误映射位于[src/asr_agent/error_catalog.json](../src/asr_agent/error_catalog.json)，记录固定版本、核验日期和官方来源；本地错误由项目代码定义。

### 官方云端状态

依据：[Filetrans HTTP API](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api)、[模型系列状态示例](https://help.aliyun.com/zh/model-studio/funauidio-asr-recorded-speech-recognition-python-sdk)、[通用异步任务管理](https://help.aliyun.com/zh/model-studio/manage-asynchronous-tasks)。

| 状态 | 官方含义 | 当前实现的实际可见性 |
| --- | --- | --- |
| PENDING | 排队中 | BL正常轮询，Python不接收逐次状态事件 |
| RUNNING | 正在执行 | 同上，不能等同本地RUNNING的细分阶段 |
| SUCCEEDED | 顶层任务成功 | BL继续处理子项/下载；不代表三种成品已完成 |
| FAILED | 云端任务失败 | BL停止，Python解释暴露的错误，不重提 |
| CANCELED / UNKNOWN | 通用任务取消/不存在或未知 | 不承诺固定模型会返回；BL2.1.0识别路径未将它们作为完成条件，可能轮询到超时 |

本项目没有公网回调服务、第二个轮询器或已验收的云端取消/恢复查询入口。终止本地等待不等于取消云端。未知状态不能解释成成功，但也不能声称Python能即时观察BL未暴露的状态。

### CLI与API错误

- 官方退出码见[CLI定义](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/errors/codes.ts)，API解释见[百炼错误码](https://www.alibabacloud.com/help/zh/model-studio/error-code)，具体映射在error_catalog.json。
- CLI退出码、HTTP状态和API code是独立字段，按原回执分别解释。
- Python仅解析BL结构化stderr中code/message/request_id/http_status，脱敏后给用户；不输出原始stderr、cause、hint或完整响应。
- 未知code明确说明字典未收录，不猜余额、权限、音频损坏或套用其它模型含义。
- FILE_DOWNLOAD_FAILED等只使用固定模型系列明确示例；不能把Paraformer专有FILE_*说明搬过来。[HTTP示例](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api)
- 官方可能建议重试；本项目只解释，不自动执行重试。

### 本地网页HTTP

来自web.py，不是阿里云状态码：200本机操作完成；400请求格式错误；403Host/Origin/会话不符；404接口/资源不存在；422输入或文件操作未完成。

保存返回明确4xx时可编辑后重新检查；连接中断或结果不明确时保持save_unknown并冻结，不自动重发。服务端未捕获异常可能使请求断开，不承诺总能返回统一错误JSON。

### 一次转写记录

| status | 含义 |
| --- | --- |
| CONFIGURED | 已保存设置，还没有execution占用 |
| PREPARING | 已占用执行，最近处于本地准备；不保证进程仍活着 |
| RUNNING | 最近进入BL进程阶段，不能区分上传/识别/下载 |
| JSON_READY | JSON通过本地结构检查，文档另看delivery |
| STOPPED | 本地准备、BL执行或JSON检查停止，失败不重试 |
| OUTCOME_UNKNOWN | 占用已存在但执行记录不可读，不能当作未执行 |

cloud_outcome取not_started/unknown/result_received。当前BL完整模式未提供可靠的云端任务编号，执行记录不生成task_id字段，也不用本地job_id冒充云端ID。执行目录永久保留；本地准备失败也不自动删除占用重跑。

| 本地code | 含义 |
| --- | --- |
| LOCAL_PROCESS_START_FAILED | BL进程未启动 |
| LOCAL_WAIT_INTERRUPTED | 本机等待中断，不能推断云端未受理或已取消 |
| LOCAL_EXECUTION_STOPPED | 准备或结果检查未完成，看具体中文说明 |
| LOCAL_RECORD_SAVE_FAILED | 本地执行记录写入失败或被中断；保留当次回执，磁盘记录可能滞后 |

LOCAL_EXECUTION_STOPPED保留error.phase和error_type，BL错误沿用已有code并补充phase。已知输入错误解释具体原因，文件错误提示存在性/权限/空间/占用，未知程序异常仅公开类型，不输出可能含正文的异常原文。

| phase | 定位范围 |
| --- | --- |
| prepare_input | 本地环境、音频摘要、运行凭据、参数及必要声道转换 |
| run_bl | BL启动与等待；更细的上传/识别/下载状态仍由BL内部处理 |
| read_result | 读取、解析并检查原始JSON |
| save_status | 写执行状态；record_error.attempted_status说明哪次状态未保存 |

执行记录写入失败或中断放在独立record_error中，不替换原始执行事实，也不自动重写。PREPARING/RUNNING写入失败时，本次回执明确STOPPED/not_started；JSON_READY写入失败时仍返回JSON_READY/result_received、结果摘要和目标路径，documents_ready=false且不进入导出。此时job-status可能仍读到旧状态；export仍要求已保存的JSON_READY及摘要，没有补签、恢复记录或重新识别入口。

json_path是已确定的JSON目标位置，不单独证明文件存在或有效；JSON_READY才表示本次已成功读取并通过结构检查。RUNNING在启动BL前保守落盘，因此后续仅凭该磁盘记录不能证明是否已启动。命令参数、配置等入口错误仍可能直接返回failed/message。上述本地code不是官方错误码。

### 文档交付记录

| delivery.status | 含义 |
| --- | --- |
| EXPORTING | 最近记录在导出，不保证进程仍活着 |
| COMPLETE | 三种成品已保存，Excel/Word回读核验通过，Markdown编码写入完成 |
| PARTIAL | 部分格式成功，其余失败；保留成功文件 |
| FAILED | 全部失败或无法创建输出目录，原JSON保留 |
| OUTCOME_UNKNOWN | 导出中断或记录不可读/写，不声称成品齐备 |

files内分别记录READY/FAILED、路径/大小或错误类型。已知格式错误有本地说明，文件系统错误提示权限/空间/占用；未知程序异常只报告类型，不假装一定是磁盘问题。

导出失败不把JSON_READY改成云端失败。显式export核对执行记录中的结果JSON摘要，在新目录生成全部三格式，不重新识别；记录缺少摘要或结果发生变化时停止，不补摘要。job-status只看最近记录，不重新验证成品存在或摘要。
