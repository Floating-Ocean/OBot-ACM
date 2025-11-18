import pixie
from easy_pixie import StyledString, calculate_height, draw_text, calculate_width, Loc, draw_img, \
    tuple_to_color, change_alpha, hex_to_color, lighten_color

from src.core.constants import Constants, Help
from src.render.pixie.model import Renderer, RenderableSection, SimpleCardRenderer

_CONTENT_WIDTH = 916
_COLUMN_PADDING = 192
_HELP_ITEM_PADDING = 64
_HELP_SECTION_PADDING = 136


class _HelpItem(RenderableSection):

    def __init__(self, single_help: Help):
        self._help = single_help

        self.str_command = StyledString(
            self._help.command, 'H', 52, font_color=(255, 255, 255), padding_bottom=16,
            max_width=_CONTENT_WIDTH
        )
        self.str_help = StyledString(
            self._help.help, 'B', 28, font_color=(255, 255, 255, 228),
            max_width=_CONTENT_WIDTH, line_multiplier=1.36
        )

    def get_height(self):
        return calculate_height([self.str_command, self.str_help])

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.str_command, current_x, current_y)
        current_y = draw_text(img, self.str_help, current_x, current_y)

        return current_y


class _HelpBundle(RenderableSection):

    def __init__(self, helps: list[Help]):
        self.section_help = [_HelpItem(single_help) for single_help in helps]

    def get_height(self):
        return (sum(single_help.get_height() for single_help in self.section_help) +
                _HELP_ITEM_PADDING * max(0, len(self.section_help) - 1))

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        current_y -= _HELP_ITEM_PADDING
        for single_help in self.section_help:
            current_y += _HELP_ITEM_PADDING
            current_y = single_help.render(img, current_x, current_y)

        return current_y


class _HelpSection(RenderableSection):

    def __init__(self, helps: dict[str, list[Help]]):
        self.section_help = [_HelpBundle(help_items) for _, help_items in helps.items()]

    def get_columns(self):
        return 3

    def get_height(self):
        _, max_height = self._split_columns(self.section_help, _HELP_SECTION_PADDING)
        return max_height

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y -= _HELP_SECTION_PADDING
        start_y, max_y = current_y, current_y

        column_split, _ = self._split_columns(self.section_help, _HELP_SECTION_PADDING)
        for current_col, _column in enumerate(column_split):
            current_y = start_y
            for help_items in _column:
                current_y += _HELP_SECTION_PADDING
                current_y = help_items.render(
                    img,
                    current_x + (_CONTENT_WIDTH + _COLUMN_PADDING) * current_col,
                    current_y
                )
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
        draw_img(img, self.img_help, Loc(x - 4, y + 13, 102, 102))

        current_x, current_y = x, y
        current_y = draw_text(img, self.str_title, current_x + 124, current_y)
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
            max_width=_CONTENT_WIDTH - calculate_width(self.str_tips_title) - 12  # 考虑右边界，不然画出去了
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


class HelpRenderer(SimpleCardRenderer):
    """帮助信息"""

    def __init__(self):
        super().__init__()

    @classmethod
    def _get_background_color(cls) -> pixie.Color:
        return tuple_to_color((255, 255, 255))

    @classmethod
    def _get_mask_color(cls) -> pixie.Color:
        return tuple_to_color((12, 12, 12, 198))

    def _get_render_sections(self) -> list[RenderableSection]:
        section_title = _TitleSection(self._gradient_color.color_list[-1])
        section_help = _HelpSection(Constants.help_contents)
        section_copyright = _CopyrightSection(self._gradient_color.name)

        return [section_title, section_help, section_copyright]
