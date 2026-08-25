import pytest
import content.auto as auto_module
from content.auto import generate_lesson, groq_llm_call, AutoGenerationError


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


def test_generate_lesson_parses_fenced_json():
    def fenced_llm(prompt: str) -> str:
        return (
            "```json\n"
            '{"items": [{"hanzi": "喝", "pinyin": "hē", "meaning_vi": "uống"}]}\n'
            "```"
        )

    items = generate_lesson("đồ uống", fenced_llm)
    assert len(items) == 1
    assert items[0].hanzi == "喝"
    assert items[0].meaning_vi == "uống"


def test_generate_lesson_parses_bare_fenced_json():
    def fenced_llm(prompt: str) -> str:
        return '```\n{"items": [{"hanzi": "吃", "meaning_vi": "ăn"}]}\n```\n'

    items = generate_lesson("đồ ăn", fenced_llm)
    assert items[0].hanzi == "吃"


def test_generate_lesson_raises_after_max_retries():
    def always_bad(prompt: str) -> str:
        return "still not json"

    with pytest.raises(AutoGenerationError):
        generate_lesson("chủ đề", always_bad, max_retries=1)


def test_groq_llm_call_raises_clear_error_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(AutoGenerationError, match="GROQ_API_KEY"):
        groq_llm_call("prompt")


def test_groq_llm_call_uses_default_model_and_returns_content(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "groq_fake_key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    calls = []

    class FakeMessage:
        content = '{"items": []}'

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return type("R", (), {"choices": [FakeChoice()]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeGroqClient:
        def __init__(self, api_key=None):
            calls.append({"init_api_key": api_key})
            self.chat = FakeChat()

    monkeypatch.setattr(auto_module, "Groq", FakeGroqClient)

    result = groq_llm_call("soạn bài")

    assert result == '{"items": []}'
    assert calls[0] == {"init_api_key": "groq_fake_key"}
    assert calls[1]["model"] == auto_module.DEFAULT_GROQ_MODEL
    assert calls[1]["messages"] == [{"role": "user", "content": "soạn bài"}]


def test_groq_llm_call_honors_groq_model_env_override(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "groq_fake_key")
    monkeypatch.setenv("GROQ_MODEL", "some-other-model")
    calls = []

    class FakeMessage:
        content = "{}"

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return type("R", (), {"choices": [FakeChoice()]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeGroqClient:
        def __init__(self, api_key=None):
            self.chat = FakeChat()

    monkeypatch.setattr(auto_module, "Groq", FakeGroqClient)

    groq_llm_call("soạn bài")

    assert calls[0]["model"] == "some-other-model"
