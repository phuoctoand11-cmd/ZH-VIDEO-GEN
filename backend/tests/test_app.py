import app as app_module
from app import _load_templates


def test_load_templates_includes_expected_names():
    templates = _load_templates()
    assert "zh-zh-vi" in templates
    assert "zh-vi-zh" in templates


def _valid_csv():
    return "hanzi,pinyin,meaning_vi\n吃,chī,ăn"


def test_generate_video_unknown_template_returns_error(monkeypatch):
    def unexpected_run_pipeline(*args, **kwargs):
        raise AssertionError("run_pipeline must not be called for an unknown template")

    monkeypatch.setattr(app_module, "run_pipeline", unexpected_run_pipeline)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "", "khong-ton-tai", ["9:16"]
    )
    assert video_9_16 is None
    assert video_16_9 is None
    assert log.startswith("Lỗi:")
    assert "khong-ton-tai" in log


def test_generate_video_empty_aspect_ratios_skips_generation(monkeypatch):
    calls = {"count": 0}

    def counting_run_pipeline(*args, **kwargs):
        calls["count"] += 1
        raise AssertionError("run_pipeline must not be called with no aspect ratio")

    monkeypatch.setattr(app_module, "run_pipeline", counting_run_pipeline)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "", "zh-zh-vi", []
    )
    assert calls["count"] == 0
    assert video_9_16 is None
    assert video_16_9 is None
    assert log.startswith("Lỗi:")
    assert "tỉ lệ khung hình" in log


def test_generate_video_invalid_aspect_ratio_returns_error(monkeypatch):
    def unexpected_run_pipeline(*args, **kwargs):
        raise AssertionError("run_pipeline must not be called for an invalid aspect ratio")

    monkeypatch.setattr(app_module, "run_pipeline", unexpected_run_pipeline)
    _, _, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "", "zh-zh-vi", ["4:3"]
    )
    assert log.startswith("Lỗi:")
    assert "4:3" in log


def test_generate_video_catches_pipeline_exception(monkeypatch):
    def exploding_run_pipeline(items, template, aspect_ratios, work_dir):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(app_module, "run_pipeline", exploding_run_pipeline)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "", "zh-zh-vi", ["9:16"]
    )
    assert video_9_16 is None
    assert video_16_9 is None
    assert log == "Lỗi: ffmpeg exploded"
