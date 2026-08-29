import subprocess
import sys
from pathlib import Path

import requests

import visuals.scene_library as scene_library
from tools import load_scene_library

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class _FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError(f"{self.status_code} Client Error")
            err.response = self
            raise err


def _write_csv(path, rows):
    lines = ["hanzi,pinyin,meaning_vi,source_path"]
    lines.extend(",".join(r) for r in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_seed_uploads_image_then_upserts_row(tmp_path, monkeypatch):
    images_root = tmp_path / "images"
    (images_root / "FRUIT").mkdir(parents=True)
    (images_root / "FRUIT" / "x.png").write_bytes(b"real-image-bytes")

    csv_path = tmp_path / "seed.csv"
    _write_csv(csv_path, [("苹果", "píngguǒ", "quả táo", "FRUIT/x.png")])

    calls = []

    def fake_post(url, headers=None, data=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "data": data, "json": json})
        return _FakeResponse()

    monkeypatch.setattr(load_scene_library.requests, "post", fake_post)

    summary = load_scene_library.load_seed(
        csv_path=str(csv_path),
        images_root=str(images_root),
        base_url="https://proj.supabase.co",
        key="fake_key",
    )

    key = scene_library.storage_key_for("苹果")
    assert len(calls) == 2
    upload_call, upsert_call = calls

    assert upload_call["url"] == f"https://proj.supabase.co/storage/v1/object/scene-images/{key}"
    assert upload_call["data"] == b"real-image-bytes"
    assert upload_call["headers"]["x-upsert"] == "true"
    assert upload_call["headers"]["Content-Type"] == "image/png"
    assert upload_call["headers"]["apikey"] == "fake_key"
    assert upload_call["headers"]["Authorization"] == "Bearer fake_key"

    assert upsert_call["url"] == "https://proj.supabase.co/rest/v1/scene_images"
    assert upsert_call["json"] == {
        "hanzi": "苹果",
        "pinyin": "píngguǒ",
        "meaning_vi": "quả táo",
        "icon_prompt": None,
        "image_path": key,
    }
    assert upsert_call["headers"]["Prefer"] == "resolution=merge-duplicates"

    assert summary.loaded == ["苹果"]
    assert summary.failed == []


def test_load_seed_records_missing_image_file_as_failed_and_continues(tmp_path, monkeypatch):
    images_root = tmp_path / "images"
    images_root.mkdir()
    (images_root / "ok.png").write_bytes(b"bytes")

    csv_path = tmp_path / "seed.csv"
    _write_csv(
        csv_path,
        [
            ("香蕉", "xiāngjiāo", "quả chuối", "gone.png"),
            ("苹果", "píngguǒ", "quả táo", "ok.png"),
        ],
    )

    calls = []
    monkeypatch.setattr(
        load_scene_library.requests,
        "post",
        lambda *a, **k: calls.append(k.get("json", {}).get("hanzi") or a[0]) or _FakeResponse(),
    )

    summary = load_scene_library.load_seed(
        csv_path=str(csv_path),
        images_root=str(images_root),
        base_url="https://proj.supabase.co",
        key="fake_key",
    )

    assert summary.loaded == ["苹果"]
    assert len(summary.failed) == 1
    assert summary.failed[0][0] == "香蕉"
    assert "gone.png" in summary.failed[0][1]
    # Only the good row hit the network (upload + upsert).
    assert len(calls) == 2


def test_load_seed_records_upload_http_error_as_failed_and_continues(tmp_path, monkeypatch):
    images_root = tmp_path / "images"
    images_root.mkdir()
    (images_root / "a.png").write_bytes(b"a")
    (images_root / "b.png").write_bytes(b"b")

    csv_path = tmp_path / "seed.csv"
    _write_csv(
        csv_path,
        [
            ("狗", "gǒu", "con chó", "a.png"),
            ("猫", "māo", "con mèo", "b.png"),
        ],
    )

    dog_key = scene_library.storage_key_for("狗")

    def fake_post(url, headers=None, data=None, json=None, timeout=None):
        if url.endswith(f"/storage/v1/object/scene-images/{dog_key}"):
            return _FakeResponse(status_code=500)
        return _FakeResponse()

    monkeypatch.setattr(load_scene_library.requests, "post", fake_post)

    summary = load_scene_library.load_seed(
        csv_path=str(csv_path),
        images_root=str(images_root),
        base_url="https://proj.supabase.co",
        key="fake_key",
    )

    assert summary.loaded == ["猫"]
    assert len(summary.failed) == 1
    assert summary.failed[0][0] == "狗"


def test_load_seed_puts_server_error_body_in_failure_reason(tmp_path, monkeypatch):
    images_root = tmp_path / "images"
    images_root.mkdir()
    (images_root / "a.png").write_bytes(b"a")

    csv_path = tmp_path / "seed.csv"
    _write_csv(csv_path, [("狗", "gǒu", "con chó", "a.png")])

    monkeypatch.setattr(
        load_scene_library.requests,
        "post",
        lambda *a, **k: _FakeResponse(status_code=400, text='{"statusCode":"400","message":"invalid key"}'),
    )

    summary = load_scene_library.load_seed(
        csv_path=str(csv_path),
        images_root=str(images_root),
        base_url="https://proj.supabase.co",
        key="fake_key",
    )

    assert summary.loaded == []
    assert len(summary.failed) == 1
    assert "invalid key" in summary.failed[0][1]


def test_script_is_runnable_as_a_loose_file():
    # Users run `python tools/load_scene_library.py ...` from backend/, which
    # puts tools/ (not backend/) on sys.path — the module must still import
    # its `visuals` dependency.
    result = subprocess.run(
        [sys.executable, "tools/load_scene_library.py", "--help"],
        cwd=_BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "usage" in result.stdout.lower()


def test_main_exits_nonzero_with_message_when_supabase_env_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    rc = load_scene_library.main(["--images-root", str(tmp_path)])

    assert rc != 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "SUPABASE_URL" in out
    assert "SUPABASE_SERVICE_ROLE_KEY" in out


def test_main_returns_1_when_a_row_failed(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake_key")

    images_root = tmp_path / "images"
    images_root.mkdir()
    csv_path = tmp_path / "seed.csv"
    _write_csv(csv_path, [("狗", "gǒu", "con chó", "missing.png")])

    monkeypatch.setattr(load_scene_library.requests, "post", lambda *a, **k: _FakeResponse())

    rc = load_scene_library.main(
        ["--images-root", str(images_root), "--csv", str(csv_path)]
    )

    assert rc == 1


def test_main_returns_0_on_full_success(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake_key")

    images_root = tmp_path / "images"
    images_root.mkdir()
    (images_root / "a.png").write_bytes(b"a")
    csv_path = tmp_path / "seed.csv"
    _write_csv(csv_path, [("狗", "gǒu", "con chó", "a.png")])

    monkeypatch.setattr(load_scene_library.requests, "post", lambda *a, **k: _FakeResponse())

    rc = load_scene_library.main(
        ["--images-root", str(images_root), "--csv", str(csv_path)]
    )

    assert rc == 0
