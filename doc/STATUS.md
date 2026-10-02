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

完整回归及独立环境验收已完成：解压源码267项Python检查无跳过通过，前端24项通过；新工作目录联网准备成功。发行ZIP共42个文件、107802字节，SHA-256：`ab9835fd40c52ea0fe7461ae3dbe233208b5e459d7217b4969cd49ad253f7643`，清单、CRC、源码及包边界核对通过。具体范围见[ACCEPTANCE](ACCEPTANCE.md)。

已按用户要求替换现有[v0.1.0](https://github.com/hx101700/asr-agent/releases/tag/v0.1.0)，运行代码提交`9e6f739dd424bab6d4f10273186c212f587a8246`已推送dev。新版附件为[asr-transcription.zip](https://github.com/hx101700/asr-agent/releases/download/v0.1.0/asr-transcription.zip)，旧附件已删除；公开下载与本地文件逐字节一致，发布说明及中英文入口已核对。未新建版本，master保持`6c8371135d92b9f9d3bd52ca9ee246747f0c7f5e`，未合并本次改动。

## 接续

先核对Git与本文件，沿[DEVELOPMENT](DEVELOPMENT.md)了解职责与协议；实际限制见[ISSUES](ISSUES.md)。使用入口为Skill内SKILL.md；开发脚本、测试和UML不进入用户ZIP。
