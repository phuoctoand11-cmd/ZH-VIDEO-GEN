"""Pre-built/organically-grown library of scene illustrations, stored in
Supabase (Postgres table `scene_images` + Storage bucket `scene-images`).
Looked up before falling back to AI generation (visuals/image.py) — see
pipeline.py's run_vocab_card_pipeline. V1 matches on exact `hanzi` only, not
semantic/vector similarity: adding a real matching step would mean pulling
in an embedding model, which is the same heavy-dependency problem this
project already backed out of once (self-hosted diffusers). Exact-hanzi
already gives real reuse, since the same word recurs across different
topics.

Every function here is best-effort and never raises into the caller: a
Supabase outage or missing config must fall through to normal AI
generation, not break video creation.
"""

import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

BUCKET = "scene-images"
REQUEST_TIMEOUT_SECONDS = 10


def _get_credentials() -> tuple[str, str] | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    return url.rstrip("/"), key


def find_cached_image(hanzi: str, cache_dir: str) -> str | None:
    """Look up an existing library image for this exact hanzi word. Returns
    a local file path (downloaded and cached) if found, else None.
    """
    credentials = _get_credentials()
    if credentials is None:
        return None
    base_url, key = credentials
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    try:
        response = requests.get(
            f"{base_url}/rest/v1/scene_images",
            headers=headers,
            params={"hanzi": f"eq.{hanzi}", "select": "image_path", "limit": 1},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        rows = response.json()
    except Exception:  # noqa: BLE001 - fall through to AI generation
        logger.exception("scene_images lookup failed for hanzi=%s", hanzi)
        return None

    if not rows:
        return None
    image_path = rows[0]["image_path"]

    try:
        image_response = requests.get(
            f"{base_url}/storage/v1/object/public/{BUCKET}/{image_path}",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        image_response.raise_for_status()
    except Exception:  # noqa: BLE001 - fall through to AI generation
        logger.exception("scene-images download failed for path=%s", image_path)
        return None

    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    local_path = Path(cache_dir) / f"lib_{hanzi}.png"
    local_path.write_bytes(image_response.content)
    return str(local_path)


def store_generated_image(
    hanzi: str,
    pinyin: str | None,
    meaning_vi: str | None,
    icon_prompt: str,
    local_image_path: str,
) -> None:
    """Upload a freshly AI-generated image to the library for future reuse.
    Only called by the caller when generation actually succeeded (never for
    the placeholder fallback) — see generate_image()'s on_success hook.
    """
    credentials = _get_credentials()
    if credentials is None:
        return
    base_url, key = credentials
    storage_path = f"{hanzi}.png"

    try:
        with open(local_image_path, "rb") as f:
            image_bytes = f.read()
        upload_response = requests.post(
            f"{base_url}/storage/v1/object/{BUCKET}/{storage_path}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "image/png",
                "x-upsert": "true",
            },
            data=image_bytes,
            timeout=30,
        )
        upload_response.raise_for_status()

        insert_response = requests.post(
            f"{base_url}/rest/v1/scene_images",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                # Upsert on the unique `hanzi` column (see supabase_setup.sql)
                # rather than erroring on conflict — a second AI generation
                # for the same word (e.g. a race between concurrent requests)
                # should just refresh the row, not fail loudly.
                "Prefer": "resolution=merge-duplicates",
            },
            json={
                "hanzi": hanzi,
                "pinyin": pinyin,
                "meaning_vi": meaning_vi,
                "icon_prompt": icon_prompt,
                "image_path": storage_path,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        insert_response.raise_for_status()
    except Exception:  # noqa: BLE001 - storing is best-effort, never fatal
        logger.exception("scene_images store failed for hanzi=%s", hanzi)
