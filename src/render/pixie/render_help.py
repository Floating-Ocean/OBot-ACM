import re

import pixie
from easy_pixie import StyledString, calculate_height, draw_text, calculate_width, Loc, draw_img, \
    tuple_to_color, change_alpha, hex_to_color, lighten_color, draw_mask_rect, GradientColor, \
    GradientDirection, draw_gradient_rect

from src.core.constants import Constants, Help
from src.render.pixie.model import Renderer, RenderableSection, SimpleCardRenderer

_CONTENT_WIDTH = 916
_COLUMN_PADDING = 192
_HELP_ITEM_PADDING = 64
_HELP_CATEGORY_PADDING = 136
_ACCENT_LIGHT_RATIO = 0.88
_LINE_ALPHA = 100

_CATEGORY_CHIP_PADDING_HORIZONTAL = 26
_CATEGORY_CHIP_PADDING_VERTICAL = 9
_RESTRICTION_CHIP_PADDING_HORIZONTAL = 26
_RESTRICTION_CHIP_PADDING_VERTICAL = 12

_CATEGORY_NAMES = {
    'Main': '榜单·比赛',
    'sub': '用户·信息',
    'contestant': '选手查询',
    'codeforces': 'Codeforces',
    'atcoder': 'AtCoder',
    'nowcoder': 'NowCoder',
    'pick_one': '来只',
    'random': '随机数',
    'mc': 'Minecraft',
    'tetris': '俄罗斯方块',
    'guess-interval': '区间猜数',
    'guess-1a2b': '1A2B',
    'git-cmd': 'Git 管理',
    'misc1': '趣味工具',
    'misc2': '管理',
    'help': '帮助',
}

# 描述文本中可识别的限制短语及其标签文案
_RESTRICTION_PATTERNS = [
    (r"需要管理员权限", "管理员"),
    (r"需要管理员审核", "需审核"),
    (r"最多连续被执行一次", "仅限1次"),
]

# 参数的正则：中括号为必填，小括号为选填
_PARAM_PATTERN = re.compile(r"(\[[^\]]*\]|\([^)]*\))")


class _HelpItem(RenderableSection):

    def __init__(self, single_help: Help, accent_color: str):
        self._help = single_help
        accent_light_color = lighten_color(hex_to_color(accent_color), _ACCENT_LIGHT_RATIO)

        # 拆出限制短语，剩余内容作为描述展示
        self._restriction_text = None
        self._help_content = single_help.help
        for pattern, tag in _RESTRICTION_PATTERNS:
            if re.search(pattern, self._help_content):
                self._restriction_text = tag
                self._help_content = self._help_content.replace(pattern, "").strip("，。 ,")

        # 命令拆分为"命令本体 + 参数"分段，参数用强调色渲染
        self._segments = []
        for raw_segment in _PARAM_PATTERN.split(single_help.command):
            if not raw_segment:
                continue
            is_param = _PARAM_PATTERN.fullmatch(raw_segment) is not None
            self._segments.append((
                StyledString(raw_segment, 'H', 52,
                             font_color=accent_light_color if is_param else (255, 255, 255)),
                is_param
            ))
        self._line_height = self._segments[0][0].height

        # 限制标签，绘制在命令行的右侧
        self.str_restriction = (StyledString(self._restriction_text, 'B', 26,
                                             font_color=(255, 222, 170)) if self._restriction_text
                                else None)
        self._restriction_chip_height = (_RESTRICTION_CHIP_PADDING_VERTICAL * 2 +
                                         (self.str_restriction.height if self.str_restriction else 0))
        self._restriction_chip_width = (_RESTRICTION_CHIP_PADDING_HORIZONTAL * 2 +
                                        int(calculate_width(self.str_restriction))
                                        if self.str_restriction else 0)

        self.str_help = StyledString(
            self._help_content, 'B', 28, font_color=(255, 255, 255, 228),
            max_width=_CONTENT_WIDTH, line_multiplier=1.36
        )

        # 将命令分段按宽度折行
        command_max_width = _CONTENT_WIDTH - self._restriction_chip_width - 28
        self._lines = [[]]
        line_width = 0
        for segment, is_param in self._segments:
            segment_width = int(calculate_width(segment))
            if line_width > 0 and line_width + segment_width > command_max_width:
                self._lines.append([])
                line_width = 0
            self._lines[-1].append((segment, is_param))
            line_width += segment_width

    def get_height(self):
        command_height = len(self._lines) * self._line_height + 16
        return command_height + calculate_height(self.str_help)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        if self.str_restriction:
            chip_x = current_x + _CONTENT_WIDTH - self._restriction_chip_width
            chip_y = current_y + (self._line_height - self._restriction_chip_height) // 2
            draw_mask_rect(img, Loc(chip_x, chip_y, self._restriction_chip_width,
                                    self._restriction_chip_height),
                           (255, 222, 170, 44), self._restriction_chip_height // 2)
            draw_text(img, self.str_restriction, chip_x + _RESTRICTION_CHIP_PADDING_HORIZONTAL,
                      chip_y + (self._restriction_chip_height - self.str_restriction.height) // 2)

        for line in self._lines:
            line_x = current_x
            for segment, _ in line:
                draw_text(img, segment, line_x, current_y)
                line_x += int(calculate_width(segment))
            current_y += self._line_height
        current_y += 16
        current_y = draw_text(img, self.str_help, current_x, current_y)

        return current_y


class _HelpCategory(RenderableSection):
    """分类色块标题 + 该分类下的指令列表"""

    def __init__(self, category_name: str, helps: list[Help], accent_color: str):
        accent_light_color = lighten_color(hex_to_color(accent_color), _ACCENT_LIGHT_RATIO)
        accent_light_color_tran = change_alpha(accent_light_color, 48)

        self.str_title = StyledString(category_name, 'H', 36, font_color=accent_light_color)
        self._chip_height = self.str_title.height + _CATEGORY_CHIP_PADDING_VERTICAL * 2
        self._chip_width = int(calculate_width(self.str_title)) + _CATEGORY_CHIP_PADDING_HORIZONTAL * 2
        self._chip_color = accent_light_color_tran
        # 标题右侧的渐隐线
        self._line_color = change_alpha(accent_light_color, _LINE_ALPHA)
        self._line_color_tran = change_alpha(accent_light_color, 0)

        self.section_items = [_HelpItem(single_help, accent_color) for single_help in helps]

    def get_height(self):
        items_height = (sum(item.get_height() for item in self.section_items) +
                        _HELP_ITEM_PADDING * max(0, len(self.section_items) - 1))
        return self._chip_height + 48 + items_height

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        draw_mask_rect(img, Loc(current_x, current_y, self._chip_width, self._chip_height),
                       self._chip_color, self._chip_height // 2)
        draw_text(img, self.str_title, current_x + _CATEGORY_CHIP_PADDING_HORIZONTAL,
                  current_y + (self._chip_height - self.str_title.height) // 2)
        draw_gradient_rect(img, Loc(current_x + self._chip_width + 16,
                                    current_y + self._chip_height // 2 - 1,
                                    _CONTENT_WIDTH - self._chip_width - 16, 2),
                           GradientColor([self._line_color, self._line_color_tran], [0.0, 1.0], ''),
                           GradientDirection.HORIZONTAL, 1)

        current_y = y + self._chip_height + 48
        current_y -= _HELP_ITEM_PADDING
        for item in self.section_items:
            current_y += _HELP_ITEM_PADDING
            current_y = item.render(img, current_x, current_y)

        return current_y


class _HelpSection(RenderableSection):

    def __init__(self, helps: dict[str, list[Help]], accent_color: str):
        self.section_categories = [
            _HelpCategory(_CATEGORY_NAMES.get(key, key), help_items, accent_color)
            for key, help_items in helps.items()
        ]

    def get_columns(self):
        return 3

    def get_height(self):
        _, max_height = self._split_columns(self.section_categories, _HELP_CATEGORY_PADDING)
        return max_height

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y -= _HELP_CATEGORY_PADDING
        start_y, max_y = current_y, current_y

        column_split, _ = self._split_columns(self.section_categories, _HELP_CATEGORY_PADDING)
        for current_col, _column in enumerate(column_split):
            current_y = start_y
            for category in _column:
                current_y += _HELP_CATEGORY_PADDING
                current_y = category.render(
                    img,
                    current_x + (_CONTENT_WIDTH + _COLUMN_PADDING) * current_col,
                    current_y
                )
                max_y = max(max_y, current_y)

        return max_y


class _TitleSection(RenderableSection):

    def __init__(self, accent_color: str):
        accent_light_color = lighten_color(hex_to_color(accent_color), _ACCENT_LIGHT_RATIO)
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

    def __init__(self, gradient_color_name: str, accent_color: str):
        mild_text_color = (255, 255, 255, 156)
        accent_light_color = lighten_color(hex_to_color(accent_color), _ACCENT_LIGHT_RATIO)
        # 顶部与内容区分隔的渐隐线
        self._line_color = change_alpha(accent_light_color, _LINE_ALPHA)
        self._line_color_tran = change_alpha(accent_light_color, 0)
        self._line_gap = 26

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

        draw_gradient_rect(img, Loc(current_x, current_y, _CONTENT_WIDTH, 2),
                           GradientColor([self._line_color, self._line_color_tran], [0.0, 1.0], ''),
                           GradientDirection.HORIZONTAL, 1)
        current_y += self._line_gap

        draw_text(img, self.str_tips_title, current_x, current_y)
        current_y = draw_text(img, self.str_tips_detail,
                              current_x + calculate_width(self.str_tips_title) + 12,
                              current_y + 8)
        current_y = draw_text(img, self.str_generator, current_x, current_y)
        draw_text(img, self.str_generation_info, current_x, current_y)

        return current_y

    def get_height(self):
        return (self._line_gap +
                calculate_height([self.str_tips_title,
                                  self.str_generator, self.str_generation_info]))


class HelpRenderer(SimpleCardRenderer):
    """帮助信息"""

    def __init__(self):
        super().__init__()

    @classmethod
    def _get_background_color(cls) -> pixie.Color:
        return tuple_to_color((255, 255, 255))

    @classmethod
    def _get_mask_color(cls) -> pixie.Color:
        return tuple_to_color((9, 9, 9, 226))

    def _get_render_sections(self) -> list[RenderableSection]:
        section_title = _TitleSection(self._gradient_color.color_list[-1])
        section_help = _HelpSection(Constants.help_contents, self._gradient_color.color_list[-1])
        section_copyright = _CopyrightSection(self._gradient_color.name,
                                              self._gradient_color.color_list[-1])

        return [section_title, section_help, section_copyright]
