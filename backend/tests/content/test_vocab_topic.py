import pytest

from content.auto import AutoGenerationError
from content.vocab_topic import generate_vocab_topic

VALID_JSON = (
    '{"radical": "冫", "radical_pinyin": "bīng", "radical_meaning_vi": "băng", '
    '"items": [{"hanzi": "冰", "pinyin": "bīng", "meaning_vi": "băng", '
    '"icon_prompt": "cute ice cube character"}]}'
)


def test_generate_vocab_topic_parses_valid_json():
    def fake_llm(prompt: str) -> str:
        return VALID_JSON

    result = generate_vocab_topic("bộ băng", fake_llm)
    assert result.radical == "冫"
    assert len(result.items) == 1
    assert result.items[0].icon_prompt == "cute ice cube character"


def test_generate_vocab_topic_retries_on_invalid_json():
    calls = {"count": 0}

    def flaky_llm(prompt: str) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json"
        return VALID_JSON

    result = generate_vocab_topic("bộ băng", flaky_llm, max_retries=1)
    assert calls["count"] == 2
    assert result.items[0].hanzi == "冰"


def test_generate_vocab_topic_parses_fenced_json():
    def fenced_llm(prompt: str) -> str:
        return f"```json\n{VALID_JSON}\n```"

    result = generate_vocab_topic("bộ băng", fenced_llm)
    assert result.items[0].hanzi == "冰"


def test_generate_vocab_topic_raises_after_max_retries():
    def always_bad(prompt: str) -> str:
        return "still not json"

    with pytest.raises(AutoGenerationError):
        generate_vocab_topic("bộ băng", always_bad, max_retries=1)


def test_generate_vocab_topic_accepts_null_radical_for_non_radical_topic():
    json_no_radical = (
        '{"radical": null, "radical_pinyin": null, "radical_meaning_vi": null, '
        '"items": [{"hanzi": "苹果", "pinyin": "píngguǒ", "meaning_vi": "táo", '
        '"icon_prompt": "cute red apple character"}]}'
    )

    def fake_llm(prompt: str) -> str:
        return json_no_radical

    result = generate_vocab_topic("đồ ăn", fake_llm)
    assert result.radical is None
