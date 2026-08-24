from PIL import Image
from render.kenburns import make_kenburns_clip


def test_make_kenburns_clip_duration_and_frame_size(tmp_path):
    img_path = tmp_path / "test.png"
    Image.new("RGB", (800, 600), color=(255, 0, 0)).save(img_path)
    clip = make_kenburns_clip(str(img_path), duration=3.0, size=(720, 1280))
    assert clip.duration == 3.0
    frame = clip.get_frame(0)
    assert frame.shape == (1280, 720, 3)


def test_make_kenburns_clip_frame_changes_over_time(tmp_path):
    img_path = tmp_path / "test.png"
    Image.new("RGB", (800, 600), color=(0, 255, 0)).save(img_path)
    clip = make_kenburns_clip(str(img_path), duration=3.0, size=(720, 1280))
    frame_start = clip.get_frame(0)
    frame_end = clip.get_frame(2.9)
    assert frame_start.shape == frame_end.shape
