# 当前状态

更新：2026-10-02。

## 产品与实现

- Windows 10/11 x64；北京地域；固定模型`qwen-audio-3.0-asr-flash-filetrans`；每次处理一个已有音频。
- 本机网页配置，Codex按授权调用BL；热词与上下文可并用，输出原JSON及Excel、Word、Markdown。
- 用例与工具按application/tools分离，执行与导出分别记录状态。模块和协议见[DEVELOPMENT](DEVELOPMENT.md)。
- README与AGENTS提供中英文，网页及导出标签仍为中文。README的三处真实截图等待用户补充。

## 当前工作

首个版本[v0.1.0](https://github.com/hx101700/asr-agent/releases/tag/v0.1.0)已发布，当前Releases仅保留这一版本。发布说明位于[release/NOTES.md](../release/NOTES.md)，[安装包可直接下载](https://github.com/hx101700/asr-agent/releases/download/v0.1.0/asr-agent.zip)。

发布说明仅包含用户可见功能和安装入口；开发验证集中在[ACCEPTANCE](ACCEPTANCE.md)。业务代码未改。

## 验证与发布

- 既有代码回归、独立安装和本机网页检查的证据见[ACCEPTANCE](ACCEPTANCE.md)。
- 新Codex完整使用、真实云端、原生窗口和Office视觉验收仍待完成，详见[ISSUES](ISSUES.md)。
- 发行清单固定为46个文件：运行代码、项目Skill、依赖锁、中英文README/AGENTS及必要使用文档。
- 本地ZIP已构建并核对，路径为`dist/asr-agent.zip`，大小118434字节。内部校验SHA-256：`de6fe64e89181f18e6ee5a8216cd7707c326321cd29c06e4779ea28a1cc8c871`。
- 文档整理后9项打包测试通过；20份Markdown及双语链接、代码字面量、Skill元信息检查通过。ZIP与当前发行源文件一致，变更均为Markdown内容。
- 发布标签`v0.1.0`对应源码`07c60975a1ec5455d972654886ffdb6ed0df2e04`。已从公开链接下载附件并逐字节核对，与本地ZIP一致。

## 接续

源码在dev维护，发行代码通过版本标签定位。核对实际Git分支、工作区与Release附件后继续工作，使用本节摘要核对安装包。

独立复测使用空目录，不复用旧凭据或任务；原始data与开发环境保留。正常使用按HELP进行，评审按ACCEPTANCE的范围进行。
