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
