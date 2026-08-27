from pathlib import Path

from PIL import Image
import visuals.image as image_module


def test_generate_image_uses_cache(tmp_path, monkeypatch):
    calls = {"count": 0}

    def fake_generate(prompt, width=768, height=768, negative_prompt=None):
        calls["count"] += 1
        return Image.new("RGB", (width, height), color=(1, 2, 3))

    monkeypatch.setattr(image_module, "_generate", fake_generate)
    path1 = image_module.generate_image("a cat", str(tmp_path))
    path2 = image_module.generate_image("a cat", str(tmp_path))
    assert path1 == path2
    assert calls["count"] == 1


def test_generate_image_passes_negative_prompt_through(tmp_path, monkeypatch):
    captured = {}

    def fake_generate(prompt, width=768, height=768, negative_prompt=None):
        captured["negative_prompt"] = negative_prompt
        return Image.new("RGB", (width, height), color=(1, 2, 3))

    monkeypatch.setattr(image_module, "_generate", fake_generate)
    image_module.generate_image("a cat", str(tmp_path), negative_prompt="blurry, text")

    assert captured["negative_prompt"] == "blurry, text"


def test_generate_image_retries_with_halved_resolution(tmp_path, monkeypatch):
    attempts = []

    def flaky_generate(prompt, width=768, height=768, negative_prompt=None):
        attempts.append((width, height))
        if len(attempts) == 1:
            raise RuntimeError("out of memory")
        return Image.new("RGB", (width, height), color=(1, 2, 3))

    monkeypatch.setattr(image_module, "_generate", flaky_generate)
    image_module.generate_image("a cat", str(tmp_path), max_retries=1, size=(768, 576))

    assert attempts == [(768, 576), (384, 288)]


def test_generate_image_falls_back_to_placeholder(tmp_path, monkeypatch):
    def always_fail(prompt, width=768, height=768, negative_prompt=None):
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


def test_get_pipeline_builds_once_and_caches(monkeypatch):
    monkeypatch.setattr(image_module, "_pipeline", None)

    calls = []

    class FakeScheduler:
        config = object()

        @classmethod
        def from_config(cls, config):
            return cls()

    class FakePipeline:
        def __init__(self):
            self.scheduler = "original-scheduler"
            self.loaded_loras = []

        def load_lora_weights(self, lora_id):
            self.loaded_loras.append(lora_id)

    fake_pipeline = FakePipeline()

    class FakeAutoPipeline:
        @staticmethod
        def from_pretrained(model_id, torch_dtype=None, safety_checker=None):
            calls.append({"model_id": model_id, "safety_checker": safety_checker})
            return fake_pipeline

    monkeypatch.setattr(image_module, "AutoPipelineForText2Image", FakeAutoPipeline)
    monkeypatch.setattr(image_module, "LCMScheduler", FakeScheduler)

    pipe = image_module._get_pipeline()

    assert pipe is fake_pipeline
    assert calls == [{"model_id": image_module.MODEL_ID, "safety_checker": None}]
    assert fake_pipeline.loaded_loras == [image_module.LORA_ID]
    assert isinstance(pipe.scheduler, FakeScheduler)

    # A second call must reuse the cached pipeline, not rebuild it.
    image_module._get_pipeline()
    assert len(calls) == 1


def test_generate_calls_pipeline_with_expected_kwargs(monkeypatch):
    monkeypatch.setattr(image_module, "_pipeline", None)

    captured = {}

    class FakeResult:
        images = [Image.new("RGB", (100, 100))]

    class FakePipeline:
        def __call__(self, **kwargs):
            captured.update(kwargs)
            return FakeResult()

    monkeypatch.setattr(image_module, "_get_pipeline", lambda: FakePipeline())

    image = image_module._generate("a cat", width=100, height=100, negative_prompt="blurry")

    assert captured == {
        "prompt": "a cat",
        "negative_prompt": "blurry",
        "width": 100,
        "height": 100,
        "num_inference_steps": image_module.DEFAULT_STEPS,
        "guidance_scale": image_module.DEFAULT_GUIDANCE,
    }
    assert image.size == (100, 100)
