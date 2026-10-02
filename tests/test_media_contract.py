"""用合成音频验证PyAV解码和声道合并。"""

import hashlib
import os
import struct
import wave
from unittest.mock import patch

import av

from asr_runtime.utils.media import MediaError, convert_to_mono, probe_audio
from tests.support import RuntimeTestCase


class MediaContractTests(RuntimeTestCase):
    def setUp(self):
        """生成合成媒体并准备声道转换测试。"""
        super().setUp()
        self.source = self.runtime.path("双声道 test.wav")
        self.output = self.runtime.path("单声道 output.flac")
        frames = b"".join(struct.pack("<hh", 8000 if i < 8000 else 0, 0 if i < 8000 else 8000)
                          for i in range(16000))
        with wave.open(str(self.source), "wb") as audio:
            audio.setnchannels(2)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(frames)
        self.source_info = probe_audio(self.source)

    def test_mono_flac_preserves_rate_duration_and_source(self):
        """验证单声道FLAC保留采样率、时长和原文件。"""
        original = hashlib.sha256(self.source.read_bytes()).digest()
        info = convert_to_mono(self.source, self.output, self.source_info)
        self.assertEqual(info, probe_audio(self.output))
        self.assertEqual(info.channels, 1)
        self.assertEqual(info.sample_rate, 16000)
        self.assertAlmostEqual(info.duration_seconds, 1.0, places=5)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(), original)

    def test_both_stereo_channels_contribute(self):
        """验证立体声两侧都参与单声道合并。"""
        convert_to_mono(self.source, self.output, self.source_info)
        chunks = []
        converter = av.AudioResampler(format="s16", layout="mono", rate=16000)
        with av.open(str(self.output)) as output:
            for decoded in output.decode(audio=0):
                for frame in converter.resample(decoded):
                    chunks.append(bytes(frame.planes[0])[:frame.samples * 2])
            for frame in converter.resample(None):
                chunks.append(bytes(frame.planes[0])[:frame.samples * 2])
        samples = list(struct.iter_unpack("<h", b"".join(chunks)))
        self.assertEqual(len(samples), 16000)
        self.assertGreater(samples[4000][0], 1000)
        self.assertGreater(samples[12000][0], 1000)

    def test_existing_output_is_not_overwritten(self):
        """验证目标已存在时保留内容并拒绝转换。"""
        self.output.write_bytes(b"existing output")
        with self.assertRaises(FileExistsError):
            convert_to_mono(self.source, self.output, self.source_info)
        self.assertEqual(self.output.read_bytes(), b"existing output")

    def test_conversion_only_probes_the_new_output(self):
        """验证转换复用源信息并探测新副本。"""
        with patch("asr_runtime.utils.media.probe_audio", wraps=probe_audio) as probe:
            convert_to_mono(self.source, self.output, self.source_info)
        probe.assert_called_once_with(self.output)

    def test_source_change_during_conversion_rejects_and_removes_new_copy(self):
        """验证转换中源文件改变时删除新副本并停止。"""
        open_media = av.open

        def open_then_touch(*args, **kwargs):
            """打开源文件时改写时间以模拟转换中变化。"""
            container = open_media(*args, **kwargs)
            if args[0] == str(self.source):
                current = self.source.stat()
                os.utime(self.source, ns=(current.st_atime_ns, current.st_mtime_ns + 1_000_000_000))
            return container

        with patch("asr_runtime.utils.media.av.open", side_effect=open_then_touch):
            with self.assertRaisesRegex(MediaError, "源文件改变"):
                convert_to_mono(self.source, self.output, self.source_info)
        self.assertTrue(self.source.is_file())
        self.assertFalse(self.output.exists())

    def test_corrupt_audio_does_not_create_output(self):
        """验证损坏音频转换失败时清理新副本。"""
        self.source.write_bytes(b"not audio")
        with self.assertRaises(MediaError):
            convert_to_mono(self.source, self.output, self.source_info)
        self.assertFalse(self.output.exists())

    def test_input_cannot_be_overwritten(self):
        """验证源文件作为目标时保留内容并拒绝转换。"""
        original = self.source.read_bytes()
        with self.assertRaises(FileExistsError):
            convert_to_mono(self.source, self.source, self.source_info)
        self.assertEqual(self.source.read_bytes(), original)

    def test_mp3_can_be_decoded_and_converted(self):
        """验证MP3可以解码并合并为单声道。"""
        compressed = self.runtime.path("synthetic.mp3")
        with av.open(str(self.source)) as original, av.open(str(compressed), "w") as output:
            stream = output.add_stream("libmp3lame", rate=16000)
            stream.layout = "stereo"
            for frame in original.decode(audio=0):
                for packet in stream.encode(frame):
                    output.mux(packet)
            for packet in stream.encode(None):
                output.mux(packet)
        convert_to_mono(compressed, self.output, probe_audio(compressed))
        info = probe_audio(self.output)
        self.assertEqual(info.channels, 1)
        self.assertEqual(info.sample_rate, 16000)
        self.assertAlmostEqual(info.duration_seconds, 1.0, places=3)

    def test_standard_six_channel_layout_converts_to_mono(self):
        """验证标准六声道布局可转换为单声道。"""
        surround = self.runtime.path("surround.flac")
        frame = av.AudioFrame(format="s16", layout="5.1", samples=1600)
        frame.sample_rate = 16000
        frame.planes[0].update(struct.pack("<6h", 1000, 1000, 1000, 0, 1000, 1000) * 1600)
        with av.open(str(surround), "w") as output:
            stream = output.add_stream("flac", rate=16000)
            stream.layout = "5.1"
            for packet in stream.encode(frame):
                output.mux(packet)
            for packet in stream.encode(None):
                output.mux(packet)
        self.assertEqual(probe_audio(surround).channels, 6)
        convert_to_mono(surround, self.output, probe_audio(surround))
        self.assertEqual(probe_audio(self.output).channels, 1)
