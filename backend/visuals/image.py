import base64
import hashlib
import io
import logging
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

MODEL_ID = "@cf/leonardo/phoenix-1.0"
API_BASE = "https://api.cloudflare.com/client/v4/accounts"
# Phoenix's guidance range is 2-10 (Cloudflare's own default is 2, the low
# end). Verified on production at guidance=8: scenes still drifted toward
# generic decorative filler unrelated to the prompt (see SCENE_NEGATIVE_PROMPT
# in prompt_builder.py) — pushed to the max since context accuracy matters
# more here than generation variety or compositional smoothness.
DEFAULT_GUIDANCE = 10
DEFAULT_STEPS = 30
# A retry after a failed attempt still needs enough steps to converge to
# something coherent, just cheaper than the first attempt.
RETRY_STEPS = 15

# Small local pastel palette for the text-free placeholder image (see
# make_placeholder_image below). Deliberately not imported from render.theme
# to keep visuals/ from depending on render/.
_PLACEHOLDER_PALETTE = [
    (255, 182, 193),  # pastel pink
    (173, 216, 230),  # pastel blue
    (183, 235, 183),  # pastel green
    (255, 218, 170),  # pastel orange
]
REQUEST_TIMEOUT_SECONDS = 60


def _get_credentials() -> tuple[str, str]:
    account_id = os.environ.get("CF_ACCOUNT_ID")
    token = os.environ.get("CF_API_TOKEN")
    if not account_id or not token:
        raise RuntimeError("CF_ACCOUNT_ID and CF_API_TOKEN environment variables must be set")
    return account_id, token


def _generate(
    prompt: str,
    width: int = 768,
    height: int = 768,
    steps: int = DEFAULT_STEPS,
    guidance: float = DEFAULT_GUIDANCE,
    negative_prompt: str | None = None,
) -> Image.Image:
    account_id, token = _get_credentials()
    url = f"{API_BASE}/{account_id}/ai/run/{MODEL_ID}"
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "num_steps": steps,
        "guidance": guidance,
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt

    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    # Cloudflare's documented response shape differs per model (some return
    # raw image bytes, some wrap a base64 string in a JSON envelope) and this
    # model's docs don't specify which — handle both rather than guess wrong.
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        data = response.json()
        if not data.get("success", True):
            raise RuntimeError(f"Cloudflare Workers AI error: {data.get('errors')}")
        image_bytes = base64.b64decode(data["result"]["image"])
    else:
        image_bytes = response.content

    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


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
    steps = DEFAULT_STEPS
    for attempt in range(max_retries + 1):
        try:
            image = _generate(
                prompt, width=width, height=height, steps=steps, negative_prompt=negative_prompt
            )
            image.save(cache_path)
            return str(cache_path)
        except Exception:  # noqa: BLE001 - fall back to a placeholder below
            # Previously silent, which made every real failure indistinguishable
            # from a normal fallback in production — this is the only signal
            # that reaches Cloud Run logs when generation fails.
            logger.exception("generate_image attempt %d failed for prompt: %s", attempt, prompt)
            width, height, steps = width // 2, height // 2, RETRY_STEPS

    placeholder = make_placeholder_image(prompt[:40], size=size)
    placeholder.save(cache_path)
    return str(cache_path)
