import pytest
from PIL import Image

from content.schema import VocabCardItem, VocabTopicResult
from render.vocab_card import draw_vocab_card, row_regions


def _make_mascot(tmp_path, name, color=(255, 255, 255)):
    path = tmp_path / name
    Image.new("RGB", (200, 200), color=color).save(path)
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
    mascots = [_make_mascot(tmp_path, "m1.png"), _make_mascot(tmp_path, "m2.png")]

    card = draw_vocab_card(result, mascots, size=(720, 1280))
    assert card.size == (720, 1280)


def test_draw_vocab_card_without_radical_skips_header(tmp_path):
    result = VocabTopicResult(items=[VocabCardItem(hanzi="吃", meaning_vi="ăn", icon_prompt="eating")])
    mascots = [_make_mascot(tmp_path, "m1.png")]

    card = draw_vocab_card(result, mascots, size=(720, 1280))
    assert card.size == (720, 1280)


def test_draw_vocab_card_rejects_mismatched_mascot_count(tmp_path):
    result = VocabTopicResult(items=[VocabCardItem(hanzi="吃", meaning_vi="ăn", icon_prompt="eating")])

    with pytest.raises(ValueError):
        draw_vocab_card(result, [], size=(720, 1280))


def test_row_regions_returns_n_increasing_centers_within_bounds():
    centers = row_regions(size=(720, 1280), n_items=5, has_header=True)
    assert len(centers) == 5
    assert all(0.0 <= c <= 1.0 for c in centers)
    assert centers == sorted(centers)


def test_row_regions_without_header_starts_higher_than_with_header():
    with_header = row_regions(size=(720, 1280), n_items=1, has_header=True)
    without_header = row_regions(size=(720, 1280), n_items=1, has_header=False)
    assert without_header[0] < with_header[0]
