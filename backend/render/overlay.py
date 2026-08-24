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


TEXT_MARGIN = 20


def _measure(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _wrap_line(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """Greedily wrap `text` onto sub-lines that each fit within `max_width`.

    Wrapping happens on spaces only (pinyin syllables / Vietnamese words). A
    single unbreakable token wider than `max_width` (e.g. a long run of hanzi)
    is left on its own line as-is.
    """
    if not text:
        return [text]
    if _measure(draw, text, font) <= max_width:
        return [text]

    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if current and _measure(draw, candidate, font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [text]


def draw_text_on_frame(frame: np.ndarray, text: str, font_size: int = 60) -> np.ndarray:
    image = Image.fromarray(frame).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    width, _height = image.size
    max_text_width = max(width - 2 * TEXT_MARGIN, 1)
    lines: list[str] = []
    for raw_line in text.split("\n"):
        lines.extend(_wrap_line(draw, raw_line, font, max_text_width))
    line_height = int(font_size * 1.4)
    total_text_height = line_height * len(lines)
    y = image.size[1] - total_text_height - 40
    for line in lines:
        text_width = _measure(draw, line, font)
        x = (width - text_width) / 2
        draw.rectangle([x - 10, y - 5, x + text_width + 10, y + font_size + 10], fill=(0, 0, 0))
        draw.text((x, y), line, fill=(255, 255, 255), font=font)
        y += line_height
    return np.array(image)
