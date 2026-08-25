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
