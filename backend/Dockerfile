FROM python:3.11-slim

# ffmpeg is required by moviepy (video assembly) and by the test suite's
# audio fixtures; it is not part of the base Python image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render injects $PORT at runtime; app.py reads it and falls back to 7860
# for local runs where $PORT is unset.
CMD ["python", "app.py"]
