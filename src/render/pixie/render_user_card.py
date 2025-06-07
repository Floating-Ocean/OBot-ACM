import pixie
from easy_pixie import draw_gradient_rect, GradientColor, Loc, GradientDirection, draw_mask_rect, darken_color, \
    draw_img, StyledString, draw_text, tuple_to_color, hex_to_color

from src.platform.model import CompetitivePlatform
from src.render.pixie.model import Renderer


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

    def render(self) -> pixie.Image:
        img = pixie.Image(1664, 1040)
        img.fill(tuple_to_color((0, 0, 0)))

        rk_color = self._platform.rks_color[self._rank_alias]
        draw_gradient_rect(img, Loc(32, 32, 1600, 976),
                           GradientColor(["#fcfcfc", rk_color], [0.0, 1.0], ''),
                           GradientDirection.DIAGONAL_LEFT_TO_RIGHT, 96)
        draw_mask_rect(img, Loc(32, 32, 1600, 976), (255, 255, 255, 152), 96)

        text_color = darken_color(hex_to_color(rk_color), 0.2)
        pf_raw_text = f"{self._platform.platform_name} ID"
        platform_img = self.load_img_resource(self._platform.platform_name, text_color)
        draw_img(img, platform_img, Loc(144 + 32, 120 + 6 + 32, 48, 48))

        pf_text = StyledString(
            pf_raw_text, 'H', 44, font_color=text_color, padding_bottom=30
        )
        handle_text = StyledString(
            self._handle, 'H', 96, font_color=text_color, padding_bottom=20
        )
        social_text = StyledString(
            self._social, 'B', 28, font_color=text_color, padding_bottom=112
        )
        rank_text = StyledString(
            self._rank, 'H', 44, font_color=text_color, padding_bottom=-6
        )
        rating_text = StyledString(
            f"{self._rating}", 'H', 256, font_color=text_color, padding_bottom=44
        )

        current_x, current_y = 144 + 32, 120 + 32
        current_y = draw_text(img, pf_text, current_x + 48 + 18, current_y)
        current_y = draw_text(img, handle_text, current_x, current_y)
        current_y = draw_text(img, social_text, current_x, current_y)
        current_y = draw_text(img, rank_text, current_x, current_y)
        draw_text(img, rating_text, current_x - 10, current_y)

        return img
