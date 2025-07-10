import pixie
from easy_pixie import draw_rect, Loc, choose_text_color, StyledString, draw_text, calculate_width, \
    draw_full, hex_to_color

from src.data.data_color_rand import Colors
from src.render.pixie.model import Renderer


class ColorCardRenderer(Renderer):
    """渲染色卡"""

    def __init__(self, color: Colors, hex_raw_text: str, rgb_raw_text: str, hsv_raw_text: str):
        self._color = color
        self._hex_raw_text = hex_raw_text
        self._rgb_raw_text = rgb_raw_text
        self._hsv_raw_text = hsv_raw_text

    def render(self) -> pixie.Image:
        img = pixie.Image(1664, 1050)
        draw_full(img, (0, 0, 0))

        paint_bg = pixie.Paint(pixie.SOLID_PAINT)
        paint_bg.color = hex_to_color(self._color.hex)
        draw_rect(img, paint_bg, Loc(32, 32, 1600, 986), 96)

        text_color = choose_text_color(paint_bg.color)
        title_raw_text = f"Color Collect - {self._color.pinyin}"

        title_text = StyledString(
            title_raw_text, 'H', 48, font_color=text_color, padding_bottom=52
        )
        name_text = StyledString(
            self._color.name, 'H', 144, font_color=text_color, padding_bottom=60
        )
        hex_text = StyledString(
            self._hex_raw_text, 'M', 72, font_color=text_color, padding_bottom=80
        )
        rgb_text = StyledString(
            self._rgb_raw_text, 'M', 72, font_color=text_color, padding_bottom=80
        )
        hsv_text = StyledString(
            self._hsv_raw_text, 'M', 72, font_color=text_color, padding_bottom=80
        )
        hex_tag = StyledString(
            "HEX", 'R', 48, font_color=text_color, padding_bottom=56
        )
        rgb_tag = StyledString(
            "RGB", 'R', 48, font_color=text_color, padding_bottom=56
        )
        hsv_tag = StyledString(
            "HSV", 'R', 48, font_color=text_color, padding_bottom=56
        )

        current_x, current_y = 144 + 32, 120 + 32
        current_y = draw_text(img, title_text, current_x, current_y)
        current_y = draw_text(img, name_text, current_x, current_y)
        draw_text(img, hex_text, current_x, current_y)
        current_y += 24
        current_y = draw_text(img, hex_tag, current_x + calculate_width(hex_text) + 32, current_y)
        draw_text(img, rgb_text, current_x, current_y)
        current_y += 24
        current_y = draw_text(img, rgb_tag, current_x + calculate_width(rgb_text) + 32, current_y)
        draw_text(img, hsv_text, current_x, current_y)
        current_y += 24
        draw_text(img, hsv_tag, current_x + calculate_width(hsv_text) + 32, current_y)

        return img
