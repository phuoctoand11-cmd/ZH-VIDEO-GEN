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
