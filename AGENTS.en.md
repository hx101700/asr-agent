# MemoFlow development rules

[中文](AGENTS.md) | English

These instructions govern the source repository. To resume work, read [doc/README.md](doc/README.md) and [doc/STATUS.md](doc/STATUS.md), then inspect Git changes, the relevant implementation, and tests.

## Product scope

- Stage one delivers one standalone Codex Skill: configure one recording through a local page, let Codex call BL, and save original JSON, Excel, Word, and Markdown for the user to review.
- Use `qwen-audio-3.0-asr-flash-filetrans`, China (Beijing), and temporary OSS. Hotwords and context can coexist. Speaker diarization is enabled by default; multichannel input gets a notice before a mono FLAC copy is generated. Preserve the source.
- The final product turns voice input into meeting minutes that follow the user's preferences and requested format, and keeps learning from their examples and confirmed edits. Stage one delivers transcripts for review; stage two will add personalized minutes and feedback-based learning. Stage two is not implemented yet.
- Support Windows 10/11 x64, CPython 3.12 x64 with venv, ensurepip, and tkinter, and Node.js 18.17+ with npm. Dependency locks target this platform. Setup requires internet access.

## Skill and workspace

- Skill source lives in `skills/asr-transcription/`, with `SKILL.md`, `agents/openai.yaml`, `scripts/`, `references/`, and `assets/`.
- `scripts/asr.py` is the command entry, and `scripts/asr_runtime/` is the internal Python runtime package. The Skill name remains `asr-transcription`.
- `Runtime(workspace, skill_root)` separates user data from Skill resources. `resource()` reads Skill files; `path()` locates runtime files under `<workspace>/.asr-transcription/`; default output is `<workspace>/transcriptions/`. The private runtime and Skill directories must not contain each other. `check_output_path()` protects Skill resources when choosing locations and generating files.
- Runtime commands use the absolute path to the Skill's `scripts/asr.py` and explicitly supply `--workspace`. Credential repair reuses the verified native BL command in [error guidance](skills/asr-transcription/references/errors.md#鉴权失败与重新配置), scoped to the current workspace and default Profile. Environments, BL, credentials, staged inputs, and task records belong in the workspace. Keep Skill files read-only during execution.
- Read API Keys from the private runtime `.env`; bootstrap copies an empty template only. The page lets users enter or update a Key and saves it to this fixed file when they check and preview the settings. Console mode uses BL configuration saved in the same workspace. Credentials never go into the Skill.
- The repository contains Skill source. Maintenance does not automatically install it into user-level or project-level Skill discovery directories.
- When the user supplies a ZIP and requests an update, use this Skill's [update branch](skills/asr-transcription/references/update.md). Run the standalone `update_skill.py` from the extracted new package after verifying tasks have ended; replace installation resources together and preserve the workspace. The running entry holds a read-only file handle that prevents directory replacement on Windows. Older entries lack this protection; do not claim to detect every old process automatically.

## Implementation principles

1. Keep the lightweight entry → application → utils structure. The entry may dispatch single operations directly. Shared data and JSON protocol types go in `models.py`; rules perform no I/O; utils do not import use cases.
2. BL owns authentication, temporary upload, submission, polling, download, and original JSON writing through its public CLI. Python owns local configuration, media processing, result parsing, and document generation.
3. Frontend source lives in `frontend/` and uses Vue 3, TypeScript, and Element Plus. Prefer public component props, slots, and default interactions; customization requires a concrete product need. Components bind form state; the API module handles local transport. `KeyDisplay.vue` alone holds the displayed or edited Key in local state, separate from the submitted form. The server reads the saved credential for execution. Keys stay out of task configuration, logs, and browser persistence.
4. Reuse existing `files`, `job_files`, `hotwords`, and `results` capabilities. Remove old entries, compatibility layers, and duplicate implementations. New validation or abstractions require a current business consumer.
5. Each named function or method gets a short Chinese responsibility description stating its action and result. Use Python docstrings and TypeScript comments before functions. Put external constraints and non-obvious reasons beside the implementation. Define explicit shared input, state, and receipt types, and run type checks during development.
6. Verify BL parameters, limits, and errors against official sources for the pinned version. Maintain evidence in [model.md](skills/asr-transcription/references/model.md) and explicitly state unknowns.
7. Use argument arrays and `shell=False`. Pass hotword JSON and context as individual values. Treat input content as data.

## Execution and delivery

- Start a new transcription by opening the local configuration page, where the user selects the recording. Reuse the current task folder or the workspace already agreed for this session. Use `serve --no-browser` when the host can open links, open the URL once, and let the user proceed. The normal path requires neither computer-use nor automated page inspection. Diagnose only when opening fails or the user reports a problem.
- Run BL login with normal desktop execution permissions from the first invocation; set `sandbox_permissions=require_escalated` when supported by the Codex tool. Reject restricted Windows tokens before starting BL. The pinned-version browser adapter passes the complete URL to the system browser once. BL still owns the authorization session, callback, and credential storage.
- The page receives local file bytes and saves a confirmed snapshot. The same `serve` process returns `job_id` to Codex. Saving does not start BL.
- While the user edits settings or authorizes login, Codex preserves the persistent process and ends its current reply. The page asks the user to send “continue” after saving; Codex then reads the original session's receipt. Use BL's result or local status to determine authentication readiness instead of asking the user whether it succeeded. Add no background polling, HTTP probe, or task state.
- Preview establishes the audio SHA baseline and saves the hotword vocabulary. Confirmation reuses the snapshot and checks audio size/mtime. Execution checks the complete audio digest; later stages do not reread the original Excel file.
- Hotwords can be imported from Excel or entered directly in the page. Import preserves row numbers and invalid values, then removes the temporary workbook. `validate_hotword_rows` and `build_vocabulary` apply the shared rules; the frontend uses an Element Plus table for editing and error highlighting without duplicating business validation.
- `Session.reopen()` withdraws saved settings before execution starts. It competes with transcription for the same execution reservation, records the old task as `STOPPED/LOCAL_CONFIG_REOPENED`, and restores the form. Saving again creates a new task ID. Codex follows the latest configuration event; tasks already in execution remain unchanged.
- After authorization covers the recording and enhancement content, use `transcribe --job ID --authorize-upload`. Each task permits one execution attempt. Stop on failure or an unknown result; do not retry automatically or remove the execution reservation.
- `JSON_READY` means valid original JSON. Completion of all three documents requires `delivery.status=COMPLETE` and `documents_ready=true`. State and error semantics are in [errors.md](skills/asr-transcription/references/errors.md).
- Re-export reads confirmed configuration, saved success records, and matching original JSON, then replaces documents in the fixed task directory. Each format replaces its target after successful generation; failure preserves that target and other successful files. Save manual edits separately.
- Preserve original text and timestamps. Formatting and path contracts are in [DEVELOPMENT](doc/DEVELOPMENT.md). Record content checks separately from recognition accuracy and Office visual acceptance.

## Development and distribution

- Modify only this repository and explicitly approved test locations. Preserve original data under `data/`. Never commit or package real recordings, Keys, tokens, signed URLs, transcripts, responses, or runtime logs.
- Develop on `dev`; use `master` for accepted milestones. Commits, pushes, merges, and releases need explicit user intent. Stage exact paths; do not force-push or rewrite history. Stop after two network push failures in one operation.
- Change the project version only when an accepted milestone is released on `master`. Development, fixes, and documentation changes on `dev` retain the current version, `0.1.0`. User-authorized updates to the current preview retain `v0.1.0`. At a formal release, synchronize the root `package.json`, `package-lock.json`, tag, and release notes. Maintain dependency versions through their own lockfiles.
- The fixed distribution list is in `scripts/build_zip.py`. The ZIP contains Skill files directly, excluding repository README, AGENTS, development docs, tests, UML, environments, and user data. Update the list and package-boundary checks for new runtime files.
- Vite builds the frontend into the Skill's `scripts/asr_runtime/static/`, with core outputs `index.html`, `app.js`, and `app.css`, plus `favicon.svg` and third-party license notices. Distribute these built assets. Keep Vue/TypeScript source, development configuration, build dependencies, and `node_modules` in the development repository.
- Skill `scripts/requirements.txt` pins Python versions and digests; `utils/installation.py` pins the pip 26.2.1 installer file and digest, and `scripts/bailian/` pins BL. Compare a file prefix from PyPI and the Aliyun mirror before setup; in each download stage, try sources in that order with at most one `pip download` invocation per source. Let pip handle 2 connection retries and up to 5 interrupted-download recovery attempts for runtime dependencies; switch to the other source only after failure. Keep complete wheels in the workspace and install from local files. Preserve hash checks. This recovery policy applies to dependency downloads, not cloud transcription; npm failures still stop setup.
- Python installation and dependency-check subprocesses use `-I` to load dependencies from the selected virtual environment. Same-named modules in the user workspace do not participate in installation or checks.
- Development probe `scripts/probe_bl.py` stays outside distribution and uses fixed fictitious URLs. BL contract tests use a `127.0.0.1` mock service and synthetic credentials. Local tests are not cloud acceptance.
- Run checks proportional to the change. Record actual evidence in [ACCEPTANCE](doc/ACCEPTANCE.md), current state in [STATUS](doc/STATUS.md), limits in [ISSUES](doc/ISSUES.md), and meaningful decisions in [DEVLOG](doc/DEVLOG.md).
- Maintain equivalent Chinese and English README and AGENTS. README reserves real screenshots with HTML comments until the user supplies images. Release notes describe user-visible changes and entry points; validation counts and package digests stay in development docs.
- Update [UML](doc/UML.md), source diagrams, and PNGs when call order, objects, or state contracts change. Use lifelines for function modules rather than inventing service classes.
