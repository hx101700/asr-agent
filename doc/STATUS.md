# 当前状态

更新：2026-10-03。

## 产品

asr-transcription是单录音转写Skill，支持网页配置、热词与上下文、说话人区分，固定通过BL2.1.0调用北京地域qwen-audio-3.0-asr-flash-filetrans，交付原始JSON、Word、Excel和Markdown供用户校对。会议总结属于后续阶段。

## 实现

- Skill源位于skills/asr-transcription，代码按入口→application→utils组织。BL保持公开CLI适配模块，不另设BL Skill。
- 用户工作目录显式传入--workspace；程序资源、私有运行目录与输出位置有明确边界。
- 运行根与Skill重叠、原生选择/默认及最终输出写入Skill均被拒绝；Python检查和安装进程使用-I隔离工作目录模块。
- 源码、配置、文档和9份UML已逐文件阅读，审查依据见[REVIEW](REVIEW.md)。

## 验证与发布

完整回归及独立环境验收已完成：解压源码267项Python检查无跳过通过，前端24项通过；新工作目录联网准备成功。候选ZIP共42个文件、107802字节，SHA-256：`ab9835fd40c52ea0fe7461ae3dbe233208b5e459d7217b4969cd49ad253f7643`，清单、CRC、源码及包边界核对通过。具体范围见[ACCEPTANCE](ACCEPTANCE.md)。

按用户要求替换现有v0.1.0并推送dev，master保留原状态。尚未执行本轮远端更新，发布完成后记录源码提交、附件摘要与公开下载结果。

## 接续

先核对Git与本文件，沿[DEVELOPMENT](DEVELOPMENT.md)了解职责与协议；实际限制见[ISSUES](ISSUES.md)。使用入口为Skill内SKILL.md；开发脚本、测试和UML不进入用户ZIP。
