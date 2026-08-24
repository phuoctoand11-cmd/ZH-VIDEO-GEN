from content.schema import LessonItem
from content.pinyin import fill_pinyin, fill_pinyin_batch


def test_fill_pinyin_generates_when_missing():
    item = LessonItem(hanzi="吃", meaning_vi="ăn")
    result = fill_pinyin(item)
    assert result.pinyin == "chī"


def test_fill_pinyin_keeps_existing():
    item = LessonItem(hanzi="吃", pinyin="custom", meaning_vi="ăn")
    result = fill_pinyin(item)
    assert result.pinyin == "custom"


def test_fill_pinyin_batch():
    items = [LessonItem(hanzi="吃", meaning_vi="ăn"), LessonItem(hanzi="喝", meaning_vi="uống")]
    results = fill_pinyin_batch(items)
    assert results[0].pinyin == "chī"
    assert results[1].pinyin == "hē"
