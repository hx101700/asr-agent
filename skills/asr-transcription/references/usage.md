# 运行与使用

此Skill将单个本地录音转写为原始JSON、Word、Excel和Markdown，完成后由用户校对。模型固定为`qwen-audio-3.0-asr-flash-filetrans`，地域为北京。

## 运行准备

本机需要Windows 10/11 x64、CPython 3.12 x64（含venv、ensurepip和tkinter）、Node.js 18.17.0或更高版本及npm。依赖安装需要联网。运行时可从[Python](https://www.python.org/downloads/windows/)和[Node.js](https://nodejs.org/en/download)官方页面获取。

选择一个位于Skill安装目录之外的现有工作目录。Skill目录存放代码和参考资料；工作目录保存环境、凭据、任务和结果。所有命令都显式传入同一个`--workspace`。转写保存位置同样应在Skill目录之外。

在PowerShell中准备位置并安装依赖：

```powershell
$skillDir = '替换为此Skill的安装目录'
$workspaceDir = '替换为用户工作目录'
$scriptPath = Join-Path $skillDir 'scripts/asr.py'
python -S -X utf8 $scriptPath --workspace $workspaceDir bootstrap
$pythonPath = Join-Path $workspaceDir '.asr-transcription/.venv/Scripts/python.exe'
```

bootstrap从Skill中的Python/npm依赖锁安装到工作目录的`.asr-transcription`，回执提供安装状态及`key_file`。已有可用环境直接复用，已有Key文件保留。安装期间没有新输出不代表失败，等待同一次进程结束；失败按实际回执处理，不自动重试、换源或改锁。

需要诊断环境时运行：

```powershell
& $pythonPath -X utf8 $scriptPath --workspace $workspaceDir doctor
```

Python依赖使用HTTPS阿里云PyPI镜像，BL由npm安装，均校验固定依赖锁。Skill不附带Python、Node、wheel或已安装依赖，不修改系统PATH或全局包。

## 认证与运行

### 控制台登录

网页保持“使用指定API Key”未勾选。首次配置运行以下命令，用户在最后打开的阿里云官方页面完成授权：

```powershell
& $pythonPath -X utf8 $scriptPath --workspace $workspaceDir login
```

已有可用配置直接复用。首次状态不明或排障时可运行`console-status`；它报告本机配置存在性，不能代表云端权限已验证。账号准备见[阿里云官方指引](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)。

### 指定API Key

bootstrap在`WORKSPACE/.asr-transcription/.env`创建空模板。用户在本机填写`DASHSCOPE_API_KEY`，再在页面勾选“使用指定API Key”。此模式不运行login，正式执行读取当时的Key。密钥不填写到聊天或参数中。

页面通过受保护的本机请求显示Key，默认遮蔽。能读取Key不表示已经在线验证，云端鉴权由BL处理。

### 打开转写页面

```powershell
& $pythonPath -X utf8 $scriptPath --workspace $workspaceDir serve
```

命令持续运行并默认打开浏览器。原生目录窗口需要正常Windows交互桌面，应遵循执行工具的权限流程启动。仅用另一个浏览器工具打开启动URL时才传`--no-browser`。URL含会话令牌，只用于本机页面，不贴入聊天、日志或截图。

## 网页配置

1. 添加一个音频文件。
2. 选择语言、说话人区分和参考人数。说话人区分初始开启；多声道会提示生成单声道FLAC副本，原文件保留。
3. 需要热词时下载模板、填写并导入Excel；需要上下文时填写含相关词语的参考文本。热词与上下文可同时使用。
4. 通过原生目录窗口选择JSON和文档保存位置，默认是工作目录的`transcriptions`。取消窗口保留原位置。
5. 检查并预览，核对后保存设置，再由Codex按本次上传授权开始转写。

文件添加和设置保存都在本机完成。保存后的热词来自已确认的词典快照；修改Excel后须重新导入确认。没有保存的编辑在刷新后不会恢复。

| 输入 | 当前要求 |
| --- | --- |
| 本机音频 | MP3、WAV、M4A、FLAC等；不超过2GB，时长不超过12小时 |
| 实际上传副本 | 不超过1GB，需要合并声道时按转换后的文件检查 |
| 热词文件 | `.xlsx`，不超过5MB，最多2,000个词，按模板填写词语和权重 |
| 上下文 | 最多400个字符，包含期望识别的具体词语 |

GB和MB按十进制计量。开启说话人区分时，官方建议音频不超过2小时。完整规则见[模型依据](model.md)。引号、换行和反斜杠按原文输入，无需手工转义；词表问题按行提示，命令过长时按提示缩短路径或减少词条。

## 执行与交付

同一个serve进程保存成功后输出`event="configured"`回执。Codex使用其中的确切job_id，在授权覆盖本次录音及增强内容后执行一次：

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
