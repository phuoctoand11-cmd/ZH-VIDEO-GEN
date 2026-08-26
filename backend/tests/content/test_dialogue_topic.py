import pytest

from content.auto import AutoGenerationError
from content.dialogue_topic import generate_dialogue_topic

VALID_JSON = (
    '{"title": "Chào hỏi", "turns": ['
    '{"speaker_name": "Minh", "line": {"hanzi": "你好", "pinyin": "nǐ hǎo", "meaning_vi": "xin chào"}}, '
    '{"speaker_name": "Lan", "line": {"hanzi": "你好吗", "pinyin": "nǐ hǎo ma", "meaning_vi": "bạn khỏe không"}}'
    ']}'
)


def test_generate_dialogue_topic_parses_valid_json():
    def fake_llm(prompt: str) -> str:
        return VALID_JSON

    result = generate_dialogue_topic("chào hỏi", fake_llm)
    assert result.title == "Chào hỏi"
    assert len(result.turns) == 2
    assert result.turns[0].speaker_name == "Minh"
    assert result.turns[1].line.hanzi == "你好吗"


def test_generate_dialogue_topic_retries_on_invalid_json():
    calls = {"count": 0}

    def flaky_llm(prompt: str) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json"
        return VALID_JSON

    result = generate_dialogue_topic("chào hỏi", flaky_llm, max_retries=1)
    assert calls["count"] == 2
    assert result.title == "Chào hỏi"


def test_generate_dialogue_topic_parses_fenced_json():
    def fenced_llm(prompt: str) -> str:
        return f"```json\n{VALID_JSON}\n```"

    result = generate_dialogue_topic("chào hỏi", fenced_llm)
    assert len(result.turns) == 2


def test_generate_dialogue_topic_raises_after_max_retries():
    def always_bad(prompt: str) -> str:
        return "still not json"

    with pytest.raises(AutoGenerationError):
        generate_dialogue_topic("chào hỏi", always_bad, max_retries=1)
