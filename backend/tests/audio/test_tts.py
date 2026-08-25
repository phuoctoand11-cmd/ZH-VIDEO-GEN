from pathlib import Path

import pytest
from audio import tts


def test_synthesize_success(tmp_path, monkeypatch):
    calls = []

    async def fake_synthesize_once(text, voice, out_path):
        calls.append((text, voice))
        Path(out_path).write_bytes(b"fake-audio")

    monkeypatch.setattr(tts, "_synthesize_once", fake_synthesize_once)
    out_path = tmp_path / "out.mp3"
    result = tts.synthesize("你好", "zh", str(out_path))
    assert result == str(out_path)
    assert out_path.read_bytes() == b"fake-audio"
    assert calls == [("你好", "zh-CN-XiaoxiaoNeural")]


def test_synthesize_unsupported_lang():
    with pytest.raises(tts.TTSError):
        tts.synthesize("hello", "en", "/tmp/x.mp3")


def test_synthesize_retries_then_succeeds(tmp_path, monkeypatch):
    attempts = {"count": 0}

    async def flaky(text, voice, out_path):
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("network error")
        Path(out_path).write_bytes(b"ok")

    monkeypatch.setattr(tts, "_synthesize_once", flaky)
    monkeypatch.setattr(tts.time, "sleep", lambda s: None)
    out_path = tmp_path / "out.mp3"
    tts.synthesize("你好", "zh", str(out_path), max_retries=2)
    assert attempts["count"] == 2


def test_synthesize_fails_after_max_retries(tmp_path, monkeypatch):
    async def always_fail(text, voice, out_path):
        raise RuntimeError("network error")

    monkeypatch.setattr(tts, "_synthesize_once", always_fail)
    monkeypatch.setattr(tts.time, "sleep", lambda s: None)
    with pytest.raises(tts.TTSError):
        tts.synthesize("你好", "zh", str(tmp_path / "out.mp3"), max_retries=1)


import subprocess


def test_get_audio_duration(tmp_path):
    audio_path = tmp_path / "silence.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", "2", str(audio_path)],
        check=True, capture_output=True,
    )
    duration = tts.get_audio_duration(str(audio_path))
    assert 1.9 <= duration <= 2.1


def test_make_silence_creates_file_with_requested_duration(tmp_path):
    out_path = tmp_path / "silence.mp3"
    tts.make_silence(str(out_path), seconds=1.5)
    assert out_path.exists()
    assert abs(tts.get_audio_duration(str(out_path)) - 1.5) < 0.1
