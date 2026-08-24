import pytest
from pydantic import ValidationError
from content.schema import LessonItem


def test_lesson_item_valid():
    item = LessonItem(hanzi="吃", pinyin="chī", meaning_vi="ăn")
    assert item.hanzi == "吃"
    assert item.pinyin == "chī"
    assert item.meaning_vi == "ăn"


def test_lesson_item_pinyin_optional():
    item = LessonItem(hanzi="吃", meaning_vi="ăn")
    assert item.pinyin is None


def test_lesson_item_rejects_empty_hanzi():
    with pytest.raises(ValidationError):
        LessonItem(hanzi="  ", meaning_vi="ăn")


def test_lesson_item_rejects_empty_meaning():
    with pytest.raises(ValidationError):
        LessonItem(hanzi="吃", meaning_vi="  ")
