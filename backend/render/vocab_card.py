from PIL import Image, ImageDraw

from content.schema import VocabTopicResult
from render.theme import (
    get_cjk_font,
    get_rounded_font,
    make_white_transparent,
    palette_color,
    wrap_text_to_width,
)

MARGIN = 40
HEADER_HEIGHT = 220
ROW_SPACING = 16


def compute_row_height(size: tuple[int, int], n_items: int, has_header: bool) -> float:
    _width, height = size
    header_height = HEADER_HEIGHT if has_header else 0
    available_height = height - header_height - 2 * MARGIN
    return (available_height - (n_items - 1) * ROW_SPACING) / n_items


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
    row_height = compute_row_height(size, n, bool(result.radical))

    for index, (item, mascot_path) in enumerate(zip(result.items, mascot_paths)):
        y0 = header_height + MARGIN + index * (row_height + ROW_SPACING)
        _draw_row(card, draw, item, mascot_path, index, MARGIN, y0, width - 2 * MARGIN, row_height)

    return card


def row_regions(size: tuple[int, int], n_items: int, has_header: bool) -> list[float]:
    _width, height = size
    header_height = HEADER_HEIGHT if has_header else 0
    row_height = compute_row_height(size, n_items, has_header)
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

    hanzi_font = get_cjk_font(int(row_height * 0.42))
    pinyin_size = int(row_height * 0.16)
    meaning_size = int(row_height * 0.15)
    pinyin_font = get_rounded_font(pinyin_size, "Bold")
    meaning_font = get_rounded_font(meaning_size, "Medium")

    text_x = x0 + 130
    hanzi_y = y0 + row_height * 0.06
    draw.text((text_x, hanzi_y), item.hanzi, fill=(30, 30, 30), font=hanzi_font)

    mascot_size = int(row_height * 0.85)
    mascot_x = int(x0 + row_width - mascot_size - 20)
    bottom_limit = y0 + row_height - 6
    # pinyin and meaning_vi stack vertically (not side by side) so both get
    # the card's full text-column width — an LLM-generated meaning can run
    # longer than a single word (e.g. "cơm, bữa ăn"), and a narrow side-by-
    # side column cuts even short text off or, for a word with no spaces
    # (e.g. "nước"), forces a per-character wrap that mangles it.
    text_col_width = max(20, mascot_x - text_x - 10)

    py = hanzi_y + hanzi_font.size * 1.15
    for line in wrap_text_to_width(draw, item.pinyin or "", pinyin_font, text_col_width):
        if py + pinyin_size > bottom_limit:
            break
        draw.text((text_x, py), line, fill=(90, 60, 20), font=pinyin_font)
        py += pinyin_size * 1.15

    my = py + 4
    for line in wrap_text_to_width(draw, item.meaning_vi, meaning_font, text_col_width):
        if my + meaning_size > bottom_limit:
            break
        draw.text((text_x, my), line, fill=(60, 60, 60), font=meaning_font)
        my += meaning_size * 1.15

    mascot = make_white_transparent(Image.open(mascot_path).convert("RGB"))
    mascot = mascot.resize((mascot_size, mascot_size))
    mascot_y = int(y0 + (row_height - mascot_size) / 2)
    card.paste(mascot, (mascot_x, mascot_y), mascot)
