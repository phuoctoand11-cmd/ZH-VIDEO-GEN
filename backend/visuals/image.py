import hashlib
import os
from pathlib import Path

from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw

MODEL_ID = "black-forest-labs/FLUX.1-dev"
# dev (unlike the distilled schnell) is trained for a real step count and
# actually uses guidance_scale — both knobs are what buys the extra prompt
# adherence and detail over schnell's 4-step/no-guidance regime.
DEFAULT_STEPS = 28
DEFAULT_GUIDANCE_SCALE = 3.5
# A retry after a failed/timed-out attempt still needs enough steps for dev
# to converge to something coherent — schnell's old retry value of 2 would
# produce noise on this model.
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
# huggingface_hub's InferenceClient has no read timeout by default, so a
# stalled/cold shared endpoint would hang the request indefinitely instead of
# falling through to the retry/placeholder path below. 60s was tuned for
# schnell's 4-step generation; FLUX.1-dev's 28-step generation routinely
# exceeded it in production (verified: 4 of 5 scene images fell back to the
# placeholder circle on a live run), so this needs real headroom for dev's
# per-step cost plus shared-endpoint queueing/cold-start variance.
REQUEST_TIMEOUT_SECONDS = 180

_client = None


def _get_client() -> InferenceClient:
    global _client
    if _client is None:
        token = os.environ.get("HF_TOKEN")
        if not token:
            raise RuntimeError("HF_TOKEN environment variable is not set")
        _client = InferenceClient(model=MODEL_ID, token=token, timeout=REQUEST_TIMEOUT_SECONDS)
    return _client


def _generate(
    prompt: str,
    width: int = 768,
    height: int = 768,
    steps: int = DEFAULT_STEPS,
    guidance_scale: float = DEFAULT_GUIDANCE_SCALE,
    negative_prompt: str | None = None,
) -> Image.Image:
    client = _get_client()
    return client.text_to_image(
        prompt,
        width=width,
        height=height,
        num_inference_steps=steps,
        guidance_scale=guidance_scale,
        negative_prompt=negative_prompt,
    )


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
            width, height, steps = width // 2, height // 2, RETRY_STEPS

    placeholder = make_placeholder_image(prompt[:40], size=size)
    placeholder.save(cache_path)
    return str(cache_path)
