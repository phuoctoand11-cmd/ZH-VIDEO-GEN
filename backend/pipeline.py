from dataclasses import dataclass, field

from audio.templates import AudioTemplate
from audio.tts import TTSError, make_silence, synthesize
from content.pinyin import fill_pinyin_batch
from content.schema import (
    DialogueResult,
    DialogueTurn,
    LessonItem,
    VocabCardItem,
    VocabTopicResult,
)
from render.assemble import ASPECT_SIZES, assemble_video, build_static_scene_clip
from render.dialogue_card import draw_dialogue_turn
from render.vocab_card import draw_vocab_card
from visuals.image import generate_image
from visuals.prompt_builder import SCENE_NEGATIVE_PROMPT, build_avatar_prompt, build_scene_prompt
from visuals.scene_library import find_cached_image, store_generated_image

SCENE_IMAGE_SIZE = (768, 576)


@dataclass
class ItemResult:
    item: LessonItem
    error: str | None = None


@dataclass
class PipelineResult:
    video_paths: dict[str, str] = field(default_factory=dict)
    item_errors: list[ItemResult] = field(default_factory=list)
    assembly_errors: dict[str, str] = field(default_factory=dict)


def run_vocab_card_pipeline(
    result: VocabTopicResult,
    template: AudioTemplate,
    aspect_ratios: list[str],
    work_dir: str,
    topic_label: str | None = None,
) -> PipelineResult:
    filled_lines = fill_pinyin_batch(
        [LessonItem(hanzi=i.hanzi, pinyin=i.pinyin, meaning_vi=i.meaning_vi) for i in result.items]
    )
    items = [
        VocabCardItem(
            hanzi=line.hanzi, pinyin=line.pinyin, meaning_vi=line.meaning_vi, icon_prompt=orig.icon_prompt
        )
        for line, orig in zip(filled_lines, result.items)
    ]
    result = VocabTopicResult(
        radical=result.radical,
        radical_pinyin=result.radical_pinyin,
        radical_meaning_vi=result.radical_meaning_vi,
        items=items,
    )

    image_paths = []
    for item in items:
        cached_path = find_cached_image(item.hanzi, cache_dir=f"{work_dir}/scenes")
        if cached_path is not None:
            image_paths.append(cached_path)
            continue

        def _remember(path: str, item=item) -> None:
            store_generated_image(item.hanzi, item.pinyin, item.meaning_vi, item.icon_prompt, path)

        image_paths.append(
            generate_image(
                build_scene_prompt(item.icon_prompt),
                cache_dir=f"{work_dir}/scenes",
                size=SCENE_IMAGE_SIZE,
                negative_prompt=SCENE_NEGATIVE_PROMPT,
                on_success=_remember,
            )
        )

    all_audio_paths: list[str] = []
    for index, item in enumerate(items):
        for seg_index, segment in enumerate(template.segments):
            text = item.hanzi if segment.lang == "zh" else item.meaning_vi
            audio_path = f"{work_dir}/vocab_audio_{index}_{seg_index}.mp3"
            try:
                synthesize(text, segment.lang, audio_path)
            except TTSError:
                make_silence(audio_path, seconds=2.0)
            all_audio_paths.append(audio_path)

    video_paths: dict[str, str] = {}
    assembly_errors: dict[str, str] = {}
    for ratio in aspect_ratios:
        size = ASPECT_SIZES[ratio]
        try:
            card = draw_vocab_card(result, image_paths, size, topic_label=topic_label)
            card_path = f"{work_dir}/vocab_card_{ratio.replace(':', 'x')}.png"
            card.save(card_path)
            clip = build_static_scene_clip(card_path, all_audio_paths, ratio)
            out_path = f"{work_dir}/output_{ratio.replace(':', 'x')}.mp4"
            try:
                clip.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
                video_paths[ratio] = out_path
            finally:
                clip.close()
        except Exception as exc:  # noqa: BLE001 - a bad ratio must not stop the others
            assembly_errors[ratio] = str(exc)

    return PipelineResult(video_paths=video_paths, item_errors=[], assembly_errors=assembly_errors)


def run_dialogue_pipeline(
    result: DialogueResult,
    template: AudioTemplate,
    aspect_ratios: list[str],
    work_dir: str,
) -> PipelineResult:
    speaker_names = list(dict.fromkeys(turn.speaker_name for turn in result.turns))
    avatar_paths = {
        name: generate_image(build_avatar_prompt(name), cache_dir=f"{work_dir}/avatars")
        for name in speaker_names
    }

    scene_clips: dict[str, list] = {ratio: [] for ratio in aspect_ratios}
    item_errors: list[ItemResult] = []

    for index, turn in enumerate(result.turns):
        try:
            line = fill_pinyin_batch([turn.line])[0]
            audio_paths = []
            for seg_index, segment in enumerate(template.segments):
                text = line.hanzi if segment.lang == "zh" else line.meaning_vi
                audio_path = f"{work_dir}/dlg_audio_{index}_{seg_index}.mp3"
                synthesize(text, segment.lang, audio_path)
                audio_paths.append(audio_path)

            for ratio in aspect_ratios:
                size = ASPECT_SIZES[ratio]
                card = draw_dialogue_turn(
                    DialogueTurn(speaker_name=turn.speaker_name, line=line),
                    avatar_paths[turn.speaker_name],
                    size,
                )
                card_path = f"{work_dir}/dlg_card_{index}_{ratio.replace(':', 'x')}.png"
                card.save(card_path)
                clip = build_static_scene_clip(card_path, audio_paths, ratio)
                scene_clips[ratio].append(clip)
        except Exception as exc:  # noqa: BLE001 - one bad turn must not stop the batch
            item_errors.append(ItemResult(item=turn.line, error=str(exc)))

    video_paths: dict[str, str] = {}
    assembly_errors: dict[str, str] = {}
    for ratio, clips in scene_clips.items():
        if not clips:
            continue
        out_path = f"{work_dir}/output_{ratio.replace(':', 'x')}.mp4"
        try:
            assemble_video(clips, out_path)
            video_paths[ratio] = out_path
        except Exception as exc:  # noqa: BLE001
            assembly_errors[ratio] = str(exc)

    return PipelineResult(
        video_paths=video_paths, item_errors=item_errors, assembly_errors=assembly_errors
    )
