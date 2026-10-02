# asr-agent

A recording transcription agent for Codex, powered by Alibaba Cloud Model Studio.

[中文](README.md) · English · [Download](https://github.com/hx101700/asr-agent/releases) · [User guide](doc/HELP.md) · [Model Studio CLI](https://github.com/modelstudioai/cli)

Turn meeting, interview, and lecture recordings into Word, Excel, and Markdown documents with timestamps and speaker labels. Choose a file and recognition options on the local page; Codex runs the transcription and shows you where the documents were saved.

## Features

- **File transcription** — MP3, WAV, M4A, FLAC, and other formats, one recording at a time.
- **Accuracy enhancements** — Import hotwords from Excel and add reference context for specialist vocabulary.
- **Speaker labels** — Enabled by default, with an optional estimated speaker count.
- **Document export** — Generate Word, Excel, and Markdown together, retain the original JSON, and re-export locally.
- **Visual setup** — Select files, adjust options, review audio details, and choose output folders in the browser.

<!-- SCREENSHOT: overview
Insert an actual overview of audio selection, transcription settings, and the review panel.
Suggested file: doc/images/01-transcription-overview.png
Caption: Choose a recording and configure transcription on one page. Hide keys and private paths.
-->

## Installation

Requires **Windows 10/11 x64, Codex desktop, Python 3.12 x64, and Node.js 18.17.0+ with npm**. Python must include tkinter. Dependency installation requires network access.

Download **asr-agent.zip** from [Releases](https://github.com/hx101700/asr-agent/releases), extract it, open the included `asr-agent` folder in Codex, and enter:

> Install asr-agent and open the recording transcription page.

On first use, sign in to Model Studio as prompted or configure your own API key for Beijing. See the [setup guide](doc/HELP.md) for details. The web UI, document labels, and detailed guide are currently in Chinese.

## Quick start

Once installed, tell Codex what you need:

| Task | Example prompt |
| --- | --- |
| Transcribe a recording | Transcribe a meeting recording and distinguish the speakers. |
| Add specialist vocabulary | I want to add hotwords and reference context before transcribing this recording. |
| Regenerate documents | Regenerate Word, Excel, and Markdown for the recording we just transcribed. |

On the page, select the recording and adjust the options. Click **检查并预览 (Check and preview)** and **保存设置 (Save settings)**, then return to Codex to authorize transcription. Codex reports the output locations when the task finishes.

Recognition uses your Model Studio account and may incur charges. The recording and enabled enhancement content are sent to Model Studio after you authorize transcription.

## Hotwords and context

Import target terms from Excel as hotwords, or add domain terms and reference text as context. Include the words you expect in the recording; both options can be used together. See [Model Studio's accuracy guidance](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy).

<!-- SCREENSHOT: enhancement
Insert an actual view with hotwords and context enabled together.
Suggested file: doc/images/02-accuracy-enhancement.png
Caption: Add recognition references for specialist vocabulary. Use public terms, without actual people's names or private content.
-->

## Transcription results

Use Word to read and edit, Excel to review and filter segments, and Markdown for notes and archives. All three retain timestamps and include speaker identifiers when diarization is enabled.

<!-- SCREENSHOT: outputs
Insert actual Word, Excel, and Markdown output screenshots.
Suggested file: doc/images/03-transcription-outputs.png
Caption: One recording, three document formats. Use a sample approved for public sharing.
-->

Re-export runs locally and updates the same files. Save a separate copy first if you want to keep manual edits. File requirements, storage details, and troubleshooting are in the [user guide](doc/HELP.md).

## Powered by Model Studio

[Alibaba Cloud Model Studio](https://help.aliyun.com/zh/model-studio/what-is-model-studio) provides cloud speech recognition. Its [official BL CLI](https://github.com/modelstudioai/cli) handles login, upload, and recognition calls. asr-agent adds the local configuration page and document exports.

The current model is `qwen-audio-3.0-asr-flash-filetrans`, in the Beijing region.

[Console](https://bailian.console.aliyun.com/) · [Model Studio docs](https://help.aliyun.com/zh/model-studio/) · [BL CLI website](https://bailian.console.aliyun.com/cli) · [BL CLI source](https://github.com/modelstudioai/cli)

## Contributing

Report problems and suggest improvements through [Issues](https://github.com/hx101700/asr-agent/issues). See the [documentation index](doc/README.md) and [UML views](doc/UML.md) for development references.

[Apache-2.0](LICENSE)
