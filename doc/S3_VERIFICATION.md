# S3 执行入口与验证

核验日期：2026-09-29。S3执行入口和本机合约已实现；真实控制台登录、临时OSS上传和模型识别尚未验收。未开始S4导出。

## 已实现入口

| 命令 | 行为与边界 |
| --- | --- |
| login | BL控制台登录；项目隔离/default配置，结束后检查模型Key存在性 |
| console-status | BL公开本地状态，只返回是否存在模型凭据，不暴露凭据 |
| transcribe --job ID --authorize-upload | 独立执行一次，必须已有明确文件/增强内容上传授权 |
| job-status --job ID | 仅查看本地记录，不云端查询或重新提交 |

S2的config.json仍为CONFIGURED、execution_authorized=false。S3显式授权记录保存在.state/jobs/ID/execution/status.json；该目录通过独占创建形成持久占用。任何成功、失败或崩溃都不自动删除占用；并发/重复执行不会启动第二个识别进程。

## 执行链路

1. 检查配置版本、固定模型/北京地域及显式授权。
2. 独占执行目录，记录PREPARING及执行器PID。
3. 检查本地鉴权配置、重新校验音频/Excel指纹和参数；拒绝变更、无效路径及超过Windows命令长度的增强输入。
4. 仅在需要时通过现有PyAV逻辑生成单声道FLAC，再检查实际大小、声道及时长；原副本不覆盖。
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
- 全量173项Python测试通过，无跳过；20项前端测试通过。Windows正常桌面执行回归，保留T30受限环境连接差异的记录。
- 16项执行用例使用真实Session合成配置及PyAV，覆盖授权、并发一次、崩溃占用、指纹变化、单双声道、转换后大小、双增强、历史文件保护、异常结果、多音轨和未知结果。
- 20项BL适配器测试覆盖环境/参数/输出隔离、Windows长度边界、错误脱敏、登录后状态核对及不重试；真实无GUI等待子进程验证了超时终止回收。
- 真实BL 2.1.0连接127.0.0.1模拟服务，新增三项验证完整执行入口的成功、退出0但空数组及HTTP401；重复执行后请求计数不增加。
- 真实BL auth status使用独立临时配置与合成Key验证，不读取用户凭据；BL仍可能进行公开版本检查，不称整个进程完全离线。
- 已确认的上传副本在Session.cleanup后仍可供独立执行用例使用，不依赖网页服务继续存活。

## 尚未验收

真实阿里云控制台浏览器登录、临时OSS、真实固定模型JSON和识别质量、大文件性能、特殊媒体多音轨、Codex/电脑退出后的进程行为。S3真实验收需要用户指定一个已保存配置并明确允许上传；不从“继续开发”推断收费识别授权。S4成品导出、S5 ZIP/Skill、S6完整安装流程另行推进。
