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
