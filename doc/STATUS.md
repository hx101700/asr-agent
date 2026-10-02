# 当前状态

更新：2026-10-02。

## 产品与实现

- Windows 10/11 x64；北京地域；固定模型`qwen-audio-3.0-asr-flash-filetrans`；每次处理一个已有音频。
- 本机网页配置，Codex按授权调用BL；热词与上下文可并用，输出原JSON及Excel、Word、Markdown。
- 导出使用任务的固定documents目录；重导更新同名成品，失败保留已有目标。交付记录位于delivery/status.json。
- README与AGENTS提供中英文，网页及导出标签仍为中文。仓库README为转写页面和精度增强保留两处真实截图位置。

## 当前工作

中英文README按账号准备、Agent安装、快速开始和相关链接组织；安装入口为将ZIP及安装提示交给Codex。详细操作保留在HELP。发布说明介绍首版功能和使用入口，按链接切换语言。

当前只保留[首版v0.1.0](https://github.com/hx101700/asr-agent/releases/tag/v0.1.0)，已更新本次中英文README、发布说明及ZIP附件。发行源码通过v0.1.0标签定位，dev保留最新开发记录。

## 验证与发布

- 固定目录导出代码已有250项Python回归通过，详细范围见[ACCEPTANCE](ACCEPTANCE.md)。
- 当前修改限于文档与发布材料，业务实现及依赖未改。9项打包测试通过；21份Markdown的本地链接、双语README与发行模板一致性、两处截图占位检查通过。
- 发行清单固定为46个文件，开发文档和截图不进入用户ZIP。
- 包`dist/asr-agent.zip`为117071字节，SHA-256：`a324a70f0c2bad3d86ce2c3fd5fd64d98f80d71065d57c6fb20218129d33759e`。CRC及逐文件源码核对通过；较上一公开包只改两份发行README和HELP。
- 公开下载与本地ZIP逐字节一致；发布正文与当前NOTES一致；latest指向v0.1.0，Releases和附件各只有一项。双语文档按Git提交内容核对，本机CRLF与Git的LF差异按文本比较。
- 新Codex完整使用、真实云端、原生窗口和Office视觉仍待验收，见[ISSUES](ISSUES.md)。

## 接续

下一步补充用户提供的真实截图，按[ACCEPTANCE](ACCEPTANCE.md)完成新Codex对话的完整使用与人工验收。开始前核对Git工作区和当前发行包；本次文档修订未改变运行逻辑。
