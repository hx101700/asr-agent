# S1 环境与能力验证记录

更新时间：2026-09-28。当前状态：**S1进行中，已完成本地基础工具与BL本机合约验证；媒体安装和真实鉴权未完成。**

## 本轮范围

只编写环境检查、项目内安装与探针。没有用户转写入口、Web页面、Excel热词导入或三种文档导出；没有用Python重写百炼上传、轮询、下载或鉴权协议。

## 已实现入口

在项目根目录执行，命令返回UTF-8 JSON；成功返回0，环境问题/失败返回1。

| 命令 | 行为 | 当前证据 |
| --- | --- | --- |
| `python scripts/asr.py bootstrap` | 检查现有Python/Node；创建无pip的本地venv；npm ci安装锁定BL | 已安装；再次执行返回already_installed并实际检查BL入口 |
| `.venv\Scripts\python.exe scripts/asr.py doctor` | 检查版本、BL实际启动及媒体工具路径；不读取凭据 | 本机正确报告FFmpeg/ffprobe缺失并返回1 |
| `.venv\Scripts\python.exe scripts/asr.py probe-bl` | 读取公开帮助，用固定example.invalid URL执行请求构造dry-run | 已通过；确认固定模型、说话人、热词、上下文映射 |
| `.venv\Scripts\python.exe scripts/asr.py bootstrap-media` | 下载固定FFmpeg构建，校验大小/SHA256/ZIP路径，再解压到项目 | 首次下载不完整，被拦截，未解压/执行 |

不接受真实音频路径的探针设计是有意限制：BL本地文件dry-run可能先上传。`probe-bl`与将来的登录配置使用不同目录，发现探针目录中有配置/凭据文件即停止而不读取。

## 实际环境与安装边界

| 项目 | 本轮观察 |
| --- | --- |
| OS | Windows x64 |
| Python | 3.12.1，复用现有运行时；`.venv`位于项目内 |
| Node | 24.19.0，复用现有运行时 |
| BL | 顶层/core/runtime/commands均为2.1.0；实际入口输出`bl 2.1.0` |
| npm依赖 | 锁定55个传递/直接包，全部具备registry.npmjs.org地址及完整性摘要 |
| BL安装目录 | `.tools/bailian/` |
| 配置 | 预留`.state/bailian/`；无凭据探针使用`.state/bailian-probe/` |
| 临时文件/缓存 | `.runtime/tmp/`、`.runtime/npm-cache/` |
| 结果记录 | `.state/bl-probe.json`、`.state/tests-report.json`，均不进Git |

安装使用npm原生命令与生成的锁文件；跳过安装脚本。已审阅BL的postinstall仅预下载推荐器Wiki，当前ASR探针不需要这些技能资产。不执行全局安装、`bl skill init`或`bl config agent`。

子进程环境用白名单构造，不继承DASHSCOPE/API Key、NPM_TOKEN、NODE_OPTIONS等；npm用户/全局配置指向项目内空文件。所有BL调用附`--quiet`走已核实的禁自动升级路径，遥测设置`DO_NOT_TRACK=1`。这不禁止BL检查公开版本信息；本轮看到的update-state.json只在项目探针目录中。

路径写入前解析并检查仍在项目内；不覆盖非空未知安装目录。版本元数据不足以证明安装完整，bootstrap和doctor还会实际运行BL版本入口，检测缺依赖状态。

**限制**：尚未在干净Windows机器验证缺Python/Node时的自动安装；未做全机文件访问追踪，不将路径配置与本机观察扩张为完整安装审计。S5安装验收仍须实际执行。

## 真实BL发布包的本机合约测试

测试使用真实BL 2.1.0程序、合成Key与127.0.0.1模拟ASR/结果服务；输入是虚构HTTPS URL，不上传本地文件。Python HTTP代码只存在于测试fixture，不是产品云端客户端。

| 场景 | 观察 |
| --- | --- |
| 完整成功 | 一次POST提交、一次GET查询、一次GET下载；BL的out正确保存JSON |
| 默认成功模式task_id | stdout没有返回模拟任务ID，不能承诺总能恢复任务 |
| 提交401/500 | 各仅一次请求；退出失败，无结果文件 |
| 查询500 | 一次提交、一次失败查询，随后退出；没有重提 |
| 任务FAILED | 一次提交/查询后失败退出 |
| 子任务FAILED | BL退出0，stdout含FAILED，out为`[]`；后续业务必须检查产物 |
| CANCELED/UNKNOWN | 查询持续至退出码5（超时），没有重新提交 |

这些结果证明所测CLI调用路径与本地输入/输出契约，不证明云端账号权限、OSS上传成功、真实音频识别质量或服务端JSON实际字段。

## 媒体工具安装结果

锁定FFmpeg官网列出的Gyan Windows x64 9.0.2 essentials构建，保留原始许可证文件，不向Git或系统PATH添加二进制。固定来源、大小和SHA256见`tools/media-lock.json`。

首次下载收到13,581,313字节，预期114,768,076字节；实际SHA256为`d2571a5a94cc3ad491386121a8f2a6bfbf581f34fbe9284adc8510ae48573048`，与锁定摘要不符，且不是完整ZIP。程序拒绝解压/执行，未自动重试。失败副本保留在`.runtime/ffmpeg-9.0.2-essentials_build.zip.part`，不进入Git。具体截断原因尚未确定，不能仅凭下载失败断言发布者文件有问题。

下载处理增加进程级360秒总截止时间，避免仅依赖socket空闲超时。该截止与错误传播的单元测试通过；修正后的完整下载路径尚未再次联网执行。已实测再次启动入口会在发现既有part时立即失败，不覆盖文件、不发起重复下载。再次安装之前应检查并处理已知失败part文件，由明确的后续操作发起，不在安装器中自动循环重试。

已编写合成立体声→单声道FLAC探针，检查原文件不变、采样率/时长、两侧信号参与及拒绝覆盖已有输出；由于没有可执行FFmpeg，三项实际转换测试跳过。不能声称转换方案已通过。

## 自动化验证

```powershell
.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -t . -v
```

最终发现28项测试：**25项成功、3项媒体合约测试跳过、0失败、0错误**。以实际成功/跳过回调逐项核对，不单凭测试运行器的总数解释结果。核心测试覆盖环境变量隔离、路径越界拒绝、无重试、安装完整性、合成URL探针、CLI合约，以及媒体归档摘要/路径/符号链接拒绝。

## 未解决事项与下一步

1. **媒体安装**：查明不完整下载的原因，取得通过原摘要校验的包后再运行三项媒体合约测试。
2. **普通Key预校验**：已确认BL公开登录模式没有stdin/env入口；`model list`为匿名目录、`config ui`保存配置不做在线校验，均不能冒充有效性验证。不增加Python校验器；下一步明确产品交互与安全输入的取舍。
3. **完整任务恢复**：已有BL模式不总暴露task_id；保留这项上游限制，不增加Python轮询器。
4. **待定产品选择**：即时热词/预编译词表、北京地域尚未收到明确答复；探针只验证参数能力，不代表替用户选定方案。
5. **进入S2之前**：继续解决S1剩余事项并报告，再开发网页与本地校验。真实登录、上传和识别尚未开始。
