# asr-agent

[中文](README.md) | English

Transcribe recordings in Codex and generate Word, Excel, and Markdown documents. Speech recognition is provided by [Alibaba Cloud Model Studio](https://help.aliyun.com/zh/model-studio/what-is-model-studio) through its official [BL CLI](https://github.com/modelstudioai/cli).

Before you start, [register an Alibaba Cloud account](https://help.aliyun.com/zh/account/step-1-register-an-alibaba-cloud-account) and follow the [official setup guide](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen) to complete account verification and activate Model Studio.

## Agent installation (recommended)

Download **asr-agent.zip** from [Releases](https://github.com/hx101700/asr-agent/releases). Send the ZIP and this prompt to Codex; it will check your environment and follow the project instructions to install and verify asr-agent:

```text
Extract this ZIP, read AGENTS.md in the extracted project, and follow its instructions to install and configure asr-agent for me.
```

Currently supports Windows 10/11 x64. Python 3.12 x64 and Node.js 18.17+ with npm must be installed on your computer. See the [user guide](doc/HELP.md) for environment requirements. The web UI and document labels are currently in Chinese.

## Quick start

Once installed, ask Codex to transcribe your recording:

```text
Transcribe this recording for me.
```

Codex will guide you through Model Studio authentication. Choose either:

- **Console login (recommended)**: authorize access on the official Alibaba Cloud page. BL manages the login credentials.
- **API key**: use an existing Model Studio key for Beijing, add it to the project's `.env` as prompted, and select “使用指定 API Key” (Use a specific API key) on the transcription page.

Codex then opens the transcription page. Add your recording, adjust settings such as language and speaker diarization, and choose where to save the files.

To help recognize specialist vocabulary, import a hotword list or add reference context. Hotwords identify terms to focus on; context supplies reference text containing those terms. You can use both together.

After reviewing and saving the settings, return to Codex and confirm that transcription can start. Codex calls BL, generates formatted Word, Excel, and Markdown documents, and tells you where they were saved.

Transcription sends the recording and enabled enhancement content to Model Studio and may incur charges.

## Related links

| Resource | Links |
| --- | --- |
| Alibaba Cloud Model Studio | [Console](https://bailian.console.aliyun.com/) · [Official docs](https://help.aliyun.com/zh/model-studio/) |
| Model Studio CLI | [Website](https://bailian.console.aliyun.com/cli) · [GitHub](https://github.com/modelstudioai/cli) |
| Recognition accuracy | [Hotwords and context](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy) |
| asr-agent | [User guide](doc/HELP.md) · [Downloads](https://github.com/hx101700/asr-agent/releases) |

Found a problem or have a suggestion? Open an [issue](https://github.com/hx101700/asr-agent/issues).

Licensed under [Apache-2.0](LICENSE).
