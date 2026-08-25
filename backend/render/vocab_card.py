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
