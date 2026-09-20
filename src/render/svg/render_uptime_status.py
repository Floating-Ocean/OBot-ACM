BAR_WIDTH = 60
BAR_HEIGHT = 300
BAR_RADIUS = 30
BAR_SPACING = 38

_MIN_VISIBLE_HEIGHT = BAR_RADIUS * 2
_LABEL_NO_DATA = "black"

# γ > 1：拉开高可用区间的差距，99% 与 100% 才看得出高度差
_HEIGHT_GAMMA = 6

_COLOR_RED = "#d9363e"
_COLOR_ORANGE = "#e8720c"
_COLOR_GREEN = "#17b45a"
_COLOR_MUTE = "#c7c7c7"


def get_percentile_color(percent: float) -> str:
    if percent < 0:  # 无数据
        return _COLOR_MUTE
    if percent >= 99:
        return _COLOR_GREEN
    if percent >= 95:
        return _COLOR_ORANGE
    return _COLOR_RED


def _get_fill_height(percent: float) -> float:
    if percent < 0:
        return 0
    ratio = min(percent, 100) / 100
    return round(_MIN_VISIBLE_HEIGHT +
                 ratio ** _HEIGHT_GAMMA * (BAR_HEIGHT - _MIN_VISIBLE_HEIGHT), 2)


def _fmt(value: float) -> str:
    value = round(value, 2)
    return str(int(value)) if float(value).is_integer() else str(value)


def _render_bar(x: int, status: dict) -> str:
    percent = -1 if status['label'] == _LABEL_NO_DATA else float(status['ratio'])
    fill_height = BAR_HEIGHT if percent < 0 else _get_fill_height(percent)
    if fill_height <= 0:
        return ''

    return (f'<rect x="{x}" y="{_fmt(BAR_HEIGHT - fill_height)}" width="{BAR_WIDTH}"'
            f' height="{_fmt(fill_height)}" rx="{BAR_RADIUS}" ry="{BAR_RADIUS}"'
            f' fill="{get_percentile_color(percent)}"/>\n')


def render_uptime_status(status_list: list[dict]) -> tuple[str, int, int]:
    """
    渲染 Uptime 在线状态条的 svg（竖向进度条，高度表示当天的可用性百分比）
    返回 svg 文本，宽度，高度
    """
    svg_width = (len(status_list) - 1) * (BAR_WIDTH + BAR_SPACING) + BAR_WIDTH
    svg_height = BAR_HEIGHT
    svg_rects = ('<svg xmlns="http://www.w3.org/2000/svg" fill="#303030"'
                 f' preserveAspectRatio="xMinYMin meet" viewBox="0 0 {svg_width} {svg_height}">\n')

    for x_offset, status in enumerate(status_list):
        svg_rects += _render_bar(x_offset * (BAR_WIDTH + BAR_SPACING), status)

    svg_rects += '</svg>'

    return svg_rects, svg_width, svg_height
