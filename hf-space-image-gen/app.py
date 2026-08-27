"""Hugging Face Space (SDK: Gradio, Hardware: ZeroGPU) that generates a single
scene illustration per call. Deployed separately from the main backend so the
Cloud Run container never needs torch/diffusers — it just calls this Space's
Gradio API via `gradio_client`.

Model: black-forest-labs/FLUX.1-schnell (Apache-2.0, no membership/paywall
gate). Inference runs on Hugging Face's real ZeroGPU allocation, not on this
process's own persistent GPU — the model is placed on 'cuda' at module level
per ZeroGPU's documented pattern (a CUDA-emulation mode is active outside the
`@spaces.GPU` function; the real GPU is only attached while it runs).
"""

import spaces
import torch
from diffusers import FluxPipeline
import gradio as gr

pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-schnell", dtype=torch.bfloat16)
pipe.to("cuda")


@spaces.GPU(duration=60)
def generate(prompt: str, width: int, height: int):
    # schnell is guidance-distilled: guidance_scale must be 0 (no CFG), and
    # negative_prompt has no effect under guidance_scale=0 — it is not
    # accepted here so the caller can't be misled into thinking it does
    # anything, unlike the higher-guidance models used earlier in this
    # project (FLUX.1-dev, Cloudflare phoenix-1.0).
    return pipe(
        prompt=prompt,
        guidance_scale=0.0,
        height=int(height),
        width=int(width),
        num_inference_steps=4,
        max_sequence_length=256,
    ).images[0]


demo = gr.Interface(
    fn=generate,
    inputs=[
        gr.Text(label="prompt"),
        gr.Number(label="width", value=768, precision=0),
        gr.Number(label="height", value=576, precision=0),
    ],
    outputs=gr.Image(type="pil"),
    api_name="generate",
)

if __name__ == "__main__":
    demo.launch()
