import pytest
from PIL import Image

from render.highlight import make_highlight_clip


def _make_card(tmp_path, size=(720, 2000)):
    path = tmp_path / "card.png"
    Image.new("RGB", size, color=(50, 60, 70)).save(path)
    return str(path)


def test_make_highlight_clip_duration_matches_sum_of_durations(tmp_path):
    clip = make_highlight_clip(
        _make_card(tmp_path), y_centers=[0.1, 0.5, 0.9], durations=[1.0, 1.5, 2.0], size=(720, 1280)
    )
    assert abs(clip.duration - 4.5) < 0.01


def test_make_highlight_clip_frame_matches_target_size(tmp_path):
    clip = make_highlight_clip(_make_card(tmp_path), y_centers=[0.5], durations=[2.0], size=(720, 1280))
    frame = clip.get_frame(1.0)
    assert frame.shape == (1280, 720, 3)


def test_make_highlight_clip_rejects_mismatched_lengths(tmp_path):
    with pytest.raises(ValueError):
        make_highlight_clip(_make_card(tmp_path), y_centers=[0.1, 0.5], durations=[1.0], size=(720, 1280))


def test_make_highlight_clip_rejects_empty_regions(tmp_path):
    with pytest.raises(ValueError):
        make_highlight_clip(_make_card(tmp_path), y_centers=[], durations=[], size=(720, 1280))
