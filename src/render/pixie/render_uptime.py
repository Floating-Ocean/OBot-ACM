from datetime import datetime

import pixie
from easy_pixie import StyledString, calculate_height, draw_text, Loc, draw_img, \
    draw_mask_rect, hex_to_color, calculate_width, darken_color, lighten_color

from src.core.constants import Constants
from src.render.pixie.model import Renderer, RenderableSection, RenderableSvgSection, \
    SimpleCardRenderer
from src.render.svg.render_uptime_status import render_uptime_status, get_percentile_color

_CONTENT_WIDTH = 1472
_UPTIME_SECTION_PADDING = 96
_STATUS_TEXT_DARKEN = 0.66

_STATUS_FONT_SIZE = 28
_BADGE_HEIGHT = 52
_BADGE_PADDING = 20
_BADGE_DOT_SIZE = 28
_BADGE_GAP = 14
_BADGE_TINT = 0.85


class _TitleSection(RenderableSection):

    def __init__(self, down_count: int):
        status_text = "部分服务异常" if down_count > 0 else "所有服务均正常运行"
        status_sub_text = ("Uptime Robot Monitor · Some Systems Down" if down_count > 0 else
                           "Uptime Robot Monitor · All Systems Operational")

        self.img_dot = Renderer.load_img_resource(
            "Dot",
            hex_to_color(get_percentile_color(100 if down_count == 0 else 98))
        )
        self.str_title = StyledString(
            status_text, 'H', 96, padding_bottom=4
        )
        self.str_subtitle = StyledString(
            status_sub_text, 'H', 28,
            font_color=(0, 0, 0, 136)
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_img(img, self.img_dot, Loc(120, 181, 102, 102))

        current_x, current_y = x, y
        current_y = draw_text(img, self.str_title, 242, current_y)
        current_y = draw_text(img, self.str_subtitle, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_title, self.str_subtitle])


class _CopyrightSection(RenderableSection):

    def __init__(self):
        mild_text_color = (0, 0, 0, 156)
        self.str_generator = StyledString(
            "Uptime Robot", 'H', 36, padding_bottom=16,
            font_color=(0, 0, 0, 228)
        )
        self.str_generation_info = StyledString(
            f'Status fetched at {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}.\n'
            f"Initiated by OBot's ACM {Constants.core_version}.",
            'B', 20, line_multiplier=1.32, font_color=mild_text_color
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.str_generator, current_x, current_y)
        current_y = draw_text(img, self.str_generation_info, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_generator, self.str_generation_info])


class _UptimeStatusSection(RenderableSvgSection):

    def _get_max_width(self) -> int:
        return _CONTENT_WIDTH

    def _generate_svg(self) -> tuple[str, int, int]:
        return render_uptime_status(self._current_status)

    def __init__(self, current_status: list[dict], svg_ts_path: str,
                 width: int = -1, height: int = -1):
        self._current_status = current_status
        super().__init__(svg_ts_path, width, height)


class _UptimeMonitorItem(RenderableSection):

    def __init__(self, monitor_status: dict, svg_ts_path: str):
        raw_status = monitor_status["statusClass"]
        status_color = darken_color(
            hex_to_color(get_percentile_color(100 if raw_status == "success" else
                                              0 if raw_status == "danger" else 98)),
            _STATUS_TEXT_DARKEN
        )
        status_info = ("正常" if raw_status == "success" else
                       "异常" if raw_status == "danger" else "暂停")

        # 正常时是淡底彩字，出问题时文字/圆点与底色对调，靠实心色块顶出来
        soft_color = lighten_color(status_color, _BADGE_TINT)
        badge_fg_color = status_color if raw_status == "success" else soft_color
        self._badge_color = soft_color if raw_status == "success" else status_color

        self.str_name = StyledString(
            monitor_status["name"], 'H', 40, padding_bottom=18
        )
        self.str_status = StyledString(
            status_info, 'H', _STATUS_FONT_SIZE, font_color=badge_fg_color
        )
        self._badge_width = (_BADGE_PADDING * 2 + _BADGE_DOT_SIZE + _BADGE_GAP +
                             int(calculate_width(self.str_status)))
        self.section_status = _UptimeStatusSection(monitor_status["dailyRatios"], svg_ts_path)
        self.img_dot = Renderer.load_img_resource("Dot", badge_fg_color)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_text(img, self.str_name, x, y)

        badge_x = x + _CONTENT_WIDTH - self._badge_width
        badge_y = y + (self.str_name.height - self.str_name.padding_bottom -
                       _BADGE_HEIGHT) // 2
        draw_mask_rect(img, Loc(badge_x, badge_y, self._badge_width, _BADGE_HEIGHT),
                       self._badge_color, _BADGE_HEIGHT // 2)
        draw_img(img, self.img_dot, Loc(badge_x + _BADGE_PADDING,
                                        badge_y + (_BADGE_HEIGHT - _BADGE_DOT_SIZE) // 2,
                                        _BADGE_DOT_SIZE, _BADGE_DOT_SIZE))
        draw_text(img, self.str_status,
                  badge_x + _BADGE_PADDING + _BADGE_DOT_SIZE + _BADGE_GAP,
                  badge_y + (_BADGE_HEIGHT - self.str_status.height) // 2)

        return self.section_status.render(img, x, y + self.str_name.height)

    def get_height(self):
        return (max(self.str_name.height, _BADGE_HEIGHT) +
                self.section_status.get_height())


class _UptimeMonitorSection(RenderableSection):

    def __init__(self, monitors: list[dict], svg_ts_path: str):
        self.section_monitor_items = [_UptimeMonitorItem(monitor, f'{svg_ts_path}_{d}')
                                      for d, monitor in enumerate(monitors)]

    def get_height(self):
        return (sum(monitor.get_height() for monitor in self.section_monitor_items) +
                _UPTIME_SECTION_PADDING * max(0, len(self.section_monitor_items) - 1))

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        current_y -= _UPTIME_SECTION_PADDING
        for monitor in self.section_monitor_items:
            current_y += _UPTIME_SECTION_PADDING
            current_y = monitor.render(img, current_x, current_y)

        return current_y


class UptimeRenderer(SimpleCardRenderer):
    """渲染服务状态"""

    def __init__(self, current_status: dict, svg_ts_path: str):
        super().__init__()
        self._current_status = current_status
        self._svg_ts_path = svg_ts_path

    @classmethod
    def _get_content_width(cls) -> int:
        return _CONTENT_WIDTH

    def _render_background_rect(self, img: pixie.Image, background_loc: Loc):
        draw_mask_rect(img, background_loc, (252, 252, 252), 96)

    def _get_render_sections(self) -> list[RenderableSection]:
        section_title = _TitleSection(self._current_status["statistics"]["counts"]["down"])
        section_uptime_monitor = _UptimeMonitorSection(self._current_status["psp"]["monitors"],
                                                       self._svg_ts_path)
        section_copyright = _CopyrightSection()

        return [section_title, section_uptime_monitor, section_copyright]
