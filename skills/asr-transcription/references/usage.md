# 运行与使用

此Skill将单个本地录音转写为原始JSON、Word、Excel和Markdown，完成后由用户校对。模型固定为`qwen-audio-3.0-asr-flash-filetrans`，地域为北京。

## 运行准备

本机需要Windows 10/11 x64、CPython 3.12 x64（含venv、ensurepip和tkinter）、Node.js 18.17.0或更高版本及npm。依赖安装需要联网。运行时可从[Python](https://www.python.org/downloads/windows/)和[Node.js](https://nodejs.org/en/download)官方页面获取。

复用本次会话已约定的工作目录；无约定时使用当前Codex任务的现有目录并告知用户。只有缺少可用目录或目录位于Skill内时才另行选择。Skill目录存放代码和参考资料；工作目录保存环境、凭据、任务和结果，录音在网页中通过文件选择器添加。所有命令都显式传入同一个`--workspace`，保存位置应在Skill目录之外。

在PowerShell中准备位置并安装依赖：

```powershell
$skillDir = '替换为此Skill的安装目录'
$workspaceDir = '替换为用户工作目录'
$scriptPath = Join-Path $skillDir 'scripts/asr.py'
python -S -X utf8 $scriptPath --workspace $workspaceDir bootstrap
$pythonPath = Join-Path $workspaceDir '.asr-transcription/.venv/Scripts/python.exe'
```

bootstrap从Skill中的Python/npm依赖锁安装到工作目录的`.asr-transcription`，回执提供安装状态及`key_file`。已有可用环境直接复用，已有Key文件保留。安装进度持续输出到stderr并同步写入本机日志；stdout输出最终JSON。正常下载没有总耗时上限，等待同一次进程结束。

需要下载Python依赖时，先比较官方PyPI和阿里云镜像的文件前缀速度，优先使用较快来源，并准备锁定的pip 26.2.1。pip自行恢复中断下载，单个业务依赖最多恢复5次；该来源最终失败后，自动尝试另一个来源一次。已完整下载的wheel保存在`.asr-transcription/.runtime/wheels`供后续安装复用，换源不跨进程续接未完成的文件。两个来源都失败时停止并保留`python-install.log`，不要在Codex中额外循环重跑或改动摘要。

需要诊断环境时运行：

```powershell
& $pythonPath -X utf8 $scriptPath --workspace $workspaceDir doctor
```

工作目录的虚拟环境解释器缺失或无法运行时，使用首次准备环境的 CPython 3.12 执行 `python -S -X utf8 $scriptPath --workspace $workspaceDir doctor`。诊断只报告问题，修复按实际回执处理。

Python依赖从HTTPS PyPI或阿里云镜像下载并校验摘要，然后从本机wheel安装。BL由npm按锁文件安装，失败停止。Skill不附带Python、Node、wheel或已安装依赖，不修改系统PATH或全局包。

## 认证与运行

先打开下文的本机转写页面，由用户选择录音与认证方式、保存配置，再按回执决定是否需要控制台登录。本机页面来自127.0.0.1；阿里云授权页面由BL的login命令另行打开。环境诊断doctor不执行登录。

### 控制台登录

网页保持“使用指定API Key”未勾选。首次配置运行以下命令，并保持同一进程等待授权。登录会启动系统默认浏览器；在受限执行环境中，通过执行工具的权限机制让命令运行于正常Windows交互桌面。普通终端可直接执行。

```powershell
& $pythonPath -X utf8 $scriptPath --workspace $workspaceDir login
```

用户在系统默认浏览器完成官方授权，Codex不另开授权页，也不通过computer-use验证页面。BL 2.1.0在Windows打开链接时存在参数引用问题：若输出完整备用链接，工具会把它交给同一系统浏览器，使用最后打开的完整链接页面。原login进程持续等待回调并保存凭据，Codex可结束当前回复并提示用户操作完成后发送“继续”。登录链接只用于打开页面，不贴入聊天或另存日志。

`WAITING_FOR_LOGIN`是启动提示。收到“继续”后读取原login会话的结果，以最终回执的`configured=true`判断模型凭据已保存；已有凭据状态不明时调用`console-status`。成功与否由BL结果判断，不另问用户是否成功。登录15分钟超时、失败或`configured=false`时说明结果并停止，不重复发起授权。

复用的是当前工作目录 `.asr-transcription/.state/bailian` 中的 BL 模型凭据。其他目录或系统级 BL 登录不代表这个工作目录已经配置。状态不明时运行`console-status`：`configured=true`表示模型 Key 存在；只有`console_configured=true`而`configured=false`时，先处理缺少模型凭据的提示。该命令只查询本机配置，云端鉴权由实际 BL 调用完成。账号准备见[阿里云官方指引](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)。

### 指定API Key

在页面选择“使用指定 API Key”，填写或修改北京地域的百炼 Key。已有 Key 会加载到密码输入框，默认遮蔽；点击“检查并预览”时，工具会将输入保存到当前工作目录的 `.asr-transcription/.env`。可以直接在网页完成配置，无需提前编辑文件。

此模式不运行login，正式执行读取该文件中当时的Key。密钥不填写到聊天或命令参数中。页面读取和保存均通过受保护的本机请求完成，云端鉴权由BL处理。

### 打开转写页面

```powershell
& $pythonPath -X utf8 $scriptPath --workspace $workspaceDir serve
```

命令持续运行并默认请求系统浏览器打开页面。宿主提供打开链接能力时使用`serve --no-browser`，收到启动回执后打开完整URL一次，随即让用户操作。正常使用不要求computer-use、截图或页面元素检查。原生目录窗口需要正常Windows交互桌面，应遵循执行工具的权限流程启动。

启动回执为`event="listening"`，包含`url`、`pid`和`browser_request`：`skipped`表示由调用方工具负责打开，`requested`表示已向系统发出打开请求，`failed`表示该请求失败。报告实际启动或请求结果，不额外等待“页面已显示”的验证。只有打开报错或用户反馈页面未出现时，按[页面打开问题](errors.md#页面打开问题)排查同一服务。URL含会话令牌，只用于本机页面，不贴入聊天、日志或截图。

## 网页配置

页面右上角提供中文/English和跟随系统、浅色、深色外观。界面语言与“音频语言”分别设置，界面切换不改变模型地域或转写原文。切换语言会保留当前输入，并要求重新检查已有预览；上传、检查或保存期间先等待当前操作结束。外观设置可独立调整。

1. 添加一个音频文件。
2. 选择语言、说话人区分和参考人数。说话人区分初始开启；多声道会提示生成单声道FLAC副本，原文件保留。
3. 开启“添加热词”后，在“热词表”旁点击带下载图标的“下载模板”，取得Excel词表，填写并导入；需要上下文时填写含相关词语的参考文本。热词与上下文可同时使用。
4. 通过原生目录窗口选择JSON和文档保存位置，默认是工作目录的`transcriptions`。取消窗口保留原位置。
5. 检查并预览，核对后保存设置，再由Codex按本次上传授权开始转写。

文件添加和设置保存都在本机完成。保存后的热词来自已确认的词典快照；修改Excel后须重新导入确认。没有保存的编辑在刷新后不会恢复。

用户填写页面期间，Codex结束当前回复并保留serve进程。网页在开始和保存成功后均提示：保存设置后回到Codex发送“继续”。收到后读取原会话的`event=configured`，衔接认证与转写准备；无需等待serve退出。网页保存不代表已授权上传，仍按实际授权范围决定是否需要用户确认。

浏览器只保存当前页面来源下的界面语言和主题偏好。录音内容、Key、热词和上下文保留在本次交互与工作目录中，网页不会将这些内容存入浏览器持久存储。界面语言不改变三种转写文档的既定标题与排版。

| 输入 | 当前要求 |
| --- | --- |
| 本机音频 | MP3、WAV、M4A、FLAC等；不超过2GB，时长不超过12小时 |
| 实际上传副本 | 不超过1GB，需要合并声道时按转换后的文件检查 |
| 热词文件 | `.xlsx`，不超过5MB，最多2,000个词，在普通工作表中按模板填写词语和权重 |
| 上下文 | 最多400个字符，包含期望识别的具体词语 |

GB和MB按十进制计量。开启说话人区分时，官方建议音频不超过2小时。完整规则见[模型依据](model.md)。引号、换行和反斜杠按原文输入，无需手工转义；词表问题按行提示，命令过长时按提示缩短路径或减少词条。

## 执行与交付

同一个serve进程保存成功后输出`event="configured"`回执。Codex使用其中的确切job_id，在授权覆盖本次录音及增强内容后执行一次：

若网页已保存而终端没有取得回执，使用[保存回执恢复](errors.md#保存回执恢复)核对任务，不根据文件时间猜测任务编号。

```powershell
$jobId = '替换为网页保存回执中的编号'
& $pythonPath -X utf8 $scriptPath --workspace $workspaceDir transcribe --job $jobId --authorize-upload
```

用户自行使用终端时，保留serve终端，在另一个终端执行转写。BL完成临时上传、提交、轮询及原始结果保存，Python生成三种文档。失败或结果未知时停止，不自动重传。

文件保存在已选择根目录的`JOB_ID/json/transcription.json`及`JOB_ID/documents/transcription.{docx,xlsx,md}`。三种文档保留原文、时间戳和启用时的说话人编号，标题为“源文件名 录音转写”。Excel/Word使用等线字体，具体排版由生成工具提供。

Codex根据回执给出成功、部分失败或失败及实际路径。只有`documents_ready=true`且`delivery.status=COMPLETE`表示三成品均已保存；`JSON_READY`只表示原JSON可用。将文件交给用户检查识别内容，转写交付不包含会议总结。

## 状态与重新导出

```powershell
& $pythonPath -X utf8 $scriptPath --workspace $workspaceDir job-status --job $jobId
& $pythonPath -X utf8 $scriptPath --workspace $workspaceDir export --job $jobId
```

状态查询只读本地记录。重新导出要求有效的成功记录与未改变的原JSON，复用同一组保存路径，覆盖同名文档；先另存手工修改内容，等待当前导出完成后再运行下一次。重导不读取Key、音频或原Excel，也不调用BL。

一种格式失败时保留该格式已有目标及其它成功文件。记录保存失败时保留本次回执，磁盘状态可能滞后；处理方式见[错误与状态](errors.md)。

## 关闭与数据保留

任务保存后可关闭页面；转写期间保持电脑及执行进程运行。网页关闭不会停止转写，终止本机等待不等于取消云端任务。结束本次网页服务时，在对应终端按Ctrl+C。

用户原文件保持原样，已确认音频副本和任务记录存于工作目录私有区；JSON和成品在关闭后保留。工作目录及用户自选输出目录可能属于Git仓库，提交前应按路径排除凭据、录音和转写内容。
