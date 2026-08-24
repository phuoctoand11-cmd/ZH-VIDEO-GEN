# Backend (zh-video-gen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `backend/` Python package — content/pinyin/TTS/image/video pipeline plus a Gradio app — deployable to Hugging Face Spaces (ZeroGPU) and callable from an external frontend via the Gradio API.

**Architecture:** A pure-logic content layer (schema, manual parsing, pinyin, LLM auto-generation) feeds a template-driven audio layer (edge-tts) and a visual layer (diffusers image generation on ZeroGPU with Ken Burns rendering). `pipeline.py` orchestrates per-item generation with per-item error isolation, and `app.py` exposes it all through Gradio, which HF Spaces serves and which also acts as the API the Cloudflare Pages frontend calls.

**Tech Stack:** Python 3.11, pydantic, pypinyin, edge-tts, mutagen, moviepy + ffmpeg, Pillow, diffusers/transformers/torch (FLUX.1-schnell), `spaces` (HF ZeroGPU), google-generativeai (Gemini free tier), gradio, pytest.

**Spec:** `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md`

## Global Constraints

- Toàn bộ dịch vụ dùng phải miễn phí: edge-tts (không key), pypinyin (offline), Gemini free tier, ZeroGPU trên HF Spaces.
- Giọng TTS cố định: tiếng Trung `zh-CN-XiaoxiaoNeural`, tiếng Việt `vi-VN-HoaiMyNeural`.
- Model ảnh: `black-forest-labs/FLUX.1-schnell`, chạy trong hàm decorate `@spaces.GPU`.
- Một item lỗi không được làm sập cả batch — pipeline xử lý từng item độc lập và gom lỗi lại (theo mục "Xử lý lỗi" trong spec).
- Tỉ lệ khung hình hỗ trợ: `9:16` (720×1280) và `16:9` (1280×720), chọn được một hoặc cả hai mỗi lần tạo.
- Không có CI; test chạy thủ công bằng `pytest` từ thư mục `backend/`.
- `ffmpeg`/`ffprobe` phải có sẵn trong PATH của môi trường dev/test (dùng để tạo audio câm test và kiểm tra video output).
- Toàn bộ code nằm trong `backend/` (thư mục con của repo `ZH-VIDEO-GEN` đã có trên GitHub) — không đụng tới `frontend/` (sẽ có plan riêng).

---

## Task 1: Scaffolding backend package

**Files:**
- Create: `backend/pytest.ini`
- Create: `backend/requirements.txt`
- Create: `backend/content/__init__.py`
- Create: `backend/audio/__init__.py`
- Create: `backend/visuals/__init__.py`
- Create: `backend/render/__init__.py`
- Create: `backend/tests/.gitkeep`

**Interfaces:**
- Produces: importable packages `content`, `audio`, `visuals`, `render` from `backend/` as rootdir; `pytest` runs from `backend/`.

- [ ] **Step 1: Create package directories and empty `__init__.py` files**

```bash
mkdir -p backend/content backend/audio backend/visuals backend/render backend/tests backend/config/templates backend/assets/fonts
touch backend/content/__init__.py backend/audio/__init__.py backend/visuals/__init__.py backend/render/__init__.py
touch backend/tests/.gitkeep
```

- [ ] **Step 2: Write `backend/pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 3: Write `backend/requirements.txt`**

```
gradio>=4.44
pydantic>=2.7
pypinyin>=0.51
edge-tts>=6.1
mutagen>=1.47
moviepy>=1.0.3
Pillow>=10.3
diffusers>=0.30
transformers>=4.42
torch>=2.3
accelerate>=0.31
google-generativeai>=0.7
spaces>=0.28
pytest>=8.2
```

- [ ] **Step 4: Verify scaffolding**

Run: `cd backend && pip install -r requirements.txt && pytest --collect-only`
Expected: dependencies install without error; pytest reports `no tests ran` (0 collected), no import errors.

- [ ] **Step 5: Commit**

```bash
git add backend/pytest.ini backend/requirements.txt backend/content/__init__.py backend/audio/__init__.py backend/visuals/__init__.py backend/render/__init__.py backend/tests/.gitkeep
git commit -m "chore: scaffold backend package structure"
```

---

## Task 2: LessonItem schema

**Files:**
- Create: `backend/content/schema.py`
- Test: `backend/tests/content/test_schema.py`

**Interfaces:**
- Produces: `LessonItem(hanzi: str, pinyin: str | None, meaning_vi: str)` (pydantic model) — used by every later task that touches lesson content.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/content/test_schema.py
import pytest
from pydantic import ValidationError
from content.schema import LessonItem


def test_lesson_item_valid():
    item = LessonItem(hanzi="吃", pinyin="chī", meaning_vi="ăn")
    assert item.hanzi == "吃"
    assert item.pinyin == "chī"
    assert item.meaning_vi == "ăn"


def test_lesson_item_pinyin_optional():
    item = LessonItem(hanzi="吃", meaning_vi="ăn")
    assert item.pinyin is None


def test_lesson_item_rejects_empty_hanzi():
    with pytest.raises(ValidationError):
        LessonItem(hanzi="  ", meaning_vi="ăn")


def test_lesson_item_rejects_empty_meaning():
    with pytest.raises(ValidationError):
        LessonItem(hanzi="吃", meaning_vi="  ")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/content/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'content.schema'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/content/schema.py
from pydantic import BaseModel, field_validator


class LessonItem(BaseModel):
    hanzi: str
    pinyin: str | None = None
    meaning_vi: str

    @field_validator("hanzi")
    @classmethod
    def hanzi_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("hanzi must not be empty")
        return v.strip()

    @field_validator("meaning_vi")
    @classmethod
    def meaning_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("meaning_vi must not be empty")
        return v.strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/content/test_schema.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/content/schema.py backend/tests/content/test_schema.py
git commit -m "feat: add LessonItem schema"
```

---

## Task 3: Pinyin auto-fill

**Files:**
- Create: `backend/content/pinyin.py`
- Test: `backend/tests/content/test_pinyin.py`

**Interfaces:**
- Consumes: `LessonItem` from Task 2.
- Produces: `fill_pinyin(item: LessonItem) -> LessonItem`, `fill_pinyin_batch(items: list[LessonItem]) -> list[LessonItem]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/content/test_pinyin.py
from content.schema import LessonItem
from content.pinyin import fill_pinyin, fill_pinyin_batch


def test_fill_pinyin_generates_when_missing():
    item = LessonItem(hanzi="吃", meaning_vi="ăn")
    result = fill_pinyin(item)
    assert result.pinyin == "chī"


def test_fill_pinyin_keeps_existing():
    item = LessonItem(hanzi="吃", pinyin="custom", meaning_vi="ăn")
    result = fill_pinyin(item)
    assert result.pinyin == "custom"


def test_fill_pinyin_batch():
    items = [LessonItem(hanzi="吃", meaning_vi="ăn"), LessonItem(hanzi="喝", meaning_vi="uống")]
    results = fill_pinyin_batch(items)
    assert results[0].pinyin == "chī"
    assert results[1].pinyin == "hē"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/content/test_pinyin.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'content.pinyin'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/content/pinyin.py
from pypinyin import pinyin, Style
from content.schema import LessonItem


def fill_pinyin(item: LessonItem) -> LessonItem:
    if item.pinyin:
        return item
    syllables = pinyin(item.hanzi, style=Style.TONE)
    generated = " ".join(s[0] for s in syllables)
    return item.model_copy(update={"pinyin": generated})


def fill_pinyin_batch(items: list[LessonItem]) -> list[LessonItem]:
    return [fill_pinyin(item) for item in items]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/content/test_pinyin.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/content/pinyin.py backend/tests/content/test_pinyin.py
git commit -m "feat: auto-fill missing pinyin from hanzi"
```

---

## Task 4: Manual list parsing (CSV)

**Files:**
- Create: `backend/content/manual.py`
- Test: `backend/tests/content/test_manual.py`

**Interfaces:**
- Consumes: `LessonItem` from Task 2.
- Produces: `parse_manual_input(csv_text: str) -> tuple[list[LessonItem], list[ManualParseError]]`, `ManualParseError(line_number: int, message: str)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/content/test_manual.py
from content.manual import parse_manual_input


def test_parse_manual_input_valid_rows():
    csv_text = "hanzi,pinyin,meaning_vi\n吃,chī,ăn\n喝,,uống\n"
    items, errors = parse_manual_input(csv_text)
    assert len(items) == 2
    assert errors == []
    assert items[0].hanzi == "吃"
    assert items[0].pinyin == "chī"
    assert items[1].pinyin is None


def test_parse_manual_input_skips_missing_hanzi():
    csv_text = "hanzi,pinyin,meaning_vi\n,chī,ăn\n喝,,uống\n"
    items, errors = parse_manual_input(csv_text)
    assert len(items) == 1
    assert len(errors) == 1
    assert errors[0].line_number == 2
    assert "hanzi" in errors[0].message


def test_parse_manual_input_skips_missing_meaning():
    csv_text = "hanzi,pinyin,meaning_vi\n吃,chī,\n"
    items, errors = parse_manual_input(csv_text)
    assert len(items) == 0
    assert len(errors) == 1
    assert "meaning_vi" in errors[0].message
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/content/test_manual.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'content.manual'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/content/manual.py
import csv
import io

from content.schema import LessonItem


class ManualParseError(Exception):
    def __init__(self, line_number: int, message: str):
        self.line_number = line_number
        self.message = message
        super().__init__(f"line {line_number}: {message}")


def parse_manual_input(csv_text: str) -> tuple[list[LessonItem], list[ManualParseError]]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    items: list[LessonItem] = []
    errors: list[ManualParseError] = []
    for line_number, row in enumerate(reader, start=2):
        hanzi = (row.get("hanzi") or "").strip()
        meaning_vi = (row.get("meaning_vi") or "").strip()
        pinyin_value = (row.get("pinyin") or "").strip() or None
        if not hanzi:
            errors.append(ManualParseError(line_number, "missing hanzi"))
            continue
        if not meaning_vi:
            errors.append(ManualParseError(line_number, "missing meaning_vi"))
            continue
        items.append(LessonItem(hanzi=hanzi, pinyin=pinyin_value, meaning_vi=meaning_vi))
    return items, errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/content/test_manual.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/content/manual.py backend/tests/content/test_manual.py
git commit -m "feat: parse manual CSV input into LessonItem list"
```

---

## Task 5: Audio templates

**Files:**
- Create: `backend/audio/templates.py`
- Create: `backend/config/templates/zh-zh-vi.json`
- Create: `backend/config/templates/zh-vi-zh.json`
- Test: `backend/tests/audio/test_templates.py`

**Interfaces:**
- Produces: `TemplateSegment(lang: str, field: str)`, `AudioTemplate(name: str, segments: list[TemplateSegment])`, `load_template(path) -> AudioTemplate`, `list_templates(templates_dir) -> list[AudioTemplate]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/audio/test_templates.py
import json
from audio.templates import load_template, list_templates


def test_load_template(tmp_path):
    template_path = tmp_path / "test.json"
    template_path.write_text(json.dumps({
        "name": "zh-zh-vi",
        "segments": [
            {"lang": "zh", "field": "hanzi"},
            {"lang": "vi", "field": "meaning_vi"},
        ],
    }), encoding="utf-8")
    template = load_template(template_path)
    assert template.name == "zh-zh-vi"
    assert len(template.segments) == 2
    assert template.segments[0].lang == "zh"


def test_list_templates(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({
        "name": "a", "segments": [{"lang": "zh", "field": "hanzi"}]
    }), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({
        "name": "b", "segments": [{"lang": "vi", "field": "meaning_vi"}]
    }), encoding="utf-8")
    templates = list_templates(tmp_path)
    assert [t.name for t in templates] == ["a", "b"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/audio/test_templates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audio.templates'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/audio/templates.py
import json
from pathlib import Path

from pydantic import BaseModel


class TemplateSegment(BaseModel):
    lang: str
    field: str


class AudioTemplate(BaseModel):
    name: str
    segments: list[TemplateSegment]


def load_template(path: str | Path) -> AudioTemplate:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return AudioTemplate(**data)


def list_templates(templates_dir: str | Path) -> list[AudioTemplate]:
    dir_path = Path(templates_dir)
    return [load_template(p) for p in sorted(dir_path.glob("*.json"))]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/audio/test_templates.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Add the two real templates the app will ship with**

```json
// backend/config/templates/zh-zh-vi.json
{
  "name": "zh-zh-vi",
  "segments": [
    {"lang": "zh", "field": "hanzi"},
    {"lang": "zh", "field": "hanzi"},
    {"lang": "vi", "field": "meaning_vi"}
  ]
}
```

```json
// backend/config/templates/zh-vi-zh.json
{
  "name": "zh-vi-zh",
  "segments": [
    {"lang": "zh", "field": "hanzi"},
    {"lang": "vi", "field": "meaning_vi"},
    {"lang": "zh", "field": "hanzi"}
  ]
}
```

- [ ] **Step 6: Verify the shipped templates load**

Run: `cd backend && python -c "from audio.templates import list_templates; print([t.name for t in list_templates('config/templates')])"`
Expected: `['zh-vi-zh', 'zh-zh-vi']`

- [ ] **Step 7: Commit**

```bash
git add backend/audio/templates.py backend/tests/audio/test_templates.py backend/config/templates/zh-zh-vi.json backend/config/templates/zh-vi-zh.json
git commit -m "feat: load configurable audio sequence templates"
```

---

## Task 6: Overlay cue timing

**Files:**
- Create: `backend/render/overlay.py`
- Test: `backend/tests/render/test_overlay.py`

**Interfaces:**
- Consumes: `LessonItem` (Task 2), `AudioTemplate`/`TemplateSegment` (Task 5).
- Produces: `OverlayCue(start: float, end: float, text: str)`, `build_overlay_cues(item, template, segment_durations: list[float]) -> list[OverlayCue]`, `total_duration(segment_durations: list[float]) -> float`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/render/test_overlay.py
import pytest
from content.schema import LessonItem
from audio.templates import AudioTemplate, TemplateSegment
from render.overlay import build_overlay_cues, total_duration


def _template():
    return AudioTemplate(name="zh-zh-vi", segments=[
        TemplateSegment(lang="zh", field="hanzi"),
        TemplateSegment(lang="zh", field="hanzi"),
        TemplateSegment(lang="vi", field="meaning_vi"),
    ])


def test_build_overlay_cues_timing():
    item = LessonItem(hanzi="吃", pinyin="chī", meaning_vi="ăn")
    cues = build_overlay_cues(item, _template(), [1.0, 1.0, 2.0])
    assert cues[0].start == 0.0 and cues[0].end == 1.0
    assert cues[1].start == 1.0 and cues[1].end == 2.0
    assert cues[2].start == 2.0 and cues[2].end == 4.0


def test_build_overlay_cues_text_content():
    item = LessonItem(hanzi="吃", pinyin="chī", meaning_vi="ăn")
    cues = build_overlay_cues(item, _template(), [1.0, 1.0, 2.0])
    assert "吃" in cues[0].text
    assert "chī" in cues[0].text
    assert cues[2].text == "ăn"


def test_build_overlay_cues_mismatched_length_raises():
    item = LessonItem(hanzi="吃", meaning_vi="ăn")
    with pytest.raises(ValueError):
        build_overlay_cues(item, _template(), [1.0])


def test_total_duration():
    assert total_duration([1.0, 2.0, 1.5]) == 4.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/render/test_overlay.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'render.overlay'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/render/overlay.py
from dataclasses import dataclass

from content.schema import LessonItem
from audio.templates import AudioTemplate


@dataclass
class OverlayCue:
    start: float
    end: float
    text: str


def build_overlay_cues(
    item: LessonItem, template: AudioTemplate, segment_durations: list[float]
) -> list[OverlayCue]:
    if len(template.segments) != len(segment_durations):
        raise ValueError("segment_durations length must match template.segments length")
    cues: list[OverlayCue] = []
    t = 0.0
    for segment, duration in zip(template.segments, segment_durations):
        if segment.lang == "zh":
            text = f"{item.hanzi}\n{item.pinyin or ''}".strip()
        else:
            text = item.meaning_vi
        cues.append(OverlayCue(start=t, end=t + duration, text=text))
        t += duration
    return cues


def total_duration(segment_durations: list[float]) -> float:
    return sum(segment_durations)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/render/test_overlay.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/render/overlay.py backend/tests/render/test_overlay.py
git commit -m "feat: compute overlay text cues synced to audio segment timing"
```

---

## Task 7: Font asset and text drawing

**Files:**
- Create: `backend/assets/fonts/NotoSansCJKsc-Regular.otf` (downloaded binary)
- Modify: `backend/render/overlay.py`
- Modify: `backend/tests/render/test_overlay.py`

**Interfaces:**
- Consumes: `OverlayCue.text` from Task 6.
- Produces: `draw_text_on_frame(frame: np.ndarray, text: str, font_size: int = 60) -> np.ndarray`, used by Task 11's scene assembly.

**Note:** the default PIL font has no CJK glyphs, so chữ Hán would render as blank boxes — a real font that covers both Chinese and Vietnamese (with diacritics) is required. Noto Sans CJK SC's Latin range covers Vietnamese precomposed characters (built on Source Han Sans, which explicitly supports Vietnamese), so one font file covers both scripts.

- [ ] **Step 1: Download the font**

```bash
mkdir -p backend/assets/fonts
curl -L -o backend/assets/fonts/NotoSansCJKsc-Regular.otf "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
```

Expected: file `backend/assets/fonts/NotoSansCJKsc-Regular.otf` exists and is about 16MB (`ls -la backend/assets/fonts/`).

- [ ] **Step 2: Write the failing test**

```python
# append to backend/tests/render/test_overlay.py
import numpy as np
from render.overlay import draw_text_on_frame


def test_draw_text_on_frame_changes_pixels():
    frame = np.zeros((200, 400, 3), dtype=np.uint8)
    result = draw_text_on_frame(frame, "吃\nchī")
    assert result.shape == frame.shape
    assert not np.array_equal(result, frame)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/render/test_overlay.py::test_draw_text_on_frame_changes_pixels -v`
Expected: FAIL with `ImportError: cannot import name 'draw_text_on_frame'`

- [ ] **Step 4: Add `draw_text_on_frame` to `backend/render/overlay.py`**

```python
# add to backend/render/overlay.py
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NotoSansCJKsc-Regular.otf"


def draw_text_on_frame(frame: np.ndarray, text: str, font_size: int = 60) -> np.ndarray:
    image = Image.fromarray(frame).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    width, _height = image.size
    lines = text.split("\n")
    line_height = int(font_size * 1.4)
    total_text_height = line_height * len(lines)
    y = image.size[1] - total_text_height - 40
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) / 2
        draw.rectangle([x - 10, y - 5, x + text_width + 10, y + font_size + 10], fill=(0, 0, 0))
        draw.text((x, y), line, fill=(255, 255, 255), font=font)
        y += line_height
    return np.array(image)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/render/test_overlay.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/assets/fonts/NotoSansCJKsc-Regular.otf backend/render/overlay.py backend/tests/render/test_overlay.py
git commit -m "feat: draw Chinese/Vietnamese text overlay using Noto Sans CJK SC"
```

---

## Task 8: Image prompt builder

**Files:**
- Create: `backend/visuals/prompt_builder.py`
- Test: `backend/tests/visuals/test_prompt_builder.py`

**Interfaces:**
- Consumes: `LessonItem` from Task 2.
- Produces: `build_image_prompt(item: LessonItem) -> str`, used by Task 12 and Task 14.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/visuals/test_prompt_builder.py
from content.schema import LessonItem
from visuals.prompt_builder import build_image_prompt


def test_build_image_prompt_includes_hanzi_and_meaning():
    item = LessonItem(hanzi="吃", meaning_vi="ăn")
    prompt = build_image_prompt(item)
    assert "吃" in prompt
    assert "ăn" in prompt


def test_build_image_prompt_excludes_text_instruction():
    item = LessonItem(hanzi="吃", meaning_vi="ăn")
    prompt = build_image_prompt(item)
    assert "no text" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/visuals/test_prompt_builder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'visuals.prompt_builder'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/visuals/prompt_builder.py
from content.schema import LessonItem


def build_image_prompt(item: LessonItem) -> str:
    return (
        f"A simple, clear illustration representing the Chinese word '{item.hanzi}' "
        f"which means '{item.meaning_vi}' in Vietnamese. Flat vector style, "
        f"bright colors, no text, no watermark, educational flashcard style."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/visuals/test_prompt_builder.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/visuals/prompt_builder.py backend/tests/visuals/test_prompt_builder.py
git commit -m "feat: build image generation prompt from LessonItem"
```

---

## Task 9: TTS wrapper and audio duration

**Files:**
- Create: `backend/audio/tts.py`
- Test: `backend/tests/audio/test_tts.py`

**Interfaces:**
- Produces: `VOICE_MAP`, `TTSError`, `synthesize(text: str, lang: str, out_path: str, max_retries: int = 2) -> str`, `get_audio_duration(path: str) -> float`. Used by Task 14 (`pipeline.py`) and Task 11 (`assemble.py` via generated audio files).

- [ ] **Step 1: Write the failing test for `synthesize`**

```python
# backend/tests/audio/test_tts.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/audio/test_tts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audio.tts'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/audio/tts.py
import asyncio
import subprocess
import time
from pathlib import Path

import edge_tts

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
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())
```

- [ ] **Step 4: Run `synthesize` tests to verify they pass**

Run: `cd backend && pytest tests/audio/test_tts.py -v -k synthesize`
Expected: PASS (4 passed)

- [ ] **Step 5: Write the failing test for `get_audio_duration`**

```python
# append to backend/tests/audio/test_tts.py
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
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && pytest tests/audio/test_tts.py -v`
Expected: PASS (5 passed). Requires `ffmpeg`/`ffprobe` on PATH.

- [ ] **Step 7: Commit**

```bash
git add backend/audio/tts.py backend/tests/audio/test_tts.py
git commit -m "feat: edge-tts wrapper with retry and audio duration lookup"
```

---

## Task 10: Ken Burns clip generation

**Files:**
- Create: `backend/render/kenburns.py`
- Test: `backend/tests/render/test_kenburns.py`

**Interfaces:**
- Produces: `make_kenburns_clip(image_path: str, duration: float, size: tuple[int, int], zoom_amount: float = 0.08) -> VideoClip` (moviepy `VideoClip`), used by Task 11.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/render/test_kenburns.py
from PIL import Image
from render.kenburns import make_kenburns_clip


def test_make_kenburns_clip_duration_and_frame_size(tmp_path):
    img_path = tmp_path / "test.png"
    Image.new("RGB", (800, 600), color=(255, 0, 0)).save(img_path)
    clip = make_kenburns_clip(str(img_path), duration=3.0, size=(720, 1280))
    assert clip.duration == 3.0
    frame = clip.get_frame(0)
    assert frame.shape == (1280, 720, 3)


def test_make_kenburns_clip_frame_changes_over_time(tmp_path):
    img_path = tmp_path / "test.png"
    Image.new("RGB", (800, 600), color=(0, 255, 0)).save(img_path)
    clip = make_kenburns_clip(str(img_path), duration=3.0, size=(720, 1280))
    frame_start = clip.get_frame(0)
    frame_end = clip.get_frame(2.9)
    assert frame_start.shape == frame_end.shape
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/render/test_kenburns.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'render.kenburns'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/render/kenburns.py
import numpy as np
from moviepy import VideoClip
from PIL import Image


def make_kenburns_clip(
    image_path: str, duration: float, size: tuple[int, int], zoom_amount: float = 0.08
) -> VideoClip:
    target_w, target_h = size
    source = Image.open(image_path).convert("RGB")
    cover_scale = max(target_w / source.width, target_h / source.height) * (1.0 + zoom_amount)
    scaled = source.resize((int(source.width * cover_scale), int(source.height * cover_scale)))
    frame_w, frame_h = scaled.size

    def make_frame(t: float) -> np.ndarray:
        progress = (t / duration) if duration > 0 else 0.0
        current_zoom = 1.0 + zoom_amount * progress
        crop_w = min(int(target_w * current_zoom / (1.0 + zoom_amount)), frame_w)
        crop_h = min(int(target_h * current_zoom / (1.0 + zoom_amount)), frame_h)
        x0 = (frame_w - crop_w) // 2
        y0 = (frame_h - crop_h) // 2
        cropped = scaled.crop((x0, y0, x0 + crop_w, y0 + crop_h))
        resized = cropped.resize((target_w, target_h))
        return np.array(resized)

    return VideoClip(make_frame, duration=duration)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/render/test_kenburns.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/render/kenburns.py backend/tests/render/test_kenburns.py
git commit -m "feat: Ken Burns pan/zoom clip from a still image"
```

---

## Task 11: Scene assembly and video export

**Files:**
- Create: `backend/render/assemble.py`
- Test: `backend/tests/render/test_assemble.py`

**Interfaces:**
- Consumes: `LessonItem` (Task 2), `AudioTemplate` (Task 5), `build_overlay_cues`/`total_duration`/`draw_text_on_frame` (Tasks 6-7), `make_kenburns_clip` (Task 10).
- Produces: `ASPECT_SIZES`, `build_scene_clip(item, template, audio_paths, image_path, aspect_ratio) -> VideoClip`, `assemble_video(scene_clips: list[VideoClip], out_path: str) -> str`. Used by Task 14.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/render/test_assemble.py
import subprocess

from PIL import Image
from content.schema import LessonItem
from audio.templates import AudioTemplate, TemplateSegment
from render.assemble import build_scene_clip, assemble_video


def _make_silence(path, seconds):
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", str(seconds), str(path)],
        check=True, capture_output=True,
    )


def test_build_scene_clip_and_assemble(tmp_path):
    img_path = tmp_path / "img.png"
    Image.new("RGB", (800, 600), color=(10, 20, 30)).save(img_path)
    audio1 = tmp_path / "a1.mp3"
    audio2 = tmp_path / "a2.mp3"
    _make_silence(audio1, 1.0)
    _make_silence(audio2, 1.0)
    item = LessonItem(hanzi="吃", pinyin="chī", meaning_vi="ăn")
    template = AudioTemplate(name="zh-vi", segments=[
        TemplateSegment(lang="zh", field="hanzi"),
        TemplateSegment(lang="vi", field="meaning_vi"),
    ])

    scene = build_scene_clip(item, template, [str(audio1), str(audio2)], str(img_path), "9:16")
    assert abs(scene.duration - 2.0) < 0.05

    out_path = tmp_path / "out.mp4"
    assemble_video([scene], str(out_path))
    assert out_path.exists()

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out_path)],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip())
    assert 1.8 <= duration <= 2.3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/render/test_assemble.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'render.assemble'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/render/assemble.py
from moviepy import AudioFileClip, VideoClip, concatenate_audioclips, concatenate_videoclips

from audio.templates import AudioTemplate
from content.schema import LessonItem
from render.kenburns import make_kenburns_clip
from render.overlay import build_overlay_cues, draw_text_on_frame, total_duration

ASPECT_SIZES = {
    "9:16": (720, 1280),
    "16:9": (1280, 720),
}


def build_scene_clip(
    item: LessonItem,
    template: AudioTemplate,
    audio_paths: list[str],
    image_path: str,
    aspect_ratio: str,
) -> VideoClip:
    size = ASPECT_SIZES[aspect_ratio]
    audio_clips = [AudioFileClip(p) for p in audio_paths]
    durations = [clip.duration for clip in audio_clips]
    scene_audio = concatenate_audioclips(audio_clips)
    cues = build_overlay_cues(item, template, durations)
    background = make_kenburns_clip(image_path, duration=total_duration(durations), size=size)

    def make_frame(t: float):
        frame = background.get_frame(t)
        active_cue = next((c for c in cues if c.start <= t < c.end), cues[-1])
        return draw_text_on_frame(frame, active_cue.text)

    scene = VideoClip(make_frame, duration=total_duration(durations))
    return scene.with_audio(scene_audio)


def assemble_video(scene_clips: list[VideoClip], out_path: str) -> str:
    final = concatenate_videoclips(scene_clips, method="compose")
    final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/render/test_assemble.py -v`
Expected: PASS (1 passed). This is the integration-level smoke test called for in the spec's Testing section.

- [ ] **Step 5: Commit**

```bash
git add backend/render/assemble.py backend/tests/render/test_assemble.py
git commit -m "feat: assemble scene clips with text overlay into exportable video"
```

---

## Task 12: AI image generation (ZeroGPU) with placeholder fallback

**Files:**
- Create: `backend/visuals/image.py`
- Test: `backend/tests/visuals/test_image.py`

**Interfaces:**
- Produces: `generate_image(prompt: str, cache_dir: str, max_retries: int = 1) -> str`, `make_placeholder_image(text: str, size) -> Image.Image`. Used by Task 14.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/visuals/test_image.py
from pathlib import Path

from PIL import Image
import visuals.image as image_module


def test_generate_image_uses_cache(tmp_path, monkeypatch):
    calls = {"count": 0}

    def fake_generate(prompt, width=768, height=768, steps=4):
        calls["count"] += 1
        return Image.new("RGB", (width, height), color=(1, 2, 3))

    monkeypatch.setattr(image_module, "_generate", fake_generate)
    path1 = image_module.generate_image("a cat", str(tmp_path))
    path2 = image_module.generate_image("a cat", str(tmp_path))
    assert path1 == path2
    assert calls["count"] == 1


def test_generate_image_falls_back_to_placeholder(tmp_path, monkeypatch):
    def always_fail(prompt, width=768, height=768, steps=4):
        raise RuntimeError("out of memory")

    monkeypatch.setattr(image_module, "_generate", always_fail)
    path = image_module.generate_image("a dog", str(tmp_path), max_retries=1)
    assert Path(path).exists()
    img = Image.open(path)
    assert img.size == (768, 768)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/visuals/test_image.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'visuals.image'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/visuals/image.py
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw

try:
    import spaces
except ImportError:
    class _NoOpSpaces:
        @staticmethod
        def GPU(func):
            return func

    spaces = _NoOpSpaces()

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        import torch
        from diffusers import FluxPipeline

        _pipeline = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-schnell", torch_dtype=torch.bfloat16
        )
        _pipeline.to("cuda")
    return _pipeline


@spaces.GPU
def _generate(prompt: str, width: int = 768, height: int = 768, steps: int = 4) -> Image.Image:
    pipeline = _get_pipeline()
    result = pipeline(prompt, width=width, height=height, num_inference_steps=steps)
    return result.images[0]


def make_placeholder_image(text: str, size: tuple[int, int] = (768, 768)) -> Image.Image:
    image = Image.new("RGB", size, color=(60, 60, 90))
    draw = ImageDraw.Draw(image)
    draw.text((20, size[1] // 2), text, fill=(255, 255, 255))
    return image


def generate_image(prompt: str, cache_dir: str, max_retries: int = 1) -> str:
    cache_path = Path(cache_dir) / f"{hashlib.sha256(prompt.encode()).hexdigest()}.png"
    if cache_path.exists():
        return str(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    width, height, steps = 768, 768, 4
    for attempt in range(max_retries + 1):
        try:
            image = _generate(prompt, width=width, height=height, steps=steps)
            image.save(cache_path)
            return str(cache_path)
        except Exception:  # noqa: BLE001 - fall back to a placeholder below
            width, height, steps = 512, 512, 2

    placeholder = make_placeholder_image(prompt[:40])
    placeholder.save(cache_path)
    return str(cache_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/visuals/test_image.py -v`
Expected: PASS (2 passed). Note: `test_generate_image_falls_back_to_placeholder` expects a 768×768 placeholder because `make_placeholder_image`'s default size is used regardless of the failed attempt's shrunk size — this is intentional so the placeholder always matches the originally requested resolution.

- [ ] **Step 5: Commit**

```bash
git add backend/visuals/image.py backend/tests/visuals/test_image.py
git commit -m "feat: FLUX.1-schnell image generation on ZeroGPU with cache and placeholder fallback"
```

---

## Task 13: LLM auto lesson generation

**Files:**
- Create: `backend/content/auto.py`
- Test: `backend/tests/content/test_auto.py`

**Interfaces:**
- Consumes: `LessonItem` from Task 2.
- Produces: `AutoGenerationError`, `generate_lesson(topic: str, llm_call: Callable[[str], str], max_retries: int = 1) -> list[LessonItem]`, `gemini_llm_call(prompt: str) -> str`. Used by Task 15 (`app.py`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/content/test_auto.py
import pytest
from content.auto import generate_lesson, AutoGenerationError


def test_generate_lesson_parses_valid_json():
    def fake_llm(prompt: str) -> str:
        return '{"items": [{"hanzi": "吃", "pinyin": "chī", "meaning_vi": "ăn"}]}'

    items = generate_lesson("đồ ăn", fake_llm)
    assert len(items) == 1
    assert items[0].hanzi == "吃"


def test_generate_lesson_retries_on_invalid_json():
    calls = {"count": 0}

    def flaky_llm(prompt: str) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json"
        return '{"items": [{"hanzi": "喝", "meaning_vi": "uống"}]}'

    items = generate_lesson("đồ uống", flaky_llm, max_retries=1)
    assert calls["count"] == 2
    assert items[0].hanzi == "喝"


def test_generate_lesson_raises_after_max_retries():
    def always_bad(prompt: str) -> str:
        return "still not json"

    with pytest.raises(AutoGenerationError):
        generate_lesson("chủ đề", always_bad, max_retries=1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/content/test_auto.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'content.auto'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/content/auto.py
import json
import os
from typing import Callable

from pydantic import BaseModel, ValidationError

from content.schema import LessonItem


class AutoGenerationError(Exception):
    pass


class _RawItem(BaseModel):
    hanzi: str
    pinyin: str | None = None
    meaning_vi: str


class _RawLesson(BaseModel):
    items: list[_RawItem]


PROMPT_TEMPLATE = (
    "Bạn là giáo viên tiếng Trung. Soạn danh sách 8-12 từ vựng hoặc câu tiếng Trung "
    "về chủ đề: \"{topic}\". Trả về CHỈ JSON theo đúng schema sau, không thêm giải thích:\n"
    '{{"items": [{{"hanzi": "...", "pinyin": "...", "meaning_vi": "..."}}]}}'
)


def generate_lesson(
    topic: str, llm_call: Callable[[str], str], max_retries: int = 1
) -> list[LessonItem]:
    prompt = PROMPT_TEMPLATE.format(topic=topic)
    last_error: Exception | None = None
    for _attempt in range(max_retries + 1):
        raw_response = llm_call(prompt)
        try:
            data = json.loads(raw_response)
            parsed = _RawLesson(**data)
            return [
                LessonItem(hanzi=i.hanzi, pinyin=i.pinyin, meaning_vi=i.meaning_vi)
                for i in parsed.items
            ]
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
    raise AutoGenerationError(
        f"LLM returned invalid lesson data after {max_retries + 1} attempts: {last_error}"
    )


def gemini_llm_call(prompt: str) -> str:
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise AutoGenerationError("GEMINI_API_KEY environment variable is not set")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/content/test_auto.py -v`
Expected: PASS (3 passed). `gemini_llm_call` is intentionally untested here — it needs a real `GEMINI_API_KEY` and network access; verify it manually in Task 16.

- [ ] **Step 5: Commit**

```bash
git add backend/content/auto.py backend/tests/content/test_auto.py
git commit -m "feat: LLM-driven auto lesson generation from a topic prompt"
```

---

## Task 14: Pipeline orchestration

**Files:**
- Create: `backend/pipeline.py`
- Test: `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `fill_pinyin_batch` (Task 3), `AudioTemplate` (Task 5), `synthesize`/`get_audio_duration` (Task 9), `build_image_prompt` (Task 8), `generate_image` (Task 12), `build_scene_clip`/`assemble_video` (Task 11).
- Produces: `ItemResult(item: LessonItem, error: str | None)`, `PipelineResult(video_paths: dict[str, str], item_errors: list[ItemResult], assembly_errors: dict[str, str])`, `run_pipeline(items, template, aspect_ratios, work_dir) -> PipelineResult`. Used by Task 15 (`app.py`). `assembly_errors` maps aspect ratio -> error message when the final `assemble_video` call for that ratio fails (per spec: "Dựng video: lỗi ffmpeg → in log ra panel UI, giữ file tạm để debug" — an assembly failure must not crash the whole pipeline).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_pipeline.py
from pathlib import Path

from content.schema import LessonItem
from audio.templates import AudioTemplate, TemplateSegment
from audio.tts import TTSError
import pipeline as pipeline_module


class _FakeClip:
    def __init__(self, label):
        self.label = label


def _fake_synthesize(text, lang, out_path):
    Path(out_path).write_bytes(b"fake")
    return out_path


def _fake_duration(path):
    return 1.0


def _fake_generate_image(prompt, cache_dir):
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    return f"{cache_dir}/img.png"


def _fake_build_scene_clip(item, template, audio_paths, image_path, ratio):
    return _FakeClip(f"{item.hanzi}-{ratio}")


def _fake_assemble_video(clips, out_path):
    Path(out_path).write_bytes(b"fake-video")
    return out_path


def _template():
    return AudioTemplate(name="zh-vi", segments=[
        TemplateSegment(lang="zh", field="hanzi"),
        TemplateSegment(lang="vi", field="meaning_vi"),
    ])


def test_run_pipeline_happy_path(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_module, "synthesize", _fake_synthesize)
    monkeypatch.setattr(pipeline_module, "get_audio_duration", _fake_duration)
    monkeypatch.setattr(pipeline_module, "generate_image", _fake_generate_image)
    monkeypatch.setattr(pipeline_module, "build_scene_clip", _fake_build_scene_clip)
    monkeypatch.setattr(pipeline_module, "assemble_video", _fake_assemble_video)

    items = [LessonItem(hanzi="吃", meaning_vi="ăn"), LessonItem(hanzi="喝", meaning_vi="uống")]
    result = pipeline_module.run_pipeline(items, _template(), ["9:16"], str(tmp_path))

    assert "9:16" in result.video_paths
    assert Path(result.video_paths["9:16"]).exists()
    assert result.item_errors == []


def test_run_pipeline_isolates_item_failure(tmp_path, monkeypatch):
    call_count = {"n": 0}

    def flaky_synthesize(text, lang, out_path):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TTSError("network down")
        Path(out_path).write_bytes(b"fake")
        return out_path

    monkeypatch.setattr(pipeline_module, "synthesize", flaky_synthesize)
    monkeypatch.setattr(pipeline_module, "get_audio_duration", _fake_duration)
    monkeypatch.setattr(pipeline_module, "generate_image", _fake_generate_image)
    monkeypatch.setattr(pipeline_module, "build_scene_clip", _fake_build_scene_clip)
    monkeypatch.setattr(pipeline_module, "assemble_video", _fake_assemble_video)

    items = [LessonItem(hanzi="吃", meaning_vi="ăn"), LessonItem(hanzi="喝", meaning_vi="uống")]
    result = pipeline_module.run_pipeline(items, _template(), ["9:16"], str(tmp_path))

    assert len(result.item_errors) == 1
    assert result.item_errors[0].item.hanzi == "吃"
    assert "9:16" in result.video_paths


def test_run_pipeline_isolates_assembly_failure(tmp_path, monkeypatch):
    def failing_assemble(clips, out_path):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(pipeline_module, "synthesize", _fake_synthesize)
    monkeypatch.setattr(pipeline_module, "get_audio_duration", _fake_duration)
    monkeypatch.setattr(pipeline_module, "generate_image", _fake_generate_image)
    monkeypatch.setattr(pipeline_module, "build_scene_clip", _fake_build_scene_clip)
    monkeypatch.setattr(pipeline_module, "assemble_video", failing_assemble)

    items = [LessonItem(hanzi="吃", meaning_vi="ăn")]
    result = pipeline_module.run_pipeline(items, _template(), ["9:16", "16:9"], str(tmp_path))

    assert result.video_paths == {}
    assert result.item_errors == []
    assert "9:16" in result.assembly_errors
    assert "16:9" in result.assembly_errors
    assert "ffmpeg exploded" in result.assembly_errors["9:16"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/pipeline.py
from dataclasses import dataclass, field

from audio.templates import AudioTemplate
from audio.tts import get_audio_duration, synthesize
from content.pinyin import fill_pinyin_batch
from content.schema import LessonItem
from render.assemble import assemble_video, build_scene_clip
from visuals.image import generate_image
from visuals.prompt_builder import build_image_prompt


@dataclass
class ItemResult:
    item: LessonItem
    error: str | None = None


@dataclass
class PipelineResult:
    video_paths: dict[str, str] = field(default_factory=dict)
    item_errors: list[ItemResult] = field(default_factory=list)
    assembly_errors: dict[str, str] = field(default_factory=dict)


def run_pipeline(
    items: list[LessonItem],
    template: AudioTemplate,
    aspect_ratios: list[str],
    work_dir: str,
) -> PipelineResult:
    items = fill_pinyin_batch(items)
    scene_clips: dict[str, list] = {ratio: [] for ratio in aspect_ratios}
    item_errors: list[ItemResult] = []

    for index, item in enumerate(items):
        try:
            audio_paths = []
            durations = []
            for seg_index, segment in enumerate(template.segments):
                text = item.hanzi if segment.lang == "zh" else item.meaning_vi
                audio_path = f"{work_dir}/audio_{index}_{seg_index}.mp3"
                synthesize(text, segment.lang, audio_path)
                audio_paths.append(audio_path)
                durations.append(get_audio_duration(audio_path))

            prompt = build_image_prompt(item)
            image_path = generate_image(prompt, cache_dir=f"{work_dir}/images")

            for ratio in aspect_ratios:
                clip = build_scene_clip(item, template, audio_paths, image_path, ratio)
                scene_clips[ratio].append(clip)
        except Exception as exc:  # noqa: BLE001 - one bad item must not stop the batch
            item_errors.append(ItemResult(item=item, error=str(exc)))

    video_paths: dict[str, str] = {}
    assembly_errors: dict[str, str] = {}
    for ratio, clips in scene_clips.items():
        if not clips:
            continue
        out_path = f"{work_dir}/output_{ratio.replace(':', 'x')}.mp4"
        try:
            assemble_video(clips, out_path)
            video_paths[ratio] = out_path
        except Exception as exc:  # noqa: BLE001 - ffmpeg failure must not crash the whole run
            assembly_errors[ratio] = str(exc)

    return PipelineResult(
        video_paths=video_paths, item_errors=item_errors, assembly_errors=assembly_errors
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_pipeline.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: orchestrate content/audio/image/render pipeline with per-item error isolation"
```

---

## Task 15: Gradio app and HF Spaces metadata

**Files:**
- Create: `backend/app.py`
- Create: `backend/README.md`
- Test: `backend/tests/test_app.py`

**Interfaces:**
- Consumes: `parse_manual_input` (Task 4), `generate_lesson`/`gemini_llm_call` (Task 13), `list_templates` (Task 5), `run_pipeline` (Task 14).
- Produces: `_load_templates() -> dict[str, AudioTemplate]`, `generate_video(...)`, `build_app() -> gr.Blocks` — this is the Space's entrypoint (`app_file: app.py`) and the API surface the frontend plan will call.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_app.py
from app import _load_templates


def test_load_templates_includes_expected_names():
    templates = _load_templates()
    assert "zh-zh-vi" in templates
    assert "zh-vi-zh" in templates
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app.py
import tempfile
from pathlib import Path

import gradio as gr

from audio.templates import list_templates
from content.auto import gemini_llm_call, generate_lesson
from content.manual import parse_manual_input
from pipeline import run_pipeline

TEMPLATES_DIR = Path(__file__).parent / "config" / "templates"


def _load_templates():
    templates = list_templates(TEMPLATES_DIR)
    return {t.name: t for t in templates}


def generate_video(mode, csv_text, topic, template_name, aspect_ratios):
    templates = _load_templates()
    template = templates[template_name]

    if mode == "Nhập danh sách":
        items, errors = parse_manual_input(csv_text)
        warnings = [f"Dòng {e.line_number}: {e.message}" for e in errors]
    else:
        items = generate_lesson(topic, gemini_llm_call)
        warnings = []

    if not items:
        message = "Không có mục hợp lệ để tạo video.\n" + "\n".join(warnings)
        return None, None, message

    work_dir = tempfile.mkdtemp(prefix="zhvideo_")
    result = run_pipeline(items, template, aspect_ratios, work_dir)

    log_lines = warnings + [f"Lỗi mục '{e.item.hanzi}': {e.error}" for e in result.item_errors]
    log_lines += [f"Lỗi dựng video ({ratio}): {msg}" for ratio, msg in result.assembly_errors.items()]
    video_9_16 = result.video_paths.get("9:16")
    video_16_9 = result.video_paths.get("16:9")
    log_text = "\n".join(log_lines) if log_lines else "Hoàn tất, không có lỗi."
    return video_9_16, video_16_9, log_text


def build_app() -> gr.Blocks:
    templates = _load_templates()
    template_names = list(templates.keys())

    with gr.Blocks() as demo:
        gr.Markdown("# Tạo video dạy tiếng Trung song ngữ Việt-Trung")
        mode = gr.Radio(
            ["Nhập danh sách", "Chủ đề tự động"], value="Nhập danh sách", label="Chế độ nhập"
        )
        csv_text = gr.Textbox(label="Danh sách CSV (hanzi,pinyin,meaning_vi)", lines=8)
        topic = gr.Textbox(label="Chủ đề (chế độ tự động)")
        template_name = gr.Dropdown(
            template_names, value=template_names[0], label="Template trình tự audio"
        )
        aspect_ratios = gr.CheckboxGroup(
            ["9:16", "16:9"], value=["9:16"], label="Tỉ lệ khung hình"
        )
        submit = gr.Button("Tạo video")
        video_9_16 = gr.Video(label="Video 9:16")
        video_16_9 = gr.Video(label="Video 16:9")
        log = gr.Textbox(label="Log", lines=6)

        submit.click(
            generate_video,
            inputs=[mode, csv_text, topic, template_name, aspect_ratios],
            outputs=[video_9_16, video_16_9, log],
        )

    return demo


if __name__ == "__main__":
    build_app().launch()
```

```markdown
<!-- backend/README.md -->
---
title: ZH Video Gen
emoji: 🈶
colorFrom: red
colorTo: yellow
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
---

# zh-video-gen backend

Backend tạo video dạy tiếng Trung song ngữ Việt-Trung, deploy trên Hugging Face Spaces (ZeroGPU).
Xem thiết kế đầy đủ tại `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md` trong repo chính.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_app.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Run the full backend test suite**

Run: `cd backend && pytest -v`
Expected: all tests from Tasks 2-15 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app.py backend/README.md backend/tests/test_app.py
git commit -m "feat: Gradio app wiring manual/auto input to the generation pipeline"
```

---

## Task 16: Deploy backend to GitHub and connect Hugging Face Space

**Files:** none (deployment/verification only)

- [ ] **Step 1: Push `backend/` to the existing GitHub repo**

```bash
git push origin main
```

Expected: push succeeds; `backend/` is visible at `https://github.com/phuoctoand11-cmd/ZH-VIDEO-GEN/tree/main/backend`.

- [ ] **Step 2: Create the Hugging Face Space**

Manual steps (no CLI credentials available to automate this):
1. Go to https://huggingface.co/new-space
2. Space name: `zh-video-gen`, SDK: `Gradio`, Hardware: `ZeroGPU`
3. Under the Space's Settings → "Repository", link it to the GitHub repo `phuoctoand11-cmd/ZH-VIDEO-GEN`, subdirectory `backend/` (HF Spaces' GitHub Actions sync template, or manually `git subtree push` if subdirectory linking isn't available for your plan — in that case push `backend/`'s contents to the Space's own git remote instead: `git subtree push --prefix=backend space main`, after `git remote add space https://huggingface.co/spaces/<username>/zh-video-gen`).
4. In the Space's Settings → "Variables and secrets", add secret `GEMINI_API_KEY` with a free-tier Gemini API key (from https://aistudio.google.com/apikey).

- [ ] **Step 3: Verify the deployed Space**

Open the Space's URL, wait for build to finish, then in the Gradio UI:
1. Select "Nhập danh sách", paste `hanzi,pinyin,meaning_vi\n吃,,ăn\n喝,,uống\n`, pick template `zh-zh-vi`, aspect ratio `9:16`, click "Tạo video".
2. Confirm a video plays back with Chinese audio, Vietnamese audio, and readable on-screen Chinese/pinyin/Vietnamese text.
3. Select "Chủ đề tự động", type a topic (e.g. "đồ ăn"), confirm a lesson is generated and a video produced.

Expected: both flows produce a downloadable video with no unhandled errors in the Space logs.

- [ ] **Step 4: Record the Space's API endpoint for the frontend plan**

Run (from the Space page, "Use via API" link) note the Space's base URL (e.g. `https://<username>-zh-video-gen.hf.space`) — this is the value the frontend plan's `@gradio/client` calls will target.

