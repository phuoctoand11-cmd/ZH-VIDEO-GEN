import pytest
from content.schema import LessonItem
from audio.templates import AudioTemplate, TemplateSegment
from render.overlay import build_overlay_cues, total_duration


def _template():
    return AudioTemplate(name="zh-zh-vi", segments=[
        TemplateSegment(lang="zh", field="hanzi"),
        TemplateSegment(lang="zh", field="hanzi"),
        TemplateSegment(lang="vi", field="meaning_vi"),
    ])


def test_build_overlay_cues_timing():
    item = LessonItem(hanzi="吃", pinyin="chī", meaning_vi="ăn")
    cues = build_overlay_cues(item, _template(), [1.0, 1.0, 2.0])
    assert cues[0].start == 0.0 and cues[0].end == 1.0
    assert cues[1].start == 1.0 and cues[1].end == 2.0
    assert cues[2].start == 2.0 and cues[2].end == 4.0


def test_build_overlay_cues_text_content():
    item = LessonItem(hanzi="吃", pinyin="chī", meaning_vi="ăn")
    cues = build_overlay_cues(item, _template(), [1.0, 1.0, 2.0])
    assert "吃" in cues[0].text
    assert "chī" in cues[0].text
    assert cues[2].text == "ăn"


def test_build_overlay_cues_mismatched_length_raises():
    item = LessonItem(hanzi="吃", meaning_vi="ăn")
    with pytest.raises(ValueError):
        build_overlay_cues(item, _template(), [1.0])


def test_total_duration():
    assert total_duration([1.0, 2.0, 1.5]) == 4.5


import numpy as np
from PIL import Image, ImageDraw, ImageFont

from render.overlay import FONT_PATH, TEXT_MARGIN, _wrap_line, draw_text_on_frame


def test_draw_text_on_frame_changes_pixels():
    frame = np.zeros((200, 400, 3), dtype=np.uint8)
    result = draw_text_on_frame(frame, "吃\nchī")
    assert result.shape == frame.shape
    assert not np.array_equal(result, frame)


def _draw_and_font(font_size=60):
    image = Image.new("RGB", (720, 1280))
    return ImageDraw.Draw(image), ImageFont.truetype(str(FONT_PATH), font_size)


def _width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def test_wrap_line_splits_long_sentence_to_fit():
    draw, font = _draw_and_font()
    max_width = 720 - 2 * TEXT_MARGIN
    sentence = "Tôi muốn uống một cốc cà phê sữa đá vào buổi sáng"
    assert _width(draw, sentence, font) > max_width  # would overflow unwrapped

    lines = _wrap_line(draw, sentence, font, max_width)
    assert len(lines) > 1
    assert all(_width(draw, line, font) <= max_width for line in lines)
    assert " ".join(lines) == sentence


def test_wrap_line_splits_long_pinyin():
    draw, font = _draw_and_font()
    max_width = 720 - 2 * TEXT_MARGIN
    pinyin = "wǒ xiǎng hē yī bēi bīng kā fēi sữa đá měi tiān zǎo shang"
    lines = _wrap_line(draw, pinyin, font, max_width)
    assert len(lines) > 1
    assert all(_width(draw, line, font) <= max_width for line in lines)


def test_wrap_line_keeps_short_line_intact():
    draw, font = _draw_and_font()
    assert _wrap_line(draw, "chī", font, 720 - 2 * TEXT_MARGIN) == ["chī"]


def test_draw_text_on_frame_wrapped_text_stays_inside_frame():
    width = 720
    frame = np.zeros((1280, width, 3), dtype=np.uint8)
    sentence = "Tôi muốn uống một cốc cà phê sữa đá vào buổi sáng"
    result = draw_text_on_frame(frame, sentence)
    assert result.shape == frame.shape

    # Unwrapped, the centred single line would start at a negative x and be
    # clipped at both edges. With wrapping, both edge columns stay untouched.
    assert np.array_equal(result[:, 0, :], frame[:, 0, :])
    assert np.array_equal(result[:, width - 1, :], frame[:, width - 1, :])
    assert not np.array_equal(result, frame)
