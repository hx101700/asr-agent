"""官方转写JSON的唯一读取边界；内存结果供三种格式共同使用。"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .environment import SetupError


@dataclass(frozen=True)
class Sentence:
    index: int
    track_index: int
    channel_id: int | None
    begin_ms: int
    end_ms: int
    speaker_id: int | None
    text: str


@dataclass(frozen=True)
class Transcript:
    sentences: tuple[Sentence, ...]
    audio_tracks: int
    json_bytes: int
    sha256: str

    def summary(self) -> dict:
        return {"audio_tracks": self.audio_tracks, "sentences": len(self.sentences),
                "json_bytes": self.json_bytes, "sha256": self.sha256}


def timestamp(milliseconds: int) -> str:
    seconds, millis = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def load_transcript(path: Path) -> Transcript:
    """保留音轨/句子的原始顺序、空句及原文，不猜测其他模型的字段别名。"""
    try:
        if path.resolve() != path:
            raise ValueError("redirected result")
        content = path.read_bytes()
        result = json.loads(content.decode("utf-8"))
        if not isinstance(result, dict) or not isinstance(result["transcripts"], list):
            raise ValueError("unexpected document")
        sentences = []
        for track_index, track in enumerate(result["transcripts"], 1):
            if not isinstance(track, dict) or not isinstance(track["sentences"], list):
                raise ValueError("unexpected track")
            channel = track.get("channel_id")
            if channel is not None and (type(channel) is not int or channel < 0):
                raise ValueError("unexpected channel")
            for sentence in track["sentences"]:
                begin, end = sentence["begin_time"], sentence["end_time"]
                if (type(begin) is not int or type(end) is not int or not 0 <= begin <= end
                        or not isinstance(sentence["text"], str)):
                    raise ValueError("unexpected sentence")
                speaker = sentence.get("speaker_id")
                if speaker is not None and (type(speaker) is not int or speaker < 0):
                    raise ValueError("unexpected speaker")
                sentences.append(Sentence(len(sentences) + 1, track_index, channel,
                                          begin, end, speaker, sentence["text"]))
        if not any(sentence.text.strip() for sentence in sentences):
            raise ValueError("no usable transcript")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SetupError("BL未生成可用的转写JSON，或结果结构不符合已核实契约。已保留现有文件；未推断失败原因，未重新识别。") from exc
    return Transcript(tuple(sentences), len(result["transcripts"]), len(content),
                      hashlib.sha256(content).hexdigest())
