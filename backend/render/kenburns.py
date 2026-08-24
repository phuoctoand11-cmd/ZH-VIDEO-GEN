import numpy as np
from moviepy import VideoClip
from PIL import Image


def make_kenburns_clip(
    image_path: str, duration: float, size: tuple[int, int], zoom_amount: float = 0.08
) -> VideoClip:
    target_w, target_h = size
    source = Image.open(image_path).convert("RGB")
    cover_scale = max(target_w / source.width, target_h / source.height) * (1.0 + zoom_amount)
    scaled = source.resize((int(source.width * cover_scale), int(source.height * cover_scale)))
    frame_w, frame_h = scaled.size

    def make_frame(t: float) -> np.ndarray:
        progress = (t / duration) if duration > 0 else 0.0
        current_zoom = 1.0 + zoom_amount * progress
        crop_w = min(int(target_w * current_zoom / (1.0 + zoom_amount)), frame_w)
        crop_h = min(int(target_h * current_zoom / (1.0 + zoom_amount)), frame_h)
        x0 = (frame_w - crop_w) // 2
        y0 = (frame_h - crop_h) // 2
        cropped = scaled.crop((x0, y0, x0 + crop_w, y0 + crop_h))
        resized = cropped.resize((target_w, target_h))
        return np.array(resized)

    return VideoClip(make_frame, duration=duration)
