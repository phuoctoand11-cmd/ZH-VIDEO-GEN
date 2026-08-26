import app as app_module
from app import MAX_VOCAB_ITEMS, _load_templates


def test_load_templates_includes_expected_names():
    templates = _load_templates()
    assert "zh-zh-vi" in templates
    assert "zh-vi-zh" in templates


def _valid_csv():
    return "hanzi,pinyin,meaning_vi\n吃,chī,ăn"


def _valid_dialogue_csv():
    return "speaker,hanzi,pinyin,meaning_vi\nMinh,你好,nǐ hǎo,xin chào"


def test_generate_video_unknown_template_returns_error(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("run_vocab_card_pipeline must not be called for an unknown template")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "khong-ton-tai", ["9:16"]
    )
    assert video_9_16 is None
    assert video_16_9 is None
    assert log.startswith("Lỗi:")
    assert "khong-ton-tai" in log


def test_generate_video_empty_aspect_ratios_skips_generation(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("pipeline must not be called with no aspect ratio")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "zh-zh-vi", []
    )
    assert video_9_16 is None
    assert video_16_9 is None
    assert "tỉ lệ khung hình" in log


def test_generate_video_invalid_aspect_ratio_returns_error(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("pipeline must not be called for an invalid aspect ratio")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    _, _, log = app_module.generate_video("Nhập danh sách", _valid_csv(), "zh-zh-vi", ["4:3"])
    assert log.startswith("Lỗi:")
    assert "4:3" in log


def test_generate_video_unknown_mode_returns_error(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("no pipeline must be called for an unknown mode")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    monkeypatch.setattr(app_module, "run_dialogue_pipeline", unexpected)
    _, _, log = app_module.generate_video("???", _valid_csv(), "zh-zh-vi", ["9:16"])
    assert log.startswith("Lỗi:")
    assert "???" in log


def test_generate_video_manual_mode_routes_to_vocab_card_pipeline(monkeypatch):
    from pipeline import PipelineResult

    calls = {"count": 0}

    def fake_pipeline(vocab_result, template, aspect_ratios, work_dir, topic_label=None):
        calls["count"] += 1
        assert vocab_result.items[0].hanzi == "吃"
        return PipelineResult(video_paths={"9:16": "out.mp4"})

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", fake_pipeline)
    video_9_16, _, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "zh-zh-vi", ["9:16"]
    )
    assert calls["count"] == 1
    assert video_9_16 == "out.mp4"
    assert log == "Hoàn tất, không có lỗi."


def _csv_with_n_rows(n):
    header = "hanzi,pinyin,meaning_vi"
    rows = [f"字{i},zi{i},nghia {i}" for i in range(n)]
    return "\n".join([header] + rows)


def test_generate_video_manual_mode_rejects_too_many_items(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("run_vocab_card_pipeline must not be called over the item cap")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    csv_text = _csv_with_n_rows(MAX_VOCAB_ITEMS + 1)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", csv_text, "zh-zh-vi", ["9:16"]
    )
    assert video_9_16 is None
    assert video_16_9 is None
    assert log.startswith("Lỗi:")
    assert str(MAX_VOCAB_ITEMS + 1) in log
    assert str(MAX_VOCAB_ITEMS) in log


def test_generate_video_manual_mode_allows_exactly_max_items(monkeypatch):
    from pipeline import PipelineResult

    calls = {"count": 0}

    def fake_pipeline(vocab_result, template, aspect_ratios, work_dir, topic_label=None):
        calls["count"] += 1
        assert len(vocab_result.items) == MAX_VOCAB_ITEMS
        return PipelineResult(video_paths={"9:16": "out.mp4"})

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", fake_pipeline)
    csv_text = _csv_with_n_rows(MAX_VOCAB_ITEMS)
    video_9_16, _, log = app_module.generate_video(
        "Nhập danh sách", csv_text, "zh-zh-vi", ["9:16"]
    )
    assert calls["count"] == 1
    assert video_9_16 == "out.mp4"
    assert log == "Hoàn tất, không có lỗi."


def test_generate_video_manual_mode_handles_none_csv_text(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("run_vocab_card_pipeline must not be called with no items")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", None, "zh-zh-vi", ["9:16"]
    )
    assert video_9_16 is None
    assert video_16_9 is None
    assert not log.startswith("Lỗi: '")  # no raw AttributeError leaked through


def test_generate_video_vocab_topic_mode_routes_to_vocab_card_pipeline_via_csv_text(monkeypatch):
    # After the "Xem trước" step, "Từ vựng theo chủ đề" renders from the same
    # csv_text box as "Nhập danh sách" — generate_video itself never calls
    # the LLM (that only happens in generate_preview).
    from pipeline import PipelineResult

    calls = {"count": 0}

    def fake_pipeline(vocab_result, template, aspect_ratios, work_dir, topic_label=None):
        calls["count"] += 1
        assert vocab_result.items[0].hanzi == "吃"
        return PipelineResult(video_paths={"9:16": "out.mp4"})

    def unexpected_llm(topic, llm_call):
        raise AssertionError("generate_video must not call the LLM directly")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", fake_pipeline)
    monkeypatch.setattr(app_module, "generate_vocab_topic", unexpected_llm)
    video_9_16, _, log = app_module.generate_video(
        "Từ vựng theo chủ đề", _valid_csv(), "zh-zh-vi", ["9:16"]
    )
    assert calls["count"] == 1
    assert video_9_16 == "out.mp4"
    assert log == "Hoàn tất, không có lỗi."


def test_generate_video_passes_topic_through_as_display_label_only(monkeypatch):
    # topic is display-only here (labels the card's "Chủ đề: …" subtitle) —
    # confirm it reaches run_vocab_card_pipeline's topic_label kwarg, and
    # confirm generate_video still never calls the LLM with it.
    from pipeline import PipelineResult

    seen = {}

    def fake_pipeline(vocab_result, template, aspect_ratios, work_dir, topic_label=None):
        seen["topic_label"] = topic_label
        return PipelineResult(video_paths={"9:16": "out.mp4"})

    def unexpected_llm(topic, llm_call):
        raise AssertionError("generate_video must not call the LLM directly")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", fake_pipeline)
    monkeypatch.setattr(app_module, "generate_vocab_topic", unexpected_llm)
    app_module.generate_video(
        "Từ vựng theo chủ đề", _valid_csv(), "zh-zh-vi", ["9:16"], topic="đồ ăn"
    )
    assert seen["topic_label"] == "đồ ăn"


def test_generate_video_defaults_topic_label_to_none_when_blank(monkeypatch):
    from pipeline import PipelineResult

    seen = {}

    def fake_pipeline(vocab_result, template, aspect_ratios, work_dir, topic_label=None):
        seen["topic_label"] = topic_label
        return PipelineResult(video_paths={"9:16": "out.mp4"})

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", fake_pipeline)
    app_module.generate_video("Nhập danh sách", _valid_csv(), "zh-zh-vi", ["9:16"])
    assert seen["topic_label"] is None


def test_generate_video_vocab_topic_mode_rejects_empty_csv_text(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("pipeline must not be called with no items")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    _, _, log = app_module.generate_video("Từ vựng theo chủ đề", "", "zh-zh-vi", ["9:16"])
    assert log.startswith("Không có mục hợp lệ")


def test_generate_video_dialogue_topic_mode_routes_to_dialogue_pipeline_via_csv_text(monkeypatch):
    from pipeline import PipelineResult

    calls = {"count": 0}

    def fake_pipeline(dialogue_result, template, aspect_ratios, work_dir):
        calls["count"] += 1
        assert dialogue_result.turns[0].speaker_name == "Minh"
        assert dialogue_result.turns[0].line.hanzi == "你好"
        return PipelineResult(video_paths={"9:16": "out.mp4"})

    def unexpected_llm(topic, llm_call):
        raise AssertionError("generate_video must not call the LLM directly")

    monkeypatch.setattr(app_module, "run_dialogue_pipeline", fake_pipeline)
    monkeypatch.setattr(app_module, "generate_dialogue_topic", unexpected_llm)
    video_9_16, _, log = app_module.generate_video(
        "Hội thoại theo chủ đề", _valid_dialogue_csv(), "zh-zh-vi", ["9:16"]
    )
    assert calls["count"] == 1
    assert video_9_16 == "out.mp4"
    assert log == "Hoàn tất, không có lỗi."


def test_generate_video_dialogue_topic_mode_rejects_empty_csv_text(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("pipeline must not be called with no turns")

    monkeypatch.setattr(app_module, "run_dialogue_pipeline", unexpected)
    _, _, log = app_module.generate_video("Hội thoại theo chủ đề", "", "zh-zh-vi", ["9:16"])
    assert log.startswith("Không có lượt thoại hợp lệ")


def test_generate_video_catches_pipeline_exception(monkeypatch):
    def exploding(*args, **kwargs):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", exploding)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "zh-zh-vi", ["9:16"]
    )
    assert video_9_16 is None
    assert video_16_9 is None
    assert log == "Lỗi: ffmpeg exploded"


def test_generate_preview_requires_topic():
    csv_text, log = app_module.generate_preview("Từ vựng theo chủ đề", "")
    assert log.startswith("Lỗi:")
    assert "chủ đề" in log


def test_generate_preview_handles_none_topic():
    csv_text, log = app_module.generate_preview("Từ vựng theo chủ đề", None)
    assert log.startswith("Lỗi:")
    assert "chủ đề" in log


def test_generate_preview_vocab_topic_calls_llm_and_formats_csv(monkeypatch):
    from content.schema import VocabCardItem, VocabTopicResult

    def fake_generate_vocab_topic(topic, llm_call):
        assert topic == "bộ băng"
        return VocabTopicResult(
            items=[
                VocabCardItem(hanzi="冰", pinyin="bīng", meaning_vi="băng", icon_prompt="ice"),
                VocabCardItem(hanzi="冷", pinyin=None, meaning_vi="lạnh", icon_prompt="cold"),
            ]
        )

    monkeypatch.setattr(app_module, "generate_vocab_topic", fake_generate_vocab_topic)
    csv_text, log = app_module.generate_preview("Từ vựng theo chủ đề", "bộ băng")
    assert csv_text == "冰,bīng,băng\n冷,,lạnh"
    assert not log.startswith("Lỗi:")


def test_generate_preview_dialogue_topic_calls_llm_and_formats_csv(monkeypatch):
    from content.schema import DialogueResult, DialogueTurn, LessonItem

    def fake_generate_dialogue_topic(topic, llm_call):
        assert topic == "chào hỏi"
        return DialogueResult(
            title="t",
            turns=[
                DialogueTurn(
                    speaker_name="Minh",
                    line=LessonItem(hanzi="你好", pinyin="nǐ hǎo", meaning_vi="xin chào"),
                )
            ],
        )

    monkeypatch.setattr(app_module, "generate_dialogue_topic", fake_generate_dialogue_topic)
    csv_text, log = app_module.generate_preview("Hội thoại theo chủ đề", "chào hỏi")
    assert csv_text == "Minh,你好,nǐ hǎo,xin chào"


def test_generate_preview_manual_mode_returns_error():
    csv_text, log = app_module.generate_preview("Nhập danh sách", "bất kỳ")
    assert log.startswith("Lỗi:")


def test_generate_preview_catches_exception(monkeypatch):
    def exploding(topic, llm_call):
        raise RuntimeError("groq exploded")

    monkeypatch.setattr(app_module, "generate_vocab_topic", exploding)
    csv_text, log = app_module.generate_preview("Từ vựng theo chủ đề", "đồ ăn")
    assert log == "Lỗi: groq exploded"
