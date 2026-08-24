import hashlib
import os
from pathlib import Path

from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw

MODEL_ID = "black-forest-labs/FLUX.1-schnell"

_client = None


def _get_client() -> InferenceClient:
    global _client
    if _client is None:
        token = os.environ.get("HF_TOKEN")
        if not token:
            raise RuntimeError("HF_TOKEN environment variable is not set")
        _client = InferenceClient(model=MODEL_ID, token=token)
    return _client


def _generate(prompt: str, width: int = 768, height: int = 768, steps: int = 4) -> Image.Image:
    client = _get_client()
    return client.text_to_image(prompt, width=width, height=height, num_inference_steps=steps)


def make_placeholder_image(text: str, size: tuple[int, int] = (768, 768)) -> Image.Image:
    image = Image.new("RGB", size, color=(60, 60, 90))
    draw = ImageDraw.Draw(image)
    draw.text((20, size[1] // 2), text, fill=(255, 255, 255))
    return image


def generate_image(prompt: str, cache_dir: str, max_retries: int = 1) -> str:
    cache_path = Path(cache_dir) / f"{hashlib.sha256(prompt.encode()).hexdigest()}.png"
    if cache_path.exists():
        return str(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    width, height, steps = 768, 768, 4
    for attempt in range(max_retries + 1):
        try:
            image = _generate(prompt, width=width, height=height, steps=steps)
            image.save(cache_path)
            return str(cache_path)
        except Exception:  # noqa: BLE001 - fall back to a placeholder below
            width, height, steps = 512, 512, 2

    placeholder = make_placeholder_image(prompt[:40])
    placeholder.save(cache_path)
    return str(cache_path)
