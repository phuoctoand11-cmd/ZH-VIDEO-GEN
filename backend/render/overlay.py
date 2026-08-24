from dataclasses import dataclass

from content.schema import LessonItem
from audio.templates import AudioTemplate


@dataclass
class OverlayCue:
    start: float
    end: float
    text: str


def build_overlay_cues(
    item: LessonItem, template: AudioTemplate, segment_durations: list[float]
) -> list[OverlayCue]:
    if len(template.segments) != len(segment_durations):
        raise ValueError("segment_durations length must match template.segments length")
    cues: list[OverlayCue] = []
    t = 0.0
    for segment, duration in zip(template.segments, segment_durations):
        if segment.lang == "zh":
            text = f"{item.hanzi}\n{item.pinyin or ''}".strip()
        else:
            text = item.meaning_vi
        cues.append(OverlayCue(start=t, end=t + duration, text=text))
        t += duration
    return cues


def total_duration(segment_durations: list[float]) -> float:
    return sum(segment_durations)
