# S2 本地配置与整改验证

最新核验：2026-09-29。当前只检查并保存本地配置，不调用云端识别。历史界面与修复过程见DEVLOG及Git记录，本文件保留当前复验方法。

## 复验入口

```powershell
.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -t . -q
node tests/test_frontend.mjs
node --check src/asr_agent/static/app.mjs
node --check src/asr_agent/static/model.mjs
node --check src/asr_agent/static/view.mjs
.venv\Scripts\python.exe scripts/asr.py serve --no-browser
```

原生目录窗口需要正常Windows交互桌面，具体启动约束见AGENTS/HELP。服务只绑定127.0.0.1随机独占端口；从启动输出的带会话令牌链接打开。旧app.js/test_web_ui.cjs已被ESM实现和契约测试替换。

## 当前职责与边界

- app.mjs编排事件/API，model.mjs管理状态，view.mjs负责DOM；web.py是HTTP入口，session.py承载用例。
- 音频与Excel通过本机会话upload_id引用；不根据浏览器路径读取原文件。每类只允许一个活动上传，失败不重试。
- 上传先短锁登记，锁外接收，完整后短锁发布；pending时不能预览或确认；关闭后迟到结果不能发布。
- DirectoryPicker只用自己的短控制锁；取消不等待文件I/O。窗口独立进程，取消/5分钟超时会回收，不自动重开。
- 默认输出为项目outputs；外部目录必须由本次原生弹窗登记，不能通过客户端手填路径新增授权。
- 通过受保护POST将指定Key交给只读控件；Key不进Model、普通状态、预览、回执、任务文件或持久存储。
- 配置写入.state/jobs/<job_id>/config.json，CONFIGURED且execution_authorized=false。S3须重新取得云端执行授权。
- Host/Origin/令牌、HttpOnly/SameSite=Strict Cookie、固定静态资源白名单仍有效；不提供任意文件下载或网页目录浏览。
- 文件/词表限制以validation.py及REFERENCES为准，GUI数字约束由session.limits提供；不截断输入或静默丢词。

## 自动化结果

全量134项Python、20项前端Model/Presenter测试通过，无跳过。Python覆盖现有BL本机合约、媒体/Key/输入规则、HTTP防护，以及本轮并发与安装检查回归。前端使用真实Model/Presenter和View/API契约替身，未将其当作浏览器。

新增并发回归验证了慢上传/慢校验期间取消及时完成、同类并发拒绝、不同类独立接收、pending阻止确认、关闭后迟到上传清理、失败替换不恢复旧预览。保存结果未知持续冻结、过期响应被丢弃、Key迟到结果不恢复凭据的回归保留。

## 实际浏览器结果

使用独立会话和合成WAV/Excel，无真实Key或用户音频：

1. number框键入“-”时value为空且badInput为真，明确拒绝并聚焦人数框。
2. 预览后只修改本次合成暂存音频，服务器拒绝确认；表单/音频控件先恢复，焦点正确位于audio-file。之后恢复合成文件。
3. 中文、参考人数3、1个热词、21字符上下文同时预览，保存并刷新恢复同一回执。
4. 落盘recognition_options和both增强正确，execution_authorized仍为false。
5. 重构版页面实际打开目录等待并取消；等待期间表单可编辑，取消后目录按钮恢复。原生路径选择及回填已在先前正常桌面修复中由用户确认。

验收截图位于忽略目录.state/mvp-verified-receipt.png。新的干净预览不覆盖用户旧会话，数据和截图不进入Git。

## 未验证范围

本轮未重新进行干净机安装、真实Key权限、云端上传/识别、三格式导出、原生拖拽回放或大文件压力测试。S3/S4/S5/S6仍按ACCEPTANCE推进，不能把本地配置成功当成转写完成。
