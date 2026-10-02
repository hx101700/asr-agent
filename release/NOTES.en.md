[中文](https://github.com/hx101700/memoflow/blob/v0.1.0/release/NOTES.md) | English

MemoFlow is being built to turn recordings into meeting minutes that follow your preferred style and format, and improve from your confirmed edits. This v0.1.0 development preview delivers the first part: the `asr-transcription` Skill produces Word, Excel, and Markdown transcripts for you to review and correct.

### Features

- Add one recording and adjust the audio language, speaker diarization, and save locations.
- Switch between Chinese and English, and choose Light, Dark, or System appearance.
- Import Excel hotwords and enter context. Both enhancement options can be used together.
- Use Console login or enter your API key on the page. Checking your settings saves the key to your workspace. The official BL CLI performs recognition.
- Keep the original JSON and all three documents, with local re-export for existing tasks.

### Installation and file storage

Install the Skill independently and keep recording tasks, credentials, and dependencies in your chosen workspace. Save locations stay outside the Skill's program directory, so you can manage the tools and transcript files separately.

### Get started

Download [asr-transcription.zip](https://github.com/hx101700/memoflow/releases/download/v0.1.0/asr-transcription.zip) and send it to Codex and ask it to install the Skill and read its `SKILL.md`. Choose a separate workspace. Codex prepares the environment and opens the configuration page, then guides authentication for the method you choose.

Windows 10/11 x64, Python 3.12 x64, and Node.js 18.17+ with npm are required. Recognition uses `qwen-audio-3.0-asr-flash-filetrans` in Beijing and may incur charges. Personalized minutes, style preferences, and learning from feedback are planned for stage two.

See the [project README](https://github.com/hx101700/memoflow/blob/v0.1.0/README.en.md) for instructions. Report problems through [Issues](https://github.com/hx101700/memoflow/issues).
