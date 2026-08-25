# Card templates (từ vựng theo chủ đề / hội thoại theo chủ đề) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay hệ thống ảnh nền "AI sinh ảnh chụp + Ken Burns + chữ vẽ đè từng frame" bằng hệ thống card thiết kế sẵn (chữ do code vẽ 1 lần, chỉ mascot/avatar do AI sinh) cho cả 3 chế độ: Nhập danh sách, Từ vựng theo chủ đề, Hội thoại theo chủ đề.

**Architecture:** Thêm module vẽ card mới (`render/vocab_card.py`, `render/dialogue_card.py`, `render/theme.py`, `render/highlight.py`), thêm content-generation cho 2 chế độ mới (`content/vocab_topic.py`, `content/dialogue_topic.py`), nối vào 2 pipeline mới trong `pipeline.py`, đổi UI backend (`app.py`) và frontend (`index.html`, `validation.js`). Tối đa hóa tái dùng hạ tầng sẵn có: TTS, `AudioTemplate`, `kenburns.py`, `assemble_video`, cơ chế lỗi-1-mục-không-sập-batch.

**Tech Stack:** Python 3.11, Pillow (đã có), moviepy (đã có), pydantic (đã có), groq (đã có). Không thêm pip package mới — chỉ thêm 1 file font (Baloo 2, Google Fonts OFL license) làm asset tĩnh.

**Spec:** `docs/superpowers/specs/2026-08-25-card-templates-design.md`

## Global Constraints

- Mọi text (hanzi/pinyin/meaning_vi/tên nhân vật/tiêu đề) phải do code (Pillow `ImageDraw`) vẽ — không bao giờ yêu cầu model sinh ảnh vẽ chữ vào ảnh.
- AI sinh ảnh (`visuals/image.py::generate_image`, không đổi interface) chỉ dùng để sinh mascot/avatar — prompt luôn phải chứa "no text" / "no letters" tương tự quy ước đã có ở `build_image_prompt`.
- 1 mục/lượt lỗi không được làm hỏng cả video — theo đúng nguyên tắc đã áp dụng trong `pipeline.py::run_pipeline` hiện có.
- Mọi module mới phải có unit test độc lập, không cần mạng/GPU (trừ test tích hợp ở `pipeline.py` — vẫn không cần mạng vì dùng fake `llm_call`/ảnh giả, nhưng cần `ffmpeg`/`ffprobe` trên PATH, giống `tests/render/test_assemble.py` hiện có).
- `ASPECT_SIZES` (`render/assemble.py`) là nguồn sự thật duy nhất cho kích thước khung hình — mọi module render mới nhận `size: tuple[int, int]` từ đây, không tự định nghĩa lại.

---

### Task 1: Font asset + `render/theme.py`

**Files:**
- Create: `backend/assets/fonts/Baloo2-Variable.ttf`
- Create: `backend/assets/fonts/Baloo2-OFL.txt`
- Create: `backend/render/theme.py`
- Test: `backend/tests/render/test_theme.py`

**Interfaces:**
- Produces: `render.theme.get_rounded_font(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont`, `render.theme.get_cjk_font(size: int) -> ImageFont.FreeTypeFont`, `render.theme.palette_color(index: int) -> tuple[int, int, int]`, `render.theme.PALETTE: list[tuple[int, int, int]]`, `render.theme.make_white_transparent(img: Image.Image, threshold: int = 235) -> Image.Image`, `render.theme.measure_text_width(draw, text, font) -> int`, `render.theme.wrap_text_to_width(draw, text, font, max_width: int) -> list[str]`. Mọi task render sau đều import từ module này.

- [ ] **Step 1: Tải font Baloo 2 (variable font, license OFL) và file license**

```bash
cd backend
mkdir -p assets/fonts
curl -sL -o assets/fonts/Baloo2-Variable.ttf "https://github.com/google/fonts/raw/main/ofl/baloo2/Baloo2%5Bwght%5D.ttf"
curl -sL -o assets/fonts/Baloo2-OFL.txt "https://raw.githubusercontent.com/google/fonts/main/ofl/baloo2/OFL.txt"
```

Xác nhận tải đúng file font thật (không phải trang lỗi HTML):

```bash
python -c "from PIL import ImageFont; f = ImageFont.truetype('assets/fonts/Baloo2-Variable.ttf', 40); print(f.get_variation_names())"
```

Expected output: `[b'Regular', b'Medium', b'SemiBold', b'Bold', b'ExtraBold']`

- [ ] **Step 2: Viết `render/theme.py`**

```python
from pathlib import Path

from PIL import ImageDraw, ImageFont, Image

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
CJK_FONT_PATH = ASSETS_DIR / "fonts" / "NotoSansCJKsc-Regular.otf"
ROUNDED_FONT_PATH = ASSETS_DIR / "fonts" / "Baloo2-Variable.ttf"

# Cycled per row (vocab card) / per speaker (dialogue card).
PALETTE = [
    (255, 214, 224),  # hồng nhạt
    (204, 229, 255),  # xanh dương nhạt
    (214, 245, 214),  # xanh lá nhạt
    (255, 229, 204),  # cam nhạt
    (229, 214, 255),  # tím nhạt
]

_FONT_CACHE: dict[tuple[str, int, str], ImageFont.FreeTypeFont] = {}


def get_rounded_font(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    key = ("rounded", size, weight)
    font = _FONT_CACHE.get(key)
    if font is None:
        font = ImageFont.truetype(str(ROUNDED_FONT_PATH), size)
        try:
            font.set_variation_by_name(weight)
        except Exception:  # noqa: BLE001 - variation support is best-effort
            pass
        _FONT_CACHE[key] = font
    return font


def get_cjk_font(size: int) -> ImageFont.FreeTypeFont:
    key = ("cjk", size, "")
    font = _FONT_CACHE.get(key)
    if font is None:
        font = ImageFont.truetype(str(CJK_FONT_PATH), size)
        _FONT_CACHE[key] = font
    return font


def palette_color(index: int) -> tuple[int, int, int]:
    return PALETTE[index % len(PALETTE)]


def make_white_transparent(img: Image.Image, threshold: int = 235) -> Image.Image:
    """Turn near-white pixels transparent so a mascot/avatar generated on a
    plain white background composites cleanly onto a colored card, without
    needing a real background-removal model.
    """
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r >= threshold and g >= threshold and b >= threshold:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def measure_text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def wrap_text_to_width(
    draw: ImageDraw.ImageDraw, text: str, font, max_width: int
) -> list[str]:
    """Greedily wrap `text` to fit `max_width`. Splits on spaces when present
    (pinyin/Vietnamese); falls back to per-character splitting for raw Hanzi
    sentences, which have no spaces.
    """
    if not text:
        return [text]
    if measure_text_width(draw, text, font) <= max_width:
        return [text]

    separator = " " if " " in text else ""
    tokens = text.split(" ") if separator else list(text)
    lines: list[str] = []
    current = ""
    for token in tokens:
        candidate = f"{current}{separator}{token}" if current else token
        if current and measure_text_width(draw, candidate, font) > max_width:
            lines.append(current)
            current = token
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [text]
```

- [ ] **Step 3: Viết test `tests/render/test_theme.py`**

```python
from PIL import Image, ImageDraw, ImageFont

from render import theme


def test_get_rounded_font_returns_cached_instance():
    f1 = theme.get_rounded_font(40)
    f2 = theme.get_rounded_font(40)
    assert f1 is f2
    assert isinstance(f1, ImageFont.FreeTypeFont)


def test_get_cjk_font_returns_freetype_font():
    font = theme.get_cjk_font(30)
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_palette_color_cycles():
    n = len(theme.PALETTE)
    assert theme.palette_color(0) == theme.palette_color(n)
    assert theme.palette_color(1) == theme.palette_color(n + 1)


def test_make_white_transparent_clears_white_keeps_color():
    img = Image.new("RGB", (2, 1))
    img.putpixel((0, 0), (255, 255, 255))
    img.putpixel((1, 0), (10, 20, 30))

    result = theme.make_white_transparent(img)

    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((1, 0)) == (10, 20, 30, 255)


def test_wrap_text_to_width_keeps_short_text_on_one_line():
    img = Image.new("RGB", (400, 100))
    draw = ImageDraw.Draw(img)
    font = theme.get_rounded_font(20)

    lines = theme.wrap_text_to_width(draw, "xin chào", font, max_width=300)
    assert lines == ["xin chào"]


def test_wrap_text_to_width_splits_long_hanzi_sentence_by_character():
    img = Image.new("RGB", (400, 200))
    draw = ImageDraw.Draw(img)
    font = theme.get_cjk_font(50)

    long_text = "随着生活水平的提高人们越来越关心自己的健康了"
    lines = theme.wrap_text_to_width(draw, long_text, font, max_width=200)

    assert len(lines) > 1
    assert "".join(lines) == long_text
```

- [ ] **Step 4: Chạy test**

Run: `cd backend && pytest tests/render/test_theme.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/assets/fonts/Baloo2-Variable.ttf backend/assets/fonts/Baloo2-OFL.txt backend/render/theme.py backend/tests/render/test_theme.py
git commit -m "feat: add render theme module (fonts, palette, wrap/composite helpers)"
```

---

### Task 2: `content/schema.py` — model mới cho card từ vựng và hội thoại

**Files:**
- Modify: `backend/content/schema.py`
- Test: `backend/tests/content/test_schema.py`

**Interfaces:**
- Consumes: `LessonItem` (đã có, không đổi).
- Produces: `content.schema.VocabCardItem`, `content.schema.VocabTopicResult`, `content.schema.DialogueTurn`, `content.schema.DialogueResult` — dùng bởi mọi task từ Task 3 trở đi.

- [ ] **Step 1: Thêm model vào `content/schema.py`**

Thêm vào cuối file (giữ nguyên `LessonItem` và import đầu file):

```python
class VocabCardItem(BaseModel):
    hanzi: str
    pinyin: str | None = None
    meaning_vi: str
    icon_prompt: str

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


class VocabTopicResult(BaseModel):
    radical: str | None = None
    radical_pinyin: str | None = None
    radical_meaning_vi: str | None = None
    items: list[VocabCardItem]


class DialogueTurn(BaseModel):
    speaker_name: str
    line: LessonItem


class DialogueResult(BaseModel):
    title: str
    turns: list[DialogueTurn]
```

- [ ] **Step 2: Thêm test vào `tests/content/test_schema.py`**

Thêm vào cuối file (giữ nguyên import + test `LessonItem` hiện có, thêm import `VocabCardItem, VocabTopicResult, DialogueTurn, DialogueResult` vào dòng import đầu file):

```python
from content.schema import (
    DialogueResult,
    DialogueTurn,
    LessonItem,
    VocabCardItem,
    VocabTopicResult,
)
```

```python
def test_vocab_card_item_valid():
    item = VocabCardItem(hanzi="冰", pinyin="bīng", meaning_vi="băng", icon_prompt="cute ice cube")
    assert item.hanzi == "冰"
    assert item.icon_prompt == "cute ice cube"


def test_vocab_card_item_rejects_empty_hanzi():
    with pytest.raises(ValidationError):
        VocabCardItem(hanzi="  ", meaning_vi="băng", icon_prompt="ice")


def test_vocab_topic_result_holds_items_and_optional_radical():
    result = VocabTopicResult(
        radical="冫",
        radical_pinyin="bīng",
        radical_meaning_vi="băng",
        items=[VocabCardItem(hanzi="冰", meaning_vi="băng", icon_prompt="ice cube")],
    )
    assert result.radical == "冫"
    assert len(result.items) == 1


def test_vocab_topic_result_radical_defaults_to_none():
    result = VocabTopicResult(
        items=[VocabCardItem(hanzi="吃", meaning_vi="ăn", icon_prompt="eating")]
    )
    assert result.radical is None


def test_dialogue_turn_wraps_lesson_item():
    turn = DialogueTurn(speaker_name="Minh", line=LessonItem(hanzi="你好", meaning_vi="xin chào"))
    assert turn.speaker_name == "Minh"
    assert turn.line.hanzi == "你好"


def test_dialogue_result_holds_turns():
    result = DialogueResult(
        title="Chào hỏi",
        turns=[DialogueTurn(speaker_name="Minh", line=LessonItem(hanzi="你好", meaning_vi="xin chào"))],
    )
    assert result.title == "Chào hỏi"
    assert len(result.turns) == 1
```

- [ ] **Step 3: Chạy test**

Run: `cd backend && pytest tests/content/test_schema.py -v`
Expected: 10 passed (4 cũ + 6 mới)

- [ ] **Step 4: Commit**

```bash
git add backend/content/schema.py backend/tests/content/test_schema.py
git commit -m "feat: add VocabCardItem/VocabTopicResult/DialogueTurn/DialogueResult schemas"
```

---

### Task 3: `content/llm_utils.py` (tách từ `content/auto.py`) + `content/vocab_topic.py`

**Files:**
- Create: `backend/content/llm_utils.py`
- Modify: `backend/content/auto.py` (tách `_strip_code_fence` ra module dùng chung)
- Create: `backend/content/vocab_topic.py`
- Test: `backend/tests/content/test_vocab_topic.py`

**Interfaces:**
- Consumes: `content.schema.VocabTopicResult` (Task 2), `content.auto.AutoGenerationError` (đã có).
- Produces: `content.llm_utils.strip_code_fence(raw_response: str) -> str` (dùng lại bởi Task 4). `content.vocab_topic.generate_vocab_topic(topic: str, llm_call: Callable[[str], str], max_retries: int = 1) -> VocabTopicResult`.

- [ ] **Step 1: Tạo `content/llm_utils.py`, chuyển `_strip_code_fence` ra đây**

```python
def strip_code_fence(raw_response: str) -> str:
    """Strip a surrounding markdown code fence from an LLM response, if present.

    LLMs frequently wrap JSON in ```json ... ``` despite being told not to.
    """
    text = (raw_response or "").strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    lines = lines[1:]  # drop the opening ``` / ```json line
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
```

- [ ] **Step 2: Sửa `content/auto.py` dùng `content.llm_utils.strip_code_fence`, xóa `_strip_code_fence` cục bộ**

Xóa hàm `_strip_code_fence` khỏi `content/auto.py` (toàn bộ định nghĩa hàm). Thêm import ở đầu file:

```python
from content.llm_utils import strip_code_fence
```

Trong `generate_lesson`, đổi dòng gọi hàm:

```python
            data = json.loads(strip_code_fence(raw_response))
```

(thay cho `data = json.loads(_strip_code_fence(raw_response))`)

- [ ] **Step 3: Xác nhận `content/auto.py` không hỏng — chạy test cũ**

Run: `cd backend && pytest tests/content/test_auto.py -v`
Expected: 8 passed (không đổi hành vi, chỉ tách hàm dùng chung)

- [ ] **Step 4: Tạo `content/vocab_topic.py`**

```python
import json
from typing import Callable

from pydantic import ValidationError

from content.auto import AutoGenerationError
from content.llm_utils import strip_code_fence
from content.schema import VocabTopicResult

PROMPT_TEMPLATE = (
    "Bạn là giáo viên tiếng Trung. Chủ đề hoặc bộ thủ: \"{topic}\". "
    "Soạn đúng 5 từ tiếng Trung liên quan (nếu là 1 bộ thủ, chọn 5 từ có chứa bộ thủ đó). "
    "Với mỗi từ, viết icon_prompt là mô tả NGẮN BẰNG TIẾNG ANH cho 1 hình minh họa mascot dễ "
    "thương đại diện nghĩa của từ (không nhắc chữ Hán, không yêu cầu vẽ chữ trong ảnh). "
    "Nếu topic là 1 bộ thủ cụ thể, điền radical (chính bộ thủ đó), radical_pinyin, "
    "radical_meaning_vi; nếu không, để 3 trường này là null. "
    "Trả về CHỈ JSON theo đúng schema sau, không thêm giải thích:\n"
    '{{"radical": "...", "radical_pinyin": "...", "radical_meaning_vi": "...", '
    '"items": [{{"hanzi": "...", "pinyin": "...", "meaning_vi": "...", "icon_prompt": "..."}}]}}'
)


def generate_vocab_topic(
    topic: str, llm_call: Callable[[str], str], max_retries: int = 1
) -> VocabTopicResult:
    prompt = PROMPT_TEMPLATE.format(topic=topic)
    last_error: Exception | None = None
    for _attempt in range(max_retries + 1):
        raw_response = llm_call(prompt)
        try:
            data = json.loads(strip_code_fence(raw_response))
            return VocabTopicResult(**data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
    raise AutoGenerationError(
        f"LLM returned invalid vocab topic data after {max_retries + 1} attempts: {last_error}"
    )
```

- [ ] **Step 5: Viết test `tests/content/test_vocab_topic.py`**

```python
import pytest

from content.auto import AutoGenerationError
from content.vocab_topic import generate_vocab_topic

VALID_JSON = (
    '{"radical": "冫", "radical_pinyin": "bīng", "radical_meaning_vi": "băng", '
    '"items": [{"hanzi": "冰", "pinyin": "bīng", "meaning_vi": "băng", '
    '"icon_prompt": "cute ice cube character"}]}'
)


def test_generate_vocab_topic_parses_valid_json():
    def fake_llm(prompt: str) -> str:
        return VALID_JSON

    result = generate_vocab_topic("bộ băng", fake_llm)
    assert result.radical == "冫"
    assert len(result.items) == 1
    assert result.items[0].icon_prompt == "cute ice cube character"


def test_generate_vocab_topic_retries_on_invalid_json():
    calls = {"count": 0}

    def flaky_llm(prompt: str) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json"
        return VALID_JSON

    result = generate_vocab_topic("bộ băng", flaky_llm, max_retries=1)
    assert calls["count"] == 2
    assert result.items[0].hanzi == "冰"


def test_generate_vocab_topic_parses_fenced_json():
    def fenced_llm(prompt: str) -> str:
        return f"```json\n{VALID_JSON}\n```"

    result = generate_vocab_topic("bộ băng", fenced_llm)
    assert result.items[0].hanzi == "冰"


def test_generate_vocab_topic_raises_after_max_retries():
    def always_bad(prompt: str) -> str:
        return "still not json"

    with pytest.raises(AutoGenerationError):
        generate_vocab_topic("bộ băng", always_bad, max_retries=1)


def test_generate_vocab_topic_accepts_null_radical_for_non_radical_topic():
    json_no_radical = (
        '{"radical": null, "radical_pinyin": null, "radical_meaning_vi": null, '
        '"items": [{"hanzi": "苹果", "pinyin": "píngguǒ", "meaning_vi": "táo", '
        '"icon_prompt": "cute red apple character"}]}'
    )

    def fake_llm(prompt: str) -> str:
        return json_no_radical

    result = generate_vocab_topic("đồ ăn", fake_llm)
    assert result.radical is None
```

- [ ] **Step 6: Chạy test**

Run: `cd backend && pytest tests/content/test_vocab_topic.py tests/content/test_auto.py -v`
Expected: 13 passed (5 mới + 8 cũ vẫn xanh)

- [ ] **Step 7: Commit**

```bash
git add backend/content/llm_utils.py backend/content/auto.py backend/content/vocab_topic.py backend/tests/content/test_vocab_topic.py
git commit -m "feat: add generate_vocab_topic, extract strip_code_fence to content/llm_utils.py"
```

---

### Task 4: `content/dialogue_topic.py`

**Files:**
- Create: `backend/content/dialogue_topic.py`
- Test: `backend/tests/content/test_dialogue_topic.py`

**Interfaces:**
- Consumes: `content.llm_utils.strip_code_fence` (Task 3), `content.schema.DialogueResult` (Task 2), `content.auto.AutoGenerationError` (đã có).
- Produces: `content.dialogue_topic.generate_dialogue_topic(topic: str, llm_call: Callable[[str], str], max_retries: int = 1) -> DialogueResult`.

- [ ] **Step 1: Viết `content/dialogue_topic.py`**

```python
import json
from typing import Callable

from pydantic import ValidationError

from content.auto import AutoGenerationError
from content.llm_utils import strip_code_fence
from content.schema import DialogueResult

PROMPT_TEMPLATE = (
    "Bạn là giáo viên tiếng Trung. Soạn 1 đoạn hội thoại tiếng Trung 6-8 lượt nói giữa 2 nhân "
    "vật, về chủ đề: \"{topic}\". Mỗi nhân vật có 1 tên tiếng Việt riêng, xưng hô tự nhiên. "
    "Mỗi lượt gồm 1 câu tiếng Trung ngắn tự nhiên, kèm pinyin và nghĩa tiếng Việt. "
    "Trả về CHỈ JSON theo đúng schema sau, không thêm giải thích:\n"
    '{{"title": "...", "turns": [{{"speaker_name": "...", "line": '
    '{{"hanzi": "...", "pinyin": "...", "meaning_vi": "..."}}}}]}}'
)


def generate_dialogue_topic(
    topic: str, llm_call: Callable[[str], str], max_retries: int = 1
) -> DialogueResult:
    prompt = PROMPT_TEMPLATE.format(topic=topic)
    last_error: Exception | None = None
    for _attempt in range(max_retries + 1):
        raw_response = llm_call(prompt)
        try:
            data = json.loads(strip_code_fence(raw_response))
            return DialogueResult(**data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
    raise AutoGenerationError(
        f"LLM returned invalid dialogue data after {max_retries + 1} attempts: {last_error}"
    )
```

- [ ] **Step 2: Viết test `tests/content/test_dialogue_topic.py`**

```python
import pytest

from content.auto import AutoGenerationError
from content.dialogue_topic import generate_dialogue_topic

VALID_JSON = (
    '{"title": "Chào hỏi", "turns": ['
    '{"speaker_name": "Minh", "line": {"hanzi": "你好", "pinyin": "nǐ hǎo", "meaning_vi": "xin chào"}}, '
    '{"speaker_name": "Lan", "line": {"hanzi": "你好吗", "pinyin": "nǐ hǎo ma", "meaning_vi": "bạn khỏe không"}}'
    ']}'
)


def test_generate_dialogue_topic_parses_valid_json():
    def fake_llm(prompt: str) -> str:
        return VALID_JSON

    result = generate_dialogue_topic("chào hỏi", fake_llm)
    assert result.title == "Chào hỏi"
    assert len(result.turns) == 2
    assert result.turns[0].speaker_name == "Minh"
    assert result.turns[1].line.hanzi == "你好吗"


def test_generate_dialogue_topic_retries_on_invalid_json():
    calls = {"count": 0}

    def flaky_llm(prompt: str) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json"
        return VALID_JSON

    result = generate_dialogue_topic("chào hỏi", flaky_llm, max_retries=1)
    assert calls["count"] == 2
    assert result.title == "Chào hỏi"


def test_generate_dialogue_topic_parses_fenced_json():
    def fenced_llm(prompt: str) -> str:
        return f"```json\n{VALID_JSON}\n```"

    result = generate_dialogue_topic("chào hỏi", fenced_llm)
    assert len(result.turns) == 2


def test_generate_dialogue_topic_raises_after_max_retries():
    def always_bad(prompt: str) -> str:
        return "still not json"

    with pytest.raises(AutoGenerationError):
        generate_dialogue_topic("chào hỏi", always_bad, max_retries=1)
```

- [ ] **Step 3: Chạy test**

Run: `cd backend && pytest tests/content/test_dialogue_topic.py -v`
Expected: 4 passed

- [ ] **Step 4: Commit**

```bash
git add backend/content/dialogue_topic.py backend/tests/content/test_dialogue_topic.py
git commit -m "feat: add generate_dialogue_topic"
```

---

### Task 5: `visuals/prompt_builder.py` — prompt cho mascot và avatar

**Files:**
- Modify: `backend/visuals/prompt_builder.py`
- Test: `backend/tests/visuals/test_prompt_builder.py`

**Interfaces:**
- Produces: `visuals.prompt_builder.build_mascot_prompt(icon_prompt: str) -> str`, `visuals.prompt_builder.build_avatar_prompt(speaker_name: str) -> str`. Dùng bởi Task 10 (`pipeline.py`).

- [ ] **Step 1: Thêm 2 hàm vào `visuals/prompt_builder.py`**

Giữ nguyên `build_image_prompt` (không xóa ở task này — sẽ đánh giá xóa ở Task 13 sau khi xác nhận không còn nơi nào gọi). Thêm vào cuối file:

```python
def build_mascot_prompt(icon_prompt: str) -> str:
    return (
        f"A cute chibi sticker illustration of {icon_prompt}. Flat vector style, "
        f"bright pastel colors, thick outline, centered on a plain white background, "
        f"no text, no letters, no watermark, kawaii mascot style."
    )


def build_avatar_prompt(speaker_name: str) -> str:
    return (
        f"A cute chibi avatar portrait of a friendly cartoon character named "
        f"'{speaker_name}'. Flat vector style, bright pastel colors, thick outline, "
        f"centered on a plain white background, no text, no letters, no watermark, "
        f"kawaii mascot style, head and shoulders only."
    )
```

- [ ] **Step 2: Thêm test vào `tests/visuals/test_prompt_builder.py`**

Thêm import ở đầu file: `from visuals.prompt_builder import build_avatar_prompt, build_image_prompt, build_mascot_prompt`

```python
def test_build_mascot_prompt_includes_icon_prompt_and_no_text_request():
    prompt = build_mascot_prompt("cute ice cube character")
    assert "cute ice cube character" in prompt
    assert "no text" in prompt


def test_build_avatar_prompt_includes_speaker_name_and_no_text_request():
    prompt = build_avatar_prompt("Minh")
    assert "Minh" in prompt
    assert "no text" in prompt
```

- [ ] **Step 3: Chạy test**

Run: `cd backend && pytest tests/visuals/test_prompt_builder.py -v`
Expected: 4 passed (2 cũ + 2 mới)

- [ ] **Step 4: Commit**

```bash
git add backend/visuals/prompt_builder.py backend/tests/visuals/test_prompt_builder.py
git commit -m "feat: add build_mascot_prompt and build_avatar_prompt"
```

---

### Task 6: `render/vocab_card.py`

**Files:**
- Create: `backend/render/vocab_card.py`
- Test: `backend/tests/render/test_vocab_card.py`

**Interfaces:**
- Consumes: `content.schema.VocabTopicResult` (Task 2), `render.theme.get_cjk_font/get_rounded_font/palette_color/make_white_transparent` (Task 1).
- Produces: `render.vocab_card.draw_vocab_card(result: VocabTopicResult, mascot_paths: list[str], size: tuple[int, int]) -> PIL.Image.Image`, `render.vocab_card.row_regions(size: tuple[int, int], n_items: int, has_header: bool) -> list[float]` (danh sách y-center dạng phân số 0..1, theo thứ tự từ trên xuống). Dùng bởi Task 10 (`pipeline.py`).

- [ ] **Step 1: Viết `render/vocab_card.py`**

```python
from PIL import Image, ImageDraw

from content.schema import VocabTopicResult
from render.theme import get_cjk_font, get_rounded_font, make_white_transparent, palette_color

MARGIN = 40
HEADER_HEIGHT = 220
ROW_SPACING = 16


def draw_vocab_card(
    result: VocabTopicResult, mascot_paths: list[str], size: tuple[int, int]
) -> Image.Image:
    if len(mascot_paths) != len(result.items):
        raise ValueError("mascot_paths must have one entry per item")
    if not result.items:
        raise ValueError("result.items must not be empty")

    width, height = size
    card = Image.new("RGB", size, color=(255, 250, 240))
    draw = ImageDraw.Draw(card)

    header_height = HEADER_HEIGHT if result.radical else 0
    if result.radical:
        _draw_header(draw, width, header_height, result)

    n = len(result.items)
    available_height = height - header_height - 2 * MARGIN
    row_height = (available_height - (n - 1) * ROW_SPACING) / n

    for index, (item, mascot_path) in enumerate(zip(result.items, mascot_paths)):
        y0 = header_height + MARGIN + index * (row_height + ROW_SPACING)
        _draw_row(card, draw, item, mascot_path, index, MARGIN, y0, width - 2 * MARGIN, row_height)

    return card


def row_regions(size: tuple[int, int], n_items: int, has_header: bool) -> list[float]:
    width, height = size
    header_height = HEADER_HEIGHT if has_header else 0
    available_height = height - header_height - 2 * MARGIN
    row_height = (available_height - (n_items - 1) * ROW_SPACING) / n_items
    centers = []
    for index in range(n_items):
        y0 = header_height + MARGIN + index * (row_height + ROW_SPACING)
        centers.append((y0 + row_height / 2) / height)
    return centers


def _draw_header(
    draw: ImageDraw.ImageDraw, width: int, header_height: int, result: VocabTopicResult
) -> None:
    draw.rectangle([0, 0, width, header_height], fill=(255, 224, 189))
    title_font = get_rounded_font(56, "Bold")
    subtitle_font = get_rounded_font(30, "Medium")
    draw.text((MARGIN, 40), f"部首：{result.radical}", fill=(60, 40, 40), font=title_font)
    subtitle = f"{result.radical_pinyin or ''}  {result.radical_meaning_vi or ''}".strip()
    draw.text((MARGIN, 120), subtitle, fill=(90, 60, 60), font=subtitle_font)


def _draw_row(
    card: Image.Image,
    draw: ImageDraw.ImageDraw,
    item,
    mascot_path: str,
    index: int,
    x0: float,
    y0: float,
    row_width: float,
    row_height: float,
) -> None:
    color = palette_color(index)
    draw.rounded_rectangle([x0, y0, x0 + row_width, y0 + row_height], radius=24, fill=color)

    badge_r = min(36, row_height / 2 - 8)
    badge_cx, badge_cy = x0 + 60, y0 + row_height / 2
    draw.ellipse(
        [badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r],
        fill=(255, 255, 255),
    )
    badge_font = get_rounded_font(int(badge_r), "Bold")
    draw.text((badge_cx, badge_cy), str(index + 1), fill=(50, 50, 50), font=badge_font, anchor="mm")

    hanzi_font = get_cjk_font(int(row_height * 0.5))
    pinyin_font = get_rounded_font(int(row_height * 0.2), "Bold")
    meaning_font = get_rounded_font(int(row_height * 0.18), "Medium")

    text_x = x0 + 130
    draw.text((text_x, y0 + row_height * 0.1), item.hanzi, fill=(30, 30, 30), font=hanzi_font)
    draw.text(
        (text_x, y0 + row_height * 0.62), item.pinyin or "", fill=(90, 60, 20), font=pinyin_font
    )
    draw.text(
        (text_x + 220, y0 + row_height * 0.62),
        item.meaning_vi,
        fill=(60, 60, 60),
        font=meaning_font,
    )

    mascot_size = int(row_height * 0.85)
    mascot = make_white_transparent(Image.open(mascot_path).convert("RGB"))
    mascot = mascot.resize((mascot_size, mascot_size))
    mascot_x = int(x0 + row_width - mascot_size - 20)
    mascot_y = int(y0 + (row_height - mascot_size) / 2)
    card.paste(mascot, (mascot_x, mascot_y), mascot)
```

- [ ] **Step 2: Viết test `tests/render/test_vocab_card.py`**

```python
import pytest
from PIL import Image

from content.schema import VocabCardItem, VocabTopicResult
from render.vocab_card import draw_vocab_card, row_regions


def _make_mascot(tmp_path, name, color=(255, 255, 255)):
    path = tmp_path / name
    Image.new("RGB", (200, 200), color=color).save(path)
    return str(path)


def test_draw_vocab_card_with_radical_returns_correct_size(tmp_path):
    result = VocabTopicResult(
        radical="冫",
        radical_pinyin="bīng",
        radical_meaning_vi="băng",
        items=[
            VocabCardItem(hanzi="冰", pinyin="bīng", meaning_vi="băng", icon_prompt="ice"),
            VocabCardItem(hanzi="冷", pinyin="lěng", meaning_vi="lạnh", icon_prompt="cold"),
        ],
    )
    mascots = [_make_mascot(tmp_path, "m1.png"), _make_mascot(tmp_path, "m2.png")]

    card = draw_vocab_card(result, mascots, size=(720, 1280))
    assert card.size == (720, 1280)


def test_draw_vocab_card_without_radical_skips_header(tmp_path):
    result = VocabTopicResult(items=[VocabCardItem(hanzi="吃", meaning_vi="ăn", icon_prompt="eating")])
    mascots = [_make_mascot(tmp_path, "m1.png")]

    card = draw_vocab_card(result, mascots, size=(720, 1280))
    assert card.size == (720, 1280)


def test_draw_vocab_card_rejects_mismatched_mascot_count(tmp_path):
    result = VocabTopicResult(items=[VocabCardItem(hanzi="吃", meaning_vi="ăn", icon_prompt="eating")])

    with pytest.raises(ValueError):
        draw_vocab_card(result, [], size=(720, 1280))


def test_row_regions_returns_n_increasing_centers_within_bounds():
    centers = row_regions(size=(720, 1280), n_items=5, has_header=True)
    assert len(centers) == 5
    assert all(0.0 <= c <= 1.0 for c in centers)
    assert centers == sorted(centers)


def test_row_regions_without_header_starts_higher_than_with_header():
    with_header = row_regions(size=(720, 1280), n_items=1, has_header=True)
    without_header = row_regions(size=(720, 1280), n_items=1, has_header=False)
    assert without_header[0] < with_header[0]
```

- [ ] **Step 3: Chạy test**

Run: `cd backend && pytest tests/render/test_vocab_card.py -v`
Expected: 5 passed

- [ ] **Step 4: Commit**

```bash
git add backend/render/vocab_card.py backend/tests/render/test_vocab_card.py
git commit -m "feat: add draw_vocab_card and row_regions"
```

---

### Task 7: `render/dialogue_card.py`

**Files:**
- Create: `backend/render/dialogue_card.py`
- Test: `backend/tests/render/test_dialogue_card.py`

**Interfaces:**
- Consumes: `content.schema.DialogueTurn` (Task 2), `render.theme.*` (Task 1).
- Produces: `render.dialogue_card.draw_dialogue_turn(turn: DialogueTurn, avatar_path: str, accent_index: int, size: tuple[int, int]) -> PIL.Image.Image`. Dùng bởi Task 10.

- [ ] **Step 1: Viết `render/dialogue_card.py`**

```python
from PIL import Image, ImageDraw

from content.schema import DialogueTurn
from render.theme import get_cjk_font, get_rounded_font, make_white_transparent, palette_color, wrap_text_to_width


def draw_dialogue_turn(
    turn: DialogueTurn, avatar_path: str, accent_index: int, size: tuple[int, int]
) -> Image.Image:
    width, height = size
    card = Image.new("RGB", size, color=_lighten(palette_color(accent_index)))
    draw = ImageDraw.Draw(card)

    avatar_size = int(width * 0.4)
    avatar = make_white_transparent(Image.open(avatar_path).convert("RGB"))
    avatar = avatar.resize((avatar_size, avatar_size))
    avatar_x = (width - avatar_size) // 2
    avatar_y = int(height * 0.08)
    card.paste(avatar, (avatar_x, avatar_y), avatar)

    name_font = get_rounded_font(44, "Bold")
    name_y = avatar_y + avatar_size + 20
    draw.text((width / 2, name_y), turn.speaker_name, fill=(50, 50, 50), font=name_font, anchor="ma")

    box_top = name_y + 90
    draw.rounded_rectangle([40, box_top, width - 40, height - 60], radius=32, fill=(255, 255, 255))

    hanzi_font = get_cjk_font(56)
    pinyin_font = get_rounded_font(34, "Bold")
    meaning_font = get_rounded_font(30, "Medium")
    max_text_width = width - 160

    text_y = box_top + 40
    text_y = _draw_wrapped(
        draw, turn.line.hanzi, hanzi_font, width / 2, text_y, max_text_width, (30, 30, 30), 68
    )
    text_y += 20
    text_y = _draw_wrapped(
        draw, turn.line.pinyin or "", pinyin_font, width / 2, text_y, max_text_width, (90, 60, 20), 42
    )
    text_y += 10
    _draw_wrapped(
        draw, turn.line.meaning_vi, meaning_font, width / 2, text_y, max_text_width, (70, 70, 70), 38
    )

    return card


def _draw_wrapped(draw, text, font, center_x, y, max_width, fill, line_height) -> float:
    for line in wrap_text_to_width(draw, text, font, max_width):
        draw.text((center_x, y), line, fill=fill, font=font, anchor="ma")
        y += line_height
    return y


def _lighten(color: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = color
    return (min(255, r + 20), min(255, g + 20), min(255, b + 20))
```

- [ ] **Step 2: Viết test `tests/render/test_dialogue_card.py`**

```python
from PIL import Image

from content.schema import DialogueTurn, LessonItem
from render.dialogue_card import draw_dialogue_turn


def _make_avatar(tmp_path):
    path = tmp_path / "avatar.png"
    Image.new("RGB", (200, 200), color=(255, 255, 255)).save(path)
    return str(path)


def test_draw_dialogue_turn_returns_correct_size(tmp_path):
    turn = DialogueTurn(
        speaker_name="Minh", line=LessonItem(hanzi="你好", pinyin="nǐ hǎo", meaning_vi="xin chào")
    )

    card = draw_dialogue_turn(turn, _make_avatar(tmp_path), accent_index=0, size=(720, 1280))
    assert card.size == (720, 1280)


def test_draw_dialogue_turn_wraps_long_hanzi_sentence_without_crashing(tmp_path):
    long_line = LessonItem(
        hanzi="随着生活水平的提高，人们越来越关心自己的健康了。",
        pinyin="Suízhe shēnghuó shuǐpíng de tígāo, rénmen yuèláiyuè guānxīn zìjǐ de jiànkāng le.",
        meaning_vi="Cùng với sự nâng cao mức sống, mọi người ngày càng quan tâm đến sức khỏe của mình.",
    )
    turn = DialogueTurn(speaker_name="Lan", line=long_line)

    card = draw_dialogue_turn(turn, _make_avatar(tmp_path), accent_index=1, size=(720, 1280))
    assert card.size == (720, 1280)


def test_draw_dialogue_turn_cycles_accent_color_by_index(tmp_path):
    turn = DialogueTurn(speaker_name="Minh", line=LessonItem(hanzi="嗨", meaning_vi="chào"))
    avatar = _make_avatar(tmp_path)

    card0 = draw_dialogue_turn(turn, avatar, accent_index=0, size=(720, 1280))
    card1 = draw_dialogue_turn(turn, avatar, accent_index=1, size=(720, 1280))
    assert card0.getpixel((10, 10)) != card1.getpixel((10, 10))
```

- [ ] **Step 3: Chạy test**

Run: `cd backend && pytest tests/render/test_dialogue_card.py -v`
Expected: 3 passed

- [ ] **Step 4: Commit**

```bash
git add backend/render/dialogue_card.py backend/tests/render/test_dialogue_card.py
git commit -m "feat: add draw_dialogue_turn"
```

---

### Task 8: `render/highlight.py`

**Files:**
- Create: `backend/render/highlight.py`
- Test: `backend/tests/render/test_highlight.py`

**Interfaces:**
- Produces: `render.highlight.make_highlight_clip(image_path: str, y_centers: list[float], durations: list[float], size: tuple[int, int], zoom_height_frac: float = 0.4) -> moviepy.VideoClip`. Dùng bởi Task 10.

- [ ] **Step 1: Viết `render/highlight.py`**

```python
import bisect

import numpy as np
from moviepy import VideoClip
from PIL import Image


def make_highlight_clip(
    image_path: str,
    y_centers: list[float],
    durations: list[float],
    size: tuple[int, int],
    zoom_height_frac: float = 0.4,
) -> VideoClip:
    if len(y_centers) != len(durations):
        raise ValueError("y_centers and durations must have the same length")
    if not y_centers:
        raise ValueError("y_centers must not be empty")

    target_w, target_h = size
    source = Image.open(image_path).convert("RGB")
    cover_scale = max(target_w / source.width, target_h / source.height)
    scaled = source.resize((int(source.width * cover_scale), int(source.height * cover_scale)))
    frame_w, frame_h = scaled.size

    crop_h = max(target_h, min(int(frame_h * zoom_height_frac), frame_h))
    crop_w = min(int(crop_h * target_w / target_h), frame_w)

    boundaries: list[float] = []
    running = 0.0
    for d in durations:
        running += d
        boundaries.append(running)
    total_duration = boundaries[-1]

    def make_frame(t: float) -> np.ndarray:
        clamped_t = min(t, max(total_duration - 1e-6, 0.0))
        row = min(bisect.bisect_right(boundaries, clamped_t), len(y_centers) - 1)
        y_center = int(frame_h * y_centers[row])

        x0 = (frame_w - crop_w) // 2
        y0 = max(0, min(frame_h - crop_h, y_center - crop_h // 2))
        cropped = scaled.crop((x0, y0, x0 + crop_w, y0 + crop_h))
        resized = cropped.resize((target_w, target_h))
        return np.array(resized)

    return VideoClip(make_frame, duration=total_duration)
```

- [ ] **Step 2: Viết test `tests/render/test_highlight.py`**

```python
import pytest
from PIL import Image

from render.highlight import make_highlight_clip


def _make_card(tmp_path, size=(720, 2000)):
    path = tmp_path / "card.png"
    Image.new("RGB", size, color=(50, 60, 70)).save(path)
    return str(path)


def test_make_highlight_clip_duration_matches_sum_of_durations(tmp_path):
    clip = make_highlight_clip(
        _make_card(tmp_path), y_centers=[0.1, 0.5, 0.9], durations=[1.0, 1.5, 2.0], size=(720, 1280)
    )
    assert abs(clip.duration - 4.5) < 0.01


def test_make_highlight_clip_frame_matches_target_size(tmp_path):
    clip = make_highlight_clip(_make_card(tmp_path), y_centers=[0.5], durations=[2.0], size=(720, 1280))
    frame = clip.get_frame(1.0)
    assert frame.shape == (1280, 720, 3)


def test_make_highlight_clip_rejects_mismatched_lengths(tmp_path):
    with pytest.raises(ValueError):
        make_highlight_clip(_make_card(tmp_path), y_centers=[0.1, 0.5], durations=[1.0], size=(720, 1280))


def test_make_highlight_clip_rejects_empty_regions(tmp_path):
    with pytest.raises(ValueError):
        make_highlight_clip(_make_card(tmp_path), y_centers=[], durations=[], size=(720, 1280))
```

- [ ] **Step 3: Chạy test**

Run: `cd backend && pytest tests/render/test_highlight.py -v`
Expected: 4 passed

- [ ] **Step 4: Commit**

```bash
git add backend/render/highlight.py backend/tests/render/test_highlight.py
git commit -m "feat: add make_highlight_clip for row-by-row zoom on a static card"
```

---

### Task 9: `render/assemble.py::build_static_scene_clip` + `audio/tts.py::make_silence`

**Files:**
- Modify: `backend/render/assemble.py`
- Modify: `backend/audio/tts.py`
- Test: `backend/tests/render/test_assemble.py`
- Test: `backend/tests/audio/test_tts.py`

**Interfaces:**
- Produces: `render.assemble.build_static_scene_clip(image_path: str, audio_paths: list[str], aspect_ratio: str) -> VideoClip` (Ken Burns + audio, không overlay text — dùng bởi Task 10 cho hội thoại). `audio.tts.make_silence(out_path: str, seconds: float) -> str` (dùng bởi Task 10 làm fallback khi TTS 1 dòng thất bại).

- [ ] **Step 1: Thêm `build_static_scene_clip` vào `render/assemble.py`**

Thêm vào cuối file (giữ nguyên `build_scene_clip` và `assemble_video` hiện có — sẽ đánh giá xóa `build_scene_clip` ở Task 13 sau khi Task 10-11 xác nhận không còn nơi nào gọi):

```python
def build_static_scene_clip(image_path: str, audio_paths: list[str], aspect_ratio: str) -> VideoClip:
    """Ken Burns pan over an already-fully-rendered card image (text baked in
    by the caller) plus its audio track — no per-frame text overlay.
    """
    size = ASPECT_SIZES[aspect_ratio]
    audio_clips = [AudioFileClip(p) for p in audio_paths]
    # concatenate_audioclips() reads from these clips lazily at write_videofile
    # time, so they must stay open — do not close them here (same caveat as
    # build_scene_clip above).
    scene_audio = concatenate_audioclips(audio_clips)
    duration = sum(clip.duration for clip in audio_clips)
    background = make_kenburns_clip(image_path, duration=duration, size=size)
    return background.with_audio(scene_audio)
```

- [ ] **Step 2: Thêm `make_silence` vào `audio/tts.py`**

Thêm import ở đầu file: `import subprocess`

Thêm hàm vào cuối file:

```python
def make_silence(out_path: str, seconds: float) -> str:
    """Generate a silent mp3 of the given duration, used as a fallback when
    TTS fails for a single row/turn so the video doesn't lose that slot.
    """
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(seconds), str(out_path),
        ],
        check=True, capture_output=True,
    )
    return str(out_path)
```

- [ ] **Step 3: Thêm test vào `tests/render/test_assemble.py`**

Thêm import: `from render.assemble import build_static_scene_clip` (bên cạnh import `build_scene_clip, assemble_video` đã có).

```python
def test_build_static_scene_clip_has_no_text_overlay(tmp_path):
    img_path = tmp_path / "card.png"
    Image.new("RGB", (720, 1280), color=(200, 100, 50)).save(img_path)
    audio1 = tmp_path / "a1.mp3"
    _make_silence(audio1, 1.5)

    scene = build_static_scene_clip(str(img_path), [str(audio1)], "9:16")
    assert abs(scene.duration - 1.5) < 0.05

    frame = scene.get_frame(0.1)
    # source is a flat solid color; Ken Burns only crops/resizes it, so if the
    # frame still matches exactly, no overlay shapes/text were drawn on top.
    assert tuple(frame[0, 0]) == (200, 100, 50)
```

- [ ] **Step 4: Thêm test vào `tests/audio/test_tts.py`**

File này dùng `from audio import tts` và gọi qua `tts.xxx(...)` (không import trực tiếp từng hàm) — thêm test theo đúng convention đó, vào cuối file, không cần thêm import mới:

```python
def test_make_silence_creates_file_with_requested_duration(tmp_path):
    out_path = tmp_path / "silence.mp3"
    tts.make_silence(str(out_path), seconds=1.5)
    assert out_path.exists()
    assert abs(tts.get_audio_duration(str(out_path)) - 1.5) < 0.1
```

- [ ] **Step 5: Chạy test**

Run: `cd backend && pytest tests/render/test_assemble.py tests/audio/test_tts.py -v`
Expected: tất cả pass (cần `ffmpeg` trên PATH)

- [ ] **Step 6: Commit**

```bash
git add backend/render/assemble.py backend/audio/tts.py backend/tests/render/test_assemble.py backend/tests/audio/test_tts.py
git commit -m "feat: add build_static_scene_clip and make_silence"
```

---

### Task 10: `pipeline.py` — `run_vocab_card_pipeline` và `run_dialogue_pipeline`

**Files:**
- Modify: `backend/pipeline.py`
- Test: `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: mọi interface từ Task 2 (schema), Task 3 (vocab_topic — chỉ dùng ở `app.py`, không dùng trực tiếp trong `pipeline.py`), Task 5 (`build_mascot_prompt`, `build_avatar_prompt`), Task 6 (`draw_vocab_card`, `row_regions`), Task 7 (`draw_dialogue_turn`), Task 8 (`make_highlight_clip`), Task 9 (`build_static_scene_clip`, `make_silence`), `content.pinyin.fill_pinyin_batch` (đã có), `audio.tts.synthesize/get_audio_duration/TTSError` (đã có), `visuals.image.generate_image` (đã có), `render.assemble.ASPECT_SIZES/assemble_video` (đã có).
- Produces: `pipeline.run_vocab_card_pipeline(result: VocabTopicResult, template: AudioTemplate, aspect_ratios: list[str], work_dir: str) -> PipelineResult`, `pipeline.run_dialogue_pipeline(result: DialogueResult, template: AudioTemplate, aspect_ratios: list[str], work_dir: str) -> PipelineResult`. Dùng bởi Task 11 (`app.py`).

- [ ] **Step 1: Thêm import vào đầu `pipeline.py`**

Giữ nguyên toàn bộ import + `ItemResult`/`PipelineResult`/`run_pipeline` hiện có. Thêm:

```python
from audio.tts import TTSError, get_audio_duration, make_silence, synthesize
from content.schema import DialogueResult, DialogueTurn, VocabCardItem, VocabTopicResult
from moviepy import AudioFileClip, concatenate_audioclips
from render.assemble import build_static_scene_clip
from render.dialogue_card import draw_dialogue_turn
from render.highlight import make_highlight_clip
from render.vocab_card import draw_vocab_card, row_regions
from visuals.prompt_builder import build_avatar_prompt, build_mascot_prompt
```

(Import `synthesize` đã có sẵn ở đầu file qua `from audio.tts import synthesize` — gộp vào 1 dòng import như trên, xóa dòng import cũ trùng lặp nếu có.)

- [ ] **Step 2: Thêm `run_vocab_card_pipeline` vào cuối `pipeline.py`**

```python
def run_vocab_card_pipeline(
    result: VocabTopicResult,
    template: AudioTemplate,
    aspect_ratios: list[str],
    work_dir: str,
) -> PipelineResult:
    filled_lines = fill_pinyin_batch(
        [LessonItem(hanzi=i.hanzi, pinyin=i.pinyin, meaning_vi=i.meaning_vi) for i in result.items]
    )
    items = [
        VocabCardItem(
            hanzi=line.hanzi, pinyin=line.pinyin, meaning_vi=line.meaning_vi, icon_prompt=orig.icon_prompt
        )
        for line, orig in zip(filled_lines, result.items)
    ]
    result = VocabTopicResult(
        radical=result.radical,
        radical_pinyin=result.radical_pinyin,
        radical_meaning_vi=result.radical_meaning_vi,
        items=items,
    )

    mascot_paths = [
        generate_image(build_mascot_prompt(item.icon_prompt), cache_dir=f"{work_dir}/mascots")
        for item in items
    ]

    row_durations: list[float] = []
    all_audio_paths: list[str] = []
    for index, item in enumerate(items):
        row_duration = 0.0
        for seg_index, segment in enumerate(template.segments):
            text = item.hanzi if segment.lang == "zh" else item.meaning_vi
            audio_path = f"{work_dir}/vocab_audio_{index}_{seg_index}.mp3"
            try:
                synthesize(text, segment.lang, audio_path)
            except TTSError:
                make_silence(audio_path, seconds=2.0)
            all_audio_paths.append(audio_path)
            row_duration += get_audio_duration(audio_path)
        row_durations.append(row_duration)

    has_header = result.radical is not None
    video_paths: dict[str, str] = {}
    assembly_errors: dict[str, str] = {}
    for ratio in aspect_ratios:
        size = ASPECT_SIZES[ratio]
        try:
            card = draw_vocab_card(result, mascot_paths, size)
            card_path = f"{work_dir}/vocab_card_{ratio.replace(':', 'x')}.png"
            card.save(card_path)
            y_centers = row_regions(size, len(items), has_header)
            clip = make_highlight_clip(card_path, y_centers, row_durations, size)
            audio_clips = [AudioFileClip(p) for p in all_audio_paths]
            clip = clip.with_audio(concatenate_audioclips(audio_clips))
            out_path = f"{work_dir}/output_{ratio.replace(':', 'x')}.mp4"
            try:
                clip.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
                video_paths[ratio] = out_path
            finally:
                clip.close()
        except Exception as exc:  # noqa: BLE001 - a bad ratio must not stop the others
            assembly_errors[ratio] = str(exc)

    return PipelineResult(video_paths=video_paths, item_errors=[], assembly_errors=assembly_errors)
```

Cần thêm import `ASPECT_SIZES` — đã có sẵn ở đầu file hiện tại qua `from render.assemble import assemble_video, build_scene_clip` — sửa dòng đó thành:

```python
from render.assemble import ASPECT_SIZES, assemble_video, build_scene_clip, build_static_scene_clip
```

(gộp với import đã thêm ở Step 1, xóa dòng `from render.assemble import build_static_scene_clip` riêng lẻ nếu trùng).

- [ ] **Step 3: Thêm `run_dialogue_pipeline` vào cuối `pipeline.py`**

```python
def run_dialogue_pipeline(
    result: DialogueResult,
    template: AudioTemplate,
    aspect_ratios: list[str],
    work_dir: str,
) -> PipelineResult:
    speaker_names = list(dict.fromkeys(turn.speaker_name for turn in result.turns))
    avatar_paths = {
        name: generate_image(build_avatar_prompt(name), cache_dir=f"{work_dir}/avatars")
        for name in speaker_names
    }

    scene_clips: dict[str, list] = {ratio: [] for ratio in aspect_ratios}
    item_errors: list[ItemResult] = []

    for index, turn in enumerate(result.turns):
        try:
            line = fill_pinyin_batch([turn.line])[0]
            audio_paths = []
            for seg_index, segment in enumerate(template.segments):
                text = line.hanzi if segment.lang == "zh" else line.meaning_vi
                audio_path = f"{work_dir}/dlg_audio_{index}_{seg_index}.mp3"
                synthesize(text, segment.lang, audio_path)
                audio_paths.append(audio_path)

            accent_index = speaker_names.index(turn.speaker_name)
            for ratio in aspect_ratios:
                size = ASPECT_SIZES[ratio]
                card = draw_dialogue_turn(
                    DialogueTurn(speaker_name=turn.speaker_name, line=line),
                    avatar_paths[turn.speaker_name],
                    accent_index,
                    size,
                )
                card_path = f"{work_dir}/dlg_card_{index}_{ratio.replace(':', 'x')}.png"
                card.save(card_path)
                clip = build_static_scene_clip(card_path, audio_paths, ratio)
                scene_clips[ratio].append(clip)
        except Exception as exc:  # noqa: BLE001 - one bad turn must not stop the batch
            item_errors.append(ItemResult(item=turn.line, error=str(exc)))

    video_paths: dict[str, str] = {}
    assembly_errors: dict[str, str] = {}
    for ratio, clips in scene_clips.items():
        if not clips:
            continue
        out_path = f"{work_dir}/output_{ratio.replace(':', 'x')}.mp4"
        try:
            assemble_video(clips, out_path)
            video_paths[ratio] = out_path
        except Exception as exc:  # noqa: BLE001
            assembly_errors[ratio] = str(exc)

    return PipelineResult(
        video_paths=video_paths, item_errors=item_errors, assembly_errors=assembly_errors
    )
```

- [ ] **Step 4: Viết test tích hợp `tests/test_pipeline.py`**

Test dùng ảnh mascot/avatar giả (PNG trắng đơn giản, không gọi HF thật) bằng cách monkeypatch `pipeline.generate_image`, và TTS thật (edge-tts, không cần key) để giữ test gần với hành vi thật nhất — theo đúng mẫu `tests/render/test_assemble.py` đã dùng ffmpeg thật.

```python
from PIL import Image

import pipeline as pipeline_module
from audio.templates import AudioTemplate, TemplateSegment
from content.schema import DialogueResult, DialogueTurn, LessonItem, VocabCardItem, VocabTopicResult
from pipeline import run_dialogue_pipeline, run_vocab_card_pipeline


def _fake_generate_image(prompt, cache_dir):
    from pathlib import Path

    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    path = Path(cache_dir) / f"{abs(hash(prompt))}.png"
    if not path.exists():
        Image.new("RGB", (200, 200), color=(255, 255, 255)).save(path)
    return str(path)


def test_run_vocab_card_pipeline_produces_valid_video(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_module, "generate_image", _fake_generate_image)

    result = VocabTopicResult(
        radical="冫",
        radical_pinyin="bīng",
        radical_meaning_vi="băng",
        items=[
            VocabCardItem(hanzi="冰", pinyin="bīng", meaning_vi="băng", icon_prompt="ice cube"),
            VocabCardItem(hanzi="冷", pinyin="lěng", meaning_vi="lạnh", icon_prompt="cold penguin"),
        ],
    )
    template = AudioTemplate(name="zh-vi", segments=[TemplateSegment(lang="zh", field="hanzi")])

    output = run_vocab_card_pipeline(result, template, ["9:16"], str(tmp_path))

    assert "9:16" in output.video_paths
    assert output.assembly_errors == {}
    from pathlib import Path

    assert Path(output.video_paths["9:16"]).exists()


def test_run_dialogue_pipeline_produces_valid_video(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_module, "generate_image", _fake_generate_image)

    result = DialogueResult(
        title="Chào hỏi",
        turns=[
            DialogueTurn(speaker_name="Minh", line=LessonItem(hanzi="你好", meaning_vi="xin chào")),
            DialogueTurn(speaker_name="Lan", line=LessonItem(hanzi="你好吗", meaning_vi="khỏe không")),
        ],
    )
    template = AudioTemplate(name="zh-vi", segments=[TemplateSegment(lang="zh", field="hanzi")])

    output = run_dialogue_pipeline(result, template, ["9:16"], str(tmp_path))

    assert "9:16" in output.video_paths
    assert output.item_errors == []
    from pathlib import Path

    assert Path(output.video_paths["9:16"]).exists()
```

- [ ] **Step 5: Chạy test**

Run: `cd backend && pytest tests/test_pipeline.py -v`
Expected: 2 passed (cần mạng thật cho edge-tts, `ffmpeg` trên PATH — giống điều kiện test tích hợp hiện có của dự án)

- [ ] **Step 6: Chạy lại toàn bộ suite để chắc chưa hỏng gì cũ**

Run: `cd backend && pytest -v`
Expected: chỉ còn các lỗi môi trường đã biết trước đó (nếu có), không có lỗi mới liên quan `pipeline.py`/`render/assemble.py`.

- [ ] **Step 7: Commit**

```bash
git add backend/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: add run_vocab_card_pipeline and run_dialogue_pipeline"
```

---

### Task 11: `app.py` — đổi UI sang 3 chế độ

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/tests/test_app.py`

**Interfaces:**
- Consumes: `content.vocab_topic.generate_vocab_topic` (Task 3), `content.dialogue_topic.generate_dialogue_topic` (Task 4), `pipeline.run_vocab_card_pipeline`/`run_dialogue_pipeline` (Task 10), `content.schema.VocabCardItem/VocabTopicResult` (Task 2).
- Produces: `app.generate_video(mode, csv_text, topic, template_name, aspect_ratios)` — giữ nguyên chữ ký hàm (không đổi `api_name="generate_video"`, frontend không cần đổi cách gọi API). `app.MODES: list[str]` (dùng ở Task 12 để đối chiếu giá trị mode với frontend).

- [ ] **Step 1: Viết lại toàn bộ `app.py`**

```python
import os
import tempfile
from pathlib import Path

import gradio as gr

from audio.templates import list_templates
from content.auto import groq_llm_call
from content.dialogue_topic import generate_dialogue_topic
from content.manual import parse_manual_input
from content.schema import VocabCardItem, VocabTopicResult
from content.vocab_topic import generate_vocab_topic
from pipeline import run_dialogue_pipeline, run_vocab_card_pipeline
from render.assemble import ASPECT_SIZES

TEMPLATES_DIR = Path(__file__).parent / "config" / "templates"

MODES = ["Nhập danh sách", "Từ vựng theo chủ đề", "Hội thoại theo chủ đề"]


def _load_templates():
    templates = list_templates(TEMPLATES_DIR)
    return {t.name: t for t in templates}


def generate_video(mode, csv_text, topic, template_name, aspect_ratios):
    """Entry point for both the Gradio UI and external API callers.

    Always returns a 3-tuple (video_9_16, video_16_9, log_text); any failure is
    reported in the log text instead of propagating a traceback to the caller.
    """
    try:
        templates = _load_templates()
        if template_name not in templates:
            valid = ", ".join(templates)
            return None, None, (
                f"Lỗi: template không hợp lệ '{template_name}'. Các template hợp lệ: {valid}."
            )
        template = templates[template_name]

        aspect_ratios = list(aspect_ratios or [])
        if not aspect_ratios:
            return None, None, (
                "Lỗi: chưa chọn tỉ lệ khung hình nào. "
                "Hãy chọn ít nhất một tỉ lệ (9:16 hoặc 16:9)."
            )
        invalid_ratios = [r for r in aspect_ratios if r not in ASPECT_SIZES]
        if invalid_ratios:
            valid = ", ".join(ASPECT_SIZES)
            return None, None, (
                f"Lỗi: tỉ lệ khung hình không hợp lệ: {', '.join(map(str, invalid_ratios))}. "
                f"Các tỉ lệ hợp lệ: {valid}."
            )

        if mode not in MODES:
            return None, None, f"Lỗi: chế độ nhập không hợp lệ '{mode}'."

        work_dir = tempfile.mkdtemp(prefix="zhvideo_")

        if mode == "Nhập danh sách":
            items, errors = parse_manual_input(csv_text)
            warnings = [f"Dòng {e.line_number}: {e.message}" for e in errors]
            if not items:
                message = "Không có mục hợp lệ để tạo video.\n" + "\n".join(warnings)
                return None, None, message
            vocab_result = VocabTopicResult(
                items=[
                    VocabCardItem(
                        hanzi=i.hanzi, pinyin=i.pinyin, meaning_vi=i.meaning_vi, icon_prompt=i.meaning_vi
                    )
                    for i in items
                ]
            )
            result = run_vocab_card_pipeline(vocab_result, template, aspect_ratios, work_dir)
            log_lines = list(warnings)

        elif mode == "Từ vựng theo chủ đề":
            if not topic.strip():
                return None, None, "Lỗi: chưa nhập chủ đề/bộ thủ."
            vocab_result = generate_vocab_topic(topic, groq_llm_call)
            result = run_vocab_card_pipeline(vocab_result, template, aspect_ratios, work_dir)
            log_lines = []

        else:  # "Hội thoại theo chủ đề"
            if not topic.strip():
                return None, None, "Lỗi: chưa nhập chủ đề."
            dialogue_result = generate_dialogue_topic(topic, groq_llm_call)
            result = run_dialogue_pipeline(dialogue_result, template, aspect_ratios, work_dir)
            log_lines = []

        log_lines += [f"Lỗi mục '{e.item.hanzi}': {e.error}" for e in result.item_errors]
        log_lines += [
            f"Lỗi dựng video ({ratio}): {msg}" for ratio, msg in result.assembly_errors.items()
        ]
        video_9_16 = result.video_paths.get("9:16")
        video_16_9 = result.video_paths.get("16:9")
        log_text = "\n".join(log_lines) if log_lines else "Hoàn tất, không có lỗi."
        return video_9_16, video_16_9, log_text
    except Exception as exc:  # noqa: BLE001 - public API must never leak a raw traceback
        return None, None, f"Lỗi: {exc}"


def build_app() -> gr.Blocks:
    templates = _load_templates()
    template_names = list(templates.keys())

    with gr.Blocks() as demo:
        gr.Markdown("# Tạo video dạy tiếng Trung song ngữ Việt-Trung")
        mode = gr.Radio(MODES, value=MODES[0], label="Chế độ nhập")
        csv_text = gr.Textbox(
            label="Danh sách CSV (hanzi,pinyin,meaning_vi)",
            placeholder="你好,nǐ hǎo,xin chào\n谢谢,xiè xie,cảm ơn",
            info="Mỗi dòng một mục, theo thứ tự hanzi,pinyin,meaning_vi (không cần dòng tiêu đề). "
            "Dùng cho \"Nhập danh sách\".",
            lines=8,
        )
        topic = gr.Textbox(
            label="Chủ đề / bộ thủ",
            placeholder="vd: đồ ăn, hoặc 冫 (bộ băng)",
            info="Dùng cho \"Từ vựng theo chủ đề\" và \"Hội thoại theo chủ đề\".",
        )
        template_name = gr.Dropdown(
            template_names, value=template_names[0], label="Template trình tự audio"
        )
        aspect_ratios = gr.CheckboxGroup(["9:16", "16:9"], value=["9:16"], label="Tỉ lệ khung hình")
        submit = gr.Button("Tạo video")
        video_9_16 = gr.Video(label="Video 9:16")
        video_16_9 = gr.Video(label="Video 16:9")
        log = gr.Textbox(label="Log", lines=6)

        submit.click(
            generate_video,
            inputs=[mode, csv_text, topic, template_name, aspect_ratios],
            outputs=[video_9_16, video_16_9, log],
            api_name="generate_video",
        )

    return demo


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    build_app().launch(server_name="0.0.0.0", server_port=port)
```

- [ ] **Step 2: Viết lại `tests/test_app.py`**

```python
import app as app_module
from app import _load_templates


def test_load_templates_includes_expected_names():
    templates = _load_templates()
    assert "zh-zh-vi" in templates
    assert "zh-vi-zh" in templates


def _valid_csv():
    return "hanzi,pinyin,meaning_vi\n吃,chī,ăn"


def test_generate_video_unknown_template_returns_error(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("run_vocab_card_pipeline must not be called for an unknown template")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "", "khong-ton-tai", ["9:16"]
    )
    assert video_9_16 is None
    assert video_16_9 is None
    assert log.startswith("Lỗi:")
    assert "khong-ton-tai" in log


def test_generate_video_empty_aspect_ratios_skips_generation(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("pipeline must not be called with no aspect ratio")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "", "zh-zh-vi", []
    )
    assert video_9_16 is None
    assert video_16_9 is None
    assert "tỉ lệ khung hình" in log


def test_generate_video_invalid_aspect_ratio_returns_error(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("pipeline must not be called for an invalid aspect ratio")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    _, _, log = app_module.generate_video("Nhập danh sách", _valid_csv(), "", "zh-zh-vi", ["4:3"])
    assert log.startswith("Lỗi:")
    assert "4:3" in log


def test_generate_video_unknown_mode_returns_error(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("no pipeline must be called for an unknown mode")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", unexpected)
    monkeypatch.setattr(app_module, "run_dialogue_pipeline", unexpected)
    _, _, log = app_module.generate_video("???", _valid_csv(), "", "zh-zh-vi", ["9:16"])
    assert log.startswith("Lỗi:")
    assert "???" in log


def test_generate_video_manual_mode_routes_to_vocab_card_pipeline(monkeypatch):
    from pipeline import PipelineResult

    calls = {"count": 0}

    def fake_pipeline(vocab_result, template, aspect_ratios, work_dir):
        calls["count"] += 1
        assert vocab_result.items[0].hanzi == "吃"
        return PipelineResult(video_paths={"9:16": "out.mp4"})

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", fake_pipeline)
    video_9_16, _, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "", "zh-zh-vi", ["9:16"]
    )
    assert calls["count"] == 1
    assert video_9_16 == "out.mp4"
    assert log == "Hoàn tất, không có lỗi."


def test_generate_video_vocab_topic_mode_requires_topic():
    _, _, log = app_module.generate_video("Từ vựng theo chủ đề", "", "", "zh-zh-vi", ["9:16"])
    assert log.startswith("Lỗi:")
    assert "chủ đề" in log


def test_generate_video_vocab_topic_mode_calls_generate_vocab_topic_and_pipeline(monkeypatch):
    from content.schema import VocabCardItem, VocabTopicResult
    from pipeline import PipelineResult

    def fake_generate_vocab_topic(topic, llm_call):
        assert topic == "bộ băng"
        return VocabTopicResult(items=[VocabCardItem(hanzi="冰", meaning_vi="băng", icon_prompt="ice")])

    def fake_pipeline(vocab_result, template, aspect_ratios, work_dir):
        return PipelineResult(video_paths={"9:16": "out.mp4"})

    monkeypatch.setattr(app_module, "generate_vocab_topic", fake_generate_vocab_topic)
    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", fake_pipeline)
    video_9_16, _, log = app_module.generate_video(
        "Từ vựng theo chủ đề", "", "bộ băng", "zh-zh-vi", ["9:16"]
    )
    assert video_9_16 == "out.mp4"
    assert log == "Hoàn tất, không có lỗi."


def test_generate_video_dialogue_topic_mode_requires_topic():
    _, _, log = app_module.generate_video("Hội thoại theo chủ đề", "", "", "zh-zh-vi", ["9:16"])
    assert log.startswith("Lỗi:")


def test_generate_video_dialogue_topic_mode_calls_generate_dialogue_topic_and_pipeline(monkeypatch):
    from content.schema import DialogueResult, DialogueTurn, LessonItem
    from pipeline import PipelineResult

    def fake_generate_dialogue_topic(topic, llm_call):
        assert topic == "chào hỏi"
        return DialogueResult(
            title="t", turns=[DialogueTurn(speaker_name="Minh", line=LessonItem(hanzi="你好", meaning_vi="chào"))]
        )

    def fake_pipeline(dialogue_result, template, aspect_ratios, work_dir):
        return PipelineResult(video_paths={"9:16": "out.mp4"})

    monkeypatch.setattr(app_module, "generate_dialogue_topic", fake_generate_dialogue_topic)
    monkeypatch.setattr(app_module, "run_dialogue_pipeline", fake_pipeline)
    video_9_16, _, log = app_module.generate_video(
        "Hội thoại theo chủ đề", "", "chào hỏi", "zh-zh-vi", ["9:16"]
    )
    assert video_9_16 == "out.mp4"


def test_generate_video_catches_pipeline_exception(monkeypatch):
    def exploding(*args, **kwargs):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(app_module, "run_vocab_card_pipeline", exploding)
    video_9_16, video_16_9, log = app_module.generate_video(
        "Nhập danh sách", _valid_csv(), "", "zh-zh-vi", ["9:16"]
    )
    assert video_9_16 is None
    assert video_16_9 is None
    assert log == "Lỗi: ffmpeg exploded"
```

- [ ] **Step 3: Chạy test**

Run: `cd backend && pytest tests/test_app.py -v`
Expected: 11 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app.py backend/tests/test_app.py
git commit -m "feat: wire 3 modes (nhập danh sách / vocab topic / dialogue topic) into app.py"
```

---

### Task 12: Frontend — cập nhật 3 chế độ

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/validation.js`
- Modify: `frontend/tests/validation.test.js`

**Interfaces:**
- Consumes: giá trị `mode` phải khớp CHÍNH XÁC với `app.MODES` ở Task 11: `"Nhập danh sách"`, `"Từ vựng theo chủ đề"`, `"Hội thoại theo chủ đề"`.

- [ ] **Step 1: Sửa `frontend/index.html`**

Thay khối `<fieldset>` chế độ nhập và label ô topic:

```html
    <fieldset>
      <legend>Chế độ nhập</legend>
      <label><input type="radio" name="mode" value="Nhập danh sách" checked> Nhập danh sách</label>
      <label><input type="radio" name="mode" value="Từ vựng theo chủ đề"> Từ vựng theo chủ đề</label>
      <label><input type="radio" name="mode" value="Hội thoại theo chủ đề"> Hội thoại theo chủ đề</label>
    </fieldset>

    <label for="csv-text">Danh sách CSV (hanzi,pinyin,meaning_vi)</label>
    <textarea id="csv-text" rows="8" placeholder="hanzi,pinyin,meaning_vi&#10;吃,chī,ăn"></textarea>

    <label for="topic">Chủ đề / bộ thủ</label>
    <input type="text" id="topic" placeholder="vd: đồ ăn, hoặc 冫 (bộ băng)">
```

- [ ] **Step 2: Sửa `frontend/js/validation.js`**

```javascript
const TOPIC_MODES = ["Từ vựng theo chủ đề", "Hội thoại theo chủ đề"];

export function validateForm(state) {
  if (state.mode === "Nhập danh sách") {
    if (!state.csvText || !state.csvText.trim()) {
      return { valid: false, error: "Vui lòng nhập danh sách CSV." };
    }
  } else if (TOPIC_MODES.includes(state.mode)) {
    if (!state.topic || !state.topic.trim()) {
      return { valid: false, error: "Vui lòng nhập chủ đề." };
    }
  } else {
    return { valid: false, error: `Chế độ không hợp lệ: ${state.mode}` };
  }

  if (!state.aspectRatios || state.aspectRatios.length === 0) {
    return { valid: false, error: "Vui lòng chọn ít nhất một tỉ lệ khung hình." };
  }

  return { valid: true, error: null };
}
```

- [ ] **Step 3: Sửa `frontend/tests/validation.test.js`**

```javascript
// frontend/tests/validation.test.js
import { test } from "node:test";
import assert from "node:assert/strict";
import { validateForm } from "../js/validation.js";

test("valid manual mode with csv text and aspect ratio", () => {
  const result = validateForm({ mode: "Nhập danh sách", csvText: "吃,chī,ăn", topic: "", aspectRatios: ["9:16"] });
  assert.equal(result.valid, true);
  assert.equal(result.error, null);
});

test("manual mode rejects empty csv text", () => {
  const result = validateForm({ mode: "Nhập danh sách", csvText: "   ", topic: "", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
  assert.match(result.error, /CSV/);
});

test("vocab topic mode rejects empty topic", () => {
  const result = validateForm({ mode: "Từ vựng theo chủ đề", csvText: "", topic: "  ", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
  assert.match(result.error, /chủ đề/i);
});

test("dialogue topic mode rejects empty topic", () => {
  const result = validateForm({ mode: "Hội thoại theo chủ đề", csvText: "", topic: "  ", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
  assert.match(result.error, /chủ đề/i);
});

test("vocab topic mode accepts a filled topic", () => {
  const result = validateForm({ mode: "Từ vựng theo chủ đề", csvText: "", topic: "đồ ăn", aspectRatios: ["9:16"] });
  assert.equal(result.valid, true);
});

test("rejects empty aspect ratios", () => {
  const result = validateForm({ mode: "Nhập danh sách", csvText: "吃,chī,ăn", topic: "", aspectRatios: [] });
  assert.equal(result.valid, false);
  assert.match(result.error, /tỉ lệ/i);
});

test("rejects unknown mode", () => {
  const result = validateForm({ mode: "???", csvText: "", topic: "", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
});
```

- [ ] **Step 4: Chạy test**

Run: `cd frontend && node --test`
Expected: tất cả pass. `validation.test.js` có 7 test (thay "auto mode rejects empty topic" bằng 2 test theo 2 mode chủ đề mới + 1 test "accepts a filled topic" mới); các file test khác không đổi.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/js/validation.js frontend/tests/validation.test.js
git commit -m "feat: update frontend for 3 modes (nhập danh sách / vocab topic / dialogue topic)"
```

---

### Task 13: Dọn code chết + cập nhật tài liệu + kiểm tra toàn bộ

**Files:**
- Modify: `backend/render/overlay.py` (xóa nếu xác nhận không còn nơi nào import)
- Modify: `backend/render/assemble.py` (xóa `build_scene_clip` nếu không còn dùng)
- Modify: `backend/pipeline.py` (xóa `run_pipeline` cũ nếu không còn dùng)
- Modify: `backend/visuals/prompt_builder.py` (xóa `build_image_prompt` nếu không còn dùng)
- Modify: `backend/README.md`
- Modify: `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md` (cập nhật kiến trúc theo hệ thống card mới, trỏ sang spec `2026-08-25-card-templates-design.md`)

- [ ] **Step 1: Xác nhận không còn nơi nào gọi các hàm cũ**

```bash
cd backend
grep -rn "run_pipeline\b" --include="*.py" .
grep -rn "build_scene_clip\b" --include="*.py" .
grep -rn "build_image_prompt\b" --include="*.py" .
grep -rn "overlay\." --include="*.py" . | grep -v "test_overlay.py"
```

Nếu mỗi lệnh trên chỉ còn ra kết quả trong file định nghĩa hàm đó và file test riêng của nó (`tests/render/test_overlay.py`, `tests/render/test_assemble.py::test_build_scene_clip_and_assemble`, `tests/visuals/test_prompt_builder.py::test_build_image_prompt_*`, `tests/test_pipeline.py` cũ nếu có) — an toàn để xóa ở bước sau. Nếu `app.py`/`pipeline.py` còn tham chiếu, DỪNG và báo cáo thay vì xóa nhầm.

- [ ] **Step 2: Xóa `run_pipeline` khỏi `pipeline.py` và test tương ứng**

Xóa hàm `run_pipeline` (toàn bộ định nghĩa) khỏi `pipeline.py`. Xóa import không còn dùng (`build_image_prompt` nếu chỉ được dùng bởi `run_pipeline`).

Trong `tests/test_pipeline.py` — file này vừa tạo ở Task 10, chỉ chứa test cho 2 pipeline mới, không có gì cần xóa ở đây (không có test cũ cho `run_pipeline` — nó nằm ở `tests/render/test_assemble.py` gián tiếp qua `build_scene_clip`, không test `run_pipeline` trực tiếp; xác nhận bằng `grep -rn "run_pipeline" tests/`).

- [ ] **Step 3: Xóa `build_scene_clip` khỏi `render/assemble.py`, xóa import `overlay` không còn dùng**

Xóa hàm `build_scene_clip` và dòng `from render.overlay import build_overlay_cues, draw_text_on_frame, total_duration` khỏi `render/assemble.py`.

Trong `tests/render/test_assemble.py`: xóa test `test_build_scene_clip_and_assemble` (không còn hàm để test), giữ nguyên `test_build_static_scene_clip_has_no_text_overlay` (Task 9) và helper `_make_silence`.

- [ ] **Step 4: Xóa `render/overlay.py` và `tests/render/test_overlay.py`**

```bash
git rm backend/render/overlay.py backend/tests/render/test_overlay.py
```

- [ ] **Step 5: Xóa `build_image_prompt` khỏi `visuals/prompt_builder.py`**

Xóa hàm `build_image_prompt`. Trong `tests/visuals/test_prompt_builder.py`, xóa 2 test cũ (`test_build_image_prompt_includes_hanzi_and_meaning`, `test_build_image_prompt_excludes_text_instruction`) và import `LessonItem`/`build_image_prompt` nếu không còn dùng.

- [ ] **Step 6: Chạy toàn bộ test suite**

Run: `cd backend && pytest -v`
Expected: tất cả pass (trừ các lỗi môi trường đã biết từ trước, không liên quan thay đổi này — nếu có lỗi mới, sửa trước khi tiếp tục).

Run: `cd frontend && node --test`
Expected: tất cả pass.

- [ ] **Step 7: Cập nhật `backend/README.md`**

Trong phần mô tả đầu file, đổi mô tả tính năng để phản ánh 3 chế độ mới (Nhập danh sách / Từ vựng theo chủ đề / Hội thoại theo chủ đề) và cơ chế "text do code vẽ, AI chỉ sinh mascot/avatar" thay vì "sinh ảnh AI qua Hugging Face Inference API" mô tả chung chung như hiện tại. Không đổi phần hướng dẫn deploy/biến môi trường (không đổi).

- [ ] **Step 8: Cập nhật `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md`**

Trong mục "Kiến trúc" và "Công nghệ chọn", thêm 1 dòng trỏ sang spec mới: "Từ 2026-08-25, hệ thống ảnh nền chuyển sang card thiết kế sẵn (chữ do code vẽ, AI chỉ sinh mascot/avatar) — xem chi tiết tại `docs/superpowers/specs/2026-08-25-card-templates-design.md`." Không cần viết lại toàn bộ mục — chỉ thêm ghi chú trỏ sang spec mới để người đọc sau này biết tài liệu nào là bản cập nhật nhất.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "chore: remove dead code (old Ken Burns overlay pipeline), update docs for card templates"
```

---

## Sau khi hoàn tất plan

Deploy lại backend (Cloud Build tự động build khi merge vào `main`) và Cloudflare Pages (tự động deploy khi merge `frontend/`). Test end-to-end thật trên production cho cả 3 chế độ (giống cách đã làm với các lần deploy trước) trước khi báo hoàn thành với người dùng — đặc biệt kiểm tra mascot/avatar compositing (nền trắng suốt) và video zoom-highlight thực tế trông có ổn không, vì đây là phần khó đánh giá chỉ qua code review.
