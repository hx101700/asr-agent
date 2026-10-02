# 官方依据与固定能力

API资料核验基线：2026-09-29。CLI固定2.1.0，对照源码提交`8bbbbc722d70fb200641ef22b6f6d033aeae9f74`及本机发布包；不把未核实的新版本能力加入当前接口。

精度增强[A04]与说话人分离[A03]资料最近核验：2026-10-02。产品输入方式和媒体处理以项目实现为准。

## 来源

| 编号 | 来源 | 用途 |
| --- | --- | --- |
| A01 | [模型详情](https://help.aliyun.com/en/model-studio/qwen-audio-3-0-asr-flash-filetrans) | 固定模型与地域 |
| A02 | [音频规格](https://help.aliyun.com/zh/model-studio/asr-model) | 容器、时长、采样率、模型文件大小 |
| A03 | [Filetrans HTTP API](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api) | 参数、句子JSON、子任务结果 |
| A04 | [提高识别准确率](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy) | 即时热词、超级词、上下文 |
| A06 | [临时文件URL](https://help.aliyun.com/zh/model-studio/get-temporary-file-url/) | 临时OSS限制及有效期 |
| A07 | [异步任务管理](https://help.aliyun.com/zh/model-studio/manage-asynchronous-tasks) | 通用任务状态 |
| A08 | [百炼错误码](https://www.alibabacloud.com/help/zh/model-studio/error-code) | API错误解释 |
| A09 | [模型系列SDK状态示例](https://help.aliyun.com/zh/model-studio/funauidio-asr-recorded-speech-recognition-python-sdk) | 状态/错误依据，不采用SDK实现 |
| A10 | [CLI安装与鉴权](https://docs.bailian.console.aliyun.com/zh/model-studio/cli/installation) | 控制台授权与本地状态 |
| A13 | [CLI语音识别](https://help.aliyun.com/zh/model-studio/cli/speech) | 公开recognize与out参数 |
| W01 | [CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw) | Windows命令行长度 |
| W02 | [cmd](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/cmd)、[os.startfile](https://docs.python.org/3.12/library/os.html#os.startfile) | 登录链接转交 |
| M01 | [PyAV18.1.0安装](https://github.com/PyAV-Org/PyAV/blob/v18.1.0/docs/overview/installation.rst) | wheel包含FFmpeg库 |
| M02 | [AudioResampler](https://github.com/PyAV-Org/PyAV/blob/v18.1.0/av/audio/resampler.py) | 声道变换、flush |
| C01 | [python-dotenv](https://bbc2.github.io/python-dotenv/) | 只解析指定.env且不展开变量 |
| O01 | [Codex构建Skill](https://learn.chatgpt.com/docs/build-skills) | SKILL.md元信息、脚本与参考资料的技能结构 |

## 模型和本地阈值

| 项目 | 当前依据与处理 |
| --- | --- |
| 模型/地域 | qwen-audio-3.0-asr-flash-filetrans，首版北京[A01] |
| 输入 | 单文件；模型<=2GB、<=12小时，任意采样率[A02] |
| 容器 | aac/amr/avi/flac/flv/m4a/mkv/mov/mp3/mp4/mpeg/ogg/opus/wav/webm/wma/wmv；只处理音频，不提供视频编辑[A02] |
| 临时上传 | 官方1GB，项目采用1,000,000,000字节阈值；限制实际上传副本，超限不压缩/切片重试[A06] |
| 临时资源 | 有效48小时，与主账号/模型绑定；没有本流程可主动删除临时音频的公开入口，不能承诺立即清除[A06] |
| 说话人 | 模型要求单声道，建议<=2小时；产品按用户要求默认开启，人数2–100为参考值，不保证真实人数[A03] |
| 语言 | API可多语种，但当前BL --language只收单值；产品自动或一种语言[A03/A13] |
| 热词 | 词→权重映射，<=2000条；权重1–5或50；超级词<=50；含非ASCII总长<=15字符，纯ASCII按空格<=7段[A04] |
| 上下文 | 单段<=400个Unicode字符，应包含要识别的相关原词，不作为模型行为指令[A04] |
| 组合增强 | input.context和parameters.vocabulary可同时存在；BL同一请求已核对[A03] |
| 音轨 | channel_id指音轨，默认[0]；不同于PyAV音轨内的channels。当前不开放选择 |
| 未开放参数 | special_word_filter没有已核实BL公开入口；keep_dialect只属3.1，固定3.0不使用 |

Excel的5MB、20MiB解压、200个内部文件、10001行和两列是本地解析资源限制，集中在utils/hotwords.py，不冒称模型限额。模型输入规则集中在application/rules.py，界面从服务端取得显示限制。

## BL复用边界

官方仓库：[modelstudioai/cli](https://github.com/modelstudioai/cli)。npm版本与完整性摘要以Skill中的`scripts/bailian/package-lock.json`为依赖来源；安装时由npm ci按锁文件获取依赖，不维护第二份依赖版本表。

| 能力 | 固定源码依据 | 本项目处理 |
| --- | --- | --- |
| 配置目录 | [paths.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/config/paths.ts) | BAILIAN_CONFIG_DIR指向WORKSPACE/.asr-transcription/.state/bailian |
| 环境Key | [resolver.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/auth/resolver.ts) | 用DASHSCOPE_API_KEY子进程环境，不把Key放argv |
| 官方登录 | [login-console.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/auth/login-console.ts)、[status.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/auth/status.ts) | BL负责回调与保存；登录后检查模型Key存在，不再调用模型验证 |
| 完整ASR | [recognize.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/speech/recognize.ts) | 本地上传、提交、轮询、下载、out保存均由BL完成 |
| 临时上传 | [upload.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/files/upload.ts) | 国内策略15秒、上传120秒；整文件读入内存，接近上限的大文件未全面验收 |
| 失败/轮询 | [http.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/client/http.ts)、[polling.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/runtime/src/utils/polling.ts) | 当前ASR请求失败上抛，正常未完成才轮询；不据此声称整个CLI所有命令都没有重试 |

使用recognize完整模式，不传--async。项目传timeout=3600、poll-interval=5；Python进程上限3900秒。这是项目等待策略，不是官方处理承诺。最后JSON下载使用原生fetch，没有单独下载超时，保留外层进程上限。

BL可能跳过失败子项、写空数组，或在没有子结果时不写文件；因此退出0仍需检查实际JSON。固定单文件成功结果已实测为对象，包含file_url/properties/transcripts；句子含begin_time/end_time/text及可空speaker_id，时间单位毫秒。Python不猜字段别名，也不声称获得了全部云端子任务信封。

完整模式不稳定暴露task_id，当前没有独立恢复入口。BL会在真实本地文件dry-run判断前执行上传，因此不能把本地文件dry-run当作无上传的预览。

### 增强文本与Windows参数

锁定的BL 2.1.0发布包中，bailian-cli-runtime/dist/index.mjs的parsePath先识别独立的--help/--version，parseFlags将分离参数中以--开头的值视为缺少参数值。解析器也支持以首个等号分隔选项和值，因此本项目将上下文构造成单个`--context=<原文>`参数；其中后续等号、引号、换行和反斜杠作为文本保留。

热词由`json.dumps`编码为一个JSON参数，再由BL的parseInstantVocabulary通过JSON.parse还原。bailian-cli-core/dist/index.mjs中的buildAsrContextMessages将上下文直接包装为input_text。本项目使用参数数组、Node入口和shell=False；Windows参数引用交给Python标准库处理。[Python参数传递规则](https://docs.python.org/3.12/library/subprocess.html#converting-an-argument-sequence-to-a-string-on-windows)、[JSON序列化](https://docs.python.org/3.12/library/json.html#json.dumps)

完整命令受Windows的32767个UTF-16单元限制（含末尾NUL）；超限在执行准备阶段明确停止。[CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)

### Windows登录转交

2.1.0的[local-server.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/shared/local-server.ts)用cmd/start传入未正确引用的URL，&needapikey参数会被拆开。BL失败后输出完整备用链接并保持原回调服务；本项目验证URL格式后用os.startfile打开一次，不修改BL源码、不建立第二个授权会话。这是针对固定版本链接引用问题的转交处理。

### 更新与安装副作用

BL中间件会检查版本并可能写update-state.json；quiet阻止后续自动升级/提示，不完全禁止版本查询。DO_NOT_TRACK=1关闭遥测。依据：[middleware.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/runtime/src/middleware.ts)、[update-checker.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/runtime/src/utils/update-checker.ts)。

安装使用官方[npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/)和[pip require-hashes](https://pip.pypa.io/en/stable/topics/secure-installs/)；BL与Python依赖分别由`package-lock.json`、`requirements.txt`锁定。Python包摘要来自官方PyPI，对应Windows x64 CPython3.12或py3-none-any包：[PyAV](https://pypi.org/pypi/av/18.1.0/json)、[dotenv](https://pypi.org/pypi/python-dotenv/1.2.3/json)、[python-docx](https://pypi.org/pypi/python-docx/1.2.0/json)、[lxml](https://pypi.org/pypi/lxml/6.1.3/json)、[typing-extensions](https://pypi.org/pypi/typing-extensions/4.16.0/json)。[pip官方说明](https://pip.pypa.io/en/stable/cli/pip_install/)支持用`--index-url`指定替代索引，[阿里云镜像站](https://developer.aliyun.com/mirror/pypi/)公布了其PyPI镜像地址。本项目使用HTTPS阿里云镜像获取全部Python依赖，仍按原PyPI摘要校验；没有随包wheel。PyAV许可见[官方LICENSE](https://github.com/PyAV-Org/PyAV/blob/v18.1.0/LICENSE.txt)；项目自身LICENSE不替代第三方许可。

## 本机窗口与成品

- [tkinter.askdirectory](https://docs.python.org/3.12/library/dialog.html#tkinter.filedialog.askdirectory)：选择现有目录。当前无人工总时限，取消与进程回收由项目处理；显示窗口需要正常交互桌面。
- [python-docx文本/分页](https://python-docx.readthedocs.io/en/latest/user/text.html)：段落、keep_with_next和widow_control；不代表无需实际页面检查。
- [openpyxl样式](https://openpyxl.readthedocs.io/en/stable/styles.html)及[Excel规格](https://support.microsoft.com/en-us/excel/excel-specifications-and-limits)：单元格32767字符、工作表1048576行、行高409。项目正文自动换行，按内容估算展示行高并封顶409，单元格保留长段全文；存储超限不截断。

使用步骤见[usage.md](usage.md)，任务状态和错误解释见[errors.md](errors.md)。
