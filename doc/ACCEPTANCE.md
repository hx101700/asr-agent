# 验证记录

日期：2026-10-03。本轮为完整代码、Skill流程、文档和UML审查。上轮界面与真实登录证据保存在[该提交的验收记录](https://github.com/hx101700/memoflow/blob/fa5c27f/doc/ACCEPTANCE.md)，本页仅记录本轮实际执行。

## 发现与修正

默认保存位置被普通文件占用时，原实现把文件当作目录窗口起点，窗口在启动前被拒绝。回归先复现该错误，再验证修改后的行为：被占用的默认位置、被替换的旧目录和已删除位置均可从工作目录重新选择，原有文件保留。

删除没有生产调用者的目录请求编号回退、后端中文语言标签、前端转调函数与旧超时说明。Skill明确条件分支和一次transcribe的完整交付职责。审查判断及保留依据见[REVIEW](REVIEW.md)。

## 已执行检查

| 检查 | 实际结果 |
| --- | --- |
| 初始Python回归 | 294项运行成功，15项跳过；当时独立BL/pip合约环境尚未准备，不计作完整通过 |
| 独立联网安装 | 在新建 `.runtime/skill-contract-workspace` 执行bootstrap成功；测速后选择阿里云镜像，pip 26.2.1及8个Python依赖摘要验证、安装成功，npm安装锁定BL 2.1.0成功 |
| 独立环境doctor | CPython 3.12.1 x64、Node 24.19.0、BL 2.1.0及锁定Python依赖可用，`issues=[]` |
| 最终Python回归 | `unittest discover -s tests -t .`：313项通过，无跳过项；包括真实BL与本机模拟服务、pip断流续传与错误摘要拒绝、媒体、文档、HTTP和打包检查 |
| Python类型 | `mypy --config-file mypy.ini`：严格检查29个源码文件通过 |
| 前端单元 | `npm run test:web`：34项通过 |
| 前端构建 | `npm run build:web`：Vue类型检查及Vite构建通过 |
| Edge本机集成 | `npm run test:browser`：1项通过，覆盖双语、主题、音频选择、指定语言、Key保存、热词与上下文、目录摘要滚动、配置确认和刷新恢复；只访问本机服务 |
| 登录与BL边界 | 全文核对项目适配和固定BL 2.1.0登录/状态代码；登录后状态读取、完整备用链接及失败子任务产物检查有具体消费者，本轮未新增登录流程 |
| Skill格式 | 官方skill-creator的quick_validate通过；校验所需PyYAML仅放在本轮临时目录 |
| Skill决策推演 | 独立评审安装完成、已有成功登录回执、转写及文档已完成三个场景，均直接衔接下一步，未追加诊断、重复登录或自动重导；属于只读指令评审 |

Node测试与Vite在受限执行环境曾遇到`spawn EPERM`，通过执行工具权限机制在正常本机权限下运行后通过。没有因此改动产品代码或测试断言。

## 复现入口

在开发仓库准备好 `.venv` 与根 `npm ci` 依赖后运行：

```powershell
.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -t .
.venv\Scripts\python.exe -B -X utf8 -m mypy --config-file mypy.ini
npm run test:web
npm run build:web
npm run test:browser
```

BL/pip合约使用专用的 `.runtime/skill-contract-workspace`，首次须建立该目录，以 Skill 入口绝对路径和明确 `--workspace` 执行bootstrap；缺少环境时相关检查会跳过。合约服务绑定127.0.0.1，使用合成输入和凭据。浏览器测试自行创建并清理临时工作目录，不操作用户页面。

## 文档、图稿与发行包

全文核对Skill、references、双语README/AGENTS、开发文档、发布说明及全部10份UML图源。图03同步语言列表和目录起点，图07明确BL执行或结果读取失败；使用校验过官方包摘要的Mermaid 11.12.0重绘为PNG并查看，核对说明文本和画布边界，修正原图说明换行溢出。

已发布ZIP包含43个文件，279753字节，SHA-256：`55c20cac17bb9b0dba5e91be86ff4a20778bcdd25980e399ecc1d41798d33c39`。固定清单、CRC、与当前Skill源码逐文件字节比对通过。解压后的入口使用本轮独立环境运行doctor，`issues=[]`。运行环境、测试、开发文档、UML和用户数据均不入包。

实现提交`96eda6e`已推送到dev，同一v0.1.0预览的附件和双语发布说明已更新。远端完整源码树的130个文件与本地提交一致；公开ZIP匿名下载后逐字节一致。核对为一个Release、一个标签、一个ZIP附件，master保持`6c83711`。发布记录单独提交，用户README修改保留在本地。

## 验证边界

本轮没有使用真实录音、真实Key或云端识别。BL、媒体和文档合约是本机测试，不能代替识别准确率、原生目录窗口可见性或Office逐页视觉验收。Skill流程审查也不能冒充新Codex对话的实际操作。

用户录音、配置、凭据、历史结果和正在编辑的README保持原样；这些私有运行资料不提交、不打包。已有Skill安装副本未自动覆盖。
