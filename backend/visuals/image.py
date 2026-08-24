import hashlib
from pathlib import Path

from PIL import Image, ImageDraw

try:
    import spaces
except ImportError:
    class _NoOpSpaces:
        @staticmethod
        def GPU(func):
            return func

    spaces = _NoOpSpaces()

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        import torch
        from diffusers import FluxPipeline

        _pipeline = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-schnell", torch_dtype=torch.bfloat16
        )
        _pipeline.to("cuda")
    return _pipeline


@spaces.GPU
def _generate(prompt: str, width: int = 768, height: int = 768, steps: int = 4) -> Image.Image:
    pipeline = _get_pipeline()
    result = pipeline(prompt, width=width, height=height, num_inference_steps=steps)
    return result.images[0]


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
