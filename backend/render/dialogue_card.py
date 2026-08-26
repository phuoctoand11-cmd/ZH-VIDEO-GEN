from PIL import Image, ImageDraw

from content.schema import DialogueTurn
from render.theme import get_cjk_font, get_rounded_font, make_white_transparent, palette_color, wrap_text_to_width


def draw_dialogue_turn(
    turn: DialogueTurn, avatar_path: str, accent_index: int, size: tuple[int, int]
) -> Image.Image:
    width, height = size
    card = Image.new("RGB", size, color=_lighten(palette_color(accent_index)))
    draw = ImageDraw.Draw(card)

    if height >= width:
        box = _draw_portrait_avatar_and_name(card, draw, turn, avatar_path, width, height)
    else:
        box = _draw_landscape_avatar_and_name(card, draw, turn, avatar_path, width, height)

    box_left, box_top, box_right, box_bottom = box
    draw.rounded_rectangle([box_left, box_top, box_right, box_bottom], radius=32, fill=(255, 255, 255))

    max_text_width = box_right - box_left - 80
    hanzi_font = get_cjk_font(56)
    pinyin_font = get_rounded_font(34, "Bold")
    meaning_font = get_rounded_font(30, "Medium")
    text_center_x = (box_left + box_right) / 2

    text_y = box_top + 40
    text_y = _draw_wrapped(
        draw, turn.line.hanzi, hanzi_font, text_center_x, text_y, max_text_width, (30, 30, 30), 68
    )
    text_y += 20
    text_y = _draw_wrapped(
        draw, turn.line.pinyin or "", pinyin_font, text_center_x, text_y, max_text_width, (90, 60, 20), 42
    )
    text_y += 10
    _draw_wrapped(
        draw, turn.line.meaning_vi, meaning_font, text_center_x, text_y, max_text_width, (70, 70, 70), 38
    )

    return card


def _draw_portrait_avatar_and_name(
    card: Image.Image, draw: ImageDraw.ImageDraw, turn: DialogueTurn, avatar_path: str, width: int, height: int
) -> tuple[int, int, int, int]:
    """Avatar top-center -> name below -> white text box filling the rest of
    the height. This is the original portrait layout, unchanged.
    """
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
    avatar = make_white_transparent(Image.open(avatar_path).convert("RGB"))
    avatar = avatar.resize((avatar_size, avatar_size))
    avatar_x = (left_col_width - avatar_size) // 2
    avatar_y = int(height * 0.12)
    card.paste(avatar, (avatar_x, avatar_y), avatar)

    name_font = get_rounded_font(40, "Bold")
    name_y = avatar_y + avatar_size + 20
    draw.text(
        (left_col_width / 2, name_y), turn.speaker_name, fill=(50, 50, 50), font=name_font, anchor="ma"
    )

    return (left_col_width + 20, 40, width - 40, height - 40)


def _draw_wrapped(draw, text, font, center_x, y, max_width, fill, line_height) -> float:
    for line in wrap_text_to_width(draw, text, font, max_width):
        draw.text((center_x, y), line, fill=fill, font=font, anchor="ma")
        y += line_height
    return y


def _lighten(color: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = color
    return (min(255, r + 20), min(255, g + 20), min(255, b + 20))
