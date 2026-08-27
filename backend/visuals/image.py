import hashlib
import logging
import os
from pathlib import Path

from gradio_client import Client
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# A separate Hugging Face Space (hf-space-image-gen/ in this repo) running
# FLUX.1-schnell on ZeroGPU — inference happens on HF's real GPU allocation,
# not in this container, so this service never needs torch/diffusers itself.
# Set to the actual deployed Space's owner/name (e.g. "username/space-name").
SPACE_ID = os.environ.get("IMAGE_SPACE_ID", "")
DEFAULT_WIDTH = 768
DEFAULT_HEIGHT = 576

# Small local pastel palette for the text-free placeholder image (see
# make_placeholder_image below). Deliberately not imported from render.theme
# to keep visuals/ from depending on render/.
_PLACEHOLDER_PALETTE = [
    (255, 182, 193),  # pastel pink
    (173, 216, 230),  # pastel blue
    (183, 235, 183),  # pastel green
    (255, 218, 170),  # pastel orange
]

_client = None


def _get_client() -> Client:
    global _client
    if _client is None:
        token = os.environ.get("HF_TOKEN")
        if not token:
            raise RuntimeError("HF_TOKEN environment variable is not set")
        if not SPACE_ID:
            raise RuntimeError("IMAGE_SPACE_ID environment variable is not set")
        # Passing hf_token authenticates the call so it draws from this
        # account's own ZeroGPU daily quota (5 min/day on a free account)
        # instead of the much stricter shared pool used for unauthenticated
        # requests (2 min/day, shared across every visitor to the Space).
        _client = Client(SPACE_ID, hf_token=token)
    return _client


def _generate(
    prompt: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    negative_prompt: str | None = None,
) -> Image.Image:
    # negative_prompt is accepted for interface symmetry with the rest of the
    # pipeline but not forwarded: the Space runs FLUX.1-schnell at
    # guidance_scale=0 (required — schnell is guidance-distilled), and
    # negative_prompt has no effect without classifier-free guidance.
    del negative_prompt
    client = _get_client()
    result_path = client.predict(prompt, width, height, api_name="/generate")
    return Image.open(result_path).convert("RGB")


def make_placeholder_image(text: str, size: tuple[int, int] = (768, 768)) -> Image.Image:
    """Text-free fallback used when AI image generation fails. This project's
    core design invariant is "AI never renders text, only code does" — this
    placeholder is composited directly as a mascot/avatar on the learning
    card, so it must never draw literal characters (that would put
    AI-adjacent/English text into a slot the rest of the app treats as pure
    graphics). Instead: a near-white background (so render.theme's white
    knockout composites it cleanly, like a real generated mascot) with a
    plain pastel circle, colored deterministically from `text` so repeated
    prompts still look visually distinct from one another.
    """
    width, height = size
    background = (250, 250, 250)
    image = Image.new("RGB", size, color=background)
    draw = ImageDraw.Draw(image)

    color_index = int(hashlib.sha256(text.encode()).hexdigest(), 16) % len(_PLACEHOLDER_PALETTE)
    color = _PLACEHOLDER_PALETTE[color_index]

    radius = int(min(width, height) * 0.32)
    cx, cy = width // 2, height // 2
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)

    return image


def generate_image(
    prompt: str,
    cache_dir: str,
    max_retries: int = 1,
    size: tuple[int, int] = (768, 768),
    negative_prompt: str | None = None,
) -> str:
    cache_path = Path(cache_dir) / f"{hashlib.sha256(prompt.encode()).hexdigest()}.png"
    if cache_path.exists():
        return str(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = size
    for attempt in range(max_retries + 1):
        try:
            image = _generate(
                prompt, width=width, height=height, negative_prompt=negative_prompt
            )
            image.save(cache_path)
            return str(cache_path)
        except Exception:  # noqa: BLE001 - fall back to a placeholder below
            logger.exception("generate_image attempt %d failed for prompt: %s", attempt, prompt)
            width, height = width // 2, height // 2

    placeholder = make_placeholder_image(prompt[:40], size=size)
    placeholder.save(cache_path)
    return str(cache_path)
