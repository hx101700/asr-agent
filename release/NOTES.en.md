[中文](https://github.com/hx101700/asr-agent/blob/v0.1.0/release/NOTES.md) | English

asr-transcription v0.1.0 provides a recording transcription Skill. Once installed, ask Codex to transcribe a recording, configure it on a local page, and receive Word, Excel, and Markdown documents to review and correct.

### Features

- Add one recording and adjust language, speaker identification, and save locations.
- Import Excel hotwords and enter context. Both enhancement options can be used together.
- Authorize through the Model Studio console or use your API Key. The official BL CLI performs recognition.
- Keep the original JSON and all three documents, with local re-export for existing tasks.

### Installation and file storage

Install the Skill independently and keep recording tasks, credentials, and dependencies in your chosen workspace. Save locations stay outside the Skill's program directory, so you can manage the tools and transcript files separately.

### Get started

Download [asr-transcription.zip](https://github.com/hx101700/asr-agent/releases/download/v0.1.0/asr-transcription.zip) and send it to Codex and ask it to install the Skill and read its `SKILL.md`. Choose a separate workspace. Codex prepares the environment and opens the configuration page, then guides authentication for the method you choose.

Windows 10/11 x64, Python 3.12 x64, and Node.js 18.17+ with npm are required. Recognition uses `qwen-audio-3.0-asr-flash-filetrans` in Beijing and may incur charges. Stage one delivers transcripts for review; meeting summaries belong to a later stage.

See the [project README](https://github.com/hx101700/asr-agent/blob/v0.1.0/README.en.md) for instructions. Report problems through [Issues](https://github.com/hx101700/asr-agent/issues).
