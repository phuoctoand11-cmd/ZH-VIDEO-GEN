from PIL import Image, ImageDraw

from content.schema import DialogueTurn
from render.theme import (
    ACCENT_CORAL,
    CARD_BORDER,
    CARD_FILL,
    PAGE_BG,
    TEXT_GRAY,
    TITLE_NAVY,
    get_cjk_font,
    get_rounded_font,
    wrap_text_to_width,
)


def draw_dialogue_turn(turn: DialogueTurn, avatar_path: str, size: tuple[int, int]) -> Image.Image:
    width, height = size
    card = Image.new("RGB", size, color=PAGE_BG)
    draw = ImageDraw.Draw(card)

    if height >= width:
        box = _draw_portrait_avatar_and_name(card, draw, turn, avatar_path, width, height)
    else:
        box = _draw_landscape_avatar_and_name(card, draw, turn, avatar_path, width, height)

    box_left, box_top, box_right, box_bottom = box
    border_w = max(2, int((box_bottom - box_top) * 0.012))
    draw.rounded_rectangle(
        [box_left, box_top, box_right, box_bottom],
        radius=32,
        outline=CARD_BORDER,
        width=border_w,
        fill=CARD_FILL,
    )

    max_text_width = box_right - box_left - 80
    hanzi_font = get_cjk_font(56)
    pinyin_font = get_rounded_font(34, "Bold")
    meaning_font = get_rounded_font(30, "Medium")
    text_center_x = (box_left + box_right) / 2

    text_y = box_top + 40
    text_y = _draw_wrapped(
        draw, turn.line.hanzi, hanzi_font, text_center_x, text_y, max_text_width, (20, 20, 20), 68
    )
    text_y += 20
    text_y = _draw_wrapped(
        draw, turn.line.pinyin or "", pinyin_font, text_center_x, text_y, max_text_width, ACCENT_CORAL, 42
    )
    text_y += 10
    _draw_wrapped(
        draw, turn.line.meaning_vi, meaning_font, text_center_x, text_y, max_text_width, TEXT_GRAY, 38
    )

    return card


def _draw_rounded_avatar(card: Image.Image, avatar_path: str, xy: tuple[int, int], avatar_size: int) -> None:
    avatar = Image.open(avatar_path).convert("RGB").resize((avatar_size, avatar_size))
    mask = Image.new("L", avatar.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, *avatar.size], radius=avatar_size * 0.14, fill=255)
    card.paste(avatar, xy, mask)


def _draw_portrait_avatar_and_name(
    card: Image.Image, draw: ImageDraw.ImageDraw, turn: DialogueTurn, avatar_path: str, width: int, height: int
) -> tuple[int, int, int, int]:
    """Avatar top-center -> name below -> bordered text box filling the rest
    of the height. This is the original portrait layout, unchanged.
    """
    avatar_size = int(width * 0.4)
    avatar_x = (width - avatar_size) // 2
    avatar_y = int(height * 0.08)
    _draw_rounded_avatar(card, avatar_path, (avatar_x, avatar_y), avatar_size)

    name_font = get_rounded_font(44, "Bold")
    name_y = avatar_y + avatar_size + 20
    draw.text((width / 2, name_y), turn.speaker_name, fill=TITLE_NAVY, font=name_font, anchor="ma")

    box_top = name_y + 90
    return (40, box_top, width - 40, height - 60)


def _draw_landscape_avatar_and_name(
    card: Image.Image, draw: ImageDraw.ImageDraw, turn: DialogueTurn, avatar_path: str, width: int, height: int
) -> tuple[int, int, int, int]:
    """Side-by-side layout: avatar + name in a left column sized off
    `height` (so it never overflows vertically at wide aspect ratios), text
    box occupying the remaining right region.
    """
    left_col_width = int(width * 0.32)
    avatar_size = min(int(left_col_width * 0.85), int(height * 0.55))
    avatar_x = (left_col_width - avatar_size) // 2
    avatar_y = int(height * 0.12)
    _draw_rounded_avatar(card, avatar_path, (avatar_x, avatar_y), avatar_size)

    name_font = get_rounded_font(40, "Bold")
    name_y = avatar_y + avatar_size + 20
    draw.text(
        (left_col_width / 2, name_y), turn.speaker_name, fill=TITLE_NAVY, font=name_font, anchor="ma"
    )

    return (left_col_width + 20, 40, width - 40, height - 40)


def _draw_wrapped(draw, text, font, center_x, y, max_width, fill, line_height) -> float:
    for line in wrap_text_to_width(draw, text, font, max_width):
        draw.text((center_x, y), line, fill=fill, font=font, anchor="ma")
        y += line_height
    return y
