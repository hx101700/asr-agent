# 代码审查

日期：2026-10-03。范围为本仓库维护的Skill源码、依赖声明、开发脚本、相关测试、使用文档及UML。采用全文阅读、沿调用者追踪数据和写入位置、合成复现与回归验证；检索仅用于修改后的引用核对。

## 阅读覆盖

代码路径相对于`skills/asr-transcription/`。25个Python文件中的130个命名函数/方法均纳入职责与调用链检查。

| 范围 | 完整阅读的文件 |
| --- | --- |
| 入口与共享定义 | scripts/asr.py；asr_transcription下的__init__.py、__main__.py、models.py、error_catalog.json |
| 应用用例 | application下的__init__、bootstrap、diagnostics、inputs、rules、session、transcription、delivery |
| 本机能力 | utils下的__init__、environment、auth、bailian、files、job_files、results、media、hotwords、documents、directory_picker、_directory_dialog |
| 网页 | web.py；static下的index.html、app.css、app.mjs、model.mjs、view.mjs、api.mjs |
| 技能与依赖 | SKILL.md、agents/openai.yaml、assets/env.example、references全部；scripts/requirements.txt、bailian/package.json和package-lock.json全部锁项 |
| 开发与交付 | scripts/build_zip.py、probe_bl.py；README/AGENTS双语、doc全部Markdown、9份UML源稿与图、Release说明；运行、权限、媒体、文档、HTTP、前端和打包相关测试 |

第三方BL及Python依赖按锁定版本使用。本审查核对其公开接口、安装边界和实际调用，不把对项目源码的审查称为第三方全部代码审计。

## 职责判断

保留一个录音转写Skill。它是一个明确用户任务，Codex负责流程选择与授权；utils/bailian.py是官方CLI适配模块，映射参数、准备子进程、解释错误。BL负责鉴权、临时上传、提交、轮询和结果下载。本机JSON解析与文档排版由本项目完成。

现在没有第二项独立BL业务用例需要跨Skill交接认证或工作目录。出现真实的新用例时，再根据共同消费者提取共享调用代码；不为未知能力增加通用Agent、动态工具注册或新的云客户端。

utils是Python包内的能力分组。application协调步骤，utils执行具体操作；没有反向导入用例。通用安装/诊断进程与BL进程在凭据、输出和生命周期上不同，保持各自入口有实际依据。

## 写入与执行边界

| 场景 | 复现与处理 |
| --- | --- |
| 私有运行目录与Skill重叠 | 可用普通目录布局复现prepare在资源区写文件；Runtime现在在构造及解析运行根时拒绝两者任意方向重叠，常规项目内Skill布局仍可用 |
| 原生选择Skill为输出目录 | 先前原生选择可触发资源区写探针；现在选择探测前、预览和最终JSON/文档创建前复用check_output_path拒绝，保留用户选择其它目录的能力 |
| 工作目录同名Python模块 | json.py/sysconfig.py可被检查或安装子进程加载；版本检查、依赖检查、ensurepip和pip使用-I，真实子进程回归确认这些工作目录文件不执行 |
| 凭据与上传 | Key只读工作目录私有.env；console独立使用BL配置；网页保存与云端执行授权分开，失败不自动重试 |
| 文件与原文 | 上传由会话ID引用；预览/确认/执行的摘要用途各不重复；导出失败保留已有目标，记录失败保留当次已知事实 |

这些是本工具入口的路径和进程约束，不代替Windows文件系统ACL；本地管理员仍拥有操作系统授予的权限。调用时若操作系统拒绝写入，程序报告实际失败，不修改系统权限。

## 变量与接口

- Runtime.workspace是用户工作目录，skill_root是程序资源；root是私有运行目录，output_root是默认结果位置。
- audio_tracks/channel_id描述音轨，channels描述音轨内声道；单声道转换使用已确认AudioInfo，没有混用。
- config是已确认输入，execution是执行记录，delivery是文档交付。job-status读取记录，不能表示云端实时状态或进程仍存活。
- export_documents(runtime, config, transcript)自行派生任务目录，避免调用者同时传入可能不一致的运行上下文与任务根。
- result_path(config)负责解析和读取位置；实际写入位置在prepare_result/prepare_documents检查，不增加重复写权限层。

## 验证

针对性复现、安装、完整回归与发行核对的实际结果集中记录在[ACCEPTANCE](ACCEPTANCE.md)。未覆盖的真实云端、原生桌面和Office人工场景见[ISSUES](ISSUES.md)。
