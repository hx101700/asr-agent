# asr-agent

在 Codex 中转写一个本地录音，保存原始 JSON，以及带时间戳的 Excel、Word、Markdown 文件。

固定使用阿里云百炼北京地域的 `qwen-audio-3.0-asr-flash-filetrans`。支持热词与上下文同时使用，默认区分说话人；多声道录音需要合并时，会在网页预览中提示。

## 安装

适用于 Windows 10/11 x64。本机需有 Windows x64 CPython 3.12（含 venv、ensurepip、tkinter）、Node.js 18.17.0 或更高版本及配套 npm。ZIP 不附带运行时或依赖包；安装需要网络。

解压后，用 Codex 打开 `asr-agent` 文件夹，提出“安装这个 Agent，帮我转写录音”。项目 Skill 位于 `.agents/skills/asr-agent/SKILL.md`，不需要复制到用户级技能目录。

安装入口：

```powershell
python -S -X utf8 scripts/asr.py bootstrap
```

Python 依赖从阿里云 PyPI 镜像下载并按锁校验，BL 从 npm 安装。环境保存在项目 `.venv` 和 `.tools/bailian`，不修改系统 PATH 或全局包。

## 使用

在 Codex 中提出“帮我转写录音”，Agent 会打开本机网页。选择一个音频，按需设置说话人、语言、热词和上下文，选择保存位置，检查预览并保存设置。

控制台方式由用户在阿里云官方页面完成首次登录。使用指定 API Key 时，将 `.env.example` 复制为 `.env` 并填写 `DASHSCOPE_API_KEY`，网页只选择使用该 Key，无需发送密钥到聊天。

网页保存设置后，Codex 在已获上传授权的范围内开始转写，并按回执告知已完成文件的位置。失败不自动重试。已有任务保留确认配置、已保存的 `JSON_READY` 执行记录和结果 JSON 时，可显式本地重导三种成品；仅有一份 JSON 文件不满足重导条件。

- [使用说明](doc/HELP.md)：安装、配置、输出格式与常见问题。
- [状态与错误说明](doc/ERRORS.md)：任务状态、失败阶段与错误解释。
- [官方能力依据](doc/REFERENCES.md)：模型参数、输入限制与官方来源。

录音、密钥、凭据、结果和运行日志属于本地用户数据，不能提交 Git。用户选择其他保存位置时，应自行管理该目录的隐私和版本控制。
