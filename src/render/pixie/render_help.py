import pixie
from easy_pixie import StyledString, calculate_height, draw_text, calculate_width, Loc, draw_img, \
    pick_gradient_color, draw_gradient_rect, GradientDirection, draw_mask_rect, tuple_to_color, \
    change_alpha, hex_to_color, lighten_color

from src.core.constants import Constants, Help
from src.render.pixie.model import Renderer, RenderableSection

_CONTENT_WIDTH = 1024
_TOP_PADDING = 168
_BOTTOM_PADDING = 128
_SIDE_PADDING = 108
_COLUMN_PADDING = 52
_HELP_SECTION_PADDING = 72
_SECTION_PADDING = 108

_SPLIT_POINT = 5


class _HelpItem(RenderableSection):
    def __init__(self, single_help: Help):
        self._help = single_help

        self.str_command = StyledString(
            self._help.command, 'H', 52, font_color=(255, 255, 255), padding_bottom=16,
            max_width=_CONTENT_WIDTH - 108 - 12 - 48
        )
        self.str_help = StyledString(
            self._help.help, 'B', 28, font_color=(255, 255, 255, 228), padding_bottom=64,
            max_width=_CONTENT_WIDTH - 108 - 12 - 48, line_multiplier=1.36
        )

    def get_height(self):
        return calculate_height([self.str_command, self.str_help])

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.str_command, current_x, current_y)
        current_y = draw_text(img, self.str_help, current_x, current_y)

        return current_y


class _HelpSection(RenderableSection):
    def __init__(self, helps: dict[str, list[Help]]):
        self._helps = helps
        self.section_help = [[_HelpItem(single_help) for single_help in help_items]
                             for _, help_items in self._helps.items()]

    def get_height(self):
        # 计算左列高度
        left_column_height = sum(
            sum(single_help.get_height() for single_help in help_items)
            for help_items in self.section_help[:_SPLIT_POINT]
        ) + _HELP_SECTION_PADDING * (_SPLIT_POINT - 1)

        # 计算右列高度
        right_column_height = sum(
            sum(single_help.get_height() for single_help in help_items)
            for help_items in self.section_help[_SPLIT_POINT:]
        ) + _HELP_SECTION_PADDING * (len(self.section_help) - _SPLIT_POINT - 1)

        return max(left_column_height, right_column_height)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        max_y = y

        current_y -= _HELP_SECTION_PADDING
        for help_items in self.section_help[:_SPLIT_POINT]:
            current_y += _HELP_SECTION_PADDING
            for single_help in help_items:
                current_y = single_help.render(img, current_x, current_y)
                max_y = max(max_y, current_y)

        current_x, current_y = x + _CONTENT_WIDTH + _COLUMN_PADDING, y

        current_y -= _HELP_SECTION_PADDING
        for help_items in self.section_help[_SPLIT_POINT:]:
            current_y += _HELP_SECTION_PADDING
            for single_help in help_items:
                current_y = single_help.render(img, current_x, current_y)
                max_y = max(max_y, current_y)

        return max_y


class _TitleSection(RenderableSection):

    def __init__(self, accent_color: str):
        accent_light_color = lighten_color(hex_to_color(accent_color), 0.8)
        accent_light_color_tran = change_alpha(accent_light_color, 136)
        self.img_help = Renderer.load_img_resource("Help", accent_light_color)

        self.str_title = StyledString(
            "指令帮助", 'H', 96, padding_bottom=4, font_color=accent_light_color
        )
        self.str_subtitle = StyledString(
            "Command Instructions for OBot", 'H', 28, font_color=accent_light_color_tran
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_img(img, self.img_help, Loc(106, 181, 102, 102))

        current_x, current_y = x, y
        current_y = draw_text(img, self.str_title, 232, current_y)
        current_y = draw_text(img, self.str_subtitle, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_title, self.str_subtitle])


class _CopyrightSection(RenderableSection):

    def __init__(self, gradient_color_name: str):
        mild_text_color = (255, 255, 255, 156)

        self.str_tips_title = StyledString(
            "Tips:", 'H', 36, padding_bottom=64, font_color=(255, 255, 255, 228)
        )
        self.str_tips_detail = StyledString(
            "中括号必填，小括号选填，使用指令时不用加括号", 'M', 28,
            line_multiplier=1.32, padding_bottom=64, font_color=(255, 255, 255, 228),
            max_width=(_CONTENT_WIDTH - 108 -  # 考虑右边界，不然画出去了
                       calculate_width(self.str_tips_title) - 12 - 48)
        )
        self.str_generator = StyledString(
            "Command Instructions", 'H', 36, padding_bottom=16,
            font_color=(255, 255, 255, 228)
        )
        self.str_generation_info = StyledString(
            f"Compatible to OBot's ACM {Constants.core_version}.\n{gradient_color_name}.",
            'B', 20, line_multiplier=1.32, font_color=mild_text_color
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        draw_text(img, self.str_tips_title, current_x, current_y)
        current_y = draw_text(img, self.str_tips_detail,
                              current_x + calculate_width(self.str_tips_title) + 12,
                              current_y + 8)
        current_y = draw_text(img, self.str_generator, current_x, current_y)
        draw_text(img, self.str_generation_info, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_tips_title,
                                 self.str_generator, self.str_generation_info])


class HelpRenderer(Renderer):
    """帮助信息"""

    def render(self) -> pixie.Image:
        gradient_color = pick_gradient_color()

        section_title = _TitleSection(gradient_color.color_list[-1])
        section_help = _HelpSection(Constants.help_contents)
        section_copyright = _CopyrightSection(gradient_color.name)

        render_sections = [section_title, section_help, section_copyright]

        width, height = (_CONTENT_WIDTH * 2 + _COLUMN_PADDING,
                         sum(section.get_height() for section in render_sections) +
                         _SECTION_PADDING * (len(render_sections) - 1) +
                         _TOP_PADDING + _BOTTOM_PADDING)

        img = pixie.Image(width + 64, height + 64)
        img.fill(tuple_to_color((255, 255, 255, 255)))  # 填充白色背景

        draw_gradient_rect(img, Loc(32, 32, width, height), gradient_color,
                           GradientDirection.DIAGONAL_RIGHT_TO_LEFT, 96)
        draw_mask_rect(img, Loc(32, 32, width, height), (12, 12, 12, 198), 96)

        current_x, current_y = _SIDE_PADDING, _TOP_PADDING - _SECTION_PADDING

        for section in render_sections:
            current_y += _SECTION_PADDING
            current_y = section.render(img, current_x, current_y)

        return img
