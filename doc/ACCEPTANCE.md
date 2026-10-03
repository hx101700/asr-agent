# 验证记录

日期：2026-10-03。本轮以人工源码复核和Skill指令优化为主。此前完整回归和独立联网安装的实际结果保存在[上一轮记录](https://github.com/hx101700/memoflow/blob/52d5d91/doc/ACCEPTANCE.md)，不重复计为本轮执行。

## 人工审查依据

全文阅读运行Python与前端实现，并沿用户操作追踪调用；固定BL登录、状态、凭据解析和配置写入代码，以及python-docx核心元数据setter用于核对外部边界。没有以旧自动检测脚本或上轮结论替代源码分析。

发现合法长文件名的Word失败链：上传允许255字符；标题追加“ 录音转写”后可达256；python-docx的core_properties.title拒绝超过255。使用实际write_docx和一段本机固定文本最小复现，得到`exceeded 255 char limit for property`。删除可选元数据赋值后，完整正文标题回读通过。

Skill参考官方格式及OpenAI的transcribe、gh-fix-ci范例，仅借鉴触发范围、脚本入口、外部CLI边界和按需引用；没有采用其模型、默认参数或不适用的审批/重试步骤。来源和具体取舍在[REVIEW](REVIEW.md)。

## 本轮已执行检查

| 检查 | 实际结果 |
| --- | --- |
| Word最小复现 | 修正前实际调用失败；修正后新增长文件名回归通过，正文标题256字符完整保留 |
| 文档、交付、打包 | `unittest tests.test_documents tests.test_delivery tests.test_package`：46项通过 |
| Python类型 | mypy严格检查29个源码文件通过 |
| 前端单元 | 38项通过，包含无音频保存Key、失败保留输入、避免重复保存及后续检查复用 |
| 前端构建 | Vue类型检查与Vite构建通过 |
| Edge本机集成 | 1项通过；合成Key第一次保存被模拟拒绝，用户动作再次保存成功；此前无音频上传、预览/确认请求和任务目录，后续完整配置保持正常 |
| BL原生命令 | 用固定BL 2.1.0在新隔离目录设置合成模型Key与console token，再运行config set空Key；auth status确认仅模型Key消失、console保留。Python参数数组及实际PowerShell命令均通过 |
| Skill格式 | 官方quick_validate通过；格式验证用于补充检查，不代替行为审查 |
| Skill情境推演 | 新录音、已有任务、成功交付、两种鉴权失败及不应触发的文字纪要请求；发现只换Key原先需录音的缺口，修正后独立复评确认无需创建任务。此项为只读决策评审 |
| UML | 图04用Mermaid 11.12.0重绘并查看，官方包摘要已校验，说明框与画布边界核对通过 |

Node工具首次受限运行出现spawn EPERM，按执行工具权限机制重跑通过；没有因此改动产品业务或测试断言。

## 复现入口

开发环境依赖准备完毕后：

```powershell
.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_documents tests.test_delivery tests.test_package
.venv\Scripts\python.exe -B -X utf8 -m mypy --config-file mypy.ini
npm run test:web
npm run build:web
npm run test:browser
```

完整Python回归仍可用`unittest discover -s tests -t .`；BL/pip合约需要先在`.runtime/skill-contract-workspace`准备锁定环境。最新全量运行证据见上轮记录，本轮仅重跑与改动相关的检查。

## 发行与限制

候选ZIP为43个Skill文件、284228字节，SHA-256：`b993414b7554f2183d62c15a2d94d40b74a045c9c6b1569b53aa3326da56c22c`。固定清单、CRC和源码逐文件字节比对通过；公开下载结果在发布后记录。开发文档、UML、测试、安装环境、录音、凭据与结果不入包。

本轮没有读取真实凭据、使用真实录音或调用云端识别。保存Key只说明本机文件已更新，BL本机状态不代表云端权限验证；真实登录、识别准确率和Office逐页视觉不计为本轮通过。
