import time
from datetime import datetime

import pixie
from easy_pixie import StyledString, calculate_height, draw_text, calculate_width, Loc, draw_img, \
    darken_color, change_alpha, hex_to_color

from src.core.constants import Constants
from src.core.util.tools import format_timestamp, format_timestamp_diff, format_seconds
from src.platform.model import Contest
from src.render.pixie.model import Renderer, RenderableSection, SimpleCardRenderer

_CONTENT_WIDTH = 916
_COLUMN_PADDING = 192
_CONTEST_PADDING = 108
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
        self._00_idx_text_width = calculate_width(self._00_idx_text)
        max_width = _CONTENT_WIDTH - self._00_idx_text_width - 48

        self.img_time = Renderer.load_img_resource("Time", (0, 0, 0), size=(32, 32))
        self.img_info = Renderer.load_img_resource("Info", (0, 0, 0), size=(32, 32))
        self.img_platform = Renderer.load_img_resource(self._contest.platform, (0, 0, 0),
                                                       size=(20, 20))
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
        current_x, current_y = x + self._00_idx_text_width - calculate_width(self.str_idx), y

        draw_text(img, self.str_idx, current_x, current_y - 14)
        current_x = x + self._00_idx_text_width + 48

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
        draw_img(img, self.img_contest, Loc(x - 4, y + 13, 102, 102))

        current_x, current_y = x, y
        current_y = draw_text(img, self.str_title, current_x + 124, current_y)
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
                    current_y -= _CONTEST_PADDING
                    start_y, max_y = current_y, current_y

                    column_split, _ = self._split_columns(_contests, _CONTEST_PADDING)
                    for current_col, _column in enumerate(column_split):
                        current_y = start_y
                        for contest in _column:
                            current_y += _CONTEST_PADDING
                            current_y = contest.render(
                                img,
                                current_x + (_CONTENT_WIDTH + _COLUMN_PADDING) * current_col,
                                current_y
                            )
                            max_y = max(max_y, current_y)

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
                    _, max_height = self._split_columns(_contests, _CONTEST_PADDING)
                    height += calculate_height(_type_title_text)
                    height += max_height + _TYPE_PADDING
        return height


class _CopyrightSection(RenderableSection):

    def __init__(self, gradient_color_name: str):
        mild_text_color = (0, 0, 0, 136)
        self.str_tips_title = StyledString(
            "Tips:", 'H', 36, padding_bottom=64, font_color=(0, 0, 0, 208)
        )
        self.str_tips_detail = StyledString(
            "数据源于平台数据爬取/API调用/手动填写，仅供参考", 'M', 28, line_multiplier=1.32,
            max_width=_CONTENT_WIDTH - calculate_width(self.str_tips_title) - 12,  # 考虑右边界，不然画出去了
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


class ContestListRenderer(SimpleCardRenderer):
    """渲染比赛列表"""

    def __init__(self, running_contests: list[Contest], upcoming_contests: list[Contest],
                 finished_contests: list[Contest]):
        super().__init__()
        self._running_contests = running_contests
        self._upcoming_contests = upcoming_contests
        self._finished_contests = finished_contests

    def _get_render_sections(self) -> list[RenderableSection]:
        section_title = _TitleSection(self._gradient_color.color_list[-1])
        section_contests = _ContestsSection(self._running_contests,
                                            self._upcoming_contests, self._finished_contests)
        section_copyright = _CopyrightSection(self._gradient_color.name)

        return [section_title, section_contests, section_copyright]
