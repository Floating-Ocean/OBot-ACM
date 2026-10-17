from dataclasses import dataclass

import pixie
from easy_pixie import StyledString, calculate_height, calculate_width, draw_gradient_rect, \
    draw_mask_rect, draw_text, GradientColor, GradientDirection, Loc

from src.core.constants import Constants
from src.render.pixie.model import RenderableSection, SimpleCardRenderer

_CONTENT_WIDTH = 916
_MAX_VISIBLE_RECORDS = 12  # 历史太长时只画最近若干条，避免图片被无限拉高

# 深色宇宙风配色
_TEXT_COLOR = (255, 255, 255, 244)
_MUTED_COLOR = (255, 255, 255, 152)
_FAINT_COLOR = (255, 255, 255, 124)
_PANEL_COLOR = (255, 255, 255, 8)
_PANEL_LATEST_COLOR = (255, 255, 255, 16)
_TILE_COLOR = (255, 255, 255, 20)
_TILE_TEXT_COLOR = (255, 255, 255, 244)
_INDEX_COLOR = (255, 255, 255, 116)
_GOLD_COLOR = (250, 204, 21)
_GOLD_PANEL_COLOR = (250, 204, 21, 16)
_RESULT_CHIP_COLOR = (255, 255, 255, 20)

_A_COLOR = (130, 205, 178)  # A：位置正确 -> 低饱和浅绿
_B_COLOR = (230, 198, 130)  # B：数字正确 -> 低饱和浅黄

_STATUS_STYLE = {
    'playing': ('进行中', (129, 140, 248)),
    'won': ('猜中了', (52, 211, 153)),
    'ended': ('已结束', (148, 148, 164)),
}
_STATUS_CHIP_HEIGHT = 48
_STATUS_CHIP_PADDING = 20
_STATUS_DOT_SIZE = 9
_STATUS_DOT_GAP = 10

# 行布局
_ROW_PADDING = 14
_ROW_GAP = 12
_ROW_RADIUS = 28
_ROW_CONTENT_PADDING = 30
_INDEX_WIDTH = 46
_TILE_WIDTH = 80
_TILE_HEIGHT = 88
_TILE_GAP = 10
_TILE_RADIUS = 20
_DIGIT_SIZE = 54
_RESULT_TEXT_SIZE = 34
_RESULT_CHIP_HEIGHT = 54
_RESULT_CHIP_PADDING = 22
_RESULT_TEXT_GAP = 14
_RESULT_GAP = 24
_ROW_HEIGHT = _TILE_HEIGHT + _ROW_PADDING * 2
_RESULT_SLOT_WIDTHS = {
    suffix: max(int(calculate_width(StyledString(f"{digit}{suffix}", 'H', _RESULT_TEXT_SIZE)))
                for digit in range(10))
    for suffix in "AB"
}

# 分块间距
_TITLE_SUBTITLE_GAP = 10
_SECTION_HEADER_GAP = 18
_EMPTY_PANEL_HEIGHT = 132
_ANSWER_PANEL_HEIGHT = 168
_BODY_GAP = 56       # 标题 / 答案 / 历史之间
_FOOTER_GAP = 84     # 历史与页脚之间


@dataclass(frozen=True)
class Guess1A2BRecord:
    """一次猜测的记录"""
    guess: str
    a: int
    b: int


def _draw_centered_text(img: pixie.Image, text: StyledString, center_x: int, y: int):
    draw_text(img, text, center_x - int(calculate_width(text)) // 2, y)


_ink_bounds_cache: dict[tuple[str, int], tuple[float, float, float, float]] = {}


def _get_ink_bounds(text: StyledString) -> tuple[float, float, float, float]:
    key = (text.content, int(text.font.size))
    if key not in _ink_bounds_cache:
        bounds = text.font.typeset(text.content).compute_bounds()
        _ink_bounds_cache[key] = (bounds.x, bounds.y, bounds.w, bounds.h)
    return _ink_bounds_cache[key]


def _draw_ink_centered(img: pixie.Image, text: StyledString,
                       left: float, top: float, width: float, height: float):
    """按实际墨迹包围盒把文本居中，避免不同字形的留白导致视觉偏移"""
    ink_x, ink_y, ink_w, ink_h = _get_ink_bounds(text)
    draw_text(img, text, left + (width - ink_w) / 2 - ink_x,
              top + (height - ink_h) / 2 - ink_y)


def _draw_digit_tile(img: pixie.Image, x: int, y: int, digit: StyledString):
    draw_mask_rect(img, Loc(x, y, _TILE_WIDTH, _TILE_HEIGHT), _TILE_COLOR, _TILE_RADIUS)
    _draw_ink_centered(img, digit, x, y, _TILE_WIDTH, _TILE_HEIGHT)


class _TitleSection(RenderableSection):
    """标题、状态徽章与一行副标题"""

    def __init__(self, target_len: int, records: list[Guess1A2BRecord],
                 answer: str, correct: bool):
        status_key = 'playing' if not answer else ('won' if correct else 'ended')

        self.str_title = StyledString("1A2B", 'H', 96, font_color=_TEXT_COLOR)

        trials = len(records)
        if status_key == 'playing':
            subtitle = f"目标为 {target_len} 位数 · 已猜 {trials} 次"
        elif status_key == 'won':
            subtitle = f"恭喜你猜中了答案，本轮共猜 {trials} 次"
        else:
            subtitle = f"游戏已结束，本轮共猜 {trials} 次"

        self.str_subtitle = StyledString(
            subtitle, 'B', 28, font_color=_MUTED_COLOR, line_multiplier=1.25,
            max_width=_CONTENT_WIDTH
        )

        status_text, status_color = _STATUS_STYLE[status_key]
        self.str_status = StyledString(status_text, 'H', 26, font_color=(255, 255, 255, 232))
        self._status_width = (_STATUS_CHIP_PADDING * 2 + _STATUS_DOT_SIZE + _STATUS_DOT_GAP +
                              int(calculate_width(self.str_status)))
        self._status_height = _STATUS_CHIP_HEIGHT
        self._status_color = status_color

        self._title_height = max(self.str_title.height, self._status_height)

    def get_height(self):
        return self._title_height + _TITLE_SUBTITLE_GAP + self.str_subtitle.height

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_text(img, self.str_title, x, y)

        status_x = x + _CONTENT_WIDTH - self._status_width
        status_y = y + (self._title_height - self._status_height) // 2
        draw_mask_rect(img, Loc(status_x, status_y, self._status_width, self._status_height),
                       _RESULT_CHIP_COLOR, self._status_height // 2)
        dot_y = status_y + (self._status_height - _STATUS_DOT_SIZE) // 2
        draw_mask_rect(img, Loc(status_x + _STATUS_CHIP_PADDING, dot_y,
                                _STATUS_DOT_SIZE, _STATUS_DOT_SIZE),
                       self._status_color, _STATUS_DOT_SIZE // 2)
        draw_text(img, self.str_status,
                  status_x + _STATUS_CHIP_PADDING + _STATUS_DOT_SIZE + _STATUS_DOT_GAP,
                  status_y + (self._status_height - self.str_status.height) // 2)

        return draw_text(img, self.str_subtitle, x,
                         y + self._title_height + _TITLE_SUBTITLE_GAP)


class _RecordRow(RenderableSection):
    """一条猜测记录：序号 + 数字方块 + xAyB 结果"""

    def __init__(self, index: int, record: Guess1A2BRecord, latest: bool, won: bool):
        self._latest = latest
        self._won = won

        self.str_index = StyledString(f"{index:02d}", 'H', 24, font_color=_INDEX_COLOR)
        self.str_digits = [StyledString(digit, 'H', _DIGIT_SIZE, font_color=_TILE_TEXT_COLOR)
                           for digit in record.guess]
        self._digit_width = (len(record.guess) * _TILE_WIDTH +
                             (len(record.guess) - 1) * _TILE_GAP)

        self.str_a = StyledString(f"{record.a}A", 'H', _RESULT_TEXT_SIZE,
                                  font_color=_A_COLOR)
        self.str_b = StyledString(f"{record.b}B", 'H', _RESULT_TEXT_SIZE,
                                  font_color=_B_COLOR)
        self._a_slot_width = _RESULT_SLOT_WIDTHS['A']
        self._b_slot_width = _RESULT_SLOT_WIDTHS['B']
        self._result_width = (self._a_slot_width + self._b_slot_width +
                              _RESULT_TEXT_GAP + _RESULT_CHIP_PADDING * 2)

    def get_height(self):
        return _ROW_HEIGHT

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        panel_color = _GOLD_PANEL_COLOR if self._won else (
            _PANEL_LATEST_COLOR if self._latest else _PANEL_COLOR)
        draw_mask_rect(img, Loc(x, y, _CONTENT_WIDTH, _ROW_HEIGHT), panel_color, _ROW_RADIUS)

        content_x = x + _ROW_CONTENT_PADDING

        # 序号
        _draw_ink_centered(img, self.str_index, content_x, y, _INDEX_WIDTH, _ROW_HEIGHT)

        # 数字方块在「序号」与「结果」之间居中
        chip_x = x + _CONTENT_WIDTH - _ROW_CONTENT_PADDING - self._result_width
        digits_region_left = content_x + _INDEX_WIDTH
        digits_region_right = chip_x - _RESULT_GAP
        digits_x = digits_region_left + (
            digits_region_right - digits_region_left - self._digit_width) // 2
        tile_y = y + _ROW_PADDING
        for idx, str_digit in enumerate(self.str_digits):
            tile_x = digits_x + idx * (_TILE_WIDTH + _TILE_GAP)
            _draw_digit_tile(img, tile_x, tile_y, str_digit)

        # xAyB 结果：单块低调的玻璃底，A/B 各占固定列宽，保证逐行上下对齐
        chip_y = y + (_ROW_HEIGHT - _RESULT_CHIP_HEIGHT) // 2
        draw_mask_rect(img, Loc(chip_x, chip_y, self._result_width, _RESULT_CHIP_HEIGHT),
                       _RESULT_CHIP_COLOR, _RESULT_CHIP_HEIGHT // 2)
        _draw_ink_centered(img, self.str_a, chip_x + _RESULT_CHIP_PADDING, chip_y,
                           self._a_slot_width, _RESULT_CHIP_HEIGHT)
        _draw_ink_centered(img, self.str_b,
                           chip_x + _RESULT_CHIP_PADDING + self._a_slot_width + _RESULT_TEXT_GAP,
                           chip_y, self._b_slot_width, _RESULT_CHIP_HEIGHT)

        return y + _ROW_HEIGHT


class _HistorySection(RenderableSection):
    """猜测历史，按时间顺序从上到下排列，最新一条在底部高亮"""

    def __init__(self, records: list[Guess1A2BRecord], answer: str, correct: bool):
        visible_records = records[-_MAX_VISIBLE_RECORDS:]
        hidden_cnt = len(records) - len(visible_records)

        self._finished = bool(answer)
        self.str_header = StyledString("猜测历史", 'H', 28, font_color=_TEXT_COLOR)
        count_text = f"共 {len(records)} 次" if hidden_cnt == 0 else (
            f"共 {len(records)} 次 · 仅显示最近 {len(visible_records)} 次")
        self.str_count = StyledString(count_text, 'B', 24, font_color=_MUTED_COLOR)

        won_index = len(records) - 1 if correct else -1
        first_index = len(records) - len(visible_records)
        self._rows = [
            _RecordRow(first_index + offset + 1, record,
                       latest=(first_index + offset == len(records) - 1),
                       won=(first_index + offset == won_index))
            for offset, record in enumerate(visible_records)
        ]
        self._empty = len(self._rows) == 0

    def get_height(self):
        header_height = max(self.str_header.height, self.str_count.height)
        if self._empty:
            return header_height + _SECTION_HEADER_GAP + _EMPTY_PANEL_HEIGHT
        rows_height = (sum(row.get_height() for row in self._rows) +
                       _ROW_GAP * (len(self._rows) - 1))
        return header_height + _SECTION_HEADER_GAP + rows_height

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_text(img, self.str_header, x, y)
        draw_text(img, self.str_count,
                  x + _CONTENT_WIDTH - int(calculate_width(self.str_count)),
                  y + self.str_header.height - self.str_count.height - 4)

        current_y = y + max(self.str_header.height, self.str_count.height)

        if self._empty:
            current_y += _SECTION_HEADER_GAP
            draw_mask_rect(img, Loc(x, current_y, _CONTENT_WIDTH, _EMPTY_PANEL_HEIGHT),
                           _PANEL_COLOR, _ROW_RADIUS)
            str_empty = StyledString("本轮没有猜测记录" if self._finished else "还没有猜测记录",
                                     'H', 34, font_color=_MUTED_COLOR)
            str_hint = StyledString("发送 /1a2b 开始新一轮" if self._finished
                                    else "发送 /1a2b [数字] 开始游戏",
                                    'B', 26, font_color=_FAINT_COLOR)
            content_height = calculate_height([str_empty, str_hint]) + 12
            content_y = current_y + (_EMPTY_PANEL_HEIGHT - content_height) // 2
            _draw_centered_text(img, str_empty, x + _CONTENT_WIDTH // 2, content_y)
            _draw_centered_text(img, str_hint, x + _CONTENT_WIDTH // 2,
                                content_y + str_empty.height + 12)
            return y + self.get_height()

        current_y += _SECTION_HEADER_GAP

        for row in self._rows:
            current_y = row.render(img, x, current_y) + _ROW_GAP

        return current_y - _ROW_GAP


class _AnswerSection(RenderableSection):
    """游戏结束时展示答案"""

    def __init__(self, answer: str, correct: bool):
        self._correct = correct

        self.str_title = StyledString("本轮答案", 'H', 28, font_color=_TEXT_COLOR)
        self.str_note = StyledString(
            "恭喜猜中！" if correct else "游戏已终止",
            'B', 26, font_color=_GOLD_COLOR if correct else _MUTED_COLOR)
        self.str_digits = [StyledString(digit, 'H', _DIGIT_SIZE,
                                        font_color=_GOLD_COLOR if correct else _TEXT_COLOR)
                           for digit in answer]
        self._digits_width = (len(answer) * _TILE_WIDTH +
                              (len(answer) - 1) * _TILE_GAP)

    def get_height(self):
        return self.str_title.height + _SECTION_HEADER_GAP + _ANSWER_PANEL_HEIGHT

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_text(img, self.str_title, x, y)
        draw_text(img, self.str_note,
                  x + _CONTENT_WIDTH - int(calculate_width(self.str_note)),
                  y + self.str_title.height - self.str_note.height - 2)

        panel_y = y + self.str_title.height + _SECTION_HEADER_GAP
        panel_color = _GOLD_PANEL_COLOR if self._correct else _PANEL_COLOR
        draw_mask_rect(img, Loc(x, panel_y, _CONTENT_WIDTH, _ANSWER_PANEL_HEIGHT),
                       panel_color, _ROW_RADIUS)

        # 答案数字块在面板中水平、垂直居中，四周留出足够边距
        digits_x = x + (_CONTENT_WIDTH - self._digits_width) // 2
        tile_y = panel_y + (_ANSWER_PANEL_HEIGHT - _TILE_HEIGHT) // 2
        for idx, str_digit in enumerate(self.str_digits):
            tile_x = digits_x + idx * (_TILE_WIDTH + _TILE_GAP)
            _draw_digit_tile(img, tile_x, tile_y, str_digit)

        return panel_y + _ANSWER_PANEL_HEIGHT


class _FooterSection(RenderableSection):

    def __init__(self):
        self.str_rule = StyledString(
            "xAyB：A 表示数字与位置都正确，B 表示数字正确但位置不对",
            'B', 23, font_color=_FAINT_COLOR, line_multiplier=1.3,
            max_width=_CONTENT_WIDTH
        )
        self.str_note = StyledString(
            f"A game included in OBot's ACM {Constants.core_version}.",
            'B', 21, font_color=_FAINT_COLOR, line_multiplier=1.3,
            max_width=_CONTENT_WIDTH
        )

    def get_height(self):
        return calculate_height([self.str_rule, self.str_note]) + 6

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_y = draw_text(img, self.str_rule, x, y)
        return draw_text(img, self.str_note, x, current_y + 6)


class _BodySection(RenderableSection):
    """把标题、答案、历史、页脚收进同一个分块，方便自行控制各块之间的间距"""

    def __init__(self, children: list[tuple[int, RenderableSection]]):
        self._children = children

    def get_height(self):
        return (sum(section.get_height() for _, section in self._children) +
                sum(gap for gap, _ in self._children))

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_y = y
        for gap, section in self._children:
            current_y = section.render(img, x, current_y + gap)
        return current_y


class Guess1A2BRenderer(SimpleCardRenderer):
    """渲染 1A2B 猜数字的对局状态与猜测历史"""

    def __init__(self, target_len: int, records: list[Guess1A2BRecord],
                 answer: str = "", correct: bool = False):
        super().__init__()

        self._target_len = target_len
        self._records = list(records)
        self._answer = answer
        self._correct = correct
        # 固定的深色渐变，同一局游戏中每次出图观感一致
        self._gradient_color = GradientColor(
            ["#1e1b4b", "#4c1d95", "#0f172a"], [0.0, 0.55, 1.0], "Guess-1A2B")

    def _render_background_rect(self, img: pixie.Image, background_loc: Loc):
        draw_gradient_rect(img, background_loc, self._gradient_color,
                           GradientDirection.DIAGONAL_LEFT_TO_RIGHT, 96)
        # 再压一层暗色蒙版：紫色更暗，黄色/彩色元素才不会显得浮在亮紫上
        draw_mask_rect(img, background_loc, (8, 6, 20, 215), 96)

    def _get_render_sections(self) -> list[RenderableSection]:
        children: list[tuple[int, RenderableSection]] = [
            (0, _TitleSection(self._target_len, self._records,
                              self._answer, self._correct))
        ]
        if self._answer:
            children.append((_BODY_GAP, _AnswerSection(self._answer, self._correct)))
        children.append((_BODY_GAP,
                         _HistorySection(self._records, self._answer, self._correct)))
        children.append((_FOOTER_GAP, _FooterSection()))
        return [_BodySection(children)]
