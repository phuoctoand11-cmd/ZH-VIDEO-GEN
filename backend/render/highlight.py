import bisect

import numpy as np
from moviepy import VideoClip
from PIL import Image


def make_highlight_clip(
    image_path: str,
    y_centers: list[float],
    durations: list[float],
    size: tuple[int, int],
    zoom_height_frac: float = 0.4,
) -> VideoClip:
    if len(y_centers) != len(durations):
        raise ValueError("y_centers and durations must have the same length")
    if not y_centers:
        raise ValueError("y_centers must not be empty")

    target_w, target_h = size
    source = Image.open(image_path).convert("RGB")
    cover_scale = max(target_w / source.width, target_h / source.height)
    scaled = source.resize((int(source.width * cover_scale), int(source.height * cover_scale)))
    frame_w, frame_h = scaled.size

    crop_h = max(target_h, min(int(frame_h * zoom_height_frac), frame_h))
    crop_w = min(int(crop_h * target_w / target_h), frame_w)

    boundaries: list[float] = []
    running = 0.0
    for d in durations:
        running += d
        boundaries.append(running)
    total_duration = boundaries[-1]

    def make_frame(t: float) -> np.ndarray:
        clamped_t = min(t, max(total_duration - 1e-6, 0.0))
        row = min(bisect.bisect_right(boundaries, clamped_t), len(y_centers) - 1)
        y_center = int(frame_h * y_centers[row])

        x0 = (frame_w - crop_w) // 2
        y0 = max(0, min(frame_h - crop_h, y_center - crop_h // 2))
        cropped = scaled.crop((x0, y0, x0 + crop_w, y0 + crop_h))
        resized = cropped.resize((target_w, target_h))
        return np.array(resized)

    return VideoClip(make_frame, duration=total_duration)
