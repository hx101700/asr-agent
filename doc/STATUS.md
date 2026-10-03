# 当前状态

更新：2026-10-04。

## 产品与入口

MemoFlow第一阶段由独立的asr-transcription Skill完成单录音网页配置、BL识别，以及JSON、Word、Excel和Markdown交付。个性化纪要与反馈学习尚未实现。

新识别固定使用qwen-audio-3.1-asr-flash-filetrans，北京地域，BL固定2.1.0。入口为skills/asr-transcription/scripts/asr.py；Python保持入口 → application → utils，前端采用Vue、TypeScript和Element Plus。开发分支dev，版本0.1.0，master保持6c83711。

## 本轮修正

- 用户IPO样表第2—5行完全重复，第3行另有非法权重。现为全部重复行生成text错误，包括首行、同权重和权重非法的行；程序不自动合并，用户决定保留哪一行。
- 官方词表SDK文档的prefix限制与text分开核对；未找到禁止IPO英文缩写的规则。重复拒绝属于本项目的明确输入要求。
- 新配置与新识别采用3.1；BL本机合约确认新模型、增强参数及最小parameters对象正确。
- 文档writer显式接收config.model。历史成功JSON可重导并保留原模型标签；其它模型的待执行配置须重新确认，原配置和摘要不改写。

## 验证与边界

353项Python完整回归通过，无跳过；严格mypy检查30个源码文件，Vue类型检查和前端构建通过。合成和实际IPO样表分别通过完整Edge回归，包括整组标红、用户删行、保存刷新及撤回恢复；原Excel摘要未改变。UML已同步受影响的模型与交付边界，详细证据见[ACCEPTANCE](ACCEPTANCE.md)。

本轮只使用BL与本机模拟服务验证请求，没有调用真实3.1云端识别。用户工作目录、已安装Skill和README本地修改保留。

## 交付状态

实现提交`ea65458`已推送dev，图稿与代码同步，同一[v0.1.0预览](https://github.com/hx101700/memoflow/releases/tag/v0.1.0)及双语说明已更新；master和版本号保持不变。

公开ZIP含46个文件、332378字节，SHA-256为`c0731d710f166d10337f43777f6901a615996f373916fde79d1608b2209dbaf1`。匿名公开下载与本地包逐字节一致；140文件的远端源码树与实现提交一致。远端仍为一个Release、一个标签和一个ZIP附件。发行包仅含Skill运行资源和按需参考资料，本轮未覆盖用户已安装副本。
