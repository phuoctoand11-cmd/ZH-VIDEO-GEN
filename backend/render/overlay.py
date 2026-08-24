from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from content.schema import LessonItem
from audio.templates import AudioTemplate


FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NotoSansCJKsc-Regular.otf"


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


def draw_text_on_frame(frame: np.ndarray, text: str, font_size: int = 60) -> np.ndarray:
    image = Image.fromarray(frame).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    width, _height = image.size
    lines = text.split("\n")
    line_height = int(font_size * 1.4)
    total_text_height = line_height * len(lines)
    y = image.size[1] - total_text_height - 40
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) / 2
        draw.rectangle([x - 10, y - 5, x + text_width + 10, y + font_size + 10], fill=(0, 0, 0))
        draw.text((x, y), line, fill=(255, 255, 255), font=font)
        y += line_height
    return np.array(image)
