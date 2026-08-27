import hashlib
import logging
import threading
from pathlib import Path

import torch
from diffusers import AutoPipelineForText2Image, LCMScheduler
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

MODEL_ID = "runwayml/stable-diffusion-v1-5"
LORA_ID = "latent-consistency/lcm-lora-sdv1-5"
# LCM-LoRA is distilled assuming near-unity classifier-free guidance — the
# high guidance values that helped prompt adherence on hosted APIs (FLUX.1-dev
# at 3.5, Cloudflare phoenix-1.0 at 10) actively degrade output here instead.
# 4 steps / guidance 1.0 are the settings documented in the LCM-LoRA release,
# not values tuned by trial here (this pipeline can't be exercised locally).
DEFAULT_STEPS = 4
DEFAULT_GUIDANCE = 1.0

# Small local pastel palette for the text-free placeholder image (see
# make_placeholder_image below). Deliberately not imported from render.theme
# to keep visuals/ from depending on render/.
_PLACEHOLDER_PALETTE = [
    (255, 182, 193),  # pastel pink
    (173, 216, 230),  # pastel blue
    (183, 235, 183),  # pastel green
    (255, 218, 170),  # pastel orange
]

_pipeline = None
_pipeline_lock = threading.Lock()


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:  # re-check: another thread may have built it first
                pipe = AutoPipelineForText2Image.from_pretrained(
                    MODEL_ID, torch_dtype=torch.float32, safety_checker=None
                )
                pipe.load_lora_weights(LORA_ID)
                pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
                _pipeline = pipe
    return _pipeline


def _generate(
    prompt: str,
    width: int = 768,
    height: int = 768,
    steps: int = DEFAULT_STEPS,
    guidance: float = DEFAULT_GUIDANCE,
    negative_prompt: str | None = None,
) -> Image.Image:
    pipe = _get_pipeline()
    # diffusers pipelines are not documented as safe for concurrent __call__
    # from multiple threads sharing one instance, and Gradio can process more
    # than one request at a time — serialize inference explicitly rather than
    # risk silently corrupted output under real concurrency.
    with _pipeline_lock:
        result = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance,
        )
    return result.images[0]


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
            # Previously silent on the Cloudflare path too, which made every
            # real failure indistinguishable from a normal fallback in
            # production — this is the only signal that reaches Cloud Run
            # logs when local generation fails (e.g. out of memory).
            logger.exception("generate_image attempt %d failed for prompt: %s", attempt, prompt)
            # LCM already runs at its minimum useful step count (4), so the
            # retry lever here is resolution (halved, still a multiple of 8
            # for the VAE) rather than steps.
            width, height = width // 2, height // 2

    placeholder = make_placeholder_image(prompt[:40], size=size)
    placeholder.save(cache_path)
    return str(cache_path)
