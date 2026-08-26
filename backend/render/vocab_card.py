from PIL import Image, ImageDraw

from content.schema import VocabTopicResult
from render.theme import (
    ACCENT_CORAL as CORAL,
    ACCENT_RED as NUMBER_RED,
    CARD_BORDER as ROW_BORDER,
    CARD_FILL as ROW_FILL,
    PAGE_BG,
    TEXT_GRAY as MEANING_GRAY,
    TITLE_NAVY,
    draw_emoji,
    get_cjk_font,
    get_rounded_font,
    wrap_text_to_width,
)

# All chrome (header/footer/margins/spacing) is sized as a fraction of the
# card's HEIGHT, not fixed pixels — the same fractions used to tune the
# design at 1280px (9:16) must still leave room for 5 legible rows at 720px
# (16:9), or the header alone eats most of the shorter canvas.
_MARGIN_FRAC = 0.022
_HEADER_FRAC = 0.172
_FOOTER_FRAC = 0.047
_ROW_SPACING_FRAC = 0.011


def _metrics(size: tuple[int, int], n_items: int) -> dict:
    width, height = size
    margin = height * _MARGIN_FRAC
    header = height * _HEADER_FRAC
    footer = height * _FOOTER_FRAC
    row_spacing = height * _ROW_SPACING_FRAC
    available_height = height - header - footer - 2 * margin
    row_height = (available_height - (n_items - 1) * row_spacing) / n_items
    return {
        "width": width,
        "height": height,
        "margin": margin,
        "header": header,
        "footer": footer,
        "row_spacing": row_spacing,
        "row_height": row_height,
    }


def compute_row_height(size: tuple[int, int], n_items: int) -> float:
    return _metrics(size, n_items)["row_height"]


def row_regions(size: tuple[int, int], n_items: int) -> list[float]:
    m = _metrics(size, n_items)
    centers = []
    for index in range(n_items):
        y0 = m["header"] + m["margin"] + index * (m["row_height"] + m["row_spacing"])
        centers.append((y0 + m["row_height"] / 2) / m["height"])
    return centers


def draw_vocab_card(
    result: VocabTopicResult,
    image_paths: list[str],
    size: tuple[int, int],
    topic_label: str | None = None,
) -> Image.Image:
    if len(image_paths) != len(result.items):
        raise ValueError("image_paths must have one entry per item")
    if not result.items:
        raise ValueError("result.items must not be empty")

    n = len(result.items)
    m = _metrics(size, n)
    card = Image.new("RGB", size, color=PAGE_BG)
    draw = ImageDraw.Draw(card)

    _draw_header(card, draw, m, result, topic_label)

    for index, (item, image_path) in enumerate(zip(result.items, image_paths)):
        y0 = m["header"] + m["margin"] + index * (m["row_height"] + m["row_spacing"])
        _draw_row(
            card, draw, item, image_path, index, m["margin"], y0, m["width"] - 2 * m["margin"], m["row_height"]
        )

    _draw_footer(card, m)

    return card


def _draw_header(
    card: Image.Image,
    draw: ImageDraw.ImageDraw,
    m: dict,
    result: VocabTopicResult,
    topic_label: str | None,
) -> None:
    height = m["height"]
    center_x = m["width"] / 2
    title_size = max(20, int(height * 0.036))
    title_font = get_rounded_font(title_size, "ExtraBold")
    sun_size = int(height * 0.042)
    star_size = int(height * 0.036)

    draw_emoji(card, (int(m["margin"]), int(height * 0.014)), "☀️", sun_size)
    draw_emoji(card, (int(m["width"] - m["margin"] - star_size), int(height * 0.019)), "⭐", star_size)

    title_y1 = height * 0.023
    title_y2 = height * 0.066
    stroke_w = max(2, int(height * 0.0047))
    draw.text(
        (center_x, title_y1),
        "TỪ VỰNG",
        font=title_font,
        fill=TITLE_NAVY,
        stroke_width=stroke_w,
        stroke_fill=(255, 255, 255),
        anchor="ma",
    )
    draw.text(
        (center_x, title_y2),
        "TIẾNG TRUNG",
        font=title_font,
        fill=TITLE_NAVY,
        stroke_width=stroke_w,
        stroke_fill=(255, 255, 255),
        anchor="ma",
    )

    subtitle_size = max(14, int(height * 0.02))
    subtitle_font = get_rounded_font(subtitle_size, "Bold")
    # Baloo 2 (the rounded UI font) has no CJK glyphs — a bare radical
    # character drawn with it renders as a blank "tofu" box. Split the label
    # into runs so the radical itself is drawn with the CJK font while the
    # surrounding Vietnamese text keeps the rounded font.
    if result.radical:
        cjk_font = get_cjk_font(subtitle_size)
        segments = [("Bộ thủ: ", subtitle_font), (result.radical, cjk_font)]
        if result.radical_meaning_vi:
            segments.append((f" ({result.radical_meaning_vi})", subtitle_font))
    elif topic_label:
        segments = [(f"Chủ đề: {topic_label}", subtitle_font)]
    else:
        segments = [("Học từ vựng mỗi ngày", subtitle_font)]

    total_w = sum(draw.textlength(text, font=font) for text, font in segments)
    pill_h = height * 0.0375
    pill_w = total_w + pill_h * 1.2
    pill_x0 = center_x - pill_w / 2
    pill_y0 = height * 0.119
    draw.rounded_rectangle(
        [pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h], radius=pill_h / 2, fill=CORAL
    )
    x = center_x - total_w / 2
    text_y = pill_y0 + pill_h / 2
    for text, font in segments:
        draw.text((x, text_y), text, font=font, fill=(255, 255, 255), anchor="lm")
        x += draw.textlength(text, font=font)


def _draw_footer(card: Image.Image, m: dict) -> None:
    height = m["height"]
    width = m["width"]
    y = height - m["footer"] + height * 0.0047
    icon_size = max(12, int(height * 0.031))
    icons = ["⏰", "⭐", "\U0001F4D6", "✏️", "⭐", "☕"]
    gap = (width - 2 * m["margin"] - len(icons) * icon_size) / (len(icons) - 1)
    x = m["margin"]
    for icon in icons:
        draw_emoji(card, (int(x), int(y)), icon, icon_size)
        x += icon_size + gap


def _draw_row(
    card: Image.Image,
    draw: ImageDraw.ImageDraw,
    item,
    image_path: str,
    index: int,
    x0: float,
    y0: float,
    row_width: float,
    row_height: float,
) -> None:
    border_w = max(2, int(row_height * 0.017))
    draw.rounded_rectangle(
        [x0, y0, x0 + row_width, y0 + row_height],
        radius=row_height * 0.13,
        outline=ROW_BORDER,
        width=border_w,
        fill=ROW_FILL,
    )

    badge_r = row_height * 0.155
    badge_cx, badge_cy = x0 + badge_r + row_height * 0.035, y0 + badge_r + row_height * 0.035
    draw.ellipse(
        [badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r],
        fill=NUMBER_RED,
    )
    badge_font = get_rounded_font(max(10, int(badge_r * 1.05)), "Bold")
    draw.text((badge_cx, badge_cy), str(index + 1), fill=(255, 255, 255), font=badge_font, anchor="mm")

    image_h = row_height - row_height * 0.12
    image_w = image_h * 1.15
    image_x0 = x0 + row_height * 0.12
    image_y0 = y0 + (row_height - image_h) / 2
    scene = Image.open(image_path).convert("RGB").resize((int(image_w), int(image_h)))
    mask = Image.new("L", scene.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, scene.size[0], scene.size[1]], radius=row_height * 0.09, fill=255
    )
    card.paste(scene, (int(image_x0), int(image_y0)), mask)

    text_x = image_x0 + image_w + row_height * 0.12
    text_right = x0 + row_width - row_height * 0.1
    text_col_width = max(20, text_right - text_x)

    hanzi_font = get_cjk_font(max(10, int(row_height * 0.38)))
    pinyin_size = max(8, int(row_height * 0.17))
    meaning_size = max(8, int(row_height * 0.15))
    pinyin_font = get_rounded_font(pinyin_size, "Bold")
    meaning_font = get_rounded_font(meaning_size, "Medium")

    hanzi_y = y0 + row_height * 0.08
    draw.text((text_x, hanzi_y), item.hanzi, fill=(20, 20, 20), font=hanzi_font)

    bottom_limit = y0 + row_height - row_height * 0.03
    py = hanzi_y + hanzi_font.size * 1.1
    for line in wrap_text_to_width(draw, item.pinyin or "", pinyin_font, text_col_width):
        if py + pinyin_size > bottom_limit:
            break
        draw.text((text_x, py), line, fill=CORAL, font=pinyin_font)
        py += pinyin_size * 1.15

    my = py + row_height * 0.01
    for line in wrap_text_to_width(draw, item.meaning_vi, meaning_font, text_col_width):
        if my + meaning_size > bottom_limit:
            break
        draw.text((text_x, my), line, fill=MEANING_GRAY, font=meaning_font)
        my += meaning_size * 1.15
