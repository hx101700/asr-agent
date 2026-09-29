"""PyAV真实解码/混音测试，只使用合成音频。"""

import hashlib
import struct
import wave

import av

from asr_agent.media import MediaError, convert_to_mono, probe_audio
from tests.support import ProjectTestCase


class MediaContractTests(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.source = self.project.path("双声道 test.wav")
        self.output = self.project.path("单声道 output.flac")
        frames = b"".join(struct.pack("<hh", 8000 if i < 8000 else 0, 0 if i < 8000 else 8000)
                          for i in range(16000))
        with wave.open(str(self.source), "wb") as audio:
            audio.setnchannels(2)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(frames)

    def test_mono_flac_preserves_rate_duration_and_source(self):
        original = hashlib.sha256(self.source.read_bytes()).digest()
        info = convert_to_mono(self.source, self.output)
        self.assertEqual(info, probe_audio(self.output))
        self.assertEqual(info.channels, 1)
        self.assertEqual(info.sample_rate, 16000)
        self.assertAlmostEqual(info.duration_seconds, 1.0, places=5)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(), original)

    def test_both_stereo_channels_contribute(self):
        convert_to_mono(self.source, self.output)
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
        self.output.write_bytes(b"existing output")
        with self.assertRaises(FileExistsError):
            convert_to_mono(self.source, self.output)
        self.assertEqual(self.output.read_bytes(), b"existing output")

    def test_mono_input_is_used_without_another_copy(self):
        convert_to_mono(self.source, self.output)
        unused = self.project.path("unneeded.flac")
        self.assertEqual(convert_to_mono(self.output, unused), probe_audio(self.output))
        self.assertFalse(unused.exists())

    def test_corrupt_audio_does_not_create_output(self):
        self.source.write_bytes(b"not audio")
        with self.assertRaises(MediaError):
            convert_to_mono(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_input_cannot_be_overwritten(self):
        original = self.source.read_bytes()
        with self.assertRaises(MediaError):
            convert_to_mono(self.source, self.source)
        self.assertEqual(self.source.read_bytes(), original)

    def test_mp3_can_be_decoded_and_converted(self):
        compressed = self.project.path("synthetic.mp3")
        with av.open(str(self.source)) as original, av.open(str(compressed), "w") as output:
            stream = output.add_stream("libmp3lame", rate=16000)
            stream.layout = "stereo"
            for frame in original.decode(audio=0):
                for packet in stream.encode(frame):
                    output.mux(packet)
            for packet in stream.encode(None):
                output.mux(packet)
        convert_to_mono(compressed, self.output)
        info = probe_audio(self.output)
        self.assertEqual(info.channels, 1)
        self.assertEqual(info.sample_rate, 16000)
        self.assertAlmostEqual(info.duration_seconds, 1.0, places=3)

    def test_standard_six_channel_layout_converts_to_mono(self):
        surround = self.project.path("surround.flac")
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
        convert_to_mono(surround, self.output)
        self.assertEqual(probe_audio(self.output).channels, 1)
