# asr-agent

在Codex中通过本机网页配置单个音频，再调用阿里云百炼CLI完成非实时转写，保存原始JSON及Excel、Word、Markdown。

模型固定为`qwen-audio-3.0-asr-flash-filetrans`，地域固定北京。支持即时热词与上下文同时使用；默认区分发言人，必要时生成单声道FLAC副本。

## 使用

适用于Windows 10/11 x64。用户发行ZIP不带运行时或依赖包。本机需有Windows x64 CPython 3.12（含venv、ensurepip、tkinter）、Node.js 18.17.0或更高版本及配套npm；安装时通过阿里云PyPI镜像获取全部Python依赖，通过npm获取BL依赖。安装器在项目内创建环境，不修改系统PATH或全局包。

下载发行ZIP后解压，使用Codex打开其中的`asr-agent`目录。项目Skill位于`.agents/skills/asr-agent/SKILL.md`；在该目录提出“帮我转写录音”即可按Skill调用以下现有入口。开发仓库运行`python -S -X utf8 scripts/build_zip.py`生成`dist/asr-agent.zip`，发行清单及模板维护见[开发说明](doc/DEVELOPMENT.md)。

```powershell
python -S -X utf8 scripts/asr.py bootstrap
.venv\Scripts\python.exe scripts/asr.py serve
```

网页只添加本机文件、检查并保存配置。确认上传范围后，由Codex运行：

```powershell
.venv\Scripts\python.exe scripts/asr.py transcribe --job <设置编号> --authorize-upload
.venv\Scripts\python.exe scripts/asr.py job-status --job <设置编号>
```

保留确认配置、已保存的JSON_READY执行记录和结果JSON的已有任务，可用`export --job <设置编号>`本地重导。控制台首次登录使用`login`；指定API Key模式读取项目`.env`，无需login。

## 文档与范围

- [使用说明](doc/HELP.md)：安装、配置、保存位置、失败处理。
- [当前状态](doc/STATUS.md)：已完成、验证范围与下一步。
- [开发说明](doc/DEVELOPMENT.md)：实际模块职责、数据与执行边界。
- [UML设计视图](doc/UML.md)：对象关系、调用时序和状态，附可编辑源稿。
- [文档索引](doc/README.md)：官方依据、错误解释及验证方法。

用户发行ZIP只包含运行代码、项目Skill、依赖锁和必要使用文档。测试、构建脚本、开发状态及验证方法保留在本仓库；根目录说明由`release/`中的用户模板提供。全部依赖在安装时下载并按锁校验；复测步骤和未覆盖范围见[验证方法](doc/ACCEPTANCE.md)。

`.env`、`data/`、`.state/`、`.runtime/`、`.venv/`、`.tools/`、`outputs/`不进入Git。用户选择其他输出位置时自行管理其隐私和版本控制范围。
