"""按固定清单构建可独立安装的录音转写 Skill。"""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SKILL_DIRECTORY = Path("skills/asr-transcription")
REQUIRED_FILES = (
    "SKILL.md", "agents/openai.yaml", "LICENSE", "assets/env.example",
    "references/usage.md", "references/errors.md", "references/model.md",
    "scripts/asr.py", "scripts/requirements.txt",
    "scripts/bailian/package.json", "scripts/bailian/package-lock.json",
    "scripts/asr_transcription/__init__.py", "scripts/asr_transcription/__main__.py",
    "scripts/asr_transcription/models.py", "scripts/asr_transcription/web.py",
    "scripts/asr_transcription/error_catalog.json",
    "scripts/asr_transcription/application/__init__.py",
    "scripts/asr_transcription/application/bootstrap.py",
    "scripts/asr_transcription/application/diagnostics.py",
    "scripts/asr_transcription/application/session.py",
    "scripts/asr_transcription/application/transcription.py",
    "scripts/asr_transcription/application/delivery.py",
    "scripts/asr_transcription/application/inputs.py",
    "scripts/asr_transcription/application/rules.py",
    "scripts/asr_transcription/utils/__init__.py",
    "scripts/asr_transcription/utils/environment.py",
    "scripts/asr_transcription/utils/auth.py",
    "scripts/asr_transcription/utils/bailian.py",
    "scripts/asr_transcription/utils/media.py",
    "scripts/asr_transcription/utils/results.py",
    "scripts/asr_transcription/utils/documents.py",
    "scripts/asr_transcription/utils/directory_picker.py",
    "scripts/asr_transcription/utils/_directory_dialog.py",
    "scripts/asr_transcription/utils/files.py",
    "scripts/asr_transcription/utils/job_files.py",
    "scripts/asr_transcription/utils/hotwords.py",
    "scripts/asr_transcription/static/index.html",
    "scripts/asr_transcription/static/app.css",
    "scripts/asr_transcription/static/app.mjs",
    "scripts/asr_transcription/static/model.mjs",
    "scripts/asr_transcription/static/view.mjs",
    "scripts/asr_transcription/static/api.mjs",
)


def release_files(skill_root: Path) -> dict[str, Path]:
    """核对 Skill 固定文件清单并返回归档路径映射。"""
    files = {name: skill_root / name for name in REQUIRED_FILES}
    for name, path in files.items():
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError(f"发行文件不是普通文件：{name}")
    return dict(sorted(files.items()))


def build_zip(root: Path, destination: Path | None = None) -> dict:
    """从仓库的 Skill 源文件创建 ZIP 并返回包清单。"""
    root = root.resolve(strict=True)
    files = release_files(root / SKILL_DIRECTORY)
    destination = (destination or root / "dist/asr-transcription.zip").resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "x", compression=ZIP_DEFLATED) as archive:
        for name, path in files.items():
            archive.write(path, name)
    return {"status": "created", "path": str(destination),
            "file_count": len(files), "files": list(files)}


def main() -> int:
    """解析输出位置，构建用户 Skill 包并打印 JSON 回执。"""
    parser = argparse.ArgumentParser(description="构建可独立安装的 asr-transcription Skill。")
    parser.add_argument("--output", type=Path, help="输出 ZIP 路径；已有文件会保留")
    options = parser.parse_args()
    try:
        report = build_zip(Path(__file__).resolve().parents[1], options.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
