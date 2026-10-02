import unittest

from asr_transcription.application.rules import LANGUAGES, validate_options
from asr_transcription.application.rules import ValidationError


class RecognitionOptionsTests(unittest.TestCase):
    def test_automatic_language_and_speakers_omit_explicit_hints(self):
        """验证自动选项生成空语言提示和自动人数。"""
        for payload in ({}, {"language_hint": None, "speaker_count": None}):
            for diarization in (False, True):
                with self.subTest(payload=payload, diarization=diarization):
                    self.assertEqual(validate_options(payload, diarization), {
                        "language_hints": [], "speaker_count": None,
                    })

    def test_each_documented_language_yields_one_cli_compatible_hint(self):
        """验证每种支持语言生成单值CLI提示。"""
        for code, _ in LANGUAGES:
            with self.subTest(language=code):
                self.assertEqual(validate_options({"language_hint": code}, True), {
                    "language_hints": [code], "speaker_count": None,
                })

    def test_rejects_unknown_or_multiple_language_values(self):
        """验证拒绝未知语言或多个语言值。"""
        for value in ("", "auto", "zh-CN", "zh,en", "xx", ["zh", "en"], 1, True, {}):
            with self.subTest(value=value), self.assertRaises(ValidationError) as caught:
                validate_options({"language_hint": value}, True)
            self.assertEqual(caught.exception.field, "language_hint")

    def test_speaker_count_accepts_inclusive_limits(self):
        """验证人数范围的两端都可以使用。"""
        for count in (2, 3, 100):
            with self.subTest(count=count):
                self.assertEqual(validate_options({"speaker_count": count}, True), {
                    "language_hints": [], "speaker_count": count,
                })

    def test_speaker_count_rejects_outside_range_and_non_integer_values(self):
        """验证拒绝超范围或非整数人数。"""
        for value in (1, 101, -1, 2.0, "3", True, False, [], {}):
            with self.subTest(value=value), self.assertRaises(ValidationError) as caught:
                validate_options({"speaker_count": value}, True)
            self.assertEqual(caught.exception.field, "speaker_count")

    def test_speaker_count_requires_diarization(self):
        """验证指定人数必须开启说话人区分。"""
        with self.assertRaises(ValidationError) as caught:
            validate_options({"speaker_count": 3}, False)
        self.assertEqual(caught.exception.field, "speaker_count")

    def test_validates_combined_options_without_modifying_payload(self):
        """验证组合选项返回规范结果并保留原始输入。"""
        payload = {"language_hint": "zh", "speaker_count": 4}
        self.assertEqual(validate_options(payload, True), {
            "language_hints": ["zh"], "speaker_count": 4,
        })
        self.assertEqual(payload, {"language_hint": "zh", "speaker_count": 4})
