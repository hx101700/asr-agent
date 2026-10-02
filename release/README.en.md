# asr-agent

[中文](README.md) | English

**Turn recordings into timestamped Word, Excel, and Markdown documents in Codex.**

asr-agent processes existing meeting, interview, and lecture recordings. Ask Codex to start, select a file and options on a local web page, and receive three document formats plus the original recognition JSON.

Speech recognition uses Alibaba Cloud Model Studio's `qwen-audio-3.0-asr-flash-filetrans` in Beijing. The tool supports Windows 10/11 x64 and processes one file at a time, with timestamps, speaker diarization, and combined hotword and context support. The current web UI and generated document labels are in Chinese.

## Before you start

Use Windows 10/11 x64 with Windows x64 CPython 3.12, including venv, ensurepip, and tkinter, plus Node.js 18.17.0 or later with npm. The ZIP does not bundle runtimes or dependencies; installation requires network access.

You also need a working Codex desktop app and an Alibaba Cloud account with permission to call the model, or a Model Studio API key for Beijing. Recognition uses your own Alibaba Cloud service and may incur model usage charges.

## First use

### 1. Install and open the page

Extract the ZIP, open its `asr-agent` folder in Codex, and enter:

> Install asr-agent and open the recording transcription page.

Codex installs project dependencies and the Alibaba Cloud Model Studio CLI, then opens the local page. Allow the initial downloads to finish. For later use, ask Codex to transcribe a recording in the same project.

### 2. Choose how to connect your account

- **Console login**: leave `使用指定 API Key` (Use a specific API key) unchecked. On first use, follow Codex's instructions to authorize access on the official Alibaba Cloud page.
- **API key**: copy `.env.example` to `.env`, enter your key after `DASHSCOPE_API_KEY=`, then select `使用指定 API Key` on the page. The key is read locally; do not send it in chat.

### 3. Add a recording and save the settings

1. Select or drag in one audio file. Supported formats include MP3, WAV, M4A, and FLAC.
2. Choose the audio language and adjust speaker diarization and the estimated speaker count if needed.
3. Download and fill in the Excel template for hotwords, or enter reference text. Both enhancements can be enabled together.
4. Use `选择文件夹` (Choose folder) to select destinations for JSON and documents. The default is the project's `outputs` folder.
5. Click `检查并预览` (Check and preview), review the details, then click `保存设置` (Save settings). The page explains any required mono conversion; the original file is preserved.

Alibaba Cloud's [accuracy guidance](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy) describes instant hotwords as terms and weights sent with a request, and context as reference text containing the target words. This project accepts them through Excel and text input, respectively.

### 4. Return to Codex to start transcription

> I authorize uploading this recording and the selected hotwords and context to Alibaba Cloud Model Studio in Beijing. Start transcription.

Codex reports where the files were saved when it finishes. You can close the page; keep the computer and execution process running during transcription. Adding files and saving settings happen locally; cloud submission follows your authorization.

## Output files

| File | Use |
| --- | --- |
| `transcription.docx` | Read and edit paragraphs with time labels and speaker information |
| `transcription.xlsx` | View or filter transcript rows by time, speaker, and text |
| `transcription.md` | Read and archive the transcript in Markdown editors or notes |
| `transcription.json` | Retain the original result for local re-export |

Document titles use the recording's filename stem followed by `录音转写` (recording transcript). By default, documents are saved in `outputs/task-id/documents/` and the original JSON in `outputs/task-id/json/`. Codex provides the actual paths.

To regenerate documents, retain the project folder and original JSON, then ask Codex: “Re-export all three document formats for task `<task-id>`.” The documents replace the task's files with the same names without recognizing the recording again. Save a separate copy of any documents you have edited first. A JSON file alone is not enough to restore a complete task.

## Usage notes

- The current version processes one existing audio file at a time. It does not support live recording, batches, translation, or automatic summaries.
- A failed transcription stops and reports its known cause. Recognition is not automatically submitted again; completed files are retained.
- Recordings, keys, and transcripts are user data. Keep them out of public repositories.
- [Detailed guide (Chinese)](doc/HELP.md): manual commands, file requirements, output locations, and stopping the application.
- [Status and errors (Chinese)](doc/ERRORS.md): what to do when an operation fails.
- [Official references (Chinese)](doc/REFERENCES.md): model parameters and input limits.

This project is licensed under [Apache-2.0](LICENSE).
