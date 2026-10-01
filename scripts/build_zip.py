"""构建面向使用者的 Agent ZIP；文件清单固定，只依赖标准库。"""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


REQUIRED_FILES = (
    "LICENSE", ".env.example", "requirements.txt", "scripts/asr.py",
    "tools/bailian/package.json", "tools/bailian/package-lock.json",
    "doc/HELP.md", "doc/ERRORS.md", "doc/REFERENCES.md",
    ".agents/skills/asr-agent/SKILL.md",
    "src/asr_agent/__init__.py", "src/asr_agent/__main__.py",
    "src/asr_agent/models.py", "src/asr_agent/web.py", "src/asr_agent/error_catalog.json",
    "src/asr_agent/application/__init__.py", "src/asr_agent/application/bootstrap.py",
    "src/asr_agent/application/diagnostics.py", "src/asr_agent/application/session.py",
    "src/asr_agent/application/transcription.py", "src/asr_agent/application/delivery.py",
    "src/asr_agent/application/inputs.py", "src/asr_agent/application/rules.py",
    "src/asr_agent/tools/__init__.py", "src/asr_agent/tools/environment.py",
    "src/asr_agent/tools/auth.py", "src/asr_agent/tools/bailian.py",
    "src/asr_agent/tools/media.py", "src/asr_agent/tools/results.py",
    "src/asr_agent/tools/documents.py", "src/asr_agent/tools/directory_picker.py",
    "src/asr_agent/tools/_directory_dialog.py", "src/asr_agent/tools/files.py",
    "src/asr_agent/tools/job_files.py", "src/asr_agent/tools/hotwords.py",
    "src/asr_agent/static/index.html", "src/asr_agent/static/app.css",
    "src/asr_agent/static/app.mjs", "src/asr_agent/static/model.mjs",
    "src/asr_agent/static/view.mjs", "src/asr_agent/static/api.mjs",
)
RELEASE_TEMPLATES = {
    "README.md": "release/README.md",
    "AGENTS.md": "release/AGENTS.md",
    ".gitignore": "release/.gitignore",
}


def release_files(root: Path) -> dict[str, Path]:
    """校验固定发行清单，返回归档名称与源码路径的映射。"""
    files = {name: root / name for name in REQUIRED_FILES}
    files.update({name: root / source for name, source in RELEASE_TEMPLATES.items()})
    for path in files.values():
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError(f"发行文件不是普通文件：{path.relative_to(root).as_posix()}")
    return dict(sorted(files.items()))


def build_zip(root: Path, destination: Path | None = None) -> dict:
    """按固定发行清单创建ZIP并返回包内容清单。"""
    root = root.resolve(strict=True)
    files = release_files(root)
    destination = destination or root / "dist" / "asr-agent.zip"
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    names = [f"asr-agent/{name}" for name in files]
    # x 模式拒绝覆盖既有包。
    with ZipFile(destination, "x", compression=ZIP_DEFLATED) as archive:
        for name, path in files.items():
            archive.write(path, f"asr-agent/{name}")
    return {"status": "created", "path": str(destination), "file_count": len(names), "files": names}


def main() -> int:
    """解析构建目标并输出JSON结果，构建失败返回非零退出码。"""
    parser = argparse.ArgumentParser(description="构建用户发行 ZIP：运行代码、Skill、依赖锁和使用文档。")
    parser.add_argument("--output", type=Path, help="输出 ZIP 路径；已有文件不会覆盖")
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
