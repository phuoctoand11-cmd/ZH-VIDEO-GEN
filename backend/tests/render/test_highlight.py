import numpy as np
import pytest
from PIL import Image

from render.highlight import make_highlight_clip


def _make_card(tmp_path, size=(720, 2000)):
    path = tmp_path / "card.png"
    Image.new("RGB", size, color=(50, 60, 70)).save(path)
    return str(path)


def _make_banded_card(tmp_path, size):
    """A card with three distinct horizontal color bands (top/middle/bottom),
    so that crops centered on different y_centers are visibly different —
    unlike a solid-color card, which would look identical regardless of crop
    position and so could never catch a no-op zoom.
    """
    width, height = size
    image = Image.new("RGB", size, color=(0, 0, 0))
    band_colors = [(220, 40, 40), (40, 200, 60), (40, 60, 220)]
    for band_index, color in enumerate(band_colors):
        y0 = height * band_index // 3
        y1 = height * (band_index + 1) // 3
        image.paste(Image.new("RGB", (width, y1 - y0), color=color), (0, y0))
    path = tmp_path / "banded_card.png"
    image.save(path)
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


def test_make_highlight_clip_zooms_to_different_rows_when_source_is_taller_than_target(tmp_path):
    """Regression test for the row-zoom no-op bug: when the source card is a
    taller "master" canvas than the target output size (the real production
    shape — pipeline.py now draws the vocab card at a taller render_size and
    make_highlight_clip pans a full-width window down it), each row's crop
    window must still differ, producing visibly different frames per row
    instead of a static full-frame image.
    """
    source_size = (720, 3200)
    target_size = (720, 1280)
    card_path = _make_banded_card(tmp_path, source_size)
    y_centers = [0.15, 0.5, 0.85]
    durations = [1.0, 1.0, 1.0]

    clip = make_highlight_clip(
        card_path, y_centers=y_centers, durations=durations, size=target_size
    )

    frames = [clip.get_frame(t) for t in (0.5, 1.5, 2.5)]

    assert not np.array_equal(frames[0], frames[1])
    assert not np.array_equal(frames[1], frames[2])
    assert not np.array_equal(frames[0], frames[2])
