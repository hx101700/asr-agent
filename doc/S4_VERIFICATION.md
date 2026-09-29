# S4 文档导出验证

核验日期：2026-09-29。三格式导出实现和内容验收通过；Excel已渲染检查，Word逐页视觉验收未完成。没有新的音频上传或识别调用，不把本阶段记录当成S6完整验收。

## 实现与使用

| 模块 | 职责 |
| --- | --- |
| results.py | 官方JSON的唯一解析边界，保留全部音轨的句子顺序、空句、毫秒时间和原文；不猜别名 |
| documents.py | Excel、Word、Markdown独立写入与内容回读，不接触凭据或云端 |
| delivery.py | 新目录隔离每轮导出，partial文件通过核验后发布，逐项保存成功/失败 |
| transcription.py | 首次转写成功后导出一次；export显式重导已有JSON；job-status读取最近记录 |

入口：`python scripts/asr.py export --job <设置编号>`。不需要`--authorize-upload`，不读取Key、原音频或热词，不调用BL。返回本次调用自己的导出编号和文件路径；job-status读取最新发起轮。重导全部三格式，不覆盖历史，不自动重试。

BL2.1.0的`speech recognize --help`已本机核验，公开`--out`保存完整JSON；没有文档格式选择入口。Python不重复云端轮询、下载或保存原JSON。新增python-docx1.2.0及其必要lxml6.1.3、typing-extensions4.16.0依赖，Windows CPython3.12 wheel版本与哈希锁定；Excel复用openpyxl3.1.5。

## 已执行验证

| 验证项 | 实际结果 |
| --- | --- |
| bootstrap及安装入口 | 初次PyPI下载超时并停止；人工诊断后将本次pip下载等待调为60秒、仍retries=0，安装成功；随后bootstrap返回already_installed。`python -S scripts/asr.py --help`通过 |
| Python全量 | 正常桌面环境运行218项，全部通过，无跳过，日志只在.runtime/s4-tests.log |
| 前端回归 | 20项全部通过，无跳过。受限环境Node测试器spawn返回EPERM，正常执行环境通过，未改测试规避 |
| 内容保真 | 三格式回读段落顺序、文字、时间和标签；含0号标签、无标签、多音轨、空句、中文、emoji、CR/LF/tab及长文本 |
| 不可信文字 | Excel公式样式正文按字符串写入；Markdown链接、图像及HTML语法被转义，不重写识别文字 |
| 部分失败 | Word失败后其余格式仍完成一次；识别结果仍为JSON_READY/result_received；重复transcribe不重新导出/识别 |
| 记录写入故障 | 保存导出记录失败仍返回已有JSON及交付结果未知，不冒充识别失败 |
| 并发/重导 | 每轮独立目录，命令返回自己的回执；显式重导保留旧文件；最新记录损坏不退回旧成功记录冒充完整交付 |
| 配置/结果变化 | 配置摘要沿用原规则；S4已记录摘要的JSON被修改后停止导出 |

## 已有真实结果验收

复用联合增强验收的既有JSON，未重新识别。实际输出329段、11,305字符，三种文件均生成；再独立提取Excel单元格、Word正文段落及Markdown转义正文逐段对照原JSON，全部一致。原JSON摘要未改变，临时file_url未复制到成品。统计和文件路径仅存于被忽略的.state/s4-qa及任务导出记录；真实正文、文件和截图不进入Git。

Excel共一个转写明细工作表，已用独立渲染工具检查开头、最长句所在行及末尾，中文、时间显示和长句换行可读；这不等于已在用户的桌面Excel内验收所有兼容行为。

Word已通过python-docx重新打开、完整段落和标签比对；样式及分页属性有合成回归。调用文档技能的render_docx.py时，首个错误为`LibreOffice soffice.exe was not found on PATH`；工具包也没有提供Windows LibreOffice路径。后续临时目录清理另有权限错误，不把它误诊为文档损坏。没有生成页面PNG，**Word逐页视觉验收仍未通过**，见ISSUES的T35。未为验收安装全局Office或改变系统PATH。

## 限制与后续

- `documents_ready=true`是三种文件写入及内容核验状态；不表示识别准确率、真实说话人人数或开发期视觉验收已证明。
- Excel超过单元格字符数/行数限制或本地估算的可展示行高时明确失败，不截断；Word/XML不可表示的控制字符只使对应格式失败。
- 不承诺中断导出自动恢复。partial文件可能保留，不作为成品；显式export新建一轮。
- 历史S3结果没有JSON摘要时仍须通过结构检查，当前导出记录绑定本轮摘要；不改写旧JSON或执行记录。
- 下一步先补Word逐页视觉验收，再推进S5技能/ZIP；多声道云端和S6整体流程仍未完成。
