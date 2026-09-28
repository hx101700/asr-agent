"""固定模型且可由 BL 2.1.0 公开参数表达的转写选项。"""

from .validation import ValidationError


# 语言代码来自 Filetrans HTTP API；CLI 的 --language 当前只接受单个值。
LANGUAGES = [
    ("zh", "中文"), ("en", "英语"), ("ja", "日语"), ("ko", "韩语"),
    ("vi", "越南语"), ("th", "泰语"), ("id", "印尼语"), ("ms", "马来语"),
    ("tl", "菲律宾语"), ("hi", "印地语"), ("ar", "阿拉伯语"), ("fr", "法语"),
    ("de", "德语"), ("es", "西班牙语"), ("pt", "葡萄牙语"), ("ru", "俄语"),
    ("it", "意大利语"), ("nl", "荷兰语"), ("sv", "瑞典语"), ("da", "丹麦语"),
    ("fi", "芬兰语"), ("no", "挪威语"), ("el", "希腊语"), ("pl", "波兰语"),
    ("cs", "捷克语"), ("hu", "匈牙利语"), ("ro", "罗马尼亚语"),
    ("bg", "保加利亚语"), ("hr", "克罗地亚语"), ("sk", "斯洛伐克语"),
]
LANGUAGE_CODES = frozenset(code for code, _ in LANGUAGES)


def validate_options(payload: dict, diarization: bool) -> dict:
    language = payload.get("language_hint")
    if language is not None and (
        not isinstance(language, str) or language not in LANGUAGE_CODES
    ):
        raise ValidationError("请选择一种语言，或使用自动识别。", "language_hint")

    speaker_count = payload.get("speaker_count")
    if speaker_count is not None:
        if not diarization:
            raise ValidationError("设置发言人数前，请开启区分发言人。", "speaker_count")
        # bool 是 int 的子类，但不能把勾选状态当作人数。
        if type(speaker_count) is not int or not 2 <= speaker_count <= 100:
            raise ValidationError("发言人数需为 2–100 的整数，或使用自动识别。", "speaker_count")

    return {
        "language_hints": [] if language is None else [language],
        "speaker_count": speaker_count,
    }
