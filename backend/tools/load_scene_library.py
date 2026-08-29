"""Bulk-load a curated set of scene illustrations into the Supabase
scene-image library (Postgres table `scene_images` + Storage bucket
`scene-images`).

This is the offline, batch counterpart to
`visuals.scene_library.store_generated_image`: it uploads each image to
the bucket as `{hanzi}.png` and upserts a matching row, so
`visuals.scene_library.find_cached_image` can serve it instead of
calling Cloudflare. Same URLs / headers / upsert semantics as the
in-app store path.

Run locally with SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY set:

    python tools/load_scene_library.py --images-root "D:/KHO ẢNH"
"""

import argparse
import csv
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import requests

# Make `visuals` importable when this file is run as a loose script
# (`python tools/load_scene_library.py`), which only puts tools/ on the
# path — not just as `python -m tools.load_scene_library`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visuals.scene_library import BUCKET, storage_key_for  # noqa: E402

REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_CSV = str(Path(__file__).with_name("scene_library_seed.csv"))


@dataclass
class Summary:
    loaded: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


def load_seed(csv_path: str, images_root: str, base_url: str, key: str) -> Summary:
    base_url = base_url.rstrip("/")
    root = Path(images_root)
    summary = Summary()

    with open(csv_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    auth = {"apikey": key, "Authorization": f"Bearer {key}"}

    for row in rows:
        hanzi = row["hanzi"]
        try:
            image_bytes = (root / row["source_path"]).read_bytes()
            storage_path = storage_key_for(hanzi)

            requests.post(
                f"{base_url}/storage/v1/object/{BUCKET}/{storage_path}",
                headers={**auth, "Content-Type": "image/png", "x-upsert": "true"},
                data=image_bytes,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ).raise_for_status()

            requests.post(
                f"{base_url}/rest/v1/scene_images",
                headers={
                    **auth,
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates",
                },
                json={
                    "hanzi": hanzi,
                    "pinyin": row.get("pinyin") or None,
                    "meaning_vi": row.get("meaning_vi") or None,
                    "icon_prompt": None,
                    "image_path": storage_path,
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            ).raise_for_status()
        except FileNotFoundError as exc:
            summary.failed.append((hanzi, f"image not found: {row['source_path']} ({exc})"))
        except requests.HTTPError as exc:
            body = getattr(exc.response, "text", "") or ""
            summary.failed.append((hanzi, f"{exc} — {body[:500]}".rstrip(" —")))
        except Exception as exc:  # noqa: BLE001 - report and move to the next row
            summary.failed.append((hanzi, str(exc)))
        else:
            summary.loaded.append(hanzi)

    return summary


def main(argv=None) -> int:
    # The summary prints hanzi; a Windows console defaults to cp1252 and would
    # crash on the first non-Latin character. Best-effort switch to UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Bulk-load the Supabase scene-image library.")
    parser.add_argument(
        "--images-root",
        required=True,
        help="Folder the CSV's source_path values are relative to",
    )
    parser.add_argument("--csv", default=DEFAULT_CSV, help=f"Seed CSV (default: {DEFAULT_CSV})")
    args = parser.parse_args(argv)

    base_url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base_url or not key:
        print(
            "Missing environment: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
            "(the service_role key) before running.",
            file=sys.stderr,
        )
        return 2

    summary = load_seed(args.csv, args.images_root, base_url, key)

    for hanzi in summary.loaded:
        print(f"  ok    {hanzi}")
    for hanzi, reason in summary.failed:
        print(f"  FAIL  {hanzi}: {reason}", file=sys.stderr)
    print(f"\n{len(summary.loaded)} loaded, {len(summary.failed)} failed")

    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
