from pathlib import Path

import visuals.scene_library as scene_library


class _FakeResponse:
    def __init__(self, json_data=None, content=b"", status_code=200):
        self._json_data = json_data
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


def test_find_cached_image_returns_none_when_credentials_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    assert scene_library.find_cached_image("鸡", str(tmp_path)) is None


def test_find_cached_image_returns_none_when_no_row_matches(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake_key")

    def fake_get(url, headers=None, params=None, timeout=None):
        assert "scene_images" in url
        return _FakeResponse(json_data=[])

    monkeypatch.setattr(scene_library.requests, "get", fake_get)

    assert scene_library.find_cached_image("鸡", str(tmp_path)) is None


def test_find_cached_image_downloads_and_caches_locally(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake_key")

    calls = []

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append(url)
        if "rest/v1/scene_images" in url:
            assert params == {"hanzi": "eq.鸡", "select": "image_path", "limit": 1}
            return _FakeResponse(json_data=[{"image_path": "鸡.png"}])
        assert url == "https://proj.supabase.co/storage/v1/object/public/scene-images/鸡.png"
        return _FakeResponse(content=b"fake-png-bytes")

    monkeypatch.setattr(scene_library.requests, "get", fake_get)

    result = scene_library.find_cached_image("鸡", str(tmp_path))

    assert result == str(Path(tmp_path) / "lib_鸡.png")
    assert Path(result).read_bytes() == b"fake-png-bytes"
    assert len(calls) == 2


def test_find_cached_image_returns_none_on_lookup_error(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake_key")

    def fake_get(url, headers=None, params=None, timeout=None):
        raise RuntimeError("network error")

    monkeypatch.setattr(scene_library.requests, "get", fake_get)

    assert scene_library.find_cached_image("鸡", str(tmp_path)) is None


def test_store_generated_image_does_nothing_when_credentials_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    calls = []
    monkeypatch.setattr(
        scene_library.requests, "post", lambda *a, **k: calls.append(1) or _FakeResponse()
    )

    img_path = tmp_path / "gen.png"
    img_path.write_bytes(b"real-image-bytes")
    scene_library.store_generated_image("鸡", "jī", "con gà", "a chicken", str(img_path))

    assert calls == []


def test_store_generated_image_uploads_then_inserts_row(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake_key")

    calls = []

    def fake_post(url, headers=None, data=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "data": data, "json": json})
        return _FakeResponse()

    monkeypatch.setattr(scene_library.requests, "post", fake_post)

    img_path = tmp_path / "gen.png"
    img_path.write_bytes(b"real-image-bytes")
    scene_library.store_generated_image("鸡", "jī", "con gà", "a chicken", str(img_path))

    assert len(calls) == 2
    upload_call, insert_call = calls
    assert upload_call["url"] == "https://proj.supabase.co/storage/v1/object/scene-images/鸡.png"
    assert upload_call["data"] == b"real-image-bytes"
    assert upload_call["headers"]["x-upsert"] == "true"

    assert insert_call["url"] == "https://proj.supabase.co/rest/v1/scene_images"
    assert insert_call["json"] == {
        "hanzi": "鸡",
        "pinyin": "jī",
        "meaning_vi": "con gà",
        "icon_prompt": "a chicken",
        "image_path": "鸡.png",
    }
    assert insert_call["headers"]["Prefer"] == "resolution=merge-duplicates"


def test_store_generated_image_swallows_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake_key")

    def fake_post(*args, **kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr(scene_library.requests, "post", fake_post)

    img_path = tmp_path / "gen.png"
    img_path.write_bytes(b"real-image-bytes")

    # Must not raise — storing is best-effort and should never break the
    # pipeline that already has a usable generated image in hand.
    scene_library.store_generated_image("鸡", "jī", "con gà", "a chicken", str(img_path))
