# asr-transcription

[中文](README.md) | English

Transcribe recordings in Codex and get Word, Excel, and Markdown documents to review. asr-transcription is a standalone Codex Skill that uses the official [BL CLI](https://github.com/modelstudioai/cli) to access [Alibaba Cloud Model Studio](https://help.aliyun.com/zh/model-studio/what-is-model-studio), with a local web page for transcription settings.

## Features

- **Recording transcription**: Process one audio file, with timestamps and optional speaker identification.
- **Accuracy enhancement**: Import hotwords from Excel and add context text. Both can be used together.
- **Visual settings**: Add a recording, adjust options, and choose save locations in your browser.
- **Document generation**: Create Word, Excel, and Markdown together, keep the original JSON, and export documents again locally.

## Install the Skill

Download `asr-transcription.zip` from [Releases](https://github.com/hx101700/asr-agent/releases/latest).

First, [register an Alibaba Cloud account](https://help.aliyun.com/zh/account/step-1-register-an-alibaba-cloud-account) and follow the [official setup guide](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen) to complete account verification and activate Model Studio.

Send the distribution package `asr-transcription.zip` to Codex with this request:

```text
Install this ZIP as the asr-transcription Skill. Read its SKILL.md and prepare the required environment. First, let me choose a workspace for recording tasks and results.
```

The Skill location holds tools and instructions. Your workspace holds the runtime environment, credentials, tasks, and results. Windows 10/11 x64, Python 3.12 x64, and Node.js 18.17+ with npm are required. Initial setup needs internet access. See the [usage guide](skills/asr-transcription/references/usage.md) for details.

## Quick start

After installation, tell Codex:

```text
Please transcribe this recording.
```

Codex uses the Skill to open the local transcription page. Add a recording, adjust the language and speaker settings, and choose where to save the files. For Model Studio authentication, choose:

- **Console login (recommended)**: Authorize access on the official Alibaba Cloud page. BL manages the credentials.
- **API Key**: Use your own Beijing-region Model Studio Key. Follow the instructions to put it in `.asr-transcription/.env` under your workspace, then select “Use specified API Key” on the transcription page.

<!-- SCREENSHOT: overview
Insert a real transcription-page screenshot showing audio selection, settings, and save locations.
Suggested file: doc/images/01-transcription-overview.png
Caption: Add a recording and adjust the transcription settings. Hide keys and private paths.
-->

To improve recognition of specialized terms, import a hotword list or enter context text. Hotwords identify terms to recognize; context supplies reference text containing those terms. You can use both together.

<!-- SCREENSHOT: enhancement
Insert a real screenshot with hotwords and context enabled together.
Suggested file: doc/images/02-accuracy-enhancement.png
Caption: Provide hotwords and context for recognition. Use public terms and publishable examples.
-->

Review and save the settings. Codex guides authentication for your chosen method. Once you confirm transcription, Codex calls BL, generates the three documents, and reports their locations for your review and correction. Transcription sends the recording and enabled enhancement content to Model Studio and may incur charges.

The current stage covers transcription and document delivery. Meeting summaries based on corrected text and document examples are planned for a later stage.

## Contributing

[Issues](https://github.com/hx101700/asr-agent/issues), feature suggestions, and pull requests are welcome. See the [development documentation](doc/README.md) for code structure, conventions, and verification.

## Related links

| Resource | Links |
| --- | --- |
| Alibaba Cloud Model Studio | [Console](https://bailian.console.aliyun.com/) · [Documentation](https://help.aliyun.com/zh/model-studio/) |
| BL CLI | [Official site](https://bailian.console.aliyun.com/cli) · [GitHub](https://github.com/modelstudioai/cli) |
| Accuracy enhancement | [Hotwords and context](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy) |
| asr-transcription | [Usage guide](skills/asr-transcription/references/usage.md) · [Downloads](https://github.com/hx101700/asr-agent/releases) |

Licensed under [Apache-2.0](LICENSE).
