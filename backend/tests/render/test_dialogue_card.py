import pytest
from PIL import Image

from content.schema import DialogueTurn, LessonItem
from render.dialogue_card import draw_dialogue_turn

SIZES = [(720, 1280), (1280, 720)]


def _make_avatar(tmp_path):
    path = tmp_path / "avatar.png"
    Image.new("RGB", (200, 200), color=(255, 255, 255)).save(path)
    return str(path)


@pytest.mark.parametrize("size", SIZES)
def test_draw_dialogue_turn_returns_correct_size(tmp_path, size):
    turn = DialogueTurn(
        speaker_name="Minh", line=LessonItem(hanzi="你好", pinyin="nǐ hǎo", meaning_vi="xin chào")
    )

    card = draw_dialogue_turn(turn, _make_avatar(tmp_path), size=size)
    assert card.size == size


@pytest.mark.parametrize("size", SIZES)
def test_draw_dialogue_turn_wraps_long_hanzi_sentence_without_crashing(tmp_path, size):
    long_line = LessonItem(
        hanzi="随着生活水平的提高，人们越来越关心自己的健康了。",
        pinyin="Suízhe shēnghuó shuǐpíng de tígāo, rénmen yuèláiyuè guānxīn zìjǐ de jiànkāng le.",
        meaning_vi="Cùng với sự nâng cao mức sống, mọi người ngày càng quan tâm đến sức khỏe của mình.",
    )
    turn = DialogueTurn(speaker_name="Lan", line=long_line)

    card = draw_dialogue_turn(turn, _make_avatar(tmp_path), size=size)
    assert card.size == size


@pytest.mark.parametrize("size", SIZES)
def test_draw_dialogue_turn_renders_different_speakers_without_crashing(tmp_path, size):
    avatar = _make_avatar(tmp_path)
    turn_a = DialogueTurn(speaker_name="Minh", line=LessonItem(hanzi="嗨", meaning_vi="chào"))
    turn_b = DialogueTurn(speaker_name="Lan", line=LessonItem(hanzi="嗨", meaning_vi="chào"))

    card_a = draw_dialogue_turn(turn_a, avatar, size=size)
    card_b = draw_dialogue_turn(turn_b, avatar, size=size)
    assert card_a.size == size == card_b.size
