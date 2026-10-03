[中文](https://github.com/hx101700/memoflow/blob/v0.1.0/release/NOTES.md) | English

MemoFlow aims to turn recordings into meeting minutes that follow your preferred style and format. This v0.1.0 development preview delivers the first step: let Codex transcribe a recording and produce timestamped Word, Excel, and Markdown documents for you to review and correct.

### Features

- **Local configuration page**: Add one recording and choose the language, speaker diarization, and save locations. Chinese and English interfaces and light and dark themes are available.
- **Recognition enhancement**: Enter hotwords in the table or import an Excel file and edit it directly. Errors appear on the affected rows; review duplicate terms and keep one entry. Hotwords and context can be used together.
- **Model Studio recognition**: Qwen-Audio-3.1-ASR-Flash-Filetrans runs through the official BL CLI. Choose Console login or enter and save your own Beijing-region API key on the page.
- **Document delivery**: Keep the original JSON and all three transcript formats. Successful tasks can be re-exported locally.

### Using the preview

After saving your settings, return to Codex and send “continue.” You can return to editing before transcription starts. If the response to a withdrawal request is interrupted, refreshing the original page restores the confirmed settings still held by the same service. Later unsaved edits are not retained.

This update fixes hotword pagination jumping after a deletion, overlapping error messages in narrow windows, temporary file collisions during local export, and recovery after an interrupted update. The page, Skill instructions, and developer diagrams have also been checked against the implementation.

### Get started

Create an Alibaba Cloud account and complete the platform's identity verification and Model Studio setup. Download [asr-transcription.zip](https://github.com/hx101700/memoflow/releases/download/v0.1.0/asr-transcription.zip) and send it to Codex with this request:

> Extract the ZIP, read its SKILL.md, and help me install and configure asr-transcription.

Once installed, ask Codex to transcribe a recording, then add your file and settings on the page it opens. Existing users can send the new ZIP to Codex and ask it to update the Skill. Finish running operations first; the update replaces tool resources while preserving credentials, recordings, and results in the workspace.

This preview supports Windows 10/11 x64 and requires Python 3.12 x64, Node.js 18.17+, and npm. Recognition uses the Beijing region and may incur charges. Personalized minutes and learning from feedback are planned for a later stage.

See the [README](https://github.com/hx101700/memoflow/blob/v0.1.0/README.en.md) for instructions, or report a problem through [Issues](https://github.com/hx101700/memoflow/issues).
