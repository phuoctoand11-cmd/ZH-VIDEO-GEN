from pathlib import Path

from PIL import Image
import visuals.image as image_module


def test_generate_image_uses_cache(tmp_path, monkeypatch):
    calls = {"count": 0}

    def fake_generate(prompt, width=768, height=768, steps=None, negative_prompt=None):
        calls["count"] += 1
        return Image.new("RGB", (width, height), color=(1, 2, 3))

    monkeypatch.setattr(image_module, "_generate", fake_generate)
    path1 = image_module.generate_image("a cat", str(tmp_path))
    path2 = image_module.generate_image("a cat", str(tmp_path))
    assert path1 == path2
    assert calls["count"] == 1


def test_generate_image_passes_steps_and_negative_prompt_through(tmp_path, monkeypatch):
    captured = {}

    def fake_generate(prompt, width=768, height=768, steps=None, negative_prompt=None):
        captured["steps"] = steps
        captured["negative_prompt"] = negative_prompt
        return Image.new("RGB", (width, height), color=(1, 2, 3))

    monkeypatch.setattr(image_module, "_generate", fake_generate)
    image_module.generate_image("a cat", str(tmp_path), negative_prompt="blurry, text")

    assert captured["steps"] == image_module.DEFAULT_STEPS
    assert captured["negative_prompt"] == "blurry, text"


def test_generate_image_retries_with_reduced_but_nonzero_steps(tmp_path, monkeypatch):
    attempts = []

    def flaky_generate(prompt, width=768, height=768, steps=None, negative_prompt=None):
        attempts.append(steps)
        if len(attempts) == 1:
            raise RuntimeError("timed out")
        return Image.new("RGB", (width, height), color=(1, 2, 3))

    monkeypatch.setattr(image_module, "_generate", flaky_generate)
    image_module.generate_image("a cat", str(tmp_path), max_retries=1)

    assert attempts == [image_module.DEFAULT_STEPS, image_module.RETRY_STEPS]
    assert image_module.RETRY_STEPS > 2


def test_generate_image_falls_back_to_placeholder(tmp_path, monkeypatch):
    def always_fail(prompt, width=768, height=768, steps=None, negative_prompt=None):
        raise RuntimeError("out of memory")

    monkeypatch.setattr(image_module, "_generate", always_fail)
    path = image_module.generate_image("a dog", str(tmp_path), max_retries=1)
    assert Path(path).exists()
    img = Image.open(path)
    assert img.size == (768, 768)

    # The fallback must never bake text onto the placeholder (this image is
    # composited directly as a mascot/avatar) — the corners should stay
    # near-white background rather than a dark box with text drawn over it.
    for corner in [(0, 0), (767, 0), (0, 767), (767, 767)]:
        r, g, b = img.getpixel(corner)
        assert r > 230 and g > 230 and b > 230, f"corner {corner} is not near-white: {(r, g, b)}"


def test_make_placeholder_image_draws_no_text_and_varies_color_by_prompt():
    img_a = image_module.make_placeholder_image("a cat", size=(200, 200))
    img_b = image_module.make_placeholder_image("a dog", size=(200, 200))

    # Corners must be near-white for both, regardless of prompt text.
    for img in (img_a, img_b):
        r, g, b = img.getpixel((0, 0))
        assert r > 230 and g > 230 and b > 230

    # Center pixel is the pastel circle, deterministically chosen from the
    # local palette via a hash of the prompt text (not literal text drawn
    # onto the image).
    center_a = img_a.getpixel((100, 100))
    center_b = img_b.getpixel((100, 100))
    assert center_a in image_module._PLACEHOLDER_PALETTE
    assert center_b in image_module._PLACEHOLDER_PALETTE
    # Same prompt must always map to the same color (deterministic).
    repeat = image_module.make_placeholder_image("a cat", size=(200, 200)).getpixel((100, 100))
    assert repeat == center_a


def test_get_client_builds_inference_client_with_model_and_token(monkeypatch):
    monkeypatch.setattr(image_module, "_client", None)
    monkeypatch.setenv("HF_TOKEN", "hf_fake_token")

    calls = []

    class FakeInferenceClient:
        def __init__(self, model=None, token=None, timeout=None):
            calls.append({"model": model, "token": token, "timeout": timeout})

    monkeypatch.setattr(image_module, "InferenceClient", FakeInferenceClient)

    client = image_module._get_client()

    assert calls == [
        {
            "model": "black-forest-labs/FLUX.1-dev",
            "token": "hf_fake_token",
            "timeout": image_module.REQUEST_TIMEOUT_SECONDS,
        }
    ]
    assert isinstance(client, FakeInferenceClient)

    # A second call must reuse the cached client, not construct a new one.
    image_module._get_client()
    assert len(calls) == 1


def test_generate_calls_client_with_guidance_scale_and_negative_prompt(monkeypatch):
    monkeypatch.setattr(image_module, "_client", None)
    monkeypatch.setenv("HF_TOKEN", "hf_fake_token")

    calls = []

    class FakeInferenceClient:
        def __init__(self, model=None, token=None, timeout=None):
            pass

        def text_to_image(self, prompt, **kwargs):
            calls.append((prompt, kwargs))
            return Image.new("RGB", (kwargs["width"], kwargs["height"]))

    monkeypatch.setattr(image_module, "InferenceClient", FakeInferenceClient)

    image_module._generate("a cat", width=100, height=100, negative_prompt="blurry")

    assert calls == [
        (
            "a cat",
            {
                "width": 100,
                "height": 100,
                "num_inference_steps": image_module.DEFAULT_STEPS,
                "guidance_scale": image_module.DEFAULT_GUIDANCE_SCALE,
                "negative_prompt": "blurry",
            },
        )
    ]


def test_get_client_raises_clear_error_without_hf_token(monkeypatch):
    monkeypatch.setattr(image_module, "_client", None)
    monkeypatch.delenv("HF_TOKEN", raising=False)

    try:
        image_module._get_client()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "HF_TOKEN" in str(exc)
