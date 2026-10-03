# 当前状态

更新：2026-10-04。

## 产品与入口

MemoFlow第一阶段由独立的asr-transcription Skill完成单录音网页配置、BL识别，以及JSON、Word、Excel和Markdown交付。个性化纪要与反馈学习尚未实现。

新识别固定使用qwen-audio-3.1-asr-flash-filetrans，北京地域，BL固定2.1.0。入口为skills/asr-transcription/scripts/asr.py；Python保持入口 → application → utils，前端采用Vue、TypeScript和Element Plus。开发分支dev，版本0.1.0，master保持6c83711。

## 本轮工作

- 按用户要求删除ZIP自更新功能。脚本、Skill触发、参考说明、入口文件占用、专用测试和更新时序图已移除；打包清单删除相应两项资源。
- 重新全文审查业务后端、安装与本机工具、全部前端源码、说明和UML；按消费者和调用顺序核对，没有新增框架、依赖、兼容入口或防御层。
- 修正DEVELOPMENT把热词Excel导入泛化为返回upload_id的旧表述，将该行限定为音频；删除相邻的重复模板说明。
- 当前Skill聚焦新录音、凭据配置和已有任务查询/重导。原安装流程保留，前端无需改动。

## 验证与边界

346项Python完整回归通过，无跳过；原更新功能的16项测试随功能删除。49项前端测试、严格mypy的29个源文件、Vue类型检查、构建及合成数据Edge回归通过。构建前后5个前端产物逐字节未变。独立合成用例验证导入、联合增强、确认、撤回、转写交付与本地重导；BL边界使用替身，未联网识别。详见[ACCEPTANCE](ACCEPTANCE.md)。

本轮未进行真实云端识别、登录授权、原生目录窗口人工操作、Office逐页检查或全新联网安装。用户已安装Skill、真实工作目录及README原有本地修改保持原样。

## 交付状态

实现提交`332fbe2`已推送dev，现有[v0.1.0预览](https://github.com/hx101700/memoflow/releases/tag/v0.1.0)的ZIP与双语说明已同步。master与版本号保持不变。

ZIP含44文件、327364字节，SHA-256为`a839b2f2aedebf2c6b42a94b8ce812a2a33fbe89340ea8f377c786c36780abab`；CRC、固定清单及源码逐文件字节比对通过，124个本地Markdown链接有效。匿名公开下载与本机包逐字节一致，135文件的远端源码树与实现提交一致。远端保持一个Release、一个标签和一个ZIP附件；本轮合成探针临时目录已清理，已安装Skill和用户数据保持原样。
