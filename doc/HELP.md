# 使用资料

asr-transcription 的安装、认证、网页操作、文件要求及重新导出说明集中维护在 Skill 的 [usage.md](../skills/asr-transcription/references/usage.md)。

- 第一次使用：阅读[项目介绍](../README.md)，再按 [usage.md](../skills/asr-transcription/references/usage.md)准备工作目录与环境；网页中可以直接填写或修改 API Key。
- 界面设置：在页面右上角切换中文/English和主题，音频语言在转写设置中另行选择。
- 热词：在网页表格直接填写，或导入Excel；错误行标红，按单元格提示修改后点击“检查词表”。上下文检查会保留原文并指出具体问题。
- 填错设置：保存后点击“修改设置”，撤回尚未执行的旧编号并恢复原输入；重新保存后告诉Codex“继续”。
- 只更换Key：在网页选择“使用指定 API Key”，填写后点击“保存 API Key”，无需添加录音；鉴权失败按[凭据修复](../skills/asr-transcription/references/errors.md#鉴权失败与重新配置)处理。
- 保存位置：点击“选择文件夹”更换目录；原位置不存在或被文件占用时，窗口从当前工作目录打开。
- 操作失败：根据 [errors.md](../skills/asr-transcription/references/errors.md)保留回执、定位阶段并处理问题。
- 查询参数依据：参阅 [model.md](../skills/asr-transcription/references/model.md)中的官方来源。
- 更新工具：将新ZIP交给Codex，明确要求更新已安装的Skill，按[更新说明](../skills/asr-transcription/references/update.md)先完成正在运行的任务，保留工作目录的数据。

Skill 中的 `SKILL.md` 是 Codex 执行入口；仓库的 `AGENTS.md` 是维护者指令。使用时的凭据、环境、任务和结果存放在用户选择的工作目录。
