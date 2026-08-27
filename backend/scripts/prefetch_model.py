"""Pre-downloads the scene-illustration model into the Docker build layer,
so a cold Cloud Run instance never waits on (or depends on) a runtime
download from Hugging Face.

Model IDs are duplicated here from visuals/image.py rather than imported —
this script runs before `COPY . .` in the Dockerfile so the expensive
download stays cached across ordinary code changes; only a change to these
two lines (or requirements.txt) should force Docker to redo it.
"""

import torch
from diffusers import AutoPipelineForText2Image

AutoPipelineForText2Image.from_pretrained(
    "runwayml/stable-diffusion-v1-5", torch_dtype=torch.float32, safety_checker=None
).load_lora_weights("latent-consistency/lcm-lora-sdv1-5")
