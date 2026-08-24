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


def test_get_client_builds_inference_client_with_model_and_token(monkeypatch):
    monkeypatch.setattr(image_module, "_client", None)
    monkeypatch.setenv("HF_TOKEN", "hf_fake_token")

    calls = []

    class FakeInferenceClient:
        def __init__(self, model=None, token=None):
            calls.append({"model": model, "token": token})

    monkeypatch.setattr(image_module, "InferenceClient", FakeInferenceClient)

    client = image_module._get_client()

    assert calls == [{"model": "black-forest-labs/FLUX.1-schnell", "token": "hf_fake_token"}]
    assert isinstance(client, FakeInferenceClient)

    # A second call must reuse the cached client, not construct a new one.
    image_module._get_client()
    assert len(calls) == 1


def test_get_client_raises_clear_error_without_hf_token(monkeypatch):
    monkeypatch.setattr(image_module, "_client", None)
    monkeypatch.delenv("HF_TOKEN", raising=False)

    try:
        image_module._get_client()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "HF_TOKEN" in str(exc)
