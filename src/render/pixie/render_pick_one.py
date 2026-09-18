import colorsys
import os
import time

import pixie
from easy_pixie import StyledString, calculate_height, calculate_width, change_alpha, \
    draw_img, draw_mask_rect, draw_text, tuple_to_color, Loc
from pypinyin import pinyin, Style

from src.core.constants import Constants
from src.core.util.tools import img_fit_in_bounds, rgb_luminance
from src.data.data_pick_one import PickOne, PickOneImgStat, get_img_full_path
from src.render.pixie.model import Renderer, RenderableSection, SimpleCardRenderer

_CONTENT_WIDTH = 640
_COLUMN_PADDING = 192
_COLUMNS = 4
_GRID_GAP = 32
_GRID_WIDTH = _CONTENT_WIDTH * _COLUMNS + _COLUMN_PADDING * (_COLUMNS - 1)
_ITEM_WIDTH = (_GRID_WIDTH - _GRID_GAP * (_COLUMNS - 1)) // _COLUMNS

_ITEM_ROUND_SIZE = 32
_ITEM_INNER_HORIZONTAL_PADDING = 40
_ITEM_INNER_TOP_PADDING = 36
_ITEM_INNER_BOTTOM_PADDING = 28  # 内容区与底边框之间的留白
_ITEM_TITLE_GAP = 18

_BAR_HEIGHT = 12
_BAR_TRACK_ALPHA = 40  # 条形底槽
_BAR_FILL_ALPHA = 232  # 条形填充
_BAR_FILL_MIN_WIDTH = 8
_BAR_EXPONENT = 0.5  # 数量 -> 条长的压缩指数
_BAR_CORNER_SEGMENTS = 24  # 底角补集多边形的弧线分段数

_NUMBER_ALPHA = 10
_NUMBER_HORIZONTAL_PADDING = 16
_NUMBER_TOP_PADDING = 16  # 数字顶部与卡片顶边的留白
_NUMBER_INK_HEIGHT_RATIO = 0.855  # 数字墨迹高度 / 字号
_NUMBER_INK_TOP_RATIO = 0.24  # 墨迹顶部相对绘制原点的偏移 / 字号

_SUMMARY_CHIP_PADDING_HORIZONTAL = 34
_SUMMARY_CHIP_PADDING_VERTICAL = 12

_TITLE_ICON_SIZE = 102
_TITLE_ICON_GAP = 18

_PREVIEW_GAP = 64
_PREVIEW_CARD_WIDTH = ((_GRID_WIDTH - _PREVIEW_GAP * (_COLUMNS - 1)) // _COLUMNS)

_PREVIEW_MEDIA_INSET = 16  # 预览底板与卡片边缘的留白
_PREVIEW_MEDIA_WIDTH = _PREVIEW_CARD_WIDTH - _PREVIEW_MEDIA_INSET * 2
_PREVIEW_MEDIA_HEIGHT = 464
_PREVIEW_MEDIA_BOX = (_PREVIEW_MEDIA_WIDTH, _PREVIEW_MEDIA_HEIGHT)
_PREVIEW_MEDIA_PLATE_HEIGHT = _PREVIEW_MEDIA_HEIGHT + _PREVIEW_MEDIA_INSET * 2

# 卡片底部信息区
_PREVIEW_FOOTER_TOP_PADDING = 18
_PREVIEW_FOOTER_MIDDLE_PADDING = 14
_PREVIEW_FOOTER_BOTTOM_PADDING = 36
_PREVIEW_ID_FONT_SIZE = 30
_PREVIEW_META_FONT_SIZE = 22
_PREVIEW_FOOTER_PADDING = 36  # 文字与卡片左右边缘的留白
_PREVIEW_ID_LINE_HEIGHT = StyledString("0", 'H', _PREVIEW_ID_FONT_SIZE).height
_PREVIEW_META_LINE_HEIGHT = StyledString("0", 'B', _PREVIEW_META_FONT_SIZE).height
_PREVIEW_FOOTER_HEIGHT = (_PREVIEW_FOOTER_TOP_PADDING + _PREVIEW_ID_LINE_HEIGHT +
                          _PREVIEW_FOOTER_MIDDLE_PADDING + _PREVIEW_META_LINE_HEIGHT +
                          _PREVIEW_FOOTER_BOTTOM_PADDING)
_PREVIEW_CARD_HEIGHT = _PREVIEW_MEDIA_PLATE_HEIGHT + _PREVIEW_FOOTER_HEIGHT
_PREVIEW_MAX_UPSCALE = 2.5  # 预览图最多放大到原图的多少倍
_PREVIEW_CARD_TINT_ALPHA = 26  # 卡片底色的不透明度

# 类别配色：色相从红扫到紫（彩虹渐变），每个类别固定取一个色相
_SPECTRUM_START_HUE = 0.0  # 红
_SPECTRUM_END_HUE = 285.0  # 紫
_SPECTRUM_SATURATION = 0.76
# 各色相的天然亮度差别很大（黄最亮、蓝紫最暗），把亮度收进区间
_TINT_LUMINANCE_RANGE = (0.50, 0.66)  # 卡片底色
_TEXT_LUMINANCE_RANGE = (0.26, 0.36)  # 类别名、条形与数量文字
_SPECTRUM_DESCRIPTION = "Rainbow spectrum: red to purple"

_TEXT_COLOR = (0, 0, 0)
_MILD_TEXT_COLOR = (0, 0, 0, 136)
_ALIAS_TEXT_COLOR = (0, 0, 0, 150)
_UNAVAILABLE_ALIAS_TEXT_COLOR = (0, 0, 0, 96)
_CARD_COLOR = (242, 242, 242)


def _draw_corner_trim(img: pixie.Image, corner_x: int, y_bottom: int, radius: int,
                      bar_height: int, direction: int, color: pixie.Color):
    """把卡片底角圆角之外、被条形方角盖住的区域补回卡片底色。

    条形是方角的，只有把两个底角按卡片圆角"切"回来，进度条才会与卡片边角完全贴合。
    direction 为 1 表示左下角、-1 表示右下角，corner_x 为该角在卡片上的横坐标。
    """
    height = min(bar_height, radius)

    def arc_offset(distance: float) -> float:
        """某点距卡片底边 distance 时，卡片边界相对角点水平内缩的距离"""
        return radius - (radius ** 2 - (radius - distance) ** 2) ** 0.5

    path = pixie.Path()
    path.move_to(corner_x, y_bottom - height)
    path.line_to(corner_x + direction * arc_offset(height), y_bottom - height)
    for idx in range(1, _BAR_CORNER_SEGMENTS + 1):
        distance = height * (1 - idx / _BAR_CORNER_SEGMENTS)
        path.line_to(corner_x + direction * arc_offset(distance), y_bottom - distance)
    path.line_to(corner_x, y_bottom)
    path.close_path()

    paint = pixie.Paint(pixie.SOLID_PAINT)
    paint.color = color
    img.fill_path(path, paint)


def _hue_color(ratio: float, luminance_range: tuple[float, float]) -> tuple[int, int, int]:
    """在彩虹渐变上按比例取色，并把亮度收进指定区间：
    过亮的色相（黄）等比压暗、过暗的色相（蓝紫）向白色混合提亮，
    区间内的色相保持原样，避免红黄系被压成褐色"""
    hue = (_SPECTRUM_START_HUE + (_SPECTRUM_END_HUE - _SPECTRUM_START_HUE) * ratio) / 360
    red, green, blue = colorsys.hsv_to_rgb(hue, _SPECTRUM_SATURATION, 1.0)

    luminance_low, luminance_high = luminance_range
    luminance = rgb_luminance(red, green, blue)
    if luminance > luminance_high:  # 等比压暗，色相与饱和度不变
        scale = luminance_high / luminance
        red, green, blue = red * scale, green * scale, blue * scale
    elif luminance < luminance_low:  # 向白色混合提亮，色相不变
        mix = (luminance_low - luminance) / (1 - luminance)
        red, green, blue = (red + (1 - red) * mix,
                            green + (1 - green) * mix,
                            blue + (1 - blue) * mix)

    return round(red * 255), round(green * 255), round(blue * 255)


class _StickerItem:
    """单个表情包类别的卡片"""

    def __init__(self, sticker_id: str, count: int, aliases: list[str],
                 spectrum_ratio: float, max_count: int):
        available = count > 0
        self._count = count
        self._text_color = tuple_to_color(_hue_color(spectrum_ratio, _TEXT_LUMINANCE_RANGE))

        def _alpha(available_alpha: int, unavailable_alpha: int) -> int:
            return available_alpha if available else unavailable_alpha

        self.str_id = StyledString(
            sticker_id, 'H', 44,
            font_color=change_alpha(self._text_color, _alpha(255, 118)))

        pixie_color = tuple_to_color(_hue_color(spectrum_ratio, _TINT_LUMINANCE_RANGE))
        self._cell_color = change_alpha(pixie_color, _alpha(26, 12))
        self._number_color = change_alpha(self._text_color, _alpha(_NUMBER_ALPHA, 6))
        self._bar_track_color = change_alpha(pixie_color, _alpha(_BAR_TRACK_ALPHA, 28))
        self._bar_fill_color = change_alpha(self._text_color, _alpha(_BAR_FILL_ALPHA, 96))
        # 避免 3000 只把 3 只压成看不见
        self._bar_ratio = (count / max_count) ** _BAR_EXPONENT if max_count > 0 else 0.0
        self._title_line_height = self.str_id.height

        self.str_aliases = (StyledString(
            f"别名：{'、'.join(aliases)}", 'B', 22, line_multiplier=1.36,
            font_color=_ALIAS_TEXT_COLOR if available else _UNAVAILABLE_ALIAS_TEXT_COLOR,
            max_width=_ITEM_WIDTH - _ITEM_INNER_HORIZONTAL_PADDING * 2
        ) if aliases else None)

    def get_height(self):
        height = (_ITEM_INNER_TOP_PADDING + self._title_line_height +
                  _ITEM_INNER_BOTTOM_PADDING + _BAR_HEIGHT)
        if self.str_aliases:
            height += _ITEM_TITLE_GAP + calculate_height(self.str_aliases)
        return height

    def _render_count_number(self, img: pixie.Image, x: int, y: int, height: int):
        """巨号数字"""
        ink_height = height - _BAR_HEIGHT - _NUMBER_TOP_PADDING
        font_size = round(ink_height / _NUMBER_INK_HEIGHT_RATIO)
        number = StyledString(f"{self._count}", 'H', font_size, font_color=self._number_color)

        max_width = _ITEM_WIDTH - _NUMBER_HORIZONTAL_PADDING * 2
        width = int(calculate_width(number))
        if width > max_width:  # 位数过多时按宽度回退，避免溢出卡片
            font_size = int(font_size * max_width / width)
            number = StyledString(f"{self._count}", 'H', font_size, font_color=self._number_color)
            width = int(calculate_width(number))

        draw_text(img, number, x + _ITEM_WIDTH - _NUMBER_HORIZONTAL_PADDING - width,
                  round(y + _NUMBER_TOP_PADDING - _NUMBER_INK_TOP_RATIO * font_size))

    def _render_bottom_bar(self, img: pixie.Image, x: int, y: int, height: int):
        """数量进度条：方角条贴满卡片下沿，再把两个底角按卡片圆角切回来"""
        bar_y = y + height - _BAR_HEIGHT
        draw_mask_rect(img, Loc(x, bar_y, _ITEM_WIDTH, _BAR_HEIGHT), self._bar_track_color)

        fill_width = round(_ITEM_WIDTH * self._bar_ratio)
        if fill_width > 0:
            fill_width = max(fill_width, _BAR_FILL_MIN_WIDTH)
            draw_mask_rect(img, Loc(x, bar_y, fill_width, _BAR_HEIGHT), self._bar_fill_color)

        y_bottom = y + height
        card_color = tuple_to_color(_CARD_COLOR)
        for direction, corner_x in ((1, x), (-1, x + _ITEM_WIDTH)):
            _draw_corner_trim(img, corner_x, y_bottom, _ITEM_ROUND_SIZE, _BAR_HEIGHT,
                              direction, card_color)

    def render(self, img: pixie.Image, x: int, y: int, height: int) -> int:
        draw_mask_rect(img, Loc(x, y, _ITEM_WIDTH, height), self._cell_color, _ITEM_ROUND_SIZE)
        self._render_count_number(img, x, y, height)

        current_x = x + _ITEM_INNER_HORIZONTAL_PADDING
        current_y = y + _ITEM_INNER_TOP_PADDING
        draw_text(img, self.str_id, current_x, current_y)

        if self.str_aliases:
            draw_text(img, self.str_aliases, current_x,
                      current_y + self._title_line_height + _ITEM_TITLE_GAP)

        self._render_bottom_bar(img, x, y, height)

        return y + height


class _StickerSection(RenderableSection):
    """表情包类别卡片网格"""

    def __init__(self, stickers: list[tuple[str, int, list[str]]]):
        # 按阅读顺序在彩虹渐变上依次取色：每个类别色相唯一，首红尾紫
        spectrum_length = max(1, len(stickers) - 1)
        max_count = max((count for _, count, _ in stickers), default=0)
        self.section_items = [
            _StickerItem(sticker_id, count, aliases, idx / spectrum_length, max_count)
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
    """标题块：图标 + 大标题 + 副标题，右侧概览"""

    def __init__(self, title: str, subtitle: str, summary: str):
        self.img_icon = Renderer.load_img_resource("Pick-One", _TEXT_COLOR)
        self.str_title = StyledString(title, 'H', 96, padding_bottom=4, font_color=_TEXT_COLOR,
                                      max_width=2048)
        self.str_subtitle = StyledString(subtitle, 'H', 28, font_color=_MILD_TEXT_COLOR)
        self.str_summary = StyledString(summary, 'H', 30, font_color=(0, 0, 0, 178))
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

    def __init__(self, tips_detail: str | None = None, generator: str = "PickOne Collection"):
        self.str_tips_title = StyledString(
            "Tips:", 'H', 36, padding_bottom=64, font_color=(0, 0, 0, 208)
        )
        self.str_tips_detail = StyledString(
            tips_detail or "发送 /来只 加类别关键词或别名即可随机获取表情包，支持模糊匹配与多候选挑选.",
            'M', 28, line_multiplier=1.32, padding_bottom=64, font_color=(0, 0, 0, 208),
            max_width=_GRID_WIDTH - calculate_width(self.str_tips_title) - 12
        )
        self.str_generator = StyledString(
            generator, 'H', 36, padding_bottom=16, font_color=(0, 0, 0, 208)
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


def _sort_key(sticker_id: str) -> str:
    """按名称排序，中文取拼音、英文取原文，保证中英混排时顺序稳定可预期"""
    return ''.join(item[0] for item in pinyin(sticker_id, Style.NORMAL)).lower()


def _collect_stickers(data: PickOne) -> list[tuple[str, int, list[str]]]:
    """汇总所有表情包类别，返回 (展示名, 数量, 别名列表)，并按名称排序"""
    counts = dict(data.ids)
    stickers = []
    for conf in data.conf.values():
        aliases = [key for key in dict.fromkeys(conf.key)
                   if key.strip().lower() != conf.id.strip().lower()]
        stickers.append((conf.id, counts.get(conf.id, 0), aliases))

    stickers.sort(key=lambda sticker: _sort_key(sticker[0]))
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

        section_title = _TitleSection(
            "表情包图鉴", "PickOne Collection of OBot. Just Currently",
            f"{len(self._stickers)} 个类别 · {total_count} 只表情包")
        section_stickers = _StickerSection(self._stickers)
        section_tips = _TipsSection()

        return [section_title, section_stickers, section_tips]


def _describe_stat(stat: PickOneImgStat) -> str:
    """一张表情包的说明"""
    if stat.likes or stat.comments or stat.pickup_times:
        return f"{stat.likes} 赞 · {stat.comments} 评 · 提起 {stat.pickup_times} 次"
    if stat.add_time:
        return f"添加于 {time.strftime('%y/%m/%d', time.localtime(stat.add_time))}"
    return "暂无互动记录"


class _PreviewCard:
    """单张表情包"""

    def __init__(self, text_color: pixie.Color, media_color: pixie.Color,
                 stat: PickOneImgStat, img_path: str):
        self._card_color = media_color
        self.img_preview = (img_fit_in_bounds(img_path, _PREVIEW_MEDIA_BOX, _PREVIEW_MAX_UPSCALE)
                            if os.path.exists(img_path) else None)

        self.str_hash_id = StyledString(
            f"ID: {stat.hash_id}", 'H', _PREVIEW_ID_FONT_SIZE, font_color=text_color,
            max_width=_PREVIEW_CARD_WIDTH - _PREVIEW_FOOTER_PADDING * 2
        )
        self.str_meta = StyledString(
            _describe_stat(stat), 'B', _PREVIEW_META_FONT_SIZE, font_color=_MILD_TEXT_COLOR,
            max_width=_PREVIEW_CARD_WIDTH - _PREVIEW_FOOTER_PADDING * 2
        )

    def render(self, img: pixie.Image, x: int, y: int):
        draw_mask_rect(img, Loc(x, y, _PREVIEW_CARD_WIDTH, _PREVIEW_CARD_HEIGHT),
                       self._card_color, _ITEM_ROUND_SIZE)

        # 预览底板：铺满卡片上部（四周略有留白），再把等比缩放后的首帧居中放上去
        media_x, media_y = x + _PREVIEW_MEDIA_INSET, y + _PREVIEW_MEDIA_INSET
        draw_mask_rect(img, Loc(media_x, media_y, _PREVIEW_MEDIA_WIDTH,
                                _PREVIEW_MEDIA_HEIGHT),
                       (255, 255, 255), _ITEM_ROUND_SIZE - _PREVIEW_MEDIA_INSET)

        if self.img_preview:
            width, height = self.img_preview.width, self.img_preview.height
            draw_img(img, self.img_preview, Loc(
                x + (_PREVIEW_CARD_WIDTH - width) // 2,
                media_y + (_PREVIEW_MEDIA_HEIGHT - height) // 2, width, height))

        current_y = y + _PREVIEW_MEDIA_PLATE_HEIGHT + _PREVIEW_FOOTER_TOP_PADDING
        current_y = draw_text(img, self.str_hash_id,
                              x + _PREVIEW_FOOTER_PADDING, current_y)
        draw_text(img, self.str_meta, x + _PREVIEW_FOOTER_PADDING,
                  current_y + _PREVIEW_FOOTER_MIDDLE_PADDING)


class _PreviewSection(RenderableSection):
    """表情包预览网格"""

    def __init__(self, text_color: pixie.Color, media_color: pixie.Color,
                 img_key: str, imgs: list[PickOneImgStat]):
        cards = [_PreviewCard(text_color, media_color, stat,
                              get_img_full_path(img_key, f"{stat.md5}.gif"))
                 for stat in imgs]
        self._rows = [cards[idx:idx + _COLUMNS]
                      for idx in range(0, len(cards), _COLUMNS)]

    def get_columns(self):
        return _COLUMNS

    def get_height(self):
        return (len(self._rows) * _PREVIEW_CARD_HEIGHT +
                _PREVIEW_GAP * (len(self._rows) - 1))

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_y = y
        for row in self._rows:
            for idx, card in enumerate(row):
                card.render(img, x + (_PREVIEW_CARD_WIDTH + _PREVIEW_GAP) * idx, current_y)
            current_y += _PREVIEW_CARD_HEIGHT + _PREVIEW_GAP

        return current_y - _PREVIEW_GAP


class PickOnePreviewRenderer(SimpleCardRenderer):
    """单个表情包类别的预览卡片"""

    def __init__(self, data: PickOne, img_key: str, imgs: list[PickOneImgStat]):
        super().__init__()
        stickers = _collect_stickers(data)
        sticker_id = data.conf[img_key].id
        for idx, (sticker_id_of, count, _) in enumerate(stickers):
            if sticker_id_of == sticker_id:
                break
        else:
            raise KeyError(f"sticker {sticker_id!r} not found in collected stickers")

        self._img_key = img_key
        self._imgs = imgs
        self._sticker_id = sticker_id
        self._count = count

        spectrum_ratio = idx / max(1, len(stickers) - 1)
        self._text_color = tuple_to_color(_hue_color(spectrum_ratio, _TEXT_LUMINANCE_RANGE))
        self._media_color = change_alpha(
            tuple_to_color(_hue_color(spectrum_ratio, _TINT_LUMINANCE_RANGE)),
            _PREVIEW_CARD_TINT_ALPHA)

    @classmethod
    def _get_content_width(cls) -> int:
        return _PREVIEW_CARD_WIDTH

    @classmethod
    def _get_column_padding(cls) -> int:
        return _PREVIEW_GAP

    def _render_background_rect(self, img: pixie.Image, background_loc: Loc):
        draw_mask_rect(img, background_loc, _CARD_COLOR, 96)

    def _get_render_sections(self) -> list[RenderableSection]:
        section_title = _TitleSection(f"表情包预览 - {self._sticker_id}",
                                      f"PickOne Preview - {self._sticker_id}",
                                      f"共 {self._count} 只")
        section_preview = _PreviewSection(self._text_color, self._media_color,
                                          self._img_key, self._imgs)
        section_tips = _TipsSection(
            f"发送 /来只 {self._img_key} 获取本类别表情包，"
            f"/预览来只 {self._img_key} 加 ID 前缀可直接获取指定表情包.",
            "PickOne Preview")

        return [section_title, section_preview, section_tips]
