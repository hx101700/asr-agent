[中文](https://github.com/hx101700/asr-agent/releases/tag/v0.1.0) | English

The first version of asr-agent is here. Give the installation package to Codex, configure your recording on the local page, and get Word, Excel, and Markdown documents when transcription finishes.

### Added

- **Web configuration**: add one recording, adjust language, speaker diarization, and estimated speaker count, and choose save locations.
- **Hotwords and context**: import hotwords from Excel and add reference text. Both enhancements can be used together.
- **Model Studio authentication**: authorize access on the official login page or use an API key from the project's `.env`.
- **Document generation**: save three document formats with timestamps and the original JSON, with local re-export from a retained task.

### Get started

Download [asr-agent.zip](https://github.com/hx101700/asr-agent/releases/download/v0.1.0/asr-agent.zip) and send it to Codex with the [installation prompt in the README](https://github.com/hx101700/asr-agent/blob/v0.1.0/README.en.md#agent-installation-recommended). Once installed, say “Transcribe this recording for me” and follow the authentication and page prompts.

Currently supports **Windows 10/11 x64**, using `qwen-audio-3.0-asr-flash-filetrans` in Beijing. Speech recognition is provided by [Alibaba Cloud Model Studio](https://help.aliyun.com/zh/model-studio/what-is-model-studio) through its official [BL CLI](https://github.com/modelstudioai/cli) and may incur charges.

Please report problems through [Issues](https://github.com/hx101700/asr-agent/issues).
