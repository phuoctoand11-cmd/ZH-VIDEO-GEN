import subprocess

import numpy as np
from PIL import Image
from render.assemble import build_static_scene_clip


def _make_silence(path, seconds):
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", str(seconds), str(path)],
        check=True, capture_output=True,
    )


def test_build_static_scene_clip_has_no_text_overlay(tmp_path):
    img_path = tmp_path / "card.png"
    Image.new("RGB", (720, 1280), color=(200, 100, 50)).save(img_path)
    audio1 = tmp_path / "a1.mp3"
    _make_silence(audio1, 1.5)

    scene = build_static_scene_clip(str(img_path), [str(audio1)], "9:16")
    assert abs(scene.duration - 1.5) < 0.05

    frame = scene.get_frame(0.1)
    # source is a flat solid color; a resize/crop would still preserve it, so
    # if the frame still matches exactly, no overlay shapes/text were drawn.
    assert tuple(frame[0, 0]) == (200, 100, 50)


def test_build_static_scene_clip_has_no_pan_or_zoom(tmp_path):
    # The user explicitly asked for genuinely still images (voice narration
    # over a static frame, no motion) — a multi-band image would visibly
    # shift/crop under the old Ken Burns pan, so identical frames at three
    # different timestamps is a real regression check, not a tautology.
    img_path = tmp_path / "card.png"
    img = Image.new("RGB", (720, 1280), (255, 255, 255))
    for i, color in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
        band = Image.new("RGB", (720, 1280 // 3), color)
        img.paste(band, (0, i * (1280 // 3)))
    img.save(img_path)

    audio1 = tmp_path / "a2.mp3"
    _make_silence(audio1, 3.0)

    scene = build_static_scene_clip(str(img_path), [str(audio1)], "9:16")
    frame_a = scene.get_frame(0.2)
    frame_b = scene.get_frame(1.5)
    frame_c = scene.get_frame(2.8)
    assert np.array_equal(frame_a, frame_b)
    assert np.array_equal(frame_b, frame_c)
