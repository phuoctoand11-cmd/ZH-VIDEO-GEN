import pytest
from content.auto import generate_lesson, AutoGenerationError


def test_generate_lesson_parses_valid_json():
    def fake_llm(prompt: str) -> str:
        return '{"items": [{"hanzi": "吃", "pinyin": "chī", "meaning_vi": "ăn"}]}'

    items = generate_lesson("đồ ăn", fake_llm)
    assert len(items) == 1
    assert items[0].hanzi == "吃"


def test_generate_lesson_retries_on_invalid_json():
    calls = {"count": 0}

    def flaky_llm(prompt: str) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json"
        return '{"items": [{"hanzi": "喝", "meaning_vi": "uống"}]}'

    items = generate_lesson("đồ uống", flaky_llm, max_retries=1)
    assert calls["count"] == 2
    assert items[0].hanzi == "喝"


def test_generate_lesson_raises_after_max_retries():
    def always_bad(prompt: str) -> str:
        return "still not json"

    with pytest.raises(AutoGenerationError):
        generate_lesson("chủ đề", always_bad, max_retries=1)
