"""定义用例与工具共享的音频、热词和转写数据结构。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioInfo:
    channels: int
    sample_rate: int
    duration_seconds: float | None
    size_bytes: int
    format_name: str
    audio_tracks: int


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
        """提取结果规模和内容摘要，供执行记录核对来源。"""
        return {"audio_tracks": self.audio_tracks, "sentences": len(self.sentences),
                "json_bytes": self.json_bytes, "sha256": self.sha256}


@dataclass(frozen=True)
class HotwordRow:
    number: int
    text: object
    weight: object
    has_formula: bool
