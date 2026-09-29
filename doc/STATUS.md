# 当前状态

更新时间：2026-09-29。S3重复校验已精简，API Key单样本真实云端验收通过；控制台登录及其他云端场景待验，尚未开始S4导出。

## 当前目标与完成情况

在已完成S1/S2基础上接入一次完整BL执行，保持明确上传授权和失败不重试。

- 前端：app.mjs为Presenter，model.mjs管理状态/派生权限，view.mjs处理DOM；无新增框架。
- 后端：web.py只处理HTTP，session.py承载用例，DirectoryPicker独立管理原生窗口与取消。
- 上传：短锁登记、锁外接收、短锁发布；目录取消不等上传/校验；关闭后迟到上传不能发布。
- 清理：删除旧app.js、旧DOM桩测试、废弃CSS、recognition_options模块及allow_super分支；模型规则统一在validation.py。
- S1：doctor核对锁定依赖版本；完整环境跳过pip；BL冲突在修改Python前拒绝；probe覆盖语言、人数和双增强。
- 已统一Key显示、依赖说明、BL本机/云端验证状态与即时热词验收规则。
- 长表单交互：桌面摘要吸顶并避开底部操作栏，长内容内部滚动；填写时显示未校验摘要，提供栏目定位，窄/矮窗口保持文档流。
- S3：transcription.py承担复核、声道准备、一次执行占用和JSON验收；bailian.py只管公开CLI进程，error_catalog.json提供有来源的解释。
- 新命令：login、console-status、transcribe --job ID --authorize-upload、job-status --job ID。启动记录独占且保留，重复执行不会重新提交。
- T33已整改：配置摘要+文件指纹后复用S2快照；argv/环境/Key只准备一次；不再执行前auth status；新FLAC复用转换器返回的实测信息。API Key模式不需要login，已有项目BL凭据直接复用。

## 已确认边界

- Windows 10/11 + Codex；固定qwen-audio-3.0-asr-flash-filetrans、北京、单文件、临时OSS。
- 热词与上下文可并用；发言人区分默认开启，多声道仅在正式执行时生成单声道副本。
- 浏览器只向本机服务传入文件；S2确认保存CONFIGURED且execution_authorized=false。
- 实际转写需用户明确授权具体配置的上传；S3授权另记execution/status.json。正常完成为JSON_READY、documents_ready=false，不冒充三格式交付成功。
- Key由项目.env提供，仅用户选择后在只读控件显示/遮蔽；不进Model、日志或任务配置。
- 输出默认在outputs，也可经原生弹窗登记项目外可写目录；不能由客户端任意路径新增授权。
- BL已有的鉴权、云上传、提交、轮询与下载不由Python重写。
- 原生窗口要求正常Windows交互桌面，遵守AGENTS执行权限规则；可取消，最多等待5分钟，不重开重试。

## 最新验证

- 本轮全量180项Python测试通过，无跳过；20项前端测试通过。受限环境既有连接差异见ISSUES T30，本轮全量使用正常桌面。
- bootstrap返回already_installed，未重复安装；python -S scripts/asr.py --help通过，安装入口保持标准库可加载。
- 真实BL连接127.0.0.1模拟ASR，完整执行入口的JSON成功、空结果与401路径通过；重复调用不增加云端模拟请求。
- 真实BL本地auth status用隔离合成配置验证；无GUI合成等待进程的超时回收通过。真实控制台浏览器登录尚未验收。
- 用户明确授权后，使用项目.env Key、固定模型/北京、单声道样本、说话人开启、无增强，真实执行一次并返回JSON_READY。原音频内容未改、配置摘要一致，实际JSON符合当前句子结构检查；不把这次成功当作所有场景或识别质量通过。
- 真实Session/PyAV覆盖双增强、单双声道、转换后超限、输入变更及关闭网页会话后执行；详见S3_VERIFICATION。
- 既有浏览器布局/交互证据见S2_VERIFICATION，本轮仅更新阶段提示，没有重新进行整页视觉验收。

## 接续与下一步

先读AGENTS、本文件和S3_VERIFICATION，再检查Git与运行服务。旧页面可能仍加载前一阶段文案，不要擅自刷新用户未保存的表单。

下一步可推进S4规范化与三格式导出，复用本次已保存JSON，不重复识别。真实验收统计在被忽略的.state/jobs/*/acceptance-summary.json；由相邻status/config确定本地结果位置，不把原始JSON或正文提交Git。控制台登录、增强/多声道云端场景与质量另按用户选择验收。BL缺task_id、未知子状态等边界见REFERENCES/ISSUES，不删除execution占用记录重提。S5 ZIP/Skill、S6完整验收尚未实施。

整改在dev形成检查点，不推送或合并master；准确提交号以git log为准。数据、凭据、截图和合成结果均不入Git。
