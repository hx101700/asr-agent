# 当前状态

更新：2026-10-02。

## 产品与实现

- Windows 10/11 x64；北京地域；固定模型`qwen-audio-3.0-asr-flash-filetrans`；每次处理一个已有音频。
- 本机网页配置，Codex按授权调用BL；热词与上下文可并用，输出原JSON及Excel、Word、Markdown。
- 导出使用任务的固定documents目录；重导更新同名成品，失败保留已有目标。交付记录位于delivery/status.json。
- README与AGENTS提供中英文，网页及导出标签仍为中文。仓库README为转写页面和精度增强保留两处真实截图位置。

## 当前工作

用户发行包与开发工程已分离：ZIP直接包含项目入口文件，解压目录即项目根目录；安装指令放发行AGENTS与HELP，Skill只负责转写与重新导出。开发探针移到scripts/probe_bl.py，不进入用户命令入口或ZIP。

当前只保留[首版v0.1.0](https://github.com/hx101700/asr-agent/releases/tag/v0.1.0)。本次发行边界修正与新包核对已完成，尚待同步源码及附件。

## 验证与发布

- 当前252项Python回归通过，包含开发探针入口边界与扁平ZIP解压后的入口、导入和文档链接检查，详细范围见[ACCEPTANCE](ACCEPTANCE.md)。
- ASR与导出流程保持既有实现；本次改变开发命令边界、指令分工和ZIP布局。转写UML已同步删除开发探针附注并重新渲染。
- 发行清单固定为46个文件，开发文档和截图不进入用户ZIP。
- 新包为114495字节，SHA-256：`9eaeebc7a429abe277a67ea6ecaa53b04da21ab53538e622b7edda621949906d`。文件清单、CRC、源码一致性、扁平入口与相对链接核对通过，尚待上传。
- 新Codex完整使用、真实云端、原生窗口和Office视觉仍待验收，见[ISSUES](ISSUES.md)。

## 接续

下一步补充用户提供的真实截图，按[ACCEPTANCE](ACCEPTANCE.md)完成新Codex对话的完整使用与人工验收。开始前核对Git工作区和当前发行包；本次文档修订未改变运行逻辑。
