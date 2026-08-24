import subprocess

from PIL import Image
from content.schema import LessonItem
from audio.templates import AudioTemplate, TemplateSegment
from render.assemble import build_scene_clip, assemble_video


def _make_silence(path, seconds):
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", str(seconds), str(path)],
        check=True, capture_output=True,
    )


def test_build_scene_clip_and_assemble(tmp_path):
    img_path = tmp_path / "img.png"
    Image.new("RGB", (800, 600), color=(10, 20, 30)).save(img_path)
    audio1 = tmp_path / "a1.mp3"
    audio2 = tmp_path / "a2.mp3"
    _make_silence(audio1, 1.0)
    _make_silence(audio2, 1.0)
    item = LessonItem(hanzi="吃", pinyin="chī", meaning_vi="ăn")
    template = AudioTemplate(name="zh-vi", segments=[
        TemplateSegment(lang="zh", field="hanzi"),
        TemplateSegment(lang="vi", field="meaning_vi"),
    ])

    scene = build_scene_clip(item, template, [str(audio1), str(audio2)], str(img_path), "9:16")
    assert abs(scene.duration - 2.0) < 0.05

    out_path = tmp_path / "out.mp4"
    assemble_video([scene], str(out_path))
    assert out_path.exists()

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out_path)],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip())
    assert 1.8 <= duration <= 2.3
