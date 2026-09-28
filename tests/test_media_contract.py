"""媒体工具探针：仅使用合成立体声，不读取data/audio。"""

import hashlib
import json
import struct
import unittest
import wave

from asr_agent.environment import Project, media_paths, run_process
from tests.support import ROOT, ProjectTestCase

TOOLS = media_paths(Project(ROOT))


@unittest.skipUnless(all(path.is_file() for path in TOOLS.values()), "需要先安装项目内FFmpeg")
class MediaContractTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.project.prepare()
        self.source = self.project.path("双声道 test.wav")
        self.output = self.project.path("单声道 output.flac")
        # 前半秒只有左声道，后半秒只有右声道；可发现误取某个声道的实现。
        frames = b"".join(struct.pack("<hh", 8000 if i < 8000 else 0, 0 if i < 8000 else 8000)
                          for i in range(16000))
        with wave.open(str(self.source), "wb") as audio:
            audio.setnchannels(2)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(frames)

    def convert(self):
        return run_process(self.project, [
            str(TOOLS["ffmpeg"]), "-hide_banner", "-nostdin", "-v", "error", "-xerror", "-n",
            "-protocol_whitelist", "file", "-i", str(self.source), "-map", "0:a:0",
            "-ac", "1", "-c:a", "flac", "-sample_fmt", "s32", "-bits_per_raw_sample", "24",
            "-map_metadata", "-1", "-map_chapters", "-1", str(self.output),
        ])

    def test_mono_flac_preserves_rate_duration_and_source(self):
        original = hashlib.sha256(self.source.read_bytes()).digest()
        result = self.convert()
        self.assertEqual(result.returncode, 0, result.stderr)
        inspected = run_process(self.project, [str(TOOLS["ffprobe"]), "-v", "error",
            "-protocol_whitelist", "file", "-show_entries", "stream=channels,sample_rate:format=duration",
            "-of", "json", str(self.output)])
        self.assertEqual(inspected.returncode, 0, inspected.stderr)
        metadata = json.loads(inspected.stdout)
        self.assertEqual(metadata["streams"][0]["channels"], 1)
        self.assertEqual(metadata["streams"][0]["sample_rate"], "16000")
        self.assertAlmostEqual(float(metadata["format"]["duration"]), 1.0, places=5)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(), original)

    def test_both_stereo_channels_contribute(self):
        result = self.convert()
        self.assertEqual(result.returncode, 0, result.stderr)
        decoded = self.project.path("decoded.raw")
        result = run_process(self.project, [str(TOOLS["ffmpeg"]), "-nostdin", "-v", "error", "-n",
            "-protocol_whitelist", "file", "-i", str(self.output), "-f", "s16le", str(decoded)])
        self.assertEqual(result.returncode, 0, result.stderr)
        samples = list(struct.iter_unpack("<h", decoded.read_bytes()))
        self.assertEqual(len(samples), 16000)
        self.assertGreater(samples[4000][0], 1000)
        self.assertGreater(samples[12000][0], 1000)

    def test_existing_output_is_not_overwritten(self):
        self.output.write_bytes(b"existing output")
        result = self.convert()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_bytes(), b"existing output")
