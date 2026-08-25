import subprocess

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
    # source is a flat solid color; Ken Burns only crops/resizes it, so if the
    # frame still matches exactly, no overlay shapes/text were drawn on top.
    assert tuple(frame[0, 0]) == (200, 100, 50)
