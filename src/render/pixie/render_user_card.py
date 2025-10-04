import pixie
from easy_pixie import draw_gradient_rect, GradientColor, Loc, GradientDirection, draw_mask_rect, darken_color, \
    draw_img, StyledString, draw_text, hex_to_color, draw_full

from src.platform.model import CompetitivePlatform
from src.render.pixie.model import Renderer

_CONTENT_WIDTH = 1664
_CONTENT_HEIGHT = 1050
_CONTAINER_PADDING = 32
_SIDE_PADDING_HORIZONTAL = 144
_SIDE_PADDING_VERTICAL = 120


class UserCardRenderer(Renderer):
    """渲染用户基础信息卡片"""

    def __init__(self, handle: str, social: str, rank: str, rank_alias: str, rating: int | str,
                 platform: type[CompetitivePlatform]):
        self._handle = handle
        self._social = social
        self._rank = rank
        self._rank_alias = rank_alias
        self._rating = rating
        self._platform = platform
        self._rk_color = self._platform.rks_color[self._rank_alias]

        text_color = darken_color(hex_to_color(self._rk_color), 0.2)
        self.str_pf = StyledString(
            f"{self._platform.platform_name} ID", 'H', 44,
            font_color=text_color, padding_bottom=30
        )
        self.str_handle = StyledString(
            self._handle, 'H', 96, font_color=text_color, padding_bottom=20
        )
        self.str_social = StyledString(
            self._social, 'B', 28, font_color=text_color, padding_bottom=112
        )
        self.str_rank = StyledString(
            self._rank, 'H', 44, font_color=text_color, padding_bottom=-6
        )
        self.str_rating = StyledString(
            f"{self._rating}", 'H', 256, font_color=text_color, padding_bottom=44
        )
        self.img_platform = self.load_img_resource(self._platform.platform_name, text_color)

    def render(self) -> pixie.Image:
        img = pixie.Image(_CONTENT_WIDTH, _CONTENT_HEIGHT)
        draw_full(img, (0, 0, 0))

        background_loc = Loc(_CONTAINER_PADDING, _CONTAINER_PADDING,
                             _CONTENT_WIDTH - _CONTAINER_PADDING * 2,
                             _CONTENT_HEIGHT - _CONTAINER_PADDING * 2)
        draw_gradient_rect(img, background_loc,
                           GradientColor(["#fcfcfc", self._rk_color], [0.0, 1.0], ''),
                           GradientDirection.DIAGONAL_LEFT_TO_RIGHT, 96)
        draw_mask_rect(img, background_loc, (255, 255, 255, 152), 96)

        current_x = _CONTAINER_PADDING + _SIDE_PADDING_HORIZONTAL
        current_y = _CONTAINER_PADDING + _SIDE_PADDING_VERTICAL
        draw_img(img, self.img_platform, Loc(current_x, current_y + 6, 48, 48))

        current_y = draw_text(img, self.str_pf, current_x + 48 + 18, current_y)
        current_y = draw_text(img, self.str_handle, current_x, current_y)
        current_y = draw_text(img, self.str_social, current_x, current_y)
        current_y = draw_text(img, self.str_rank, current_x, current_y)
        draw_text(img, self.str_rating, current_x - 10, current_y)

        return img
