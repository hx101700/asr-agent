"""从用户提供的 ZIP 更新已安装的 Skill，保留工作目录中的运行数据。"""

import argparse
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import tempfile
from typing import TypedDict
from zipfile import BadZipFile, ZipFile


class UpdateReport(TypedDict):
    """描述资源替换及依赖锁是否改变。"""

    status: str
    skill_dir: str
    dependencies_changed: bool
    retained_backup: str | None


def _check_skill(directory: Path) -> None:
    """核对目录中的 Skill 名称与执行入口。"""
    content = (directory / "SKILL.md").read_text(encoding="utf-8-sig")
    sections = content.split("---", 2)
    if (len(sections) != 3 or sections[0].strip()
            or not re.search(r"(?m)^name:\s*(?:asr-transcription|'asr-transcription'|\"asr-transcription\")\s*$", sections[1])
            or not (directory / "scripts/asr.py").is_file()):
        raise ValueError("请选择 asr-transcription 的 Skill 安装目录和发行 ZIP。")


def _extract_package(archive_path: Path, destination: Path) -> None:
    """解压普通发行文件并拒绝越界、链接和重复的 Windows 路径。"""
    seen: set[str] = set()
    with ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            name = entry.orig_filename
            path = PurePosixPath(name)
            mode = stat.S_IFMT(entry.external_attr >> 16)
            normalized = name.rstrip("/").casefold()
            if (not name or path.is_absolute() or "\\" in name or ":" in name
                    or any(ord(character) < 32 or ord(character) == 127 for character in name)
                    or any(not part or part.endswith((" ", ".")) or PureWindowsPath(part).is_reserved()
                           for part in name.rstrip("/").split("/"))
                    or normalized in seen
                    or mode not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or path.parts[0] not in {"SKILL.md", "LICENSE", "agents", "scripts", "references", "assets"}):
                raise ValueError(f"ZIP 含不支持的发行路径：{name}")
            seen.add(normalized)
            target = destination.joinpath(*path.parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
    _check_skill(destination)


def update_skill(archive_path: Path, skill_dir: Path, *, tasks_finished: bool) -> UpdateReport:
    """暂存资源并整体替换 Skill，报告结果与保留的备份。"""
    if os.name != "nt":
        raise ValueError("此更新入口适用于 Windows。")
    if not tasks_finished:
        raise ValueError("请先确认使用此 Skill 的任务均已结束，再传入 --tasks-finished。")
    skill_dir = skill_dir.resolve(strict=True)
    archive_path = archive_path.resolve(strict=True)
    _check_skill(skill_dir)
    if Path(__file__).resolve().is_relative_to(skill_dir) or archive_path.is_relative_to(skill_dir):
        raise ValueError("请从安装目录之外的新 ZIP 解压目录运行更新脚本，并将 ZIP 保留在安装目录之外。")

    # 与目标保持同卷，目录改名既避免逐文件混用，也让运行入口的只读句柄阻止热替换。
    temporary = Path(tempfile.mkdtemp(prefix=".asr-transcription-update-", dir=skill_dir.parent))
    candidate = temporary / "candidate"
    previous = temporary / "previous"
    try:
        candidate.mkdir()
        _extract_package(archive_path, candidate)
        dependency_files = ("scripts/requirements.txt", "scripts/bailian/package-lock.json")
        # 两种锁都必须读取完成，不能因Python锁先变化而跳过BL锁的检查。
        dependency_changes = [
            (candidate / name).read_bytes() != (skill_dir / name).read_bytes()
            for name in dependency_files
        ]
        dependencies_changed = any(dependency_changes)
        try:
            skill_dir.rename(previous)
        except PermissionError as exc:
            raise ValueError("Skill 正被任务使用，或安装目录没有修改权限；原资源已保留。请结束相关任务或检查目录权限后再更新。") from exc
        candidate.rename(skill_dir)
    except BaseException:
        # 两次改名及其中断共用恢复边界；安装位置已被接管时不覆盖现有资源。
        if previous.exists() and not skill_dir.exists():
            try:
                previous.rename(skill_dir)
            except BaseException:
                raise RuntimeError(f"更新未完成，原 Skill 保留在：{previous}") from None
        if previous.exists():
            raise RuntimeError(f"更新未完成，安装位置已有资源，未覆盖该目录；原 Skill 保留在：{previous}") from None
        shutil.rmtree(temporary)
        raise

    retained_backup: str | None = None
    try:
        shutil.rmtree(temporary)
    except OSError:
        retained_backup = str(temporary)
    return {"status": "updated", "skill_dir": str(skill_dir),
            "dependencies_changed": dependencies_changed, "retained_backup": retained_backup}


def main(argv: list[str] | None = None) -> int:
    """读取更新目标与 ZIP，输出操作结果。"""
    parser = argparse.ArgumentParser(description="更新已安装的 asr-transcription Skill。")
    parser.add_argument("--zip", type=Path, required=True, help="用户提供的发行 ZIP")
    parser.add_argument("--skill-dir", type=Path, required=True, help="已安装的 Skill 目录")
    parser.add_argument("--tasks-finished", action="store_true", help="已确认使用此 Skill 的任务均已结束")
    args = parser.parse_args(argv)
    try:
        report = update_skill(args.zip, args.skill_dir, tasks_finished=args.tasks_finished)
    except (OSError, ValueError, RuntimeError, BadZipFile) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
