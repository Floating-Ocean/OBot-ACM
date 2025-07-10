from datetime import datetime

import pixie
from easy_pixie import StyledString, calculate_height, draw_text, Loc, draw_img, \
    draw_mask_rect, tuple_to_color, hex_to_color, calculate_width, darken_color

from src.core.constants import Constants
from src.render.pixie.model import Renderer, RenderableSection, RenderableSvgSection
from src.render.svg.render_uptime_status import render_uptime_status, get_percentile_color

_CONTENT_WIDTH = 1536
_TOP_PADDING = 168
_BOTTOM_PADDING = 128
_SIDE_PADDING = 108
_UPTIME_SECTION_PADDING = 96
_SECTION_PADDING = 108


class _TitleSection(RenderableSection):

    def __init__(self, down_count: int):
        status_text = "部分服务异常" if down_count > 0 else "所有服务均正常运行"
        status_sub_text = ("Uptime Robot Monitor · Some Systems Down" if down_count > 0 else
                           "Uptime Robot Monitor · All Systems Operational")

        self.logo_path = Renderer.load_img_resource(
            "Dot",
            hex_to_color(get_percentile_color(100 if down_count == 0 else 98)[0])
        )
        self.title_text = StyledString(
            status_text, 'H', 96, padding_bottom=4
        )
        self.subtitle_text = StyledString(
            status_sub_text, 'H', 28,
            font_color=(0, 0, 0, 136)
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_img(img, self.logo_path, Loc(106, 181, 102, 102))

        current_x, current_y = x, y
        current_y = draw_text(img, self.title_text, 232, current_y)
        current_y = draw_text(img, self.subtitle_text, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.title_text, self.subtitle_text])


class _CopyrightSection(RenderableSection):

    def __init__(self):
        self.mild_text_color = (0, 0, 0, 156)
        self.generator_text = StyledString(
            "Uptime Robot", 'H', 36, padding_bottom=16,
            font_color=(0, 0, 0, 228)
        )
        self.generation_info_text = StyledString(
            f'Status fetched at {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}.\n'
            f"Initiated by OBot's ACM {Constants.core_version}.",
            'B', 20, line_multiplier=1.32, font_color=self.mild_text_color
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.generator_text, current_x, current_y)
        current_y = draw_text(img, self.generation_info_text, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.generator_text, self.generation_info_text])


class _UptimeStatusSection(RenderableSvgSection):

    def _get_max_width(self) -> int:
        return _CONTENT_WIDTH + 64 - _SIDE_PADDING * 2

    def _generate_svg(self) -> tuple[str, int, int]:
        return render_uptime_status(self.current_status)

    def __init__(self, current_status: list[dict], svg_ts_path: str,
                 width: int = -1, height: int = -1):
        self.current_status = current_status
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

        self.name_text = StyledString(
            monitor_status["name"], 'H', 40, padding_bottom=16
        )
        self.status_text = StyledString(
            status_info, 'H', 40, padding_bottom=16, font_color=status_color
        )
        self.status_section = _UptimeStatusSection(monitor_status["dailyRatios"], svg_ts_path)
        self.dot_path = Renderer.load_img_resource("Dot", status_color)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        status_text_width = calculate_width(self.status_text)

        draw_text(img, self.name_text, current_x, current_y)
        current_x = _CONTENT_WIDTH + 64 - current_x - status_text_width
        draw_img(img, self.dot_path, Loc(current_x - 48, current_y + 6, 40, 40))
        current_y = draw_text(img, self.status_text, current_x, current_y)

        current_x = x
        current_y = self.status_section.render(img, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height(self.status_text) + self.status_section.get_height()


class _UptimeMonitorSection(RenderableSection):

    def __init__(self, monitors: list[dict], svg_ts_path: str):
        self.monitor_items = [_UptimeMonitorItem(monitor, f'{svg_ts_path}_{d}')
                              for d, monitor in enumerate(monitors)]

    def get_height(self):
        return (sum(monitor.get_height() for monitor in self.monitor_items) +
                _UPTIME_SECTION_PADDING * (len(self.monitor_items) - 1))

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        current_y -= _UPTIME_SECTION_PADDING
        for monitor in self.monitor_items:
            current_y += _UPTIME_SECTION_PADDING
            current_y = monitor.render(img, current_x, current_y)

        return current_y


class UptimeRenderer(Renderer):
    """渲染服务状态"""

    def __init__(self, current_status: dict, svg_ts_path: str):
        self.current_status = current_status
        self.svg_ts_path = svg_ts_path

    def render(self) -> pixie.Image:
        title_section = _TitleSection(self.current_status["statistics"]["counts"]["down"])
        uptime_monitor_section = _UptimeMonitorSection(self.current_status["psp"]["monitors"],
                                                       self.svg_ts_path)
        copyright_section = _CopyrightSection()

        render_sections = [title_section, uptime_monitor_section, copyright_section]

        width, height = (_CONTENT_WIDTH,
                         sum(section.get_height() for section in render_sections) +
                         _SECTION_PADDING * (len(render_sections) - 1) +
                         _TOP_PADDING + _BOTTOM_PADDING)

        img = pixie.Image(width + 64, height + 64)
        img.fill(tuple_to_color((0, 0, 0, 255)))  # 填充背景

        draw_mask_rect(img, Loc(32, 32, width, height), (252, 252, 252), 96)

        current_x, current_y = _SIDE_PADDING, _TOP_PADDING - _SECTION_PADDING

        for section in render_sections:
            current_y += _SECTION_PADDING
            current_y = section.render(img, current_x, current_y)

        return img
