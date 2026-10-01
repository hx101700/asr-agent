# 使用说明

## 适用范围

Windows 10/11 x64，需本机已有Windows x64 CPython 3.12、Node.js 18.17.0或更高版本及配套npm。首次安装需要访问阿里云PyPI镜像和npm仓库。固定北京、固定`qwen-audio-3.0-asr-flash-filetrans`；每次一个本地文件，仅临时OSS。

支持JSON、Excel、Word、Markdown；带毫秒时间戳，发言人区分默认开启。热词Excel与上下文可独立或同时启用。没有实时录音、翻译、自动摘要、批量音频或多音轨选择。

## 安装与诊断

将发行ZIP解压，使用Codex打开其中的`asr-agent`目录。交给Codex安装到指定空目录时，展开ZIP最外层`asr-agent/`的内容，使工作目录直接包含`scripts`和`.agents`。项目Skill位于`.agents/skills/asr-agent/SKILL.md`；无需复制到用户级目录。

在项目目录执行：

```powershell
python -S -X utf8 scripts/asr.py bootstrap
.venv\Scripts\python.exe scripts/asr.py doctor
```

`bootstrap`核对本机Python/Node和依赖锁，在项目`.venv`通过`https://mirrors.aliyun.com/pypi/simple/`下载全部Python依赖（含PyAV），由pip核对`requirements.txt`的版本和SHA-256；需要新增BL安装时再检查npm并在项目`.tools/bailian`运行`npm ci`。完整环境会复用，已有BL不再要求npm入口，冲突目录不会自动覆盖。安装不修改全局包或系统PATH。`doctor`只报告环境问题，不安装、不登录或识别。

本机Python需支持`venv`、`ensurepip`和`tkinter`；浏览器保存位置使用原生目录窗口。PyAV的官方wheel自带所需FFmpeg库，无需额外安装FFmpeg可执行文件。安装后使用项目内`.venv`入口；运行BL仍需本机Node。

pip/npm安装期间可能没有持续输出；安装命令失败返回后，才把输出写入`.runtime/python-install.log`或`.runtime/bootstrap.log`。前置检查失败或用户中断不保证生成这些日志，先查看实际回执及其提供的路径。没有新输出或日志尚不存在不能单独判断安装失败。下载速度随网络变化，等待同一安装进程的结果。

安装失败不自动重试、改锁或切换镜像；先检查网络、版本及实际错误。清华镜像由用户反馈当前不可用，不作为自动后备。Codex隔离执行出现网络异常时应遵循工具权限流程排查。非空或不完整的BL安装目录会拒绝覆盖；可启动且平台正确的Python虚拟环境可以复用。处理冲突目录前先确认内容，保留正常安装、凭据和用户文件。

## 鉴权

### 控制台方式

第一次配置或主动重新登录时运行：

```powershell
.venv\Scripts\python.exe scripts/asr.py login
```

用户在最后打开的阿里云官方页面完成授权，BL将凭据保存到项目`.state/bailian`。当前BL Windows打开链接可能先出现一个参数不完整的页面，程序会转交BL提供的完整备用链接一次；不要重复提交旧页面。

login结束时已调用BL的本地状态命令，并返回configured（模型Key存在）和console_configured（控制台凭据存在）。这不表示在线权限已验证。已有凭据直接复用；状态不明或排障时可单独运行`console-status`，无需在每次login之后重复查询。

### 指定API Key

将`.env.example`复制为项目`.env`，填写`DASHSCOPE_API_KEY`，然后在网页勾选“使用指定API Key”。页面从本机读取并显示在只读密码控件中，可显示/隐藏。不要发送Key到聊天或提交Git。

页面读取时只检查非空和内部空白，不发在线鉴权请求。预览和确认不再读取或绑定.env文件；**正式执行读取当时的.env**。页面当前显示的Key不意味着之后永久固定使用该值。控制台模式不读取.env。

## 网页配置

```powershell
.venv\Scripts\python.exe scripts/asr.py serve
```

原生目录窗口需要可显示GUI的正常Windows交互桌面。Codex启动时应使用工具执行权限流程；仅能import tkinter不能证明窗口可见。

1. 选择或拖入一个音频。此时只把字节传入127.0.0.1本机副本，没有发送阿里云。
2. 选择语言及发言人设置。多声道且开启发言人区分时，核对生成单声道FLAC副本的提示；原文件保留。
3. 按需添加热词Excel、上下文。热词Excel列为text/weight或热词/权重，下载模板可查看示例；错误按行显示。上下文应含可能识别的具体词语。
4. 使用系统弹窗选择JSON与文档保存根目录；默认outputs。目录选择没有总时间限制，可在原生窗口取消或点击网页“取消等待”。其他目录必须经本机会话的原生弹窗登记。
5. 点击“检查并预览”，核对媒体信息、增强设置与保存路径，再保存设置。网页与启动它的进程都会给出同一`job_id`回执；此时尚未授权上传或开始识别。进程启动URL含本机会话令牌，不贴进聊天或日志。

音频本机接收最多2,000,000,000字节；实际云端上传文件须满足项目1,000,000,000字节阈值。需合并声道时以转换后的文件为准，超限停止，不自动压缩/切片。热词文件本机上限5MB，词表及上下文规则见[官方依据](REFERENCES.md)。

热词和上下文按原文填写，引号、反斜杠等字符由程序完成参数编码，无需手工添加转义符。上下文可以保留换行；热词按普通文本单元格填写，公式、首尾空白及词条中的控制字符会按行提示修改。词表满足模型数量限制后，完整命令仍需符合Windows长度上限；超长时程序明确提示缩短路径或减少词表，不截断内容。

保存确认只复用预览快照，并轻量检查音频文件元信息。实际执行前还会完整核对音频大小和SHA。热词已导入配置，不保存或依赖临时Excel路径和摘要：修改Excel要重新导入、检查和确认，不会改变已有任务。

保存结果不明确时页面保持冻结，不自动重发。普通未保存编辑不会在页面刷新后自动恢复；已保存回执只能从仍运行的同一网页服务恢复。

## 执行和查看结果

确认这次音频及增强内容可发送阿里云百炼北京后执行：

```powershell
$jobId = '网页回执中的32位设置编号'
.venv\Scripts\python.exe scripts/asr.py transcribe --job $jobId --authorize-upload
.venv\Scripts\python.exe scripts/asr.py job-status --job $jobId
```

BL负责上传、提交、正常轮询、下载和原始JSON保存；Python随后本地导出三种成品。失败不自动重试。同一个job最多启动一次BL；授权和配置检查通过后，再次transcribe只读取原记录，不能删除execution目录绕过保护。

JSON_READY表示JSON可用；documents_ready=true及delivery.status=COMPLETE表示本轮三种成品已保存，Excel/Word回读通过，Markdown写入完成。file路径在delivery.files中。单格式失败会保留其他成功文件；云端已成功不等于成品全部完成。

出现record_error时，保留本次回执：它说明执行记录未保存，之后查看的磁盘状态可能滞后。若本次已经是JSON_READY，原JSON和摘要仍会返回，但本次不生成文档；不要重新识别或自行补写摘要。json_path是本次JSON的目标位置，不能仅凭路径字段判断文件存在或可用。失败阶段和记录错误的解释见[ERRORS](ERRORS.md)。

job-status只读最近本地记录，不查询云端、不确认进程仍存活，也不重新验证文件现在还在不在。进程退出码0不能单独当作完整交付成功；须检查状态字段。

## 本地重导

```powershell
.venv\Scripts\python.exe scripts/asr.py export --job $jobId
```

重导需要保留此任务的确认配置及其摘要、已保存的JSON_READY执行记录，以及原始结果JSON；不需要Key、原音频或原词表。程序先核对任务记录，再读取JSON并比对结果摘要。配置、成功记录或摘要缺失，以及JSON发生变化时停止；仅有一份JSON文件不能导入重导。通过后在新目录生成全部三格式，不覆盖上一轮、不再次识别。

文档位置为已选根目录/job_id/documents/导出编号/，JSON为已选根目录/job_id/json/transcription.json。音轨/说话人保留模型原编号，缺失则显示未标注，不推断真实姓名。

三种成品标题使用“源文件名（不含扩展名） 录音转写”，不再单列音频信息。Excel、Word导出内容使用等线。Excel采用无填充色的黑白表格，顶部标题及模型/任务信息左对齐，第三行直接为表头；表头及序号、音轨、时间、说话人列居中，转写正文左对齐、自动换行。Word使用20磅标题；正文、元信息、时间标签及页码统一等线10磅，1.25倍行距。时间标签用空格分隔、没有圆点，跟随下一段；页码居中。

Excel按正文长度调整展示行高；长文本完整保存在单元格中，超过Excel最大行高的内容可在编辑栏查看。真正的单元格字符数/行数限制仍明确报错，不截断。Markdown转义语法以显示原文，不把转写当作链接/HTML指令执行。

## 文件保留和退出

- 用户原始音频和Excel不修改、不自动删除。
- 正常网页服务退出时，未确认的本机副本被清理；确认后的音频副本保留供执行；热词临时副本可清理，因为词典已存config。
- 关闭浏览器不停止网页服务；在启动终端Ctrl+C才正常退出。转写是独立CLI进程，仍需电脑和该进程持续运行。
- BL等待中断不表示云端任务取消，也不能自动重提；当前没有可靠task_id恢复入口。
- 原JSON、成品和各轮状态保留；中断可能留下partial文件，不把它们当作正式成品。
- 默认运行目录被Git忽略。选择项目内其他未忽略目录可能产生可被Git收录的文件，提交前须检查；程序不自动修改所选位置的Git规则。

问题定位见[状态与错误说明](ERRORS.md)，模型规则见[官方能力依据](REFERENCES.md)。
