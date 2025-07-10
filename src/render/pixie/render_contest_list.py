import math
import time
from datetime import datetime

import pixie
from easy_pixie import StyledString, calculate_height, draw_text, calculate_width, Loc, draw_img, \
    pick_gradient_color, draw_gradient_rect, GradientDirection, draw_mask_rect, darken_color, tuple_to_color, \
    change_alpha, hex_to_color

from src.core.constants import Constants
from src.core.util.tools import format_timestamp, format_timestamp_diff, format_seconds
from src.platform.model import Contest
from src.render.pixie.model import Renderer, RenderableSection

_CONTENT_WIDTH = 1024
_TOP_PADDING = 168
_BOTTOM_PADDING = 128
_SIDE_PADDING = 108
_COLUMN_PADDING = 52
_CONTEST_PADDING = 108
_SECTION_PADDING = 108
_TYPE_PADDING = 128


class _ContestItem(RenderableSection):
    def __init__(self, contest: Contest, idx: int):
        self._contest = contest
        self._idx = idx + 1

        if int(time.time()) >= self._contest.start_time:
            _status = self._contest.phase  # 用于展示"比赛中"，或者诸如 Codeforces 平台的 "正在重测中"
        else:
            _status = format_timestamp_diff(int(time.time()) - self._contest.start_time)

        self._00_idx_text = StyledString(
            "00", 'H', 72
        )
        self._begin_x = _SIDE_PADDING + calculate_width(self._00_idx_text) + 48
        max_width = _CONTENT_WIDTH + 32 - self._begin_x - 48 - _SIDE_PADDING

        self.img_time = Renderer.load_img_resource("Time", (0, 0, 0))
        self.img_info = Renderer.load_img_resource("Info", (0, 0, 0))
        self.img_platform = Renderer.load_img_resource(self._contest.platform, (0, 0, 0))
        self.str_idx = StyledString(
            f"{self._idx:02d}", 'H', 78, font_color=(0, 0, 0, 30), padding_bottom=12
        )
        self.str_subtitle = StyledString(
            f"{self._contest.platform.upper()} · {self._contest.abbr}", 'H', 20,
            max_width=max_width, padding_bottom=12
        )
        self.str_title = StyledString(
            f"{self._contest.name}", 'H', 56, max_width=max_width, padding_bottom=12
        )
        self.str_time = StyledString(
            f"{_status}, {format_timestamp(self._contest.start_time)}", 'M', 32,
            max_width=max_width, padding_bottom=12
        )
        self.str_status = StyledString(
            f"持续 {format_seconds(self._contest.duration)}, {self._contest.supplement}", 'M', 32,
            max_width=max_width, padding_bottom=12
        )

    def get_height(self):
        return calculate_height([self.str_subtitle, self.str_title,
                                 self.str_time, self.str_status])

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = (self._begin_x - _SIDE_PADDING + x -
                                calculate_width(self.str_idx) - 48, y)

        draw_text(img, self.str_idx, current_x, current_y - 14)
        current_x = self._begin_x - _SIDE_PADDING + x

        draw_img(img, self.img_platform, Loc(current_x, current_y + 4, 20, 20))
        current_y = draw_text(img, self.str_subtitle, current_x + 28, current_y)
        current_y = draw_text(img, self.str_title, current_x, current_y)

        draw_img(img, self.img_time, Loc(current_x, current_y + 6, 32, 32))
        current_y = draw_text(img, self.str_time, current_x + 38, current_y)
        draw_img(img, self.img_info, Loc(current_x, current_y + 6, 32, 32))
        current_y = draw_text(img, self.str_status, current_x + 38, current_y)

        return current_y


class _TitleSection(RenderableSection):

    def __init__(self, accent_color: str):
        accent_dark_color = darken_color(hex_to_color(accent_color), 0.3)
        accent_dark_color_tran = change_alpha(accent_dark_color, 136)
        self.img_contest = Renderer.load_img_resource("Contest", accent_dark_color)

        self.str_title = StyledString(
            "近日算法竞赛", 'H', 96, padding_bottom=4, font_color=accent_dark_color
        )
        self.str_subtitle = StyledString(
            "Recent Competitive Programming Competitions", 'H', 28,
            font_color=accent_dark_color_tran
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_img(img, self.img_contest, Loc(106, 181, 102, 102))

        current_x, current_y = x, y
        current_y = draw_text(img, self.str_title, 232, current_y)
        current_y = draw_text(img, self.str_subtitle, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_title, self.str_subtitle])


class _ContestsSection(RenderableSection):

    def __init__(self, running_contests: list[Contest], upcoming_contests: list[Contest],
                 finished_contests: list[Contest]):
        mild_ext_color = (0, 0, 0, 192)
        self.section_running = [_ContestItem(contest, idx) for idx, contest in enumerate(running_contests)]
        self.section_upcoming = [_ContestItem(contest, idx) for idx, contest in enumerate(upcoming_contests)]
        self.section_finished = [_ContestItem(contest, idx) for idx, contest in enumerate(finished_contests)]
        self.img_running = Renderer.load_img_resource("Running", mild_ext_color, 1, 192 / 255)
        self.img_pending = Renderer.load_img_resource("Pending", mild_ext_color, 1, 192 / 255)
        self.img_ended = Renderer.load_img_resource("Ended", mild_ext_color, 1, 192 / 255)

        self.str_none_title = StyledString(
            "最近没有比赛，放松一下吧", 'H', 52, padding_bottom=72
        )
        self.str_running_title = StyledString(
            "RUNNING 正在进行", 'H', 52, padding_bottom=72, font_color=mild_ext_color
        )
        self.str_upcoming_title = StyledString(
            "PENDING 即将进行", 'H', 52, padding_bottom=72, font_color=mild_ext_color
        )
        self.str_finished_title = StyledString(
            "ENDED 已结束", 'H', 52, padding_bottom=72, font_color=mild_ext_color
        )
        self._column = self.get_columns()

    def get_columns(self):
        max_column = 0
        for contest_len in [len(self.section_running),
                            len(self.section_upcoming), len(self.section_finished)]:
            if contest_len > 12:
                max_column = max(max_column, 3)
            elif contest_len > 5:
                max_column = max(max_column, 2)
            else:
                max_column = max(max_column, 1)
        return max_column

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        if (len(self.section_running) == 0 and
                len(self.section_upcoming) == 0 and len(self.section_finished) == 0):
            current_y = draw_text(img, self.str_none_title, current_x, current_y)
        else:
            current_y -= _TYPE_PADDING
            for _contests, _type_logo_path, _type_title_text in [
                (self.section_running, self.img_running, self.str_running_title),
                (self.section_upcoming, self.img_pending, self.str_upcoming_title),
                (self.section_finished, self.img_ended, self.str_finished_title)
            ]:
                if len(_contests) > 0:
                    current_y += _TYPE_PADDING
                    draw_img(img, _type_logo_path, Loc(current_x, current_y + 10, 50, 50))
                    current_y = draw_text(img, _type_title_text, current_x + 50 + 28, current_y)
                    column_count = math.ceil(len(_contests) / self._column)  # 其实不一定合理，因为item高度不固定
                    current_y -= _CONTEST_PADDING
                    start_y, max_y, current_col = current_y, current_y, 0
                    for idx, contest in enumerate(_contests):
                        current_y += _CONTEST_PADDING
                        current_y = contest.render(
                            img,
                            current_x + (_CONTENT_WIDTH + _COLUMN_PADDING) * current_col,
                            current_y
                        )
                        max_y = max(max_y, current_y)
                        if (idx + 1) % column_count == 0:  # 分栏
                            current_col += 1
                            current_y = start_y
                    current_y = max_y

        return current_y

    def get_height(self):
        height = 0
        if max(len(self.section_upcoming), len(self.section_running), len(self.section_finished)) == 0:
            height += calculate_height(self.str_none_title)
        else:
            height -= _TYPE_PADDING
            for _contests, _type_title_text in [(self.section_running, self.str_running_title),
                                                (self.section_upcoming, self.str_upcoming_title),
                                                (self.section_finished, self.str_finished_title)]:
                if len(_contests) > 0:
                    height += calculate_height(_type_title_text)
                    column_count = math.ceil(len(_contests) / self._column)
                    column_split = [_contests[i:i + column_count] for i in range(0, len(_contests), column_count)]
                    height += max(sum(contest.get_height() for contest in column)
                                  for column in column_split) + _TYPE_PADDING
                    height += _CONTEST_PADDING * (column_count - 1)  # 各比赛间的 padding
        return height


class _CopyrightSection(RenderableSection):

    def __init__(self, gradient_color_name: str):
        mild_text_color = (0, 0, 0, 136)
        self.str_tips_title = StyledString(
            "Tips:", 'H', 36, padding_bottom=64, font_color=(0, 0, 0, 208)
        )
        self.str_tips_detail = StyledString(
            "数据源于平台数据爬取/API调用/手动填写，仅供参考", 'M', 28, line_multiplier=1.32,
            max_width=(_CONTENT_WIDTH - 108 -  # 考虑右边界，不然画出去了
                       calculate_width(self.str_tips_title) - 12 - 48),
            padding_bottom=64, font_color=(0, 0, 0, 208)
        )
        self.str_generator = StyledString(
            "Contest List Renderer", 'H', 36, font_color=(0, 0, 0, 208), padding_bottom=16
        )
        self.str_generator_info = StyledString(
            f'Generated at {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}.\n'
            f'Initiated by OBot\'s ACM {Constants.core_version}.\n'
            f'{gradient_color_name}.', 'B', 20, line_multiplier=1.32, font_color=mild_text_color
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        draw_text(img, self.str_tips_title, current_x, current_y)
        current_y = draw_text(img, self.str_tips_detail,
                              current_x + calculate_width(self.str_tips_title) + 12,
                              current_y + 8)
        current_y = draw_text(img, self.str_generator, current_x, current_y)
        draw_text(img, self.str_generator_info, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_tips_title, self.str_generator, self.str_generator_info])


class ContestListRenderer(Renderer):
    """渲染比赛列表"""

    def __init__(self, running_contests: list[Contest], upcoming_contests: list[Contest],
                 finished_contests: list[Contest]):
        self._running_contests = running_contests
        self._upcoming_contests = upcoming_contests
        self._finished_contests = finished_contests

    def render(self) -> pixie.Image:
        gradient_color = pick_gradient_color()

        section_title = _TitleSection(gradient_color.color_list[-1])
        section_contests = _ContestsSection(self._running_contests,
                                            self._upcoming_contests, self._finished_contests)
        section_copyright = _CopyrightSection(gradient_color.name)

        render_sections = [section_title, section_contests, section_copyright]
        max_column = max(section.get_columns() for section in render_sections)

        width, height = (_CONTENT_WIDTH * max_column + _SECTION_PADDING * (max_column - 1),
                         sum(section.get_height() for section in render_sections) +
                         _SECTION_PADDING * (len(render_sections) - 1) +
                         _TOP_PADDING + _BOTTOM_PADDING)

        img = pixie.Image(width + 64, height + 64)
        img.fill(tuple_to_color((0, 0, 0)))  # 填充黑色背景

        draw_gradient_rect(img, Loc(32, 32, width, height), gradient_color,
                           GradientDirection.DIAGONAL_RIGHT_TO_LEFT, 96)
        draw_mask_rect(img, Loc(32, 32, width, height), (255, 255, 255, 178), 96)

        current_x, current_y = _SIDE_PADDING, _TOP_PADDING - _SECTION_PADDING

        for section in render_sections:
            current_y += _SECTION_PADDING
            current_y = section.render(img, current_x, current_y)

        return img
