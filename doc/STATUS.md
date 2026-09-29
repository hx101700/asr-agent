# 当前状态

更新时间：2026-09-29。S4三格式导出已接入并完成真实结果内容验收；Word逐页视觉检查仍待完成。分支dev，未进入S5打包或合并master。

## 当前目标

补齐从已保存JSON到Excel、Word、Markdown的本地交付，保持BL负责全部云端流程、失败不自动重试。下一次接续先处理Word视觉验收限制，详情见[S4_VERIFICATION.md](S4_VERIFICATION.md)。

## 已完成

- S1局部环境与BL2.1.0能力探针；依赖锁定，完整安装不重复运行pip，安装入口可在未加载第三方库时启动。
- S2前端轻量MVP：model管理交互状态，view处理DOM，app编排；web处理HTTP，session承载本地配置。上传短锁登记/发布，锁外接收；原生目录窗口可取消、不阻塞表单。
- 直接选单个文件，热词与上下文独立且可并用；说话人默认开启，多声道最终确认前提示合并；默认outputs，也可由原生弹窗登记外部输出目录。
- S3核对配置字节摘要、输入指纹后复用S2快照；PreparedCommand只构造一次参数和环境，Key读取一次，不额外调用auth status。
- 用户指定样本已完成API Key无增强和热词+上下文联合增强真实识别，原JSON只留本地；不据此声称准确率改善。
- Windows控制台登录链接丢失needapikey参数的问题已修复。BL同一回调会话给出的完整官方链接由os.startfile转交一次，实际登录已有模型Key和控制台凭据；没有为登录再次识别。
- S4新建results.py共享解析、documents.py三种writer、delivery.py逐格式交付。转写成功后自动导出一次；export --job ID只读已有JSON，在新目录生成全部三格式，不覆盖历史、不重跑BL。
- 导出状态独立于云端记录。逐项回读文字/时间/标签后发布正式文件；单格式失败不阻止其他格式；状态记录失败仍报告已有JSON。
- 并行导出每次返回自己的回执；job-status展示最新发起轮，未知/损坏记录不冒充成功。网页阶段说明和HELP已同步。

## 验证情况

- Python全量218项、前端20项通过，无跳过。Python在正常桌面环境执行；前端受限环境spawn EPERM，正常环境通过。未修改测试规避环境错误。
- 新Word依赖从官方PyPI安装并锁定哈希；首次下载超时停止，经诊断后单次延长下载等待安装成功，bootstrap复核already_installed；python -S入口检查通过。
- 复用既有联合增强JSON完成真实本地导出：329段、11,305字符，Excel/Word/Markdown全文独立比对一致，JSON未改，未带出临时file_url，无新增ASR请求。
- Excel首部、最长句与末尾渲染已检查。Word成功写入并回读全文，但渲染器缺LibreOffice，没有页面PNG；不得报告逐页视觉通过。问题T35。
- S3本机模拟ASR、媒体转换及失败语义仍在全量回归内；多声道云端、账号凭据下单独ASR和人工识别质量尚未由本轮覆盖。

## 状态与边界

- 模型固定qwen-audio-3.0-asr-flash-filetrans、北京、Windows首版、临时OSS、一次单文件。
- 网页确认只保存CONFIGURED、execution_authorized=false；上传授权单独给transcribe。一次execution占用永久保留，重复命令不重新上传或导出。
- JSON_READY仅表示JSON已通过结构检查；delivery.status=COMPLETE、documents_ready=true表示三成品通过写入和内容核验，不等于准确率或人工视觉验收。
- export是纯本地操作，每轮在<已选根目录>/<job_id>/documents/<导出编号>/保存三文件；源码不处理新云端协议。
- 用户已授权本项目指定样本范围内的合理真实测试，不逐次询问；仍限制次数、失败不重试，不扩展到无关数据。
- 凭据、音频、真实热词/上下文、原始结果、成品和截图仅在被忽略的data/.state/.runtime/outputs等目录，不进Git。

## 接续

先读AGENTS、本文件、S4_VERIFICATION，再看Git和当前进程。不要刷新用户未保存的旧网页；旧console-diagnostic只是登录修复前历史。

可从.state/jobs各任务的execution/status.json和exports/<导出编号>/status.json定位真实结果；本轮统计/Excel预览/Word渲染日志在.state/s4-qa，测试日志在.runtime。不要打印完整原始响应或读取凭据值。

先补Word逐页视觉，再由用户推进S5 Skill/ZIP与S6从ZIP到交付的整体验收。当前保留dev检查点，不推送或合并master；提交号以git log为准。
