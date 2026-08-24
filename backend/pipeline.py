from dataclasses import dataclass, field

from audio.templates import AudioTemplate
from audio.tts import synthesize
from content.pinyin import fill_pinyin_batch
from content.schema import LessonItem
from render.assemble import assemble_video, build_scene_clip
from visuals.image import generate_image
from visuals.prompt_builder import build_image_prompt


@dataclass
class ItemResult:
    item: LessonItem
    error: str | None = None


@dataclass
class PipelineResult:
    video_paths: dict[str, str] = field(default_factory=dict)
    item_errors: list[ItemResult] = field(default_factory=list)
    assembly_errors: dict[str, str] = field(default_factory=dict)


def run_pipeline(
    items: list[LessonItem],
    template: AudioTemplate,
    aspect_ratios: list[str],
    work_dir: str,
) -> PipelineResult:
    items = fill_pinyin_batch(items)
    scene_clips: dict[str, list] = {ratio: [] for ratio in aspect_ratios}
    item_errors: list[ItemResult] = []

    for index, item in enumerate(items):
        try:
            audio_paths = []
            for seg_index, segment in enumerate(template.segments):
                text = item.hanzi if segment.lang == "zh" else item.meaning_vi
                audio_path = f"{work_dir}/audio_{index}_{seg_index}.mp3"
                synthesize(text, segment.lang, audio_path)
                audio_paths.append(audio_path)

            prompt = build_image_prompt(item)
            image_path = generate_image(prompt, cache_dir=f"{work_dir}/images")

            for ratio in aspect_ratios:
                clip = build_scene_clip(item, template, audio_paths, image_path, ratio)
                scene_clips[ratio].append(clip)
        except Exception as exc:  # noqa: BLE001 - one bad item must not stop the batch
            item_errors.append(ItemResult(item=item, error=str(exc)))

    video_paths: dict[str, str] = {}
    assembly_errors: dict[str, str] = {}
    for ratio, clips in scene_clips.items():
        if not clips:
            continue
        out_path = f"{work_dir}/output_{ratio.replace(':', 'x')}.mp4"
        try:
            assemble_video(clips, out_path)
            video_paths[ratio] = out_path
        except Exception as exc:  # noqa: BLE001 - ffmpeg failure must not crash the whole run
            assembly_errors[ratio] = str(exc)

    return PipelineResult(
        video_paths=video_paths, item_errors=item_errors, assembly_errors=assembly_errors
    )
