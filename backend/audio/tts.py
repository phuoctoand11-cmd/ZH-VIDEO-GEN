import asyncio
import time
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3

VOICE_MAP = {
    "zh": "zh-CN-XiaoxiaoNeural",
    "vi": "vi-VN-HoaiMyNeural",
}


class TTSError(Exception):
    pass


async def _synthesize_once(text: str, voice: str, out_path: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def synthesize(text: str, lang: str, out_path: str, max_retries: int = 2) -> str:
    voice = VOICE_MAP.get(lang)
    if voice is None:
        raise TTSError(f"unsupported lang: {lang}")
    out = Path(out_path)
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            asyncio.run(_synthesize_once(text, voice, str(out)))
            return str(out)
        except Exception as exc:  # noqa: BLE001 - retried below, re-raised as TTSError
            last_error = exc
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    raise TTSError(f"failed to synthesize after {max_retries + 1} attempts: {last_error}")


def get_audio_duration(path: str) -> float:
    """Return the duration of an mp3 file in seconds.

    Uses mutagen (a pure-Python mp3 header reader) so that no system
    `ffprobe` binary is required at runtime.
    """
    return float(MP3(str(path)).info.length)
