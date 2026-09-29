# 官方资料与能力基线

> 初次核验：2026-09-28；S3相关资料于2026-09-29复核。仅采用官方资料及本机证据。2.1.0发布包和执行入口的本机验证见[S3_VERIFICATION.md](S3_VERIFICATION.md)；源码/模拟服务通过不等于真实云端验收。

## 来源索引

| 编号 | 官方来源 | 用途 |
| --- | --- | --- |
| A01 | [模型详情](https://help.aliyun.com/en/model-studio/qwen-audio-3-0-asr-flash-filetrans) | 固定模型确实存在 |
| A02 | [语音识别与音频规格](https://help.aliyun.com/zh/model-studio/asr-model) | 格式、大小、时长和采样率 |
| A03 | [Filetrans HTTP API](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api) | 请求参数、任务与转写 JSON |
| A04 | [提升识别准确率](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy) | 即时热词、预编译热词、上下文限制 |
| A05 | [热词 HTTP API](https://help.aliyun.com/zh/model-studio/vocabulary-http-api) | 创建、查询、删除预编译词表 |
| A06 | [临时文件 URL](https://help.aliyun.com/zh/model-studio/get-temporary-file-url/) | 上传限额、有效期及资源约束 |
| A07 | [管理异步任务](https://help.aliyun.com/zh/model-studio/manage-asynchronous-tasks) | 通用任务状态与轮询 |
| A08 | [百炼错误码](https://www.alibabacloud.com/help/zh/model-studio/error-code) | 通用错误；页面更新于 2026-09-25 |
| A09 | [本模型系列 Python SDK 参考](https://help.aliyun.com/zh/model-studio/funauidio-asr-recorded-speech-recognition-python-sdk) | 状态/错误示例，仅作为资料，不采用 SDK 实现 |
| A10 | [CLI 安装与鉴权](https://help.aliyun.com/zh/model-studio/cli/installation) | 安装要求和官方鉴权流程 |
| A11 | [CLI 快速开始](https://help.aliyun.com/zh/model-studio/cli/quickstart) | Agent 调用范式 |
| A12 | [CLI 配置与工具](https://help.aliyun.com/zh/model-studio/cli/config) | 文件上传和配置命令 |
| A13 | [CLI 语音合成与识别](https://help.aliyun.com/zh/model-studio/cli/speech) | --url本地文件、识别选项与--out |
| W01 | [Windows CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw) | 完整Unicode命令行32767字符（含终止NUL） |
| O01 | [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | 项目指令发现与优先级 |
| O02 | [Codex Skills](https://learn.chatgpt.com/docs/build-skills) | SKILL.md、发现路径和渐进加载 |
| M01 | [PyAV18.1.0安装文档](https://github.com/PyAV-Org/PyAV/blob/v18.1.0/docs/overview/installation.rst) | Windows wheel包含FFmpeg库 |
| M02 | [PyAV18.1.0 AudioResampler](https://github.com/PyAV-Org/PyAV/blob/v18.1.0/av/audio/resampler.py) | 声道转换和逐帧flush契约 |
| C01 | [python-dotenv文档](https://bbc2.github.io/python-dotenv/) | 解析指定.env而不修改全局环境 |

## 模型与文件

固定 ID：`qwen-audio-3.0-asr-flash-filetrans`。不能用 `qwen3-asr-flash-filetrans`、实时版或 3.1 替代。官方列出的地域为北京、新加坡。[A01](https://help.aliyun.com/en/model-studio/qwen-audio-3-0-asr-flash-filetrans)

| 约束 | 官方值/语义 | 首版处理 |
| --- | --- | --- |
| 每次输入 | 一个文件 URL | 只接受单文件 |
| 模型大小/时长 | ≤2 GB，≤12 小时 | 还须满足临时存储限制 |
| 采样率 | 任意 | 检测但不强制改为 16 kHz |
| 格式 | aac、amr、avi、flac、flv、m4a、mkv、mov、mp3、mp4、mpeg、ogg、opus、wav、webm、wma、wmv | 首版UI面向音频；视频容器是否展示待定，不承诺视频编辑 |

依据：[音频规格 A02](https://help.aliyun.com/zh/model-studio/asr-model)。本地须验证真实媒体内容，扩展名合法不能证明可识别。

## 临时 OSS

单文件上传上限 **1 GB**；资源有效 **48 小时**，与模型和阿里云主账号绑定。上传后不能查询、修改或下载；官方说明会在到期后清理，未找到本流程可主动删除临时音频的公开接口。获取上传凭证按主账号和模型限 **100 QPS**。`oss://` 识别请求需要 `X-DashScope-OssResourceResolve: enable`。官方不建议用于生产、高并发或压测。[A06](https://help.aliyun.com/zh/model-studio/get-temporary-file-url/)

**项目方案**：采用保守阈值 1,000,000,000 字节，UI 明示为项目上传上限；这是 GB 单位未进一步澄清时的设计选择，不声称官方精确字节数。限制作用于实际上传文件：无需合并时检查原文件，需要合并时检查生成的单声道副本。实际上传文件超过阈值则停止，不自动压缩/切片重试。转换本身的资源限制在S1单独验证。

## 请求和结果注意事项

- 固定模型必须有 `parameters` 对象，空配置也需 `{}`。
- 上下文位置为 `input.context`；即时热词位置为 `parameters.vocabulary`。
- `channel_id` 默认 `[0]`，多音轨独立计费；首版不提供多音轨选择。
- 官方`diarization_enabled`默认关闭，仅单声道；开启建议≤2小时。项目按用户决定默认开启，显式传BL的`--diarization`，不混淆产品默认值与官方默认值。可选`speaker_count`为2–100，仅是算法参考。
- `keep_dialect` 为 3.1 专属，不给固定 3.0 开放。
- 成功需检查任务和 `results[*].subtask_status`；转写链接有效 24 小时；句/词时间单位为毫秒。
- 官方示例与字段表对全文/时长字段命名存在差异（`text`/`transcript`、`content_duration_in_milliseconds`/`content_duration`），S3 必须核实真实响应。

依据：[A03](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api)。此页同一示例同时包含input.context与parameters.vocabulary；BL2.1.0同一请求也同时构造二者。已修正旧三选一界面，使用两个独立开关；联合请求构造探针再次通过。

### 单声道准备：取证范围与设计决定

用户已要求说话人默认开启，多声道合并为单声道且网页提醒。2026-09-28针对固定CLI提交检查`recognize.ts`、`upload.ts`及命令注册表，识别参数有`--diarization`和`--channel-id`，已检查路径未见声道合并入口。此结论限定于上述源码，不声称所有BL版本均无此能力；S1仍需核对安装版本公开帮助。

现采用PyAV18.1.0官方wheel，自带FFmpeg库；AudioResampler支持改变格式、声道布局、采样率，传None用于flush。项目仅调用其声道转换并保留采样率，随后编码FLAC，不调用独立FFmpeg程序、不实现混音计算。[M01](https://github.com/PyAV-Org/PyAV/blob/v18.1.0/docs/overview/installation.rst)、[M02](https://github.com/PyAV-Org/PyAV/blob/v18.1.0/av/audio/resampler.py)

网页合并提示属于本项目交互；转换后的单声道要求来自模型接口。`channel_id`是音轨选择，不能代替媒体声道合并。

## 热词与上下文

| 项目 | 官方规则 | 项目策略 |
| --- | --- | --- |
| 即时热词 | 请求携带词→权重映射，无须建云表 | 用户已确定采用；可与上下文同时使用 |
| 总词数 | 最多 2,000 | 本地阻止超限，避免服务端选择部分词 |
| 权重 | 普通 1–5；50 为超级热词，超级词最多 50 个 | 不默认启用超级热词 |
| 词长 | 含非 ASCII 字符时总长≤15字符；纯 ASCII 按空格分段≤7段 | 逐行校验并解释 |
| 词义 | 真实词语、语种受模型支持 | 只能校验结构；不能承诺自动判断所有词义 |
| 预编译配额 | 每账号最多10表，共享配额；更新建议间隔≥5分钟 | 不复用用户既有表，不做更新循环 |
| 上下文 | 每轮合计≤400字符；最多保留最近5轮；服务端可能截断 | 首版单段文本≤400字符，超限阻止 |
| 上下文效果 | 应包含待识别的相关原词 | 不把它当作摘要/行为指令 |
| 海外限制 | 新加坡子业务空间暂不支持热词 | 海外不列首版保证 |

依据：[A04](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy)。字符计数须在实现时明确 Unicode 语义，不能用 UTF-8 字节数或估计 token 数替代。

预编译方案使用 `speech-biasing` 的 create/query/delete 操作；`target_model` 必须等于固定模型。前缀只能含数字、小写字母且≤10字符，查询状态 `OK` 可用、`UNDEPLOYED` 不可用。管理与识别需同账号。[A05](https://help.aliyun.com/zh/model-studio/vocabulary-http-api)

**差异**：A05 的权重说明仍为 1–5，A04/A03 已支持 50。预编译方案若被采用，先仅开放 1–5，等实际契约明确后再讨论超级词；不可用不确定的“兼容”代码掩盖差异。

## CLI 取证版本

- 官方仓库：[modelstudioai/cli](https://github.com/modelstudioai/cli)。
- 已检查源码提交：`8bbbbc722d70fb200641ef22b6f6d033aeae9f74`，提交时间 `2026-09-28T05:23:20Z`。
- [固定提交 package.json](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/cli/package.json) 与 [npm latest 元数据](https://registry.npmjs.org/bailian-cli/latest) 均显示 `2.1.0`，Node 要求 `>=18.17.0`。
- [2.1.0 发布包](https://registry.npmjs.org/bailian-cli/-/bailian-cli-2.1.0.tgz) integrity：`sha512-G90UvW74qgMzZWSonLsbfCAca9+md6jnP99xFI8KkDR2xUPH7TlUmNKQENDTB2GeVAGcvCWSbUysjIAZtrn8Kw==`。
- npm 元数据缺少 `gitHead`；源码与发布包是否一致仍需 S1 核验。不把搜索缓存中的旧版 1.25.0 当作当前版本。

### 安装与鉴权源码事实

| 发现 | 实现影响 | 官方源码 |
| --- | --- | --- |
| `BAILIAN_CONFIG_DIR` 可重定位配置/凭据 | 设计项目内独立目录，安装后验证实际写入 | [paths.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/config/paths.ts) |
| postinstall下载Wiki，也使用该配置目录 | 安装钩子也需考虑缓存和网络，不执行未经审查的默认全局安装脚本 | [postinstall.js](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/cli/postinstall.js) |
| 模型请求支持 `DASHSCOPE_API_KEY` | Key可由内存注入子进程环境；不必放argv | [resolver.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/auth/resolver.ts) |
| `auth login --api-key` 在线校验但Key在argv；未见stdin入口 | 不能直接用于本项目安全输入流程；校验方式待定 | [login-api-key.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/auth/login-api-key.ts) |
| `auth status`只检查本地配置 | 不能把authenticated等同于模型可用 | [status.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/auth/status.ts) |
| 源码读取 `DASHSCOPE_BASE_URL`，帮助资料写过 `BAILIAN_BASE_URL` | 固定版本实测，不能凭名称猜环境变量 | [loader.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/config/loader.ts) |

### 自动更新与遥测

命令中间件存在更新检查与条件自动更新，可能运行全局 npm 更新和 `bl skill update`。`--quiet` 可阻止这一步实际更新，但不完全禁止检查网络和写更新状态。`DO_NOT_TRACK=1` 关闭遥测，不能代替关闭更新。未查到可直接使用的禁更新环境变量，不创造变量名。

依据：[middleware.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/runtime/src/middleware.ts)、[update-checker.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/runtime/src/utils/update-checker.ts)。

### ASR 命令契约（发布包/本机合约已验证，真实云端待验）

2026-09-28再次核对：`handleAsyncMode`在未指定`--async`时内置提交、`poll(...)`、结果下载及`--out`写文件；本地文件上传亦在同一命令内完成。**因此首选复用完整命令，不能把这些已有功能归为Python待开发项。**

S3正式流程采用的命令模板：

```text
bl speech recognize --config default --model qwen-audio-3.0-asr-flash-filetrans --url <上传文件绝对路径> --base-url https://dashscope.aliyuncs.com --diarization --out <JSON绝对路径> --timeout 3600 --poll-interval 5 --quiet --output json
```

模板对应项目默认开启说话人；若需要合并，上传路径为已通过校验的单声道副本，用户关闭说话人时省略`--diarization`。Python读取`--out`文件而非把stdout当JSON；S3丢弃可能含正文的stdout。本机真实CLI合约已确认完整模式通常不暴露task_id、子任务失败可能退出0并写空数组，以及取消/未知状态超时；真实云端鉴权、音频和结果格式仍须S3验收。存在接口限制不代表CLI没有相应云端能力。3600秒为项目等待策略，不是官方处理时限。

以下`--async`只是待研究的另一模式，不是默认实现路线：

```text
bl speech recognize --model qwen-audio-3.0-asr-flash-filetrans --url <上传文件绝对路径> --diarization --async --quiet --output json
```

`--async --quiet` 分支仍返回 `task_id` JSON；`--out` 在该分支不保存结果。该模板只用于说明契约，完整启动方式应使用锁定的本地 CLI 入口，避免 PATH 上的另一版本。

参数：`--context <text>` 转为上下文；`--vocabulary <json>` 为即时词映射；`--vocabulary-id` 为预编译表；`--diarization`、`--speaker-count`、`--channel-id` 分别控制相关参数。没有查到 `--context-file`，不得编造。[recognize.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/speech/recognize.ts)

**Windows 已实施边界**：按subprocess.list2cmdline的完整参数计算UTF-16单元并计入终止NUL，超过32767即在启动前拒绝；引号、反斜线和代理对测试通过。2,000条是模型上限，不保证全部能放入Windows命令行；不截词或改用云表。[W01](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)

### 需要规避的行为

1. `recognize` 在检查 dry-run 之前可能上传本地音频；本地预检不得调用此路径。
2. 默认等待模式的 stdout 不能保证为完整 JSON；子任务失败可能仅打印信息而退出0。
3. 等待代码对 `CANCELED/UNKNOWN` 的处理不能满足本项目终态语义，需要自行有界管理。

依据：[recognize.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/speech/recognize.ts)。

独立恢复入口限制：注册表未提供`speech task get`；`bl video task get`实际使用通用任务查询路径，但名称与正式能力文档不匹配，且`--quiet`会丢弃`results`。这不表示BL缺少正常转写中的轮询或下载。仅在需要恢复任务时核实入口，不据此另建Python云端客户端。[task-get.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/video/task-get.ts)、[commands.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/cli/src/commands.ts)

### 鉴权复用的边界

2026-09-29复核：npm最新仍为2.1.0，integrity与锁文件一致，GitHub main仍为上述固定提交。S3控制台登录使用`auth login --console --console-site domestic --config default`，不能同时指定--base-url；识别命令才显式覆盖国内端点。BL会打开默认浏览器，15分钟空等也可能退出0，auth status的authenticated也可能仅代表控制台token或AK，因此结束后必须检查api_key对象。只检查模型凭据存在性，不额外在线验证。[login.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/auth/login.ts)、[login-console.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/auth/login-console.ts)、[status.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/auth/status.ts)

recognize的模型鉴权优先级为显式--api-key、DASHSCOPE_API_KEY、profile的api_key；项目不使用明文argv Key，API Key模式由.env环境注入覆盖已有控制台配置，控制台模式不读.env。固定default profile避免继承其他活动配置。

最后下载JSON使用原生fetch而没有独立AbortSignal；S3外层3900秒终止并回收BL进程，不能称为取消云端。--out单份下载写对象、零份写[]、多份写列表；顶层results为空时甚至不写文件。S3只验收单文件对象的稳定句子字段，空/异常结果保留且不重提；该JSON不包含子任务元数据，不能声称Python验证了所有云端子状态。[recognize.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/commands/src/commands/speech/recognize.ts)

普通Key登录已包含在线有效性校验，`auth status`只反映本地配置。本项目按用户最新决定使用.env本地检查，并通过BL支持的DASHSCOPE_API_KEY子进程环境变量正式调用；不执行带明文Key参数的登录命令、不另做在线预验证。[安装与鉴权](https://help.aliyun.com/zh/model-studio/cli/installation)、[resolver.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/auth/resolver.ts)

本地解析使用`dotenv_values`，显式指定项目文件并关闭变量展开；结果状态不会暴露原值。配置存在只表示已填写，不代表在线有效。[C01](https://bbc2.github.io/python-dotenv/)

### 上传和失败次数

当前上传实现使用国内端点，整体读入文件再构造 Blob；上传凭证超时15秒、上传超时120秒。大文件内存和网络耗时可能早于官方大小上限成为限制，S1/S3 必须验证，不能承诺任意接近1GB的文件都可成功。[upload.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/files/upload.ts)

已审查的 ASR 主路径中，HTTP/上传失败直接抛出，正常未终结状态才轮询，未发现自动重提识别。此结论不覆盖整个 CLI；控制台域存在令牌刷新后再次调用的分支。安装包必须用请求计数测试复核。[http.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/core/src/client/http.ts)、[polling.ts](https://github.com/modelstudioai/cli/blob/8bbbbc722d70fb200641ef22b6f6d033aeae9f74/packages/runtime/src/utils/polling.ts)

## Codex 文件约定

`AGENTS.md` 是项目常驻规则，按目录发现；`SKILL.md` 是可按需加载的工作流，元数据需说明触发边界。项目技能由 `.agents/skills` 发现，单独 ZIP 未安装/未置于发现目录不等于可在所有聊天自动使用。首版在本项目范围内接入，后续若需跨项目调用另行讨论安装范围。[O01](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[O02](https://learn.chatgpt.com/docs/build-skills)

## 取证局限

尝试查看用户已打开的浏览器标签页时，浏览器工具先返回连接失败，后续超时；未取得标签页正文、登录状态或账户配置。公开官方资料已经另行读取。没有访问密钥内容、创建资源、上传音频或产生模型调用。

S1已安装真实CLI发布包并执行公开帮助、虚构URL dry-run及本机模拟服务识别命令。没有真实阿里云ASR调用或用户音频上传，不能据此认定云端权限/质量/媒体兼容性通过。未确认项目见[ISSUES.md](ISSUES.md)。

## S1安装资料

- BL使用npm生成的锁文件与`npm ci --ignore-scripts`；隔离userconfig/globalconfig/cache，禁止安装阶段重试。参数依据：[npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/)、[npm配置](https://docs.npmjs.com/cli/v11/using-npm/config/)。
- Python库版本/wheel摘要来源：[av18.1.0 PyPI元数据](https://pypi.org/pypi/av/18.1.0/json)、[python-dotenv1.2.3元数据](https://pypi.org/pypi/python-dotenv/1.2.3/json)，已写入requirements.txt；仅使用二进制wheel。
- pip通过原生require-hashes验证安装包；项目未保留自建下载器。[pip安全安装](https://pip.pypa.io/en/stable/topics/secure-installs/)

## S2界面设计依据

核验日期：2026-09-28。以下为设计参考，非百炼API约束，也不表示本项目是阿里官方产品。

- [Ant Design：Form Page](https://ant.design/docs/spec/research-form/)：按相关性组织表单，使用清楚的标题与提示，减少冗余说明，并提供核对和完成反馈。本项目据此采用三组表单和“填写、核对、保存”进度指示。
- [Ant Design：Data Entry](https://ant.design/docs/spec/data-entry/)：提供合理默认值、上下文帮助；复选框支持多选；上传区说明格式、大小及传入状态。本项目保留双增强独立复选框、原生文件选择与拖拽，使用不定进度条表示正在传入，不显示未经测量的百分比。

橙色强调、中性背景、字号、间距、折叠默认目录和底部操作栏是本项目设计选择，不冒充官方强制规范。采用较深橙色保证白色按钮文案可读，键盘焦点采用独立蓝色轮廓。

## 产品文案核验（2026-09-29）

- [提升识别准确率](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy)：热词与上下文均用于专有词汇增强；上下文应包含音频中待识别的原词，泛泛的语义背景效果有限。页面采用“热词增强”“上下文增强”和“参考文本”，示例给出具体术语及人名。即时热词及400字符限制不变。
- [Filetrans HTTP API](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api)：核对固定模型支持的context、vocabulary与diarization_enabled。“区分发言人”是说话人分离的产品用语，不表示识别真实身份；单声道要求与超过2小时的建议继续明确提示。
- [百炼CLI安装与鉴权](https://help.aliyun.com/zh/model-studio/cli/installation)：账号登录通过官方浏览器页面完成。产品页保留登录与API Key两个选择；预览版尚不执行登录，本地Key检测不能写成“验证成功”。
- [通义听悟官网](https://tingwu.aliyun.com/)：参考以录音场景、发言人和操作动作描述用途的表达方式。仅参考公开首页，不借用其速度、实时翻译、总结等能力承诺，也未访问用户的听悟内容。

## 模型参数与当前界面覆盖（2026-09-29）

范围固定为qwen-audio-3.0-asr-flash-filetrans和已安装BL2.1.0。API依据：[Filetrans参数](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api)。

| 参数 | 官方模型能力 | BL2.1.0公开入口与项目处理 |
| --- | --- | --- |
| language_hints | 最多4种语言，省略时自动识别 | --language只接受一个字符串并包装为单元素数组；UI仅自动/一种语言，不拼接伪多选 |
| speaker_count | 2–100参考值，需开启说话人分离，不保证精确人数 | --speaker-count，UI自动或指定整数，关闭分离时不传 |
| diarization_enabled | 单声道，建议不超过2小时 | --diarization；项目多声道合并方案保留 |
| context / vocabulary | 上下文与即时热词可并用 | --context / --vocabulary；继续独立展开输入 |
| channel_id | 音轨索引数组，各轨单独计费 | --channel-id只接受一个ID；BL帮助称“声道”，PyAV流到云端轨道对应尚未实测，暂不开放UI选择 |
| special_word_filter | API支持敏感词过滤 | BL公开help及已安装commands/core包没有该选项或请求透传入口；不自造参数/HTTP后备 |
| keep_dialect | 仅3.1模型支持 | 固定3.0不开放 |

已实际运行锁定BL帮助及保留域名URL的dry-run：--language zh --diarization --speaker-count 3 --channel-id 1，输出parameters包含language_hints:["zh"]、speaker_count:3、diarization_enabled:true、channel_id:[1]。无真实Key或音频。证据位于安装包bailian-cli-commands/dist/index.mjs识别命令及bailian-cli-core/dist/index.mjs语言构造函数；通用参数表不能替代发布包验证。

目录窗口使用Python3.12标准库[tkinter.filedialog.askdirectory](https://docs.python.org/3.12/library/dialog.html#tkinter.filedialog.askdirectory)，支持initialdir/parent和mustexist。用户已授权选择项目外保存位置；当前只选现有目录，不用浏览器文件上传控件冒充保存位置选择。

目录故障补充：Python[线程模型说明](https://docs.python.org/3.12/library/tkinter.html#threading-model)允许Tk解释器属于单独线程，不能仅凭HTTP工作线程创建Tk认定违规。本机对照确认默认受限执行与正常交互桌面的原生窗口显示结果不同；这是运行证据，不是官方文档对Codex实现的结论。独立GUI进程用于取消/超时回收，正常桌面启动解决已观察的可见性问题。
