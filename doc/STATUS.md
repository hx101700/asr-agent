# 当前状态

更新：2026-10-02。

## 产品与实现

- Windows 10/11 x64；北京地域；固定模型`qwen-audio-3.0-asr-flash-filetrans`；每次处理一个已有音频。
- 本机网页配置，Codex按授权调用BL；热词与上下文可并用，输出原JSON及Excel、Word、Markdown。
- 导出使用任务的固定documents目录；重导更新同名成品，失败保留已有目标。交付记录位于delivery/status.json。
- README与AGENTS提供中英文，网页及导出标签仍为中文。仓库README为转写页面和精度增强保留两处真实截图位置。

## 当前工作

中英文README参考百炼CLI的栏目组织，提供功能特性、Agent安装、快速开始、参与贡献和相关链接。安装入口为将ZIP及安装提示交给Codex，详细操作保留在HELP。发行README的开发文档链接指向GitHub，开发文档保持在源码仓库中。

当前只保留[首版v0.1.0](https://github.com/hx101700/asr-agent/releases/tag/v0.1.0)，本次README补充已推送dev，新附件已更新并完成公开下载验证。发行源码通过v0.1.0标签定位，dev保留最新开发记录。

## 验证与发布

- 固定目录导出代码已有250项Python回归通过，详细范围见[ACCEPTANCE](ACCEPTANCE.md)。
- 当前修改限于文档与发布材料，业务实现及依赖未改。9项打包测试通过；21份Markdown的本地链接、双语README与发行模板一致性、两处截图占位检查通过。
- 发行清单固定为46个文件，开发文档和截图不进入用户ZIP。
- 包`dist/asr-agent.zip`为117526字节，SHA-256：`52df329f00ce40396ed2ca9c9e042bf3508891ad499b104dbf27403cba4ee425`。CRC及逐文件源码核对通过；较上一公开包只改两份发行README。
- 公开下载与本地ZIP逐字节一致，GitHub的中英文README与提交一致；latest指向唯一首版，附件只有一项，发布正文保持当前NOTES。
- 新Codex完整使用、真实云端、原生窗口和Office视觉仍待验收，见[ISSUES](ISSUES.md)。

## 接续

下一步补充用户提供的真实截图，按[ACCEPTANCE](ACCEPTANCE.md)完成新Codex对话的完整使用与人工验收。开始前核对Git工作区和当前发行包；本次文档修订未改变运行逻辑。
