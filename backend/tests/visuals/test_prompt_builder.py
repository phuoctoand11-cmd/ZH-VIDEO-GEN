from content.schema import LessonItem
from visuals.prompt_builder import build_image_prompt


def test_build_image_prompt_includes_hanzi_and_meaning():
    item = LessonItem(hanzi="吃", meaning_vi="ăn")
    prompt = build_image_prompt(item)
    assert "吃" in prompt
    assert "ăn" in prompt


def test_build_image_prompt_excludes_text_instruction():
    item = LessonItem(hanzi="吃", meaning_vi="ăn")
    prompt = build_image_prompt(item)
    assert "no text" in prompt
