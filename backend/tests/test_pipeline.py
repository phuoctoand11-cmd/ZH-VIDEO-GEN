from pathlib import Path

from content.schema import LessonItem
from audio.templates import AudioTemplate, TemplateSegment
from audio.tts import TTSError
import pipeline as pipeline_module


class _FakeClip:
    def __init__(self, label):
        self.label = label


def _fake_synthesize(text, lang, out_path):
    Path(out_path).write_bytes(b"fake")
    return out_path


def _fake_duration(path):
    return 1.0


def _fake_generate_image(prompt, cache_dir):
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    return f"{cache_dir}/img.png"


def _fake_build_scene_clip(item, template, audio_paths, image_path, ratio):
    return _FakeClip(f"{item.hanzi}-{ratio}")


def _fake_assemble_video(clips, out_path):
    Path(out_path).write_bytes(b"fake-video")
    return out_path


def _template():
    return AudioTemplate(name="zh-vi", segments=[
        TemplateSegment(lang="zh", field="hanzi"),
        TemplateSegment(lang="vi", field="meaning_vi"),
    ])


def test_run_pipeline_happy_path(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_module, "synthesize", _fake_synthesize)
    monkeypatch.setattr(pipeline_module, "get_audio_duration", _fake_duration)
    monkeypatch.setattr(pipeline_module, "generate_image", _fake_generate_image)
    monkeypatch.setattr(pipeline_module, "build_scene_clip", _fake_build_scene_clip)
    monkeypatch.setattr(pipeline_module, "assemble_video", _fake_assemble_video)

    items = [LessonItem(hanzi="吃", meaning_vi="ăn"), LessonItem(hanzi="喝", meaning_vi="uống")]
    result = pipeline_module.run_pipeline(items, _template(), ["9:16"], str(tmp_path))

    assert "9:16" in result.video_paths
    assert Path(result.video_paths["9:16"]).exists()
    assert result.item_errors == []


def test_run_pipeline_isolates_item_failure(tmp_path, monkeypatch):
    call_count = {"n": 0}

    def flaky_synthesize(text, lang, out_path):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TTSError("network down")
        Path(out_path).write_bytes(b"fake")
        return out_path

    monkeypatch.setattr(pipeline_module, "synthesize", flaky_synthesize)
    monkeypatch.setattr(pipeline_module, "get_audio_duration", _fake_duration)
    monkeypatch.setattr(pipeline_module, "generate_image", _fake_generate_image)
    monkeypatch.setattr(pipeline_module, "build_scene_clip", _fake_build_scene_clip)
    monkeypatch.setattr(pipeline_module, "assemble_video", _fake_assemble_video)

    items = [LessonItem(hanzi="吃", meaning_vi="ăn"), LessonItem(hanzi="喝", meaning_vi="uống")]
    result = pipeline_module.run_pipeline(items, _template(), ["9:16"], str(tmp_path))

    assert len(result.item_errors) == 1
    assert result.item_errors[0].item.hanzi == "吃"
    assert "9:16" in result.video_paths


def test_run_pipeline_isolates_assembly_failure(tmp_path, monkeypatch):
    def failing_assemble(clips, out_path):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(pipeline_module, "synthesize", _fake_synthesize)
    monkeypatch.setattr(pipeline_module, "get_audio_duration", _fake_duration)
    monkeypatch.setattr(pipeline_module, "generate_image", _fake_generate_image)
    monkeypatch.setattr(pipeline_module, "build_scene_clip", _fake_build_scene_clip)
    monkeypatch.setattr(pipeline_module, "assemble_video", failing_assemble)

    items = [LessonItem(hanzi="吃", meaning_vi="ăn")]
    result = pipeline_module.run_pipeline(items, _template(), ["9:16", "16:9"], str(tmp_path))

    assert result.video_paths == {}
    assert result.item_errors == []
    assert "9:16" in result.assembly_errors
    assert "16:9" in result.assembly_errors
    assert "ffmpeg exploded" in result.assembly_errors["9:16"]
