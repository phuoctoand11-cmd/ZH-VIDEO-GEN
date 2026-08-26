import pytest
from PIL import Image

from content.schema import VocabCardItem, VocabTopicResult
from render.vocab_card import draw_vocab_card, row_regions


def _make_scene_image(tmp_path, name, color=(255, 255, 255)):
    path = tmp_path / name
    Image.new("RGB", (200, 160), color=color).save(path)
    return str(path)


def test_draw_vocab_card_with_radical_returns_correct_size(tmp_path):
    result = VocabTopicResult(
        radical="冫",
        radical_pinyin="bīng",
        radical_meaning_vi="băng",
        items=[
            VocabCardItem(hanzi="冰", pinyin="bīng", meaning_vi="băng", icon_prompt="ice"),
            VocabCardItem(hanzi="冷", pinyin="lěng", meaning_vi="lạnh", icon_prompt="cold"),
        ],
    )
    images = [_make_scene_image(tmp_path, "s1.png"), _make_scene_image(tmp_path, "s2.png")]

    card = draw_vocab_card(result, images, size=(720, 1280))
    assert card.size == (720, 1280)


def test_draw_vocab_card_without_radical_returns_correct_size(tmp_path):
    result = VocabTopicResult(items=[VocabCardItem(hanzi="吃", meaning_vi="ăn", icon_prompt="eating")])
    images = [_make_scene_image(tmp_path, "s1.png")]

    card = draw_vocab_card(result, images, size=(720, 1280))
    assert card.size == (720, 1280)


def test_draw_vocab_card_with_topic_label_returns_correct_size(tmp_path):
    result = VocabTopicResult(items=[VocabCardItem(hanzi="吃", meaning_vi="ăn", icon_prompt="eating")])
    images = [_make_scene_image(tmp_path, "s1.png")]

    card = draw_vocab_card(result, images, size=(720, 1280), topic_label="Ăn uống")
    assert card.size == (720, 1280)


def test_draw_vocab_card_rejects_mismatched_image_count(tmp_path):
    result = VocabTopicResult(items=[VocabCardItem(hanzi="吃", meaning_vi="ăn", icon_prompt="eating")])

    with pytest.raises(ValueError):
        draw_vocab_card(result, [], size=(720, 1280))


def test_draw_vocab_card_at_16x9_returns_correct_size(tmp_path):
    result = VocabTopicResult(
        items=[
            VocabCardItem(hanzi="吃", meaning_vi="ăn", icon_prompt="eating"),
            VocabCardItem(hanzi="喝", meaning_vi="uống", icon_prompt="drinking"),
        ]
    )
    images = [_make_scene_image(tmp_path, "s1.png"), _make_scene_image(tmp_path, "s2.png")]

    card = draw_vocab_card(result, images, size=(1280, 720))
    assert card.size == (1280, 720)


def test_row_regions_returns_n_increasing_centers_within_bounds():
    centers = row_regions(size=(720, 1280), n_items=5)
    assert len(centers) == 5
    assert all(0.0 <= c <= 1.0 for c in centers)
    assert centers == sorted(centers)


def test_row_regions_scales_with_aspect_ratio():
    # The header/footer/margins are fractions of height, not fixed pixels, so
    # a shorter (16:9) canvas must still produce valid, increasing centers.
    centers = row_regions(size=(1280, 720), n_items=5)
    assert len(centers) == 5
    assert all(0.0 <= c <= 1.0 for c in centers)
    assert centers == sorted(centers)
