import unittest

from asr_agent.validation import LANGUAGES, validate_options
from asr_agent.validation import ValidationError


class RecognitionOptionsTests(unittest.TestCase):
    def test_automatic_language_and_speakers_omit_explicit_hints(self):
        for payload in ({}, {"language_hint": None, "speaker_count": None}):
            for diarization in (False, True):
                with self.subTest(payload=payload, diarization=diarization):
                    self.assertEqual(validate_options(payload, diarization), {
                        "language_hints": [], "speaker_count": None,
                    })

    def test_each_documented_language_yields_one_cli_compatible_hint(self):
        for code, _ in LANGUAGES:
            with self.subTest(language=code):
                self.assertEqual(validate_options({"language_hint": code}, True), {
                    "language_hints": [code], "speaker_count": None,
                })

    def test_rejects_unknown_or_multiple_language_values(self):
        for value in ("", "auto", "zh-CN", "zh,en", "xx", ["zh", "en"], 1, True, {}):
            with self.subTest(value=value), self.assertRaises(ValidationError) as caught:
                validate_options({"language_hint": value}, True)
            self.assertEqual(caught.exception.field, "language_hint")

    def test_speaker_count_accepts_inclusive_limits(self):
        for count in (2, 3, 100):
            with self.subTest(count=count):
                self.assertEqual(validate_options({"speaker_count": count}, True), {
                    "language_hints": [], "speaker_count": count,
                })

    def test_speaker_count_rejects_outside_range_and_non_integer_values(self):
        for value in (1, 101, -1, 2.0, "3", True, False, [], {}):
            with self.subTest(value=value), self.assertRaises(ValidationError) as caught:
                validate_options({"speaker_count": value}, True)
            self.assertEqual(caught.exception.field, "speaker_count")

    def test_speaker_count_requires_diarization(self):
        with self.assertRaises(ValidationError) as caught:
            validate_options({"speaker_count": 3}, False)
        self.assertEqual(caught.exception.field, "speaker_count")

    def test_validates_combined_options_without_modifying_payload(self):
        payload = {"language_hint": "zh", "speaker_count": 4}
        self.assertEqual(validate_options(payload, True), {
            "language_hints": ["zh"], "speaker_count": 4,
        })
        self.assertEqual(payload, {"language_hint": "zh", "speaker_count": 4})
