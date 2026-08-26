import base64
import io
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


def _png_bytes(size=(4, 4), color=(10, 20, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="PNG")
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, headers, json_data=None, content=b""):
        self.headers = headers
        self._json_data = json_data
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self._json_data


def test_get_credentials_reads_account_id_and_token_from_env(monkeypatch):
    monkeypatch.setenv("CF_ACCOUNT_ID", "acct123")
    monkeypatch.setenv("CF_API_TOKEN", "cf_fake_token")

    assert image_module._get_credentials() == ("acct123", "cf_fake_token")


def test_get_credentials_raises_clear_error_when_missing(monkeypatch):
    monkeypatch.delenv("CF_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CF_API_TOKEN", raising=False)

    try:
        image_module._get_credentials()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "CF_ACCOUNT_ID" in str(exc)
        assert "CF_API_TOKEN" in str(exc)


def test_generate_posts_expected_payload_and_parses_json_envelope(monkeypatch):
    monkeypatch.setenv("CF_ACCOUNT_ID", "acct123")
    monkeypatch.setenv("CF_API_TOKEN", "cf_fake_token")

    calls = []
    image_b64 = base64.b64encode(_png_bytes()).decode()

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse(
            headers={"content-type": "application/json"},
            json_data={"success": True, "result": {"image": image_b64}},
        )

    monkeypatch.setattr(image_module.requests, "post", fake_post)

    image = image_module._generate("a cat", width=100, height=100, negative_prompt="blurry")

    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == f"{image_module.API_BASE}/acct123/ai/run/{image_module.MODEL_ID}"
    assert call["headers"] == {"Authorization": "Bearer cf_fake_token"}
    assert call["json"] == {
        "prompt": "a cat",
        "width": 100,
        "height": 100,
        "num_steps": image_module.DEFAULT_STEPS,
        "guidance": image_module.DEFAULT_GUIDANCE,
        "negative_prompt": "blurry",
    }
    assert image.size == (4, 4)


def test_generate_handles_raw_binary_response(monkeypatch):
    monkeypatch.setenv("CF_ACCOUNT_ID", "acct123")
    monkeypatch.setenv("CF_API_TOKEN", "cf_fake_token")

    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse(headers={"content-type": "image/png"}, content=_png_bytes())

    monkeypatch.setattr(image_module.requests, "post", fake_post)

    image = image_module._generate("a cat", width=100, height=100)
    assert image.size == (4, 4)


def test_generate_omits_negative_prompt_key_when_not_given(monkeypatch):
    monkeypatch.setenv("CF_ACCOUNT_ID", "acct123")
    monkeypatch.setenv("CF_API_TOKEN", "cf_fake_token")

    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        return _FakeResponse(headers={"content-type": "image/png"}, content=_png_bytes())

    monkeypatch.setattr(image_module.requests, "post", fake_post)

    image_module._generate("a cat", width=100, height=100)

    assert "negative_prompt" not in calls[0]
