from datetime import datetime

import pixie
from easy_pixie import StyledString, calculate_height, draw_text, Loc, draw_img, \
    draw_mask_rect, hex_to_color, calculate_width, darken_color

from src.core.constants import Constants
from src.render.pixie.model import Renderer, RenderableSection, RenderableSvgSection, SimpleCardRenderer
from src.render.svg.render_uptime_status import render_uptime_status, get_percentile_color

_CONTENT_WIDTH = 1472
_UPTIME_SECTION_PADDING = 96


class _TitleSection(RenderableSection):

    def __init__(self, down_count: int):
        status_text = "部分服务异常" if down_count > 0 else "所有服务均正常运行"
        status_sub_text = ("Uptime Robot Monitor · Some Systems Down" if down_count > 0 else
                           "Uptime Robot Monitor · All Systems Operational")

        self.img_dot = Renderer.load_img_resource(
            "Dot",
            hex_to_color(get_percentile_color(100 if down_count == 0 else 98)[0])
        )
        self.str_title = StyledString(
            status_text, 'H', 96, padding_bottom=4
        )
        self.str_subtitle = StyledString(
            status_sub_text, 'H', 28,
            font_color=(0, 0, 0, 136)
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_img(img, self.img_dot, Loc(106, 181, 102, 102))

        current_x, current_y = x, y
        current_y = draw_text(img, self.str_title, 232, current_y)
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
                                              0 if raw_status == "danger" else 98)[0]),
            0.66
        )
        status_info = ("正常" if raw_status == "success" else
                       "异常" if raw_status == "danger" else "暂停")

        self.str_name = StyledString(
            monitor_status["name"], 'H', 40, padding_bottom=16
        )
        self.str_status = StyledString(
            status_info, 'H', 40, padding_bottom=16, font_color=status_color
        )
        self.section_status = _UptimeStatusSection(monitor_status["dailyRatios"], svg_ts_path)
        self.img_dot = Renderer.load_img_resource("Dot", status_color)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        status_text_width = calculate_width(self.str_status)

        draw_text(img, self.str_name, current_x, current_y)
        current_x = current_x + _CONTENT_WIDTH - status_text_width
        draw_img(img, self.img_dot, Loc(current_x - 48, current_y + 6, 40, 40))
        current_y = draw_text(img, self.str_status, current_x, current_y)

        current_x = x
        current_y = self.section_status.render(img, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height(self.str_status) + self.section_status.get_height()


class _UptimeMonitorSection(RenderableSection):

    def __init__(self, monitors: list[dict], svg_ts_path: str):
        self.section_monitor_items = [_UptimeMonitorItem(monitor, f'{svg_ts_path}_{d}')
                                      for d, monitor in enumerate(monitors)]

    def get_height(self):
        return (sum(monitor.get_height() for monitor in self.section_monitor_items) +
                _UPTIME_SECTION_PADDING * (len(self.section_monitor_items) - 1))

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
