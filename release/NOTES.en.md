[中文](https://github.com/hx101700/asr-agent/releases/tag/v0.1.1) | English

This update makes exported files easier to find. Previously, each re-export created another folder, leaving documents for the same recording in different places. A task now has one set of Word, Excel, and Markdown files, so you can return to the same location after re-exporting.

## A fixed location for your documents

All three documents are saved directly in the task's `documents` folder:

```text
documents/
├── transcription.docx
├── transcription.xlsx
└── transcription.md
```

Re-export updates these files. It reads the saved recognition result and generates documents locally, without uploading the recording or starting recognition again. If one format fails to write, its existing file is preserved and the other formats are still processed.

## Before you re-export

If you have edited a Word or Excel document and want to keep those changes, save a separate copy first. Folders and files created by older versions stay in their original locations for you to organize as needed.

The Chinese and English guides, agent rules, and UML have also been updated to match the new output paths.

## Download and get started

Download **asr-agent.zip** from the [release assets](https://github.com/hx101700/asr-agent/releases/tag/v0.1.1), extract it, open the `asr-agent` folder in Codex, and ask: “Install asr-agent and open the recording transcription page.” See the [user guide](https://github.com/hx101700/asr-agent/blob/v0.1.1/README.en.md) for prerequisites and account setup.

Speech recognition is provided by [Alibaba Cloud Model Studio](https://help.aliyun.com/zh/model-studio/what-is-model-studio) through its official [BL CLI](https://github.com/modelstudioai/cli). asr-agent brings together local file selection, enhancement settings, and document delivery.
