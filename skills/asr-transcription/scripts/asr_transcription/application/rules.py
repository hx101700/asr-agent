"""校验固定模型的音频属性、识别选项和增强内容。"""

import math
from collections.abc import Iterable, Mapping
from typing import cast

from ..models import AudioInfo, HotwordConfig, HotwordIssue, HotwordRow, RecognitionOptions
from ..utils.i18n import translate


# 官方模型/临时OSS限制见Skill的references/model.md A02、A04、A06。
AUDIO_SUFFIXES = frozenset(f".{name}" for name in (
    "aac", "amr", "avi", "flac", "flv", "m4a", "mkv", "mov", "mp3",
    "mp4", "mpeg", "ogg", "opus", "wav", "webm", "wma", "wmv",
))
SUPPORTED_CONTAINERS = frozenset({
    "aac", "amr", "avi", "flac", "flv", "mov", "mp3", "mpeg", "ogg",
    "wav", "matroska", "webm", "asf",
})
MAX_UPLOAD_BYTES = 1_000_000_000
MAX_DURATION_SECONDS = 12 * 60 * 60
MAX_HOTWORDS = 2000
MAX_CONTEXT_CHARS = 400
MIN_SPEAKERS = 2
MAX_SPEAKERS = 100


class ValidationError(ValueError):
    """携带表单字段和修改提示的输入校验错误。"""

    def __init__(self, message: str, field: str, details: list[HotwordIssue] | None = None) -> None:
        """携带可公开的说明、表单字段和可选行级错误。"""
        super().__init__(translate(message))
        self.field = field
        self.details: list[HotwordIssue] = [
            {**detail, "message": translate(detail["message"])} for detail in details or []
        ]


def check_audio_limits(info: AudioInfo, diarization: bool) -> None:
    """根据模型和临时存储规格校验音频属性。"""
    if not set(info.format_name.split(",")) & SUPPORTED_CONTAINERS:
        raise ValidationError("实际媒体格式不在固定模型支持范围内。", "audio_path")
    duration = info.duration_seconds
    if duration is None or not math.isfinite(duration) or duration <= 0:
        raise ValidationError("无法确定有效音频时长，不能完成上传前校验。", "audio_path")
    if duration > MAX_DURATION_SECONDS:
        raise ValidationError("音频时长超过模型允许的12小时。", "audio_path")
    if not (diarization and info.channels > 1) and info.size_bytes > MAX_UPLOAD_BYTES:
        raise ValidationError("待上传音频超过临时OSS的1 GB上限。", "audio_path")


def validate_context(text: object) -> str:
    """校验参考文本的长度与字符要求，保留用户原文。"""
    if not isinstance(text, str) or not text.strip():
        raise ValidationError("请输入参考文本，或关闭上下文增强。", "context")
    if len(text) > MAX_CONTEXT_CHARS:
        raise ValidationError(translate(
            "参考文本共 {count} 个字符，最多支持 {maximum} 个，请精简后重新检查。"
        ).format(count=len(text), maximum=MAX_CONTEXT_CHARS), "context")
    if "\x00" in text or any(0xD800 <= ord(char) <= 0xDFFF for char in text):
        raise ValidationError("参考文本中含有无法识别的特殊字符，请删除后重新检查。", "context")
    return text


def build_vocabulary(rows: Iterable[HotwordRow]) -> HotwordConfig:
    """校验热词行并构建即时词典，汇总行级错误和导入提示。"""
    vocabulary: dict[str, int] = {}
    first_rows: dict[str, int] = {}
    details: list[HotwordIssue] = []
    warnings = []
    ignored_blank_rows = 0
    super_count = 0
    for row in rows:
        row_number, text, weight = row.number, row.text, row.weight
        if text is None and weight is None:
            ignored_blank_rows += 1
            continue
        if row.has_formula:
            details.append({"row": row_number, "field": "row", "message": "不接受公式，请填写固定文本和数值。"})
            continue
        row_errors = []
        if not isinstance(text, str) or not text.strip():
            row_errors.append(("text", "热词必须为非空文本。"))
        elif text != text.strip() or any(ord(char) < 32 or ord(char) == 127 for char in text):
            row_errors.append(("text", "请移除热词首尾空白、换行或控制字符；程序不会自动修改。"))
        elif not text.isascii() and len(text) > 15:
            row_errors.append(("text", "含非ASCII字符时，热词总长度最多15个字符。"))
        elif text.isascii() and len([part for part in text.split(" ") if part]) > 7:
            row_errors.append(("text", "纯ASCII热词按空格切分后最多7段。"))
        allowed_weights = (1, 2, 3, 4, 5, 50)
        if (isinstance(weight, bool) or not isinstance(weight, (int, float))
                or weight not in allowed_weights):
            row_errors.append(("weight", "权重必须为1至5的整数或50。"))
        if row_errors:
            details.extend({"row": row_number, "field": name, "message": message}
                           for name, message in row_errors)
            continue
        # 行级错误已排除非文本热词与非法权重，转换只保留已接受的值。
        text = cast(str, text)
        weight = int(cast(int | float, weight))
        if text in vocabulary:
            if vocabulary[text] != weight:
                details.append({"row": row_number, "field": "weight",
                                "message": translate("与第{first_row}行热词重复但权重不同，请统一。").format(
                                    first_row=first_rows[text])})
            else:
                warnings.append(translate("第{row}行与第{first_row}行完全相同，已合并为一个词条。").format(
                    row=row_number, first_row=first_rows[text]))
            continue
        vocabulary[text] = weight
        first_rows[text] = row_number
        if len(vocabulary) == MAX_HOTWORDS + 1:
            details.append({"row": row_number, "field": "text", "message": "热词总数超过2000个，请减少。"})
        if weight == 50:
            super_count += 1
            if super_count == 51:
                details.append({"row": row_number, "field": "weight", "message": "超级热词（权重50）最多50个。"})
    if details:
        raise ValidationError("热词文件中有不符合要求的内容，请按以下行号修改后重新添加文件。", "hotwords_path", details)
    if not vocabulary:
        raise ValidationError("热词Excel未包含有效词条。", "hotwords_path")
    if ignored_blank_rows:
        warnings.append(translate("已忽略{count}个完全空白行。").format(count=ignored_blank_rows))
    return {"vocabulary": vocabulary, "count": len(vocabulary), "warnings": warnings}


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


def validate_options(payload: Mapping[str, object], diarization: object) -> RecognitionOptions:
    """核对语言和参考人数，形成执行所用的识别选项。"""
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
        if type(speaker_count) is not int or not MIN_SPEAKERS <= speaker_count <= MAX_SPEAKERS:
            raise ValidationError(translate(
                "发言人数需为 {minimum}–{maximum} 的整数，或使用自动识别。"
            ).format(minimum=MIN_SPEAKERS, maximum=MAX_SPEAKERS), "speaker_count")

    return {
        "language_hints": [] if language is None else [language],
        "speaker_count": speaker_count,
    }
