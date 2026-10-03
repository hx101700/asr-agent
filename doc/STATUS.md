# 当前状态

更新：2026-10-03。

## 产品与入口

MemoFlow第一阶段由独立的`asr-transcription` Skill完成单个录音的本机网页配置、BL识别和JSON、Word、Excel、Markdown交付。个性化会议纪要及反馈学习尚未实现。

入口为`skills/asr-transcription/scripts/asr.py`，执行包为`asr_runtime/`；Python保持入口 → application → utils，前端为Vue、TypeScript、Element Plus。版本仍为0.1.0，开发分支dev，master保持`6c83711`。

## 本轮修复

核对用户实际对话的两次login调用：首次使用默认受限权限，重试才使用`require_escalated`。Windows令牌对照检查也确认两种执行方式不同；用户没有改动浏览器配置。

- Skill从首次login就要求使用执行工具提供的正常桌面权限。Python在启动BL前检查Windows限制SID，发现受限令牌即返回可操作错误，避免先尝试打开Chrome。
- BL 2.1.0的Windows开页调用会被cmd拆开含`&`的URL。仅在控制台登录进程预加载小型适配，将这次调用交给BL已有的完整链接出口，Python通过系统URL处理器打开一次。BL授权会话、回调及凭据保存保持原生实现。
- 移除项目叠加的登录总等待上限，以及“使用最后打开页面”的提示。BL自身的会话有效期仍由上游管理。

运行回归318项、针对性登录/BL/打包47项、29个Python文件的严格类型检查和登录适配编译均通过。真实BL回调测试确认一个完整URL、原生cmd开页未执行、合成凭据由BL保存；测试没有启动真实浏览器。桌面验证与交付结果见[ACCEPTANCE](ACCEPTANCE.md)。

## 凭据与登录结论

控制台模式由BL保存模型Key与控制台凭据；指定Key模式由网页保存至私有.env。配置存在不保证云端仍接受。本轮独立桌面登录进程已结束，BL回执未保存模型或控制台凭据；未收到本次窗口表现的用户确认，因此不记为真实登录通过。不触及用户原工作目录的凭据，不调用云端识别。

已确认失败与重试的执行权限差异、BL拆参及二次开页路径；没有取得Chrome内部崩溃转储，不能把`0x80000003`概括为所有机器上的同一原因。令牌检查只阻止本次观察到的受限执行路径。

## 用户工作与测试边界

用户测试工作目录及`.runtime/browser-startup-case/work`含用户录音和设置，保持原样；用户级Skill副本不自动覆盖。README.md的用户本地修改保留且不暂存。本轮测试与临时渲染材料位于`.runtime/`，不进入Git或ZIP。

## 交付状态

本轮尚未发布。登录UML源稿与PNG已同步；待构建ZIP并更新同一[v0.1.0预览](https://github.com/hx101700/memoflow/releases/tag/v0.1.0)。版本号与master保持不变；旧包不包含本轮修复，用户级Skill副本也尚未更新。
