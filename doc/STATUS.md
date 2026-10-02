# 当前状态

更新：2026-10-02。

## 产品与实现

- Windows 10/11 x64；北京地域；固定模型`qwen-audio-3.0-asr-flash-filetrans`；每次处理一个已有音频。
- 本机网页配置，Codex按授权调用BL；热词与上下文可并用，输出原JSON及Excel、Word、Markdown。
- 用例与工具按application/tools分离，执行与导出分别记录状态。模块和协议见[DEVELOPMENT](DEVELOPMENT.md)。
- README与AGENTS提供中英文，网页及导出标签仍为中文。README的三处真实截图等待用户补充。

## 当前工作

[v0.1.1](https://github.com/hx101700/asr-agent/releases/tag/v0.1.1)已发布：导出文档直接保存到任务的固定`documents`目录；显式重新导出替换三个同名成品，失败保留已有目标。删除导出编号、历史目录排序及重复摘要字段，只保留一份`delivery/status.json`。实现提交为`0dcc06cfdb30b8e4f0b36d2eaf19b21926e6c88e`，发布说明位于[中文](../release/NOTES.md)和[English](../release/NOTES.en.md)。

中英文使用文档、Agent规则和相关UML已同步。原JSON来源检查与一次识别占用保持不变；旧导出文件不自动清理。[当前安装包](https://github.com/hx101700/asr-agent/releases/download/v0.1.1/asr-agent.zip)对应v0.1.1，v0.1.0保留为历史发布。

README已补充阿里云百炼介绍、控制台、官方文档及BL CLI源码入口。发布说明按中英文分文件维护，中文Release通过English链接打开对应版本的英文说明；英文页面可返回中文发布页面。

## 验证与发布

- 既有代码回归、独立安装和本机网页检查的证据见[ACCEPTANCE](ACCEPTANCE.md)。
- 新Codex完整使用、真实云端、原生窗口和Office视觉验收仍待完成，详见[ISSUES](ISSUES.md)。
- 发行清单固定为46个文件：运行代码、项目Skill、依赖锁、中英文README/AGENTS及必要使用文档。
- 本地ZIP已构建并核对，路径为`dist/asr-agent.zip`，大小119445字节。内部校验SHA-256：`ebc3d156517bcf369818c9d0ccd53f115854341fd8d2c8c013ca1d7437ffcec1`。
- 59项导出相关检查与250项全量Python回归通过；双语文档、Skill和包内链接检查通过。ZIP的CRC及当前源文件逐字节比较通过。
- 三张受影响的UML图已重新渲染并查看；运行代码及使用文档中没有旧轮次实现残留。
- 上游说明与语言切换更新后，9项打包测试及文档链接检查通过；与前一份固定目录包相比，仅两份发行README内容变化。
- 发布标签v0.1.1指向`0a108cfc840308a0908ecb9f5cf0f8e2b0089593`。公开附件下载与本地ZIP逐字节一致；两个Release的语言入口及对应英文文件已核对，latest指向v0.1.1。

## 接续

源码在dev维护，发行代码通过版本标签定位。核对实际Git分支、工作区与Release附件后继续工作，使用本节摘要核对安装包。

版本发布完成，后续按具体功能变更继续开发；维护发布说明时同步语言入口及对应版本的英文文件。

独立复测使用空目录，不复用旧凭据或任务；原始data与开发环境保留。正常使用按HELP进行，评审按ACCEPTANCE的范围进行。
