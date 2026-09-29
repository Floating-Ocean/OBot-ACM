from dataclasses import dataclass, field
from datetime import datetime

import pixie
from PIL import Image
from easy_pixie import StyledString, calculate_height, calculate_width, draw_text, Loc, draw_img, \
    draw_mask_rect, draw_gradient_rect, GradientColor, GradientDirection, darken_color, \
    lighten_color, change_alpha, hex_to_color

from src.core.constants import Constants
from src.core.util.output_cache import get_cached_prefix
from src.core.util.tools import download_img
from src.render.pixie.model import Renderer, RenderableSection, SimpleCardRenderer

_CONTENT_WIDTH = 1216
_AVATAR_SIZE = 176
_AVATAR_RADIUS = 44
_AVATAR_GAP = 48
_AVATAR_RING = 7
_HANDLE_GAP = 24
_DETAIL_GAP = 28

_CONTENT_COLOR = (0, 0, 0, 208)
_BODY_COLOR = (0, 0, 0, 172)
_MUTED_COLOR = (0, 0, 0, 116)

_BAND_PADDING = 60
_BAND_SIDE_PADDING = 64
_BAND_RADIUS = 48
_RATING_SIZE = 168
_RATING_MIN_SIZE = 108
_RANK_SIZE = 40
_RANK_MIN_SIZE = 28

_CELL_HEIGHT = 168
_CELL_GAP = 32
_CELL_RADIUS = 36
_CELL_SIDE_PADDING = 40
_CELL_VERTICAL_PADDING = 36
_CELL_COLOR = (255, 255, 255, 136)
_CELL_VALUE_SIZE = 56
_CELL_VALUE_MIN_SIZE = 40
_CELL_LABEL_SIZE = 26
_SECTION_PADDING = 88


@dataclass
class UserCardSection:
    """名片中的一段文字信息"""
    title: str
    lines: list[str]


@dataclass
class UserCardInfo:
    """渲染一张用户信息名片所需的全部数据"""
    platform_name: str
    handle: str
    accent_color: str
    rating: str
    rank: str
    rating_note: str = ""
    avatar_url: str | None = None
    social: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    metrics: list[tuple[str, str]] = field(default_factory=list)
    sections: list[UserCardSection] = field(default_factory=list)


def _load_avatar(url: str | None, size: int = _AVATAR_SIZE) -> pixie.Image | None:
    """下载头像并裁为圆角正方形，失败时返回 None（名片不因头像缺失而无法渲染）"""
    if not url:
        return None

    try:
        raw_path = f"{get_cached_prefix('User-Card-Avatar')}.png"
        squared_path = f"{get_cached_prefix('User-Card-Avatar')}.png"
        if not download_img(url, raw_path):
            return None

        with Image.open(raw_path) as raw:
            raw.seek(0)  # 动图一律取首帧
            frame = raw.convert("RGBA")
            side = min(frame.width, frame.height)
            frame = frame.crop(((frame.width - side) // 2, (frame.height - side) // 2,
                                (frame.width - side) // 2 + side,
                                (frame.height - side) // 2 + side))
            if side != size:
                frame = frame.resize((size, size), Image.Resampling.LANCZOS)
            frame.save(squared_path, format="PNG")

        avatar = pixie.read_image(squared_path)
        mask = pixie.Mask(size, size)
        path = pixie.Path()
        path.rounded_rect(0, 0, size, size,
                          _AVATAR_RADIUS, _AVATAR_RADIUS, _AVATAR_RADIUS, _AVATAR_RADIUS)
        mask.fill_path(path)
        avatar.mask_draw(mask)
        return avatar

    except Exception as e:
        Constants.log.warning("[render] 加载用户头像失败")
        Constants.log.exception(f"[render] {e}")
        return None


def _fit_styled_string(content: str, weight: str, max_size: int, min_size: int,
                       max_width: int, **kwargs) -> StyledString:
    """字号从 max_size 逐级下降，直到文本宽度不超过 max_width"""
    size = max_size
    while size > min_size:
        candidate = StyledString(content, weight, size, **kwargs)
        if calculate_width(candidate) <= max_width:
            return candidate
        size -= 2
    return StyledString(content, weight, min_size, **kwargs)


class _IdentitySection(RenderableSection):
    """头像与身份信息

    头像与「平台 + handle」两行同高对齐，其余信息另起整行铺满宽度，
    这样左右两侧始终等高，也不会因为补充信息换行把头像挤成半截。
    """

    def __init__(self, info: UserCardInfo, text_color: pixie.Color):
        self.img_platform = Renderer.load_img_resource(info.platform_name, text_color,
                                                       size=(36, 36))
        self._avatar = _load_avatar(info.avatar_url)
        self._ring_color = change_alpha(hex_to_color(info.accent_color), alpha=88)

        head_width = _CONTENT_WIDTH
        if self._avatar:
            head_width -= _AVATAR_SIZE + _AVATAR_GAP

        self.str_platform = StyledString(
            f"{info.platform_name} ID", 'H', 36, font_color=text_color, max_width=head_width
        )
        self.str_handle = StyledString(
            info.handle, 'H', 92, font_color=text_color, max_width=head_width
        )
        # 补充信息整行铺满宽度，空文本仍会占一行高度，需要显式跳过
        self.str_social = StyledString(
            ' · '.join(info.social), 'B', 30, font_color=_BODY_COLOR,
            line_multiplier=1.3, padding_bottom=10, max_width=_CONTENT_WIDTH
        )
        self.str_timeline = StyledString(
            ' · '.join(info.timeline), 'B', 26, font_color=_MUTED_COLOR,
            line_multiplier=1.3, max_width=_CONTENT_WIDTH
        )
        self._detail_rows = [row for row in [self.str_social, self.str_timeline]
                             if row.content]

        # 头像与「平台 + handle」两行等高，两侧上下边缘自然对齐
        self._head_height = calculate_height([self.str_platform, self.str_handle]) + _HANDLE_GAP
        if self._avatar:
            self._head_height = max(_AVATAR_SIZE, self._head_height)

    def get_height(self):
        height = self._head_height
        if len(self._detail_rows) > 0:
            height += _DETAIL_GAP + calculate_height(self._detail_rows)
        return height

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x = x
        if self._avatar:
            avatar_y = y + (self._head_height - _AVATAR_SIZE) // 2
            draw_mask_rect(img, Loc(x - _AVATAR_RING, avatar_y - _AVATAR_RING,
                                    _AVATAR_SIZE + _AVATAR_RING * 2,
                                    _AVATAR_SIZE + _AVATAR_RING * 2),
                           self._ring_color, _AVATAR_RADIUS + _AVATAR_RING)
            draw_img(img, self._avatar, Loc(x, avatar_y, _AVATAR_SIZE, _AVATAR_SIZE))
            current_x = x + _AVATAR_SIZE + _AVATAR_GAP

        head_text_height = calculate_height([self.str_platform, self.str_handle]) + _HANDLE_GAP
        current_y = y + (self._head_height - head_text_height) // 2
        draw_img(img, self.img_platform, Loc(current_x, current_y + 6, 36, 36))
        current_y = draw_text(img, self.str_platform, current_x + 36 + 16, current_y)
        draw_text(img, self.str_handle, current_x, current_y + _HANDLE_GAP)

        if len(self._detail_rows) > 0:
            current_y = y + self._head_height + _DETAIL_GAP
            for row in self._detail_rows:
                current_y = draw_text(img, row, x, current_y)

        return y + self.get_height()


class _RatingSection(RenderableSection):
    """Rating 与段位"""

    def __init__(self, info: UserCardInfo, text_color: pixie.Color):
        accent = hex_to_color(info.accent_color)
        self._panel_color = change_alpha(accent, alpha=36)
        self._pill_color = change_alpha(accent, alpha=48)

        self.str_label = StyledString(
            "比赛 Rating", 'M', 30, font_color=_MUTED_COLOR, padding_bottom=10
        )
        self.str_rank = _fit_styled_string(info.rank, 'H', _RANK_SIZE, _RANK_MIN_SIZE,
                                           _CONTENT_WIDTH // 2, font_color=darken_color(accent, 0.5))
        self._rank_text_width = calculate_width(self.str_rank)
        self._rank_text_height = calculate_height(self.str_rank)
        self._pill_width = int(self._rank_text_width) + 56
        self._pill_height = int(self._rank_text_height) + 28
        # 大号数字需要给右侧段位徽章留出位置
        self.str_rating = _fit_styled_string(
            info.rating, 'H', _RATING_SIZE, _RATING_MIN_SIZE,
            max(256, _CONTENT_WIDTH - _BAND_SIDE_PADDING * 2 - self._pill_width - 72),
            font_color=text_color
        )
        self.str_note = StyledString(
            info.rating_note, 'B', 28, font_color=_MUTED_COLOR, max_width=720
        )
        self._note_text_width = calculate_width(self.str_note)
        self._note_text_height = calculate_height(self.str_note)

        self._left_height = calculate_height([self.str_label, self.str_rating])
        self._right_height = self._pill_height + 22 + (
            self._note_text_height if info.rating_note else 0)
        # 段位徽章与左侧大号数字顶部对齐，不随字号自适应上下浮动
        self._right_offset = calculate_height(self.str_label) + 28

    def get_height(self):
        return (max(self._left_height, self._right_offset + self._right_height)
                + _BAND_PADDING * 2 - 20)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        height = self.get_height()
        draw_mask_rect(img, Loc(x, y, _CONTENT_WIDTH, height), self._panel_color, _BAND_RADIUS)

        current_y = y + _BAND_PADDING
        current_y = draw_text(img, self.str_label, x + _BAND_SIDE_PADDING, current_y)
        draw_text(img, self.str_rating, x + _BAND_SIDE_PADDING - 8, current_y)

        right = x + _CONTENT_WIDTH - _BAND_SIDE_PADDING
        current_y = y + _BAND_PADDING + self._right_offset
        pill_x = right - self._rank_text_width - 28
        draw_mask_rect(img, Loc(pill_x, current_y, self._pill_width, self._pill_height),
                       self._pill_color, self._pill_height // 2)
        draw_text(img, self.str_rank,
                  pill_x + (self._pill_width - self._rank_text_width) // 2,
                  current_y + 14)
        current_y += self._pill_height + 22
        if self.str_note.content:
            draw_text(img, self.str_note, right - self._note_text_width, current_y)

        return y + height


class _MetricsSection(RenderableSection):
    """数据指标格子

    所有数值共用同一字号，宁可整组缩小也不让单个格子变小，避免大小参差；
    格子高度按内容自适应，实在放不下时换行而不是溢出或省略。
    """

    def __init__(self, metrics: list[tuple[str, str]]):
        self._cols = max(1, len(metrics)) if len(metrics) <= 4 else (
            3 if len(metrics) % 3 == 0 else 4)
        self._cell_width = ((_CONTENT_WIDTH - _CELL_GAP * (self._cols - 1)) // self._cols
                            if metrics else 0)
        inner_width = self._cell_width - _CELL_SIDE_PADDING * 2

        self._value_size = self._pick_value_size([value for _, value in metrics], inner_width)
        self._cells = [
            (StyledString(value, 'H', self._value_size, font_color=_CONTENT_COLOR,
                          max_width=inner_width, padding_bottom=6),
             StyledString(label, 'B', _CELL_LABEL_SIZE, font_color=_MUTED_COLOR,
                          max_width=inner_width))
            for label, value in metrics
        ]
        self._row_height = max(
            _CELL_HEIGHT,
            max((calculate_height([value, label]) for value, label in self._cells), default=0)
            + _CELL_VERTICAL_PADDING * 2
        )

    @classmethod
    def _pick_value_size(cls, values: list[str], inner_width: int) -> int:
        size = _CELL_VALUE_SIZE
        while size > _CELL_VALUE_MIN_SIZE:
            if all(calculate_width(StyledString(value, 'H', size)) <= inner_width
                   for value in values):
                break
            size -= 2
        return size

    def get_height(self):
        if not self._cells:
            return 0
        rows = (len(self._cells) + self._cols - 1) // self._cols
        return rows * self._row_height + (rows - 1) * _CELL_GAP

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        if not self._cells:
            return y

        for idx, (str_value, str_label) in enumerate(self._cells):
            row, col = divmod(idx, self._cols)
            cell_x = x + col * (self._cell_width + _CELL_GAP)
            cell_y = y + row * (self._row_height + _CELL_GAP)
            draw_mask_rect(img, Loc(cell_x, cell_y, self._cell_width, self._row_height),
                           _CELL_COLOR, _CELL_RADIUS)

            content_height = calculate_height([str_value, str_label])
            content_y = cell_y + (self._row_height - content_height) // 2
            draw_text(img, str_value, cell_x + _CELL_SIDE_PADDING, content_y)
            draw_text(img, str_label, cell_x + _CELL_SIDE_PADDING,
                      content_y + calculate_height(str_value))

        return y + self.get_height()


class _DetailSection(RenderableSection):
    """带标题的补充信息块"""

    def __init__(self, section: UserCardSection, accent_color: pixie.Color):
        self._bar_color = change_alpha(accent_color, alpha=108)
        self.str_title = StyledString(
            section.title, 'H', 34, font_color=_CONTENT_COLOR, padding_bottom=26
        )
        self.str_lines = [StyledString(line, 'M', 30, font_color=_BODY_COLOR,
                                       line_multiplier=1.3, padding_bottom=10,
                                       max_width=_CONTENT_WIDTH - 28)
                          for line in section.lines]

    def get_height(self):
        return calculate_height(self.str_title) + calculate_height(self.str_lines)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_mask_rect(img, Loc(x, y + 8, 6, 30), self._bar_color, 3)
        current_y = draw_text(img, self.str_title, x + 28, y)
        for str_line in self.str_lines:
            current_y = draw_text(img, str_line, x + 28, current_y)

        return y + self.get_height()


class _FooterSection(RenderableSection):

    def __init__(self, platform_name: str):
        self.str_note = StyledString(
            f'Generated at {datetime.now().strftime("%Y/%m/%d %H:%M:%S")} · '
            f"Data from {platform_name} · "
            f"Initiated by OBot's ACM {Constants.core_version}.",
            'B', 24, font_color=_MUTED_COLOR, line_multiplier=1.3, max_width=_CONTENT_WIDTH
        )

    def get_height(self):
        return 2 + 30 + calculate_height(self.str_note)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_mask_rect(img, Loc(x, y, _CONTENT_WIDTH, 2), (0, 0, 0, 24), 1)
        return draw_text(img, self.str_note, x, y + 30)


class UserCardRenderer(SimpleCardRenderer):
    """渲染用户完整信息名片"""

    def __init__(self, info: UserCardInfo):
        super().__init__()
        accent = hex_to_color(info.accent_color)
        self._accent_color = accent
        self._gradient_color = GradientColor(["#fcfcfc", lighten_color(accent, 0.3)],
                                             [0.0, 1.0], info.accent_color)
        self._info = info
        self._text_color = darken_color(accent, 0.32)

    @classmethod
    def _get_content_width(cls) -> int:
        return _CONTENT_WIDTH

    @classmethod
    def _get_section_padding(cls) -> int:
        return _SECTION_PADDING

    def _render_background_rect(self, img: pixie.Image, background_loc: Loc):
        draw_gradient_rect(img, background_loc, self._gradient_color,
                           GradientDirection.DIAGONAL_LEFT_TO_RIGHT, 96)
        draw_mask_rect(img, background_loc, (255, 255, 255, 152), 96)

    def _get_render_sections(self) -> list[RenderableSection]:
        sections: list[RenderableSection] = [
            _IdentitySection(self._info, self._text_color),
            _RatingSection(self._info, self._text_color),
            _MetricsSection(self._info.metrics)
        ]
        sections.extend(_DetailSection(section, self._accent_color)
                        for section in self._info.sections)
        sections.append(_FooterSection(self._info.platform_name))
        return sections
