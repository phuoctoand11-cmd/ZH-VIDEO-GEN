from pathlib import Path

from PIL import Image
import visuals.image as image_module


def test_generate_image_uses_cache(tmp_path, monkeypatch):
    calls = {"count": 0}

    def fake_generate(prompt, width=768, height=768, steps=4):
        calls["count"] += 1
        return Image.new("RGB", (width, height), color=(1, 2, 3))

    monkeypatch.setattr(image_module, "_generate", fake_generate)
    path1 = image_module.generate_image("a cat", str(tmp_path))
    path2 = image_module.generate_image("a cat", str(tmp_path))
    assert path1 == path2
    assert calls["count"] == 1


def test_generate_image_falls_back_to_placeholder(tmp_path, monkeypatch):
    def always_fail(prompt, width=768, height=768, steps=4):
        raise RuntimeError("out of memory")

    monkeypatch.setattr(image_module, "_generate", always_fail)
    path = image_module.generate_image("a dog", str(tmp_path), max_retries=1)
    assert Path(path).exists()
    img = Image.open(path)
    assert img.size == (768, 768)
