# asr-agent

[中文](README.md) | English

**Turn recordings into timestamped Word, Excel, and Markdown documents in Codex.**

asr-agent is a recording transcription tool for Windows. It is designed for existing meeting, interview, and lecture recordings. Ask Codex to start, choose a file and options on a local web page, and receive documents you can read, edit, and archive.

Speech recognition uses Alibaba Cloud Model Studio's `qwen-audio-3.0-asr-flash-filetrans` in the Beijing region. This Windows preview processes one file at a time. The current web UI and generated document labels are in Chinese.

[Download the package](https://github.com/hx101700/asr-agent/releases) · [Get started](#get-started) · [Output files](#output-files) · [FAQ](#faq) · [Detailed guide (Chinese)](doc/HELP.md)

## Features

- **Three document formats from one transcription**: generate Word, Excel, and Markdown together, and keep the original recognition JSON.
- **Timestamps and speakers**: retain segment timing and distinguish speakers by default. You can disable speaker diarization or provide an estimated speaker count.
- **Hotwords and context**: import an Excel vocabulary and provide reference text. Both can be enabled together.
- **Visual configuration**: select or drag in an audio file, preview its duration and channels, and choose output folders through the system dialog.
- **Local re-export**: regenerate documents from a retained task and its original result without recognizing the recording again.

<!-- SCREENSHOT: overview
Screenshot slot 1: insert an actual overview of the local page, showing audio selection, transcription settings, and the review panel.
Suggested file: doc/images/01-transcription-overview.png
Suggested caption: Add a recording, configure transcription, and review the details on one page.
Hide keys, account details, and private file paths before capture. Share the same image with the Chinese README.
-->

## Get started

### 1. Prepare your environment and get the project

| Requirement | Details |
| --- | --- |
| Operating system | Windows 10 / 11, 64-bit |
| Codex | A working installation of the desktop app |
| Python | Windows x64 CPython 3.12, including venv, ensurepip, and tkinter |
| Node.js | Version 18.17.0 or later, including npm |
| Model Studio access | An Alibaba Cloud account with permission to call the model, or a Model Studio API key for Beijing |
| Network | Required to download dependencies during installation and to connect to Model Studio for transcription |

Download **asr-agent.zip** from the Assets section of [Releases](https://github.com/hx101700/asr-agent/releases). Extract it and open the included `asr-agent` folder in Codex. This package contains the files needed to use the tool.

For the full source and development documentation, [download the dev branch](https://github.com/hx101700/asr-agent/archive/refs/heads/dev.zip) and open the extracted `asr-agent-dev` folder. GitHub's Source code archives on a release page contain the full source for that release.

### 2. Ask Codex to install and open the page

In a Codex conversation for this project, enter:

> Install asr-agent and open the recording transcription page.

Codex installs the project dependencies and the Alibaba Cloud Model Studio CLI, then opens the local page. Allow the initial downloads to finish. The environment stays inside the project folder. For later use, ask Codex to transcribe a recording in the same project.

### 3. Choose how to connect your account

| Method | What you need to do |
| --- | --- |
| Console login | Leave `使用指定 API Key` (Use a specific API key) unchecked. On first use, follow Codex's instructions to authorize access on the official Alibaba Cloud login page. |
| API key | Copy `.env.example` to `.env` in the project, enter your key after `DASHSCOPE_API_KEY=`, then select `使用指定 API Key` on the page. |

The page reads your API key from the local file. Do not send the key in chat. Recognition uses your own Alibaba Cloud service and may incur model usage charges.

### 4. Add a recording and review the settings

1. **Add audio**: select or drag in one file. Supported formats include MP3, WAV, M4A, and FLAC.
2. **Set transcription options**: choose the audio language and adjust speaker diarization and the estimated speaker count if needed.
3. **Add accuracy enhancements**: download and fill in the Excel template for hotwords, or enter reference text related to the recording.
4. **Choose output folders**: select separate destinations for JSON and documents if needed. The default is the project's `outputs` folder.
5. Click **`检查并预览` (Check and preview)**, review the details, then click **`保存设置` (Save settings)**.

Following Alibaba Cloud's [accuracy enhancement guidance](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy):

- **Hotwords** send terms and weights with the recognition request to help recognize product names and specialist vocabulary. This project imports an instant vocabulary from Excel.
- **Context** supplies domain terms or reference text containing the exact words to recognize. Related meaning alone provides limited correction.

When speaker diarization is enabled for multichannel audio, the page explains that a mono copy will be created. The original file is preserved.

<!-- SCREENSHOT: enhancement
Screenshot slot 2: insert the accuracy enhancement section and review details, with hotwords and context both enabled.
Suggested file: doc/images/02-accuracy-enhancement.png
Suggested caption: Enable hotwords and context together, then review the transcription settings before submission.
Use public product or technical terms. Exclude actual people's names, private vocabularies, recording content, and keys.
-->

### 5. Return to Codex to start transcription

After saving the settings, confirm the upload in Codex. For example:

> I authorize uploading this recording and the selected hotwords and context to Alibaba Cloud Model Studio in Beijing. Start transcription.

Codex runs the transcription and reports where the files were saved. You can close the web page; keep the computer and execution process running during transcription.

## Output files

| File | Use |
| --- | --- |
| `transcription.docx` | Read and edit the transcript in paragraphs with time labels and speaker information |
| `transcription.xlsx` | View or filter transcript rows by time, speaker, and text |
| `transcription.md` | Read and archive the transcript in Markdown editors, notes, or repositories |
| `transcription.json` | Keep the original recognition result for local re-export |

Document titles use the recording's filename stem followed by `录音转写` (recording transcript). Speaker labels use the model's identifiers; they do not identify people by name.

<!-- SCREENSHOT: outputs
Screenshot slot 3: insert actual exported documents, optionally showing Word, Excel, and Markdown side by side.
Suggested file: doc/images/03-transcription-outputs.png
Suggested caption: The same transcript in three formats, retaining timestamps and speaker information.
Use a sample authorized for public sharing. Adding a screenshot does not establish transcription accuracy or page-by-page layout acceptance.
-->

The default structure is shown below. Task and export IDs are generated by the application:

```text
outputs/
└── task-id/
    ├── json/
    │   └── transcription.json
    └── documents/
        └── export-id/
            ├── transcription.docx
            ├── transcription.xlsx
            └── transcription.md
```

To regenerate documents, keep the project folder and original JSON, and ask Codex: “Re-export all three document formats for task `<task-id>`.” Each export gets a new folder and preserves the previous files. A JSON file alone is not enough to restore the full task.

## FAQ

**Is audio uploaded to the cloud as soon as I add it?**

Adding a file and saving settings happen locally. The recording and enabled hotwords and context are sent to Model Studio in Beijing after you authorize transcription. Use recordings you are permitted to upload, and keep keys, recordings, and transcripts out of public repositories.

**Can it record live audio, process batches, or generate summaries?**

The current version processes one existing audio file at a time. Live recording, batch processing, translation, and automatic summaries are outside its current scope.

**What happens if transcription fails?**

Codex explains the known failure and reports any saved files. It does not automatically submit recognition again. If only document export failed, inspect the retained result before deciding whether to re-export. See [status and error guidance (Chinese)](doc/ERRORS.md).

**Do I have to install it with terminal commands?**

You can use the Codex prompt above. For manual installation and opening the settings page, run these commands in the project folder:

```powershell
python -S -X utf8 scripts/asr.py bootstrap
.venv\Scripts\python.exe -X utf8 scripts/asr.py serve
```

The [detailed guide (Chinese)](doc/HELP.md) also covers login, transcription, and local re-export commands.

## Documentation and contributions

The detailed documents below are currently in Chinese:

- [User guide](doc/HELP.md): installation, configuration, file limits, and troubleshooting.
- [Official references](doc/REFERENCES.md): the model, parameters, and input requirements.
- [Development guide](doc/DEVELOPMENT.md) and [UML views](doc/UML.md): implementation and source locations.
- [Verification scope](doc/ACCEPTANCE.md) and [known issues](doc/ISSUES.md): tested scenarios and current limitations.

Report problems through [Issues](https://github.com/hx101700/asr-agent/issues). Include how you used the tool, environment versions, and the error message, with keys, recording content, and other sensitive information removed.

This project is licensed under [Apache-2.0](LICENSE).
