# S3 执行入口与验证

核验日期：2026-09-29。S3精简及本机合约已完成，API Key单样本的真实临时上传/固定模型识别通过。真实控制台登录及其他云端场景待验收，未开始S4导出。

## 已实现入口

| 命令 | 行为与边界 |
| --- | --- |
| login | 首次或主动重新登录时调用BL；API Key模式不需要，已有项目凭据直接复用 |
| console-status | BL公开本地状态，只返回是否存在模型凭据，不暴露凭据 |
| transcribe --job ID --authorize-upload | 独立执行一次，必须已有明确文件/增强内容上传授权 |
| job-status --job ID | 仅查看本地记录，不云端查询或重新提交 |

S2的config.json仍为CONFIGURED、execution_authorized=false，旁边新增config.sha256，以相同UTF-8字节保存并计算摘要。S3先核对一致性，旧记录缺摘要或配置发生变化时要求重新确认，不自动补签。摘要不是安全签名。S3显式授权记录保存在.state/jobs/ID/execution/status.json；该目录通过独占创建形成持久占用。任何成功、失败或崩溃都不自动删除占用；并发/重复执行不会启动第二个识别进程。

## 执行链路

1. 检查配置版本、固定模型/北京地域及显式授权。
2. 独占执行目录，记录PREPARING及执行器PID。
3. 复核音频/Excel指纹，直接使用S2快照中的参数、词表与媒体信息。实际argv、Windows长度和进程环境只准备一次；API Key仅此时读取，不另发鉴权预检或每次调用auth status。
4. 仅在需要时通过PyAV生成单声道FLAC，转换器返回已经实测的AudioInfo；同一份模型/上传限额函数检查该信息，不再次探测副本。原副本不覆盖。
5. 创建独占JSON目录；记录RUNNING，启动项目内BL 2.1.0的一次完整recognize命令。
6. 检查BL落盘对象中的transcripts/sentences、句子text、整数毫秒时间及可选speaker_id。保留全部原始音轨和扩展字段，不猜text/transcript别名。
7. 记录JSON_READY，或STOPPED/未知结果及脱敏错误。未输出Excel/Word/Markdown，documents_ready为false。

RUNNING只表示最近进入BL执行阶段；若宿主异常退出，记录可能停留在该值，job-status不把它宣称为仍在运行。task_id未被BL稳定暴露，保持null；JSON_READY的cloud_outcome为result_received，不声称Python已确认全部云端子状态。

## BL命令与失败边界

使用--url本地路径、--out独占结果路径、--base-url https://dashscope.aliyuncs.com、--config default、固定模型和经核实的增强/语言/人数参数。没有--file、--context-file、自建上传器或Python云端轮询器。Windows长度按subprocess.list2cmdline生成的完整参数、UTF-16单元及终止NUL计算，上限32767；超限不截断。

BL --timeout=3600同时影响请求和等待，不覆盖最后原生fetch下载；包装器限制整个进程3900秒。上传凭证/OSS超时仍由BL的15秒/120秒控制。转写stdout直接丢弃；stderr只解析完整官方错误JSON的白名单字段，脱敏已知输入、Key和URL，不转发cause/hint/栈或原文。错误解释直接读取error_catalog.json。

控制台登录由BL打开默认浏览器，最多等待15分钟，外层930秒。未打开浏览器时可中止，不重新实现回调/登录服务器或猜造--no-browser。BL的手动回退URL不会显示给用户，这是当前明确的限制；正常登录仍需实际验收。

## 已执行验证

- bootstrap返回already_installed，未重复安装；python -S scripts/asr.py --help成功，安装入口没有提前导入PyAV等尚待安装的库。
- 本轮全量180项Python测试通过，无跳过；20项前端测试通过。Windows正常桌面执行回归，保留T30受限环境连接差异的记录。
- 22项执行用例使用真实Session/PyAV，新增摘要字节一致、快照修改/旧配置拒绝、不重复探测原音频/解析Excel、不运行auth status等检查，保留原有失败和并发边界。
- 21项BL适配器测试覆盖一次构造/长度检查/Key读取及同一准备对象实际启动，repr不泄露输入；保留错误、超时和真实本机BL状态合约。
- 真实BL 2.1.0连接127.0.0.1模拟服务，新增三项验证完整执行入口的成功、退出0但空数组及HTTP401；重复执行后请求计数不增加。
- 真实BL auth status使用独立临时配置与合成Key验证，不读取用户凭据；BL仍可能进行公开版本检查，不称整个进程完全离线。
- 已确认的上传副本在Session.cleanup后仍可供独立执行用例使用，不依赖网页服务继续存活。

## 尚未验收

真实阿里云控制台浏览器登录、云端增强/多声道场景、人工识别质量、大文件性能、特殊媒体多音轨、Codex/电脑退出后的进程行为。额外云端调用仍须明确本次文件和上传授权，不能因为一次验收获准就继续发送其他数据。S4成品导出、S5 ZIP/Skill、S6完整安装流程另行推进。

## 一次真实API Key验收

用户明确批准具体音频、项目.env Key、百炼北京、固定模型、说话人开启、无热词/上下文和可能计费后执行。只启动一次BL识别进程，正常返回JSON_READY，没有应用层重试。输入本身为单声道，因此这次未触发媒体转换；转换路径仍由真实PyAV合成测试覆盖。

本地验收确认原音频SHA-256与选择时副本一致、配置摘要未变、结果对象可读且所有句子时间和可选说话人字段满足当前契约。具体统计和路径保存在被忽略的.state/jobs/*/acceptance-summary.json及相邻执行记录；正文、文件URL、文件名和凭据不写入版本库。没有人工参考文本，不声称准确率或说话人标签数量等于真实人数。

本次结果根字段为file_url、properties、transcripts；音轨字段包含channel_id、content_duration_in_milliseconds、text和sentences；句子包含begin_time/end_time、sentence_id、speaker_id、text、words。此证据支持后续S4对当前样本导出，不擅自增加未见字段别名兼容。
