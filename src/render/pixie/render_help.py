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


class _HelpItem(RenderableSection):
    def __init__(self, single_help: Help):
        self._help = single_help

        self._cmd_text = StyledString(
            self._help.command, 'H', 52, font_color=(255, 255, 255), padding_bottom=16,
            max_width=_CONTENT_WIDTH - 108 - 12 - 48
        )
        self._help_text = StyledString(
            self._help.help, 'B', 28, font_color=(255, 255, 255, 228), padding_bottom=64,
            max_width=_CONTENT_WIDTH - 108 - 12 - 48, line_multiplier=1.36
        )

    def get_height(self):
        return calculate_height([self._cmd_text, self._help_text])

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self._cmd_text, current_x, current_y)
        current_y = draw_text(img, self._help_text, current_x, current_y)

        return current_y


class _HelpSection(RenderableSection):
    def __init__(self, helps: dict[str, list[Help]]):
        self._helps = helps
        self._help_items = [[_HelpItem(single_help) for single_help in help_items]
                            for _, help_items in self._helps.items()]

    def get_height(self):
        # 计算左列高度
        left_column_height = sum(
            sum(single_help.get_height() for single_help in help_items)
            for help_items in self._help_items[:4]
        ) + _HELP_SECTION_PADDING * 3

        # 计算右列高度
        right_column_height = sum(
            sum(single_help.get_height() for single_help in help_items)
            for help_items in self._help_items[4:]
        ) + _HELP_SECTION_PADDING * (len(self._help_items) - 5)

        return max(left_column_height, right_column_height)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        max_y = y

        current_y -= _HELP_SECTION_PADDING
        for help_items in self._help_items[:4]:
            current_y += _HELP_SECTION_PADDING
            for single_help in help_items:
                current_y = single_help.render(img, current_x, current_y)
                max_y = max(max_y, current_y)

        current_x, current_y = x + _CONTENT_WIDTH + _COLUMN_PADDING, y

        current_y -= _HELP_SECTION_PADDING
        for help_items in self._help_items[4:]:
            current_y += _HELP_SECTION_PADDING
            for single_help in help_items:
                current_y = single_help.render(img, current_x, current_y)
                max_y = max(max_y, current_y)

        return max_y


class _TitleSection(RenderableSection):

    def __init__(self, accent_color: str):
        self.accent_light_color = lighten_color(hex_to_color(accent_color), 0.8)
        self.accent_light_color_tran = change_alpha(self.accent_light_color, 136)
        self.logo_path = Renderer.load_img_resource("Help", self.accent_light_color)

        self.title_text = StyledString(
            "指令帮助", 'H', 96, padding_bottom=4, font_color=self.accent_light_color
        )
        self.subtitle_text = StyledString(
            "Command Instructions for OBot", 'H', 28, font_color=self.accent_light_color_tran
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_img(img, self.logo_path, Loc(106, 181, 102, 102))

        current_x, current_y = x, y
        current_y = draw_text(img, self.title_text, 232, current_y)
        current_y = draw_text(img, self.subtitle_text, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.title_text, self.subtitle_text])


class _CopyrightSection(RenderableSection):

    def __init__(self, gradient_color_name: str):
        self.mild_text_color = (255, 255, 255, 156)

        self.tips_title_text = StyledString(
            "Tips:", 'H', 36, padding_bottom=64, font_color=(255, 255, 255, 228)
        )
        self.tips_detail_text = StyledString(
            "中括号必填，小括号选填，使用指令时不用加括号", 'M', 28,
            line_multiplier=1.32, padding_bottom=64, font_color=(255, 255, 255, 228),
            max_width=(_CONTENT_WIDTH - 108 -  # 考虑右边界，不然画出去了
                       calculate_width(self.tips_title_text) - 12 - 48)
        )
        self.generator_text = StyledString(
            "Command Instructions", 'H', 36, padding_bottom=16,
            font_color=(255, 255, 255, 228)
        )
        self.generation_info_text = StyledString(
            f"Compatible to OBot's ACM {Constants.core_version}.\n{gradient_color_name}.",
            'B', 20, line_multiplier=1.32, font_color=self.mild_text_color
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        draw_text(img, self.tips_title_text, current_x, current_y)
        current_y = draw_text(img, self.tips_detail_text,
                              current_x + calculate_width(self.tips_title_text) + 12,
                              current_y + 8)
        current_y = draw_text(img, self.generator_text, current_x, current_y)
        draw_text(img, self.generation_info_text, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.tips_title_text, self.generator_text, self.generation_info_text])

class HelpRenderer(Renderer):
    """帮助信息"""

    def render(self) -> pixie.Image:
        gradient_color = pick_gradient_color()

        title_section = _TitleSection(gradient_color.color_list[-1])
        help_section = _HelpSection(Constants.help_contents)
        copyright_section = _CopyrightSection(gradient_color.name)

        render_sections = [title_section, help_section, copyright_section]

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
