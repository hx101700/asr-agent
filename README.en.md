# MemoFlow

[中文](README.md) | English

MemoFlow aims to turn recordings into meeting minutes that follow your preferences and requested format, learning from the examples, requirements, and corrections you confirm.

Stage one is currently available as the `asr-transcription` Skill: transcribe one recording in Codex and receive Word, Excel, and Markdown documents to review. It uses the official [BL CLI](https://github.com/modelstudioai/cli) to access [Alibaba Cloud Model Studio](https://help.aliyun.com/zh/model-studio/what-is-model-studio), with a local web page for transcription settings.

## Features

- **Recording transcription**: Process one audio file, with timestamps and optional speaker diarization.
- **Accuracy enhancement**: Import hotwords from Excel and add context text. Both can be used together.
- **Visual settings**: Add a recording, adjust options, and choose save locations in your browser, with Chinese and English interfaces and light or dark themes.
- **Document generation**: Create Word, Excel, and Markdown together, keep the original JSON, and export documents again locally.

## Install the Skill

Download the stage-one development preview, `asr-transcription.zip`, from [Releases](https://github.com/hx101700/memoflow/releases).

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

Codex uses the Skill to open the local transcription page. Add a recording, adjust the audio language and speaker diarization settings, and choose where to save the files. Use the controls at the top right to switch between Chinese and English, or select System, Light, or Dark appearance. For Model Studio authentication, choose:

- **Console login (recommended)**: Authorize access on the official Alibaba Cloud page. BL manages the credentials.
- **API Key**: Select “Use a standard API Key” on the transcription page, then enter or update your Model Studio Key for China (Beijing). It is saved in the current workspace when you check and preview the settings.

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

**Stage two (planned)** will create meeting minutes from reviewed transcripts, document examples, and formatting requirements, then use corrections you confirm to improve later results. Preference storage and feedback adoption will be designed in that stage. The current Skill delivers transcripts for review.

## Contributing

[Issues](https://github.com/hx101700/memoflow/issues), feature suggestions, and pull requests are welcome. See the [development documentation](doc/README.md) for code structure, conventions, and verification.

## Related links

| Resource | Links |
| --- | --- |
| Alibaba Cloud Model Studio | [Console](https://bailian.console.aliyun.com/) · [Documentation](https://help.aliyun.com/zh/model-studio/) |
| BL CLI | [Official site](https://bailian.console.aliyun.com/cli) · [GitHub](https://github.com/modelstudioai/cli) |
| Accuracy enhancement | [Hotwords and context](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy) |
| MemoFlow | [Usage guide](skills/asr-transcription/references/usage.md) · [Downloads](https://github.com/hx101700/memoflow/releases) |

Licensed under [Apache-2.0](LICENSE).
