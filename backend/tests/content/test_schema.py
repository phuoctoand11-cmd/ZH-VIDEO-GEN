import pytest
from pydantic import ValidationError
from content.schema import (
    DialogueResult,
    DialogueTurn,
    LessonItem,
    VocabCardItem,
    VocabTopicResult,
)


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


def test_vocab_card_item_valid():
    item = VocabCardItem(hanzi="冰", pinyin="bīng", meaning_vi="băng", icon_prompt="cute ice cube")
    assert item.hanzi == "冰"
    assert item.icon_prompt == "cute ice cube"


def test_vocab_card_item_rejects_empty_hanzi():
    with pytest.raises(ValidationError):
        VocabCardItem(hanzi="  ", meaning_vi="băng", icon_prompt="ice")


def test_vocab_topic_result_holds_items_and_optional_radical():
    result = VocabTopicResult(
        radical="冫",
        radical_pinyin="bīng",
        radical_meaning_vi="băng",
        items=[VocabCardItem(hanzi="冰", meaning_vi="băng", icon_prompt="ice cube")],
    )
    assert result.radical == "冫"
    assert len(result.items) == 1


def test_vocab_topic_result_radical_defaults_to_none():
    result = VocabTopicResult(
        items=[VocabCardItem(hanzi="吃", meaning_vi="ăn", icon_prompt="eating")]
    )
    assert result.radical is None


def test_dialogue_turn_wraps_lesson_item():
    turn = DialogueTurn(speaker_name="Minh", line=LessonItem(hanzi="你好", meaning_vi="xin chào"))
    assert turn.speaker_name == "Minh"
    assert turn.line.hanzi == "你好"


def test_dialogue_result_holds_turns():
    result = DialogueResult(
        title="Chào hỏi",
        turns=[DialogueTurn(speaker_name="Minh", line=LessonItem(hanzi="你好", meaning_vi="xin chào"))],
    )
    assert result.title == "Chào hỏi"
    assert len(result.turns) == 1
