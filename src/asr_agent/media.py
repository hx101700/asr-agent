"""用PyAV自带的FFmpeg库探测和合并声道，不依赖外部可执行程序。"""

from dataclasses import dataclass
from pathlib import Path

import av


class MediaError(ValueError):
    """媒体内容或转换结果不符合要求。"""


@dataclass(frozen=True)
class AudioInfo:
    channels: int
    sample_rate: int
    duration_seconds: float | None
    size_bytes: int
    format_name: str
    audio_tracks: int


def probe_audio(path: Path) -> AudioInfo:
    """探测第一个音轨，与首版BL默认音轨选择一致；不读取标题等私有标签。"""
    path = path.resolve(strict=True)
    if not path.is_file():
        raise MediaError("请选择本地音频文件。")
    try:
        with av.open(str(path), options={"protocol_whitelist": "file"}) as container:
            if not container.streams.audio:
                raise MediaError("文件没有可识别的音轨。")
            stream = container.streams.audio[0]
            duration = None
            if stream.duration is not None and stream.time_base is not None:
                duration = float(stream.duration * stream.time_base)
            elif container.duration is not None:
                duration = container.duration / av.time_base
            channels = len(stream.codec_context.layout.channels)
            rate = stream.codec_context.sample_rate
            if channels < 1 or rate < 1:
                raise MediaError("无法确定音频声道数或采样率。")
            return AudioInfo(channels, rate, duration, path.stat().st_size,
                             container.format.name, len(container.streams.audio))
    except av.FFmpegError as exc:
        raise MediaError("无法读取音频，请检查文件是否损坏或格式是否支持。") from exc


def convert_to_mono(source: Path, destination: Path) -> AudioInfo:
    """生成并检测单声道FLAC，返回实测信息供模型限额检查复用；单声道输入不另建副本。"""
    source = source.resolve(strict=True)
    destination = destination.resolve()
    info = probe_audio(source)
    if info.channels == 1:
        return info
    if destination == source or destination.suffix.lower() != ".flac":
        raise MediaError("单声道副本必须使用不同于源文件的.flac路径。")

    created = False
    samples = 0
    try:
        with av.open(str(source), options={"protocol_whitelist": "file"}) as original:
            # xb保证不覆盖已有文件；逐帧处理，避免将长音频整体读入内存。
            with destination.open("xb") as file:
                created = True
                with av.open(file, mode="w", format="flac") as output:
                    stream = output.add_stream("flac", rate=info.sample_rate)
                    stream.layout = "mono"
                    stream.format = "s32"
                    resampler = av.AudioResampler(format="s32", layout="mono", rate=info.sample_rate)

                    def write_frames(frames):
                        for frame in frames:
                            for packet in stream.encode(frame):
                                output.mux(packet)

                    for frame in original.decode(audio=0):
                        samples += frame.samples
                        write_frames(resampler.resample(frame))
                    write_frames(resampler.resample(None))
                    for packet in stream.encode(None):
                        output.mux(packet)

        converted = probe_audio(destination)
        if (samples == 0 or converted.channels != 1 or converted.sample_rate != info.sample_rate
                or converted.duration_seconds is None
                or abs(converted.duration_seconds - samples / info.sample_rate) > 1 / info.sample_rate):
            raise MediaError("转换后的声道、采样率或有效样本时长检查失败。")
        return converted
    except (av.FFmpegError, OSError, ValueError):
        # 只删除本次以xb新建的失败副本，原文件及已存在目标不受影响。
        if created:
            destination.unlink(missing_ok=True)
        raise
