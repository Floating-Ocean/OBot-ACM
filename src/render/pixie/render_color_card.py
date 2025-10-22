import pixie
from easy_pixie import draw_rect, Loc, choose_text_color, StyledString, draw_text, calculate_width, \
    draw_full, hex_to_color

from src.data.data_color_rand import Colors
from src.render.pixie.model import Renderer

COLOR_QRCODE_COORD = (1215, 618)

_CONTENT_WIDTH = 1664
_CONTENT_HEIGHT = 1050
_CONTAINER_PADDING = 32
_SIDE_PADDING_HORIZONTAL = 144
_SIDE_PADDING_VERTICAL = 120


class ColorCardRenderer(Renderer):
    """渲染色卡"""

    def __init__(self, color: Colors, hex_raw_text: str, rgb_raw_text: str, hsv_raw_text: str):
        self._color = color
        self._hex_raw_text = hex_raw_text
        self._rgb_raw_text = rgb_raw_text
        self._hsv_raw_text = hsv_raw_text

        text_color = choose_text_color(hex_to_color(self._color.color))
        title_raw_text = f"Color Collect - {self._color.id}"
        self.str_title = StyledString(
            title_raw_text, 'H', 48, font_color=text_color, padding_bottom=52
        )
        self.str_name = StyledString(
            self._color.name, 'H', 144, font_color=text_color, padding_bottom=60
        )
        self.str_hex = StyledString(
            self._hex_raw_text, 'M', 72, font_color=text_color, padding_bottom=80
        )
        self.str_rgb = StyledString(
            self._rgb_raw_text, 'M', 72, font_color=text_color, padding_bottom=80
        )
        self.str_hsv = StyledString(
            self._hsv_raw_text, 'M', 72, font_color=text_color, padding_bottom=80
        )
        self.str_hex_tag = StyledString(
            "HEX", 'R', 48, font_color=text_color, padding_bottom=56
        )
        self.str_rgb_tag = StyledString(
            "RGB", 'R', 48, font_color=text_color, padding_bottom=56
        )
        self.str_hsv_tag = StyledString(
            "HSV", 'R', 48, font_color=text_color, padding_bottom=56
        )

    def render(self) -> pixie.Image:
        img = pixie.Image(_CONTENT_WIDTH, _CONTENT_HEIGHT)
        draw_full(img, (0, 0, 0))

        paint_bg = pixie.Paint(pixie.SOLID_PAINT)
        paint_bg.color = hex_to_color(self._color.color)
        background_loc = Loc(_CONTAINER_PADDING, _CONTAINER_PADDING,
                             _CONTENT_WIDTH - _CONTAINER_PADDING * 2,
                             _CONTENT_HEIGHT - _CONTAINER_PADDING * 2)
        draw_rect(img, paint_bg, background_loc, 96)

        current_x = _CONTAINER_PADDING + _SIDE_PADDING_HORIZONTAL
        current_y = _CONTAINER_PADDING + _SIDE_PADDING_VERTICAL
        current_y = draw_text(img, self.str_title, current_x, current_y)
        current_y = draw_text(img, self.str_name, current_x, current_y)
        draw_text(img, self.str_hex, current_x, current_y)
        current_y += 24
        current_y = draw_text(img, self.str_hex_tag,
                              current_x + calculate_width(self.str_hex) + 32, current_y)
        draw_text(img, self.str_rgb, current_x, current_y)
        current_y += 24
        current_y = draw_text(img, self.str_rgb_tag,
                              current_x + calculate_width(self.str_rgb) + 32, current_y)
        draw_text(img, self.str_hsv, current_x, current_y)
        current_y += 24
        draw_text(img, self.str_hsv_tag,
                  current_x + calculate_width(self.str_hsv) + 32, current_y)

        return img
