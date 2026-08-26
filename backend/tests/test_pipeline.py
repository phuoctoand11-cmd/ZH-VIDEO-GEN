from pathlib import Path

from PIL import Image

from content.schema import (
    DialogueResult,
    DialogueTurn,
    LessonItem,
    VocabCardItem,
    VocabTopicResult,
)
from audio.templates import AudioTemplate, TemplateSegment
import pipeline as pipeline_module
from pipeline import run_dialogue_pipeline, run_vocab_card_pipeline


def _fake_generate_image_for_cards(prompt, cache_dir, size=(200, 200), negative_prompt=None):
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    path = Path(cache_dir) / f"{abs(hash(prompt))}.png"
    if not path.exists():
        Image.new("RGB", size, color=(255, 255, 255)).save(path)
    return str(path)


def test_run_vocab_card_pipeline_produces_valid_video(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_module, "generate_image", _fake_generate_image_for_cards)

    result = VocabTopicResult(
        radical="冫",
        radical_pinyin="bīng",
        radical_meaning_vi="băng",
        items=[
            VocabCardItem(hanzi="冰", pinyin="bīng", meaning_vi="băng", icon_prompt="ice cube"),
            VocabCardItem(hanzi="冷", pinyin="lěng", meaning_vi="lạnh", icon_prompt="cold penguin"),
        ],
    )
    template = AudioTemplate(name="zh-vi", segments=[TemplateSegment(lang="zh", field="hanzi")])

    output = run_vocab_card_pipeline(result, template, ["9:16"], str(tmp_path))

    assert "9:16" in output.video_paths
    assert output.assembly_errors == {}
    assert Path(output.video_paths["9:16"]).exists()


def test_run_dialogue_pipeline_produces_valid_video(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_module, "generate_image", _fake_generate_image_for_cards)

    result = DialogueResult(
        title="Chào hỏi",
        turns=[
            DialogueTurn(speaker_name="Minh", line=LessonItem(hanzi="你好", meaning_vi="xin chào")),
            DialogueTurn(speaker_name="Lan", line=LessonItem(hanzi="你好吗", meaning_vi="khỏe không")),
        ],
    )
    template = AudioTemplate(name="zh-vi", segments=[TemplateSegment(lang="zh", field="hanzi")])

    output = run_dialogue_pipeline(result, template, ["9:16"], str(tmp_path))

    assert "9:16" in output.video_paths
    assert output.item_errors == []
    assert Path(output.video_paths["9:16"]).exists()
