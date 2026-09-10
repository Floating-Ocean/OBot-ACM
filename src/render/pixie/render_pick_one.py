import colorsys

import pixie
from easy_pixie import StyledString, calculate_height, calculate_width, change_alpha, \
    draw_img, draw_mask_rect, draw_text, tuple_to_color, Loc

from src.core.constants import Constants
from src.data.data_pick_one import PickOne
from src.render.pixie.model import Renderer, RenderableSection, SimpleCardRenderer

_CONTENT_WIDTH = 640
_COLUMN_PADDING = 192
_COLUMNS = 4
_GRID_GAP = 32
_GRID_WIDTH = _CONTENT_WIDTH * _COLUMNS + _COLUMN_PADDING * (_COLUMNS - 1)
_ITEM_WIDTH = (_GRID_WIDTH - _GRID_GAP * (_COLUMNS - 1)) // _COLUMNS

_ITEM_ROUND_SIZE = 32
_ITEM_INNER_HORIZONTAL_PADDING = 40
_ITEM_INNER_VERTICAL_PADDING = 36
_ITEM_TITLE_GAP = 18

_COUNT_CHIP_PADDING_HORIZONTAL = 26
_COUNT_CHIP_PADDING_VERTICAL = 10
_SUMMARY_CHIP_PADDING_HORIZONTAL = 34
_SUMMARY_CHIP_PADDING_VERTICAL = 12

_TITLE_ICON_SIZE = 102
_TITLE_ICON_GAP = 18

# 类别配色：色相从红扫到紫（彩虹渐变），每个类别固定取一个色相
_SPECTRUM_START_HUE = 0.0  # 红
_SPECTRUM_END_HUE = 285.0  # 紫
_SPECTRUM_SATURATION = 0.86
_SPECTRUM_VALUE = 0.76
_NAME_VALUE = 0.56
_COUNT_VALUE = 0.56
_SPECTRUM_DESCRIPTION = "Rainbow spectrum: red to purple"

_TEXT_COLOR = (0, 0, 0)
_MILD_TEXT_COLOR = (0, 0, 0, 136)
_ALIAS_TEXT_COLOR = (0, 0, 0, 150)
_UNAVAILABLE_ALIAS_TEXT_COLOR = (0, 0, 0, 96)
_CARD_COLOR = (242, 242, 242)


def _hue_color(ratio: float, value: float = _SPECTRUM_VALUE) -> tuple[int, int, int]:
    """在彩虹渐变上按比例取色：色相自红至紫均匀变化，压暗明度可得同色系的深色"""
    hue = _SPECTRUM_START_HUE + (_SPECTRUM_END_HUE - _SPECTRUM_START_HUE) * ratio
    red, green, blue = colorsys.hsv_to_rgb((hue % 360) / 360, _SPECTRUM_SATURATION, value)
    return round(red * 255), round(green * 255), round(blue * 255)


class _StickerItem:
    """单个表情包类别的卡片：展示名、数量与别名，使用所属类别的配色"""

    def __init__(self, sticker_id: str, count: int, aliases: list[str],
                 spectrum_ratio: float):
        available = count > 0
        pixie_color = tuple_to_color(_hue_color(spectrum_ratio))
        name_color = tuple_to_color(_hue_color(spectrum_ratio, _NAME_VALUE))
        count_color = tuple_to_color(_hue_color(spectrum_ratio, _COUNT_VALUE))

        def _text_color(color: pixie.Color, unavailable_alpha: int) -> pixie.Color:
            """数量为 0 的类别降低不透明度，表示暂不可用"""
            return change_alpha(color, 255 if available else unavailable_alpha)

        self.str_id = StyledString(sticker_id, 'H', 44, font_color=_text_color(name_color, 118))
        self.str_count = StyledString(f"{count} 只", 'B', 24,
                                      font_color=_text_color(count_color, 118))

        self._cell_color = change_alpha(pixie_color, 26 if available else 12)
        self._chip_color = change_alpha(pixie_color, 58 if available else 20)
        self._chip_height = self.str_count.height + _COUNT_CHIP_PADDING_VERTICAL * 2
        self._chip_width = (int(calculate_width(self.str_count)) +
                            _COUNT_CHIP_PADDING_HORIZONTAL * 2)
        self._title_line_height = max(self.str_id.height, self._chip_height)

        self.str_aliases = (StyledString(
            f"别名：{'、'.join(aliases)}", 'B', 22, line_multiplier=1.36,
            font_color=_ALIAS_TEXT_COLOR if available else _UNAVAILABLE_ALIAS_TEXT_COLOR,
            max_width=_ITEM_WIDTH - _ITEM_INNER_HORIZONTAL_PADDING * 2
        ) if aliases else None)

    def get_height(self):
        height = _ITEM_INNER_VERTICAL_PADDING * 2 + self._title_line_height
        if self.str_aliases:
            height += _ITEM_TITLE_GAP + calculate_height(self.str_aliases)
        return height

    def render(self, img: pixie.Image, x: int, y: int, height: int) -> int:
        draw_mask_rect(img, Loc(x, y, _ITEM_WIDTH, height), self._cell_color, _ITEM_ROUND_SIZE)

        current_x = x + _ITEM_INNER_HORIZONTAL_PADDING
        current_y = y + _ITEM_INNER_VERTICAL_PADDING
        draw_text(img, self.str_id, current_x, current_y)

        chip_x = x + _ITEM_WIDTH - _ITEM_INNER_HORIZONTAL_PADDING - self._chip_width
        chip_y = current_y + (self._title_line_height - self._chip_height) // 2
        draw_mask_rect(img, Loc(chip_x, chip_y, self._chip_width, self._chip_height),
                       self._chip_color, self._chip_height // 2)
        draw_text(img, self.str_count, chip_x + _COUNT_CHIP_PADDING_HORIZONTAL,
                  chip_y + (self._chip_height - self.str_count.height) // 2)

        if self.str_aliases:
            draw_text(img, self.str_aliases, current_x,
                      current_y + self._title_line_height + _ITEM_TITLE_GAP)

        return y + height


class _StickerSection(RenderableSection):
    """表情包类别卡片网格"""

    def __init__(self, stickers: list[tuple[str, int, list[str]]]):
        # 按阅读顺序在彩虹渐变上依次取色：每个类别色相唯一，首红尾紫
        spectrum_length = max(1, len(stickers) - 1)
        self.section_items = [
            _StickerItem(sticker_id, count, aliases, idx / spectrum_length)
            for idx, (sticker_id, count, aliases) in enumerate(stickers)
        ]
        self._rows = [self.section_items[idx:idx + _COLUMNS]
                      for idx in range(0, len(self.section_items), _COLUMNS)]

    def get_columns(self):
        return _COLUMNS

    def get_height(self):
        if not self._rows:
            return 0
        return (sum(max(item.get_height() for item in row) for row in self._rows) +
                _GRID_GAP * (len(self._rows) - 1))

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_y = y
        for row in self._rows:
            row_height = max(item.get_height() for item in row)
            for idx, item in enumerate(row):
                item.render(img, x + (_ITEM_WIDTH + _GRID_GAP) * idx, current_y, row_height)
            current_y += row_height + _GRID_GAP

        return current_y - _GRID_GAP if self._rows else y


class _TitleSection(RenderableSection):

    def __init__(self, type_count: int, sticker_count: int):
        self.img_icon = Renderer.load_img_resource("Pick-One", _TEXT_COLOR)
        self.str_title = StyledString(
            "表情包图鉴", 'H', 96, padding_bottom=4, font_color=_TEXT_COLOR
        )
        self.str_subtitle = StyledString(
            "PickOne Collection of OBot. Just Currently", 'H', 28, font_color=_MILD_TEXT_COLOR
        )
        self.str_summary = StyledString(
            f"{type_count} 个类别 · {sticker_count} 只表情包", 'H', 30,
            font_color=(0, 0, 0, 178)
        )
        self._chip_color = (0, 0, 0, 16)
        self._chip_height = self.str_summary.height + _SUMMARY_CHIP_PADDING_VERTICAL * 2
        self._chip_width = (int(calculate_width(self.str_summary)) +
                            _SUMMARY_CHIP_PADDING_HORIZONTAL * 2)

    def get_height(self):
        return calculate_height([self.str_title, self.str_subtitle])

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_img(img, self.img_icon,
                 Loc(x - 4, y + 13, _TITLE_ICON_SIZE, _TITLE_ICON_SIZE))

        chip_x = x + _GRID_WIDTH - self._chip_width
        chip_y = y + max(0, (self.str_title.height - self._chip_height) // 2)
        draw_mask_rect(img, Loc(chip_x, chip_y, self._chip_width, self._chip_height),
                       self._chip_color, self._chip_height // 2)
        draw_text(img, self.str_summary, chip_x + _SUMMARY_CHIP_PADDING_HORIZONTAL,
                  chip_y + (self._chip_height - self.str_summary.height) // 2)

        current_x = x + _TITLE_ICON_SIZE + _TITLE_ICON_GAP
        current_y = draw_text(img, self.str_title, current_x, y)
        current_y = draw_text(img, self.str_subtitle, x, current_y)

        return current_y


class _TipsSection(RenderableSection):
    """底部提示与生成信息"""

    def __init__(self):
        self.str_tips_title = StyledString(
            "Tips:", 'H', 36, padding_bottom=64, font_color=(0, 0, 0, 208)
        )
        self.str_tips_detail = StyledString(
            "发送 /来只 加类别关键词或别名即可随机获取表情包，支持模糊匹配与多候选挑选.",
            'M', 28, line_multiplier=1.32, padding_bottom=64, font_color=(0, 0, 0, 208),
            max_width=_GRID_WIDTH - calculate_width(self.str_tips_title) - 12
        )
        self.str_generator = StyledString(
            "PickOne Collection", 'H', 36, padding_bottom=16, font_color=(0, 0, 0, 208)
        )
        self.str_generation_info = StyledString(
            f"A module of OBot's ACM {Constants.core_version}.\n{_SPECTRUM_DESCRIPTION}.",
            'B', 20, line_multiplier=1.32, font_color=(0, 0, 0, 136)
        )

    def get_height(self):
        return calculate_height([self.str_tips_title,
                                 self.str_generator, self.str_generation_info])

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_text(img, self.str_tips_title, x, y)
        current_y = draw_text(img, self.str_tips_detail,
                              x + calculate_width(self.str_tips_title) + 12, y + 8)
        current_y = draw_text(img, self.str_generator, x, current_y)
        draw_text(img, self.str_generation_info, x, current_y)

        return current_y


def _collect_stickers(data: PickOne) -> list[tuple[str, int, list[str]]]:
    """汇总所有表情包类别，返回 (展示名, 数量, 别名列表)，并按数量降序排序"""
    counts = dict(data.ids)
    stickers = []
    for conf in data.conf.values():
        aliases = [key for key in dict.fromkeys(conf.key)
                   if key.strip().lower() != conf.id.strip().lower()]
        stickers.append((conf.id, counts.get(conf.id, 0), aliases))

    stickers.sort(key=lambda sticker: sticker[1], reverse=True)
    return stickers


class PickOneRenderer(SimpleCardRenderer):
    """表情包图鉴"""

    def __init__(self, data: PickOne):
        super().__init__()
        self._stickers = _collect_stickers(data)

    @classmethod
    def _get_content_width(cls) -> int:
        return _CONTENT_WIDTH

    def _render_background_rect(self, img: pixie.Image, background_loc: Loc):
        draw_mask_rect(img, background_loc, _CARD_COLOR, 96)

    def _get_render_sections(self) -> list[RenderableSection]:
        total_count = sum(count for _, count, _ in self._stickers)

        section_title = _TitleSection(len(self._stickers), total_count)
        section_stickers = _StickerSection(self._stickers)
        section_tips = _TipsSection()

        return [section_title, section_stickers, section_tips]
