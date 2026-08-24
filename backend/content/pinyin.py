from pypinyin import pinyin, Style
from content.schema import LessonItem


def fill_pinyin(item: LessonItem) -> LessonItem:
    if item.pinyin:
        return item
    syllables = pinyin(item.hanzi, style=Style.TONE)
    generated = " ".join(s[0] for s in syllables)
    return item.model_copy(update={"pinyin": generated})


def fill_pinyin_batch(items: list[LessonItem]) -> list[LessonItem]:
    return [fill_pinyin(item) for item in items]
