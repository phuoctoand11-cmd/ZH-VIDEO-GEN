FROM python:3.11-slim

# ffmpeg is required by moviepy (video assembly) and by the test suite's
# audio fixtures; it is not part of the base Python image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only torch build first — the default PyPI wheel bundles CUDA runtimes
# (several GB) that this service never uses, since Cloud Run here has no GPU.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the scene-illustration model weights into the image at build time so a
# cold instance never depends on a runtime download from Hugging Face — this
# removes HF's uptime/rate limits from the request path entirely (unlike the
# Cloudflare Workers AI call this replaces, which stayed subject to Cloudflare's
# own limits on every single request).
ENV HF_HOME=/app/.cache/huggingface
COPY scripts/prefetch_model.py scripts/prefetch_model.py
RUN python scripts/prefetch_model.py

COPY . .

# Render injects $PORT at runtime; app.py reads it and falls back to 7860
# for local runs where $PORT is unset.
CMD ["python", "app.py"]
