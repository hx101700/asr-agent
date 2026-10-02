"""预览用例：协调本机文件、媒体和热词读取，再应用输入规则。"""

from dataclasses import asdict
from pathlib import Path

from ..utils.files import FileError, check_file_unchanged, file_fingerprint, resolve_input
from ..utils.hotwords import HotwordFileError, read_hotwords
from ..utils.media import MediaError, probe_audio
from .rules import AUDIO_SUFFIXES, ValidationError, build_vocabulary, check_audio_limits


def validate_audio(input_root: Path, path: str | Path, diarization: bool) -> dict:
    """校验音频，返回媒体属性、内容摘要和处理提示。"""
    field = "audio_path"
    try:
        source = resolve_input(input_root, path, AUDIO_SUFFIXES)
        if not isinstance(diarization, bool):
            raise ValidationError("说话人选项必须为开启或关闭。", "diarization")
        before = source.stat()
        if before.st_size == 0:
            raise ValidationError("音频文件为空。", field)
        info = probe_audio(source)
        check_audio_limits(info, diarization)
        duration = info.duration_seconds
        requires_mono = diarization and info.channels > 1
        warnings = []
        if requires_mono:
            warnings.append(
                f"此音频包含 {info.channels} 个声道。为区分发言人，转写前将生成单声道 FLAC 副本，"
                "保留原文件。副本通过大小和时长检查后才会上传。"
            )
        if diarization and duration > 2 * 60 * 60:
            warnings.append("音频超过 2 小时。启用发言人区分可能导致识别失败或超时，建议使用 2 小时以内的音频。")
        if info.audio_tracks > 1:
            warnings.append(f"此文件包含 {info.audio_tracks} 个音轨，仅转写第一个音轨（索引0），其余音轨不会转写。")
        fingerprint = file_fingerprint(source)
        after = source.stat()
        if (fingerprint["size_bytes"] != info.size_bytes
                or (before.st_size, before.st_mtime_ns, before.st_ino)
                != (after.st_size, after.st_mtime_ns, after.st_ino)):
            raise ValidationError("文件在校验期间发生变化，请重新校验。", field)
        return {"path": str(source), "metadata": asdict(info), "fingerprint": fingerprint,
                "requires_mono": requires_mono, "warnings": warnings}
    except FileError as exc:
        raise ValidationError(str(exc), field) from exc
    except (MediaError, OSError) as exc:
        raise ValidationError("无法读取音频，请检查文件是否损坏及格式是否支持。", field) from exc


def load_hotwords(input_root: Path, path: str | Path) -> dict:
    """读取并校验热词Excel，返回即时词典和导入提示。"""
    field = "hotwords_path"
    try:
        source = resolve_input(input_root, path, {".xlsx"})
        before = source.stat()
        rows, warnings = read_hotwords(source)
        result = build_vocabulary(rows)
        result["warnings"] = warnings + result["warnings"]
        check_file_unchanged(source, {"size_bytes": before.st_size, "mtime_ns": before.st_mtime_ns})
        return result
    except HotwordFileError as exc:
        raise ValidationError(str(exc), field, exc.details) from exc
    except FileError as exc:
        raise ValidationError(str(exc), field) from exc
    except OSError as exc:
        raise ValidationError("无法读取热词Excel，请检查文件是否损坏或仍在写入。", field) from exc
