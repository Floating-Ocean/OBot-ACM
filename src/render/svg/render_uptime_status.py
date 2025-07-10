BAR_WIDTH = 60
BAR_HEIGHT = 300
BAR_SPACING = 38

_COLOR_RED = "#df484a"
_COLOR_ORANGE = "#f29030"
_COLOR_GREEN = "#3bd671"
_COLOR_MUTE = "#687790"


def get_percentile_color(percent: float) -> tuple[str, float]:
    if percent == -1:
        return _COLOR_MUTE, 1
    if percent == 100:
        return _COLOR_GREEN, 1
    if percent >= 99:
        return _COLOR_GREEN, 0.5
    if percent >= 95:
        return _COLOR_ORANGE, 1
    return _COLOR_RED, 1


def render_uptime_status(status_list: list[dict]) -> tuple[str, int, int]:
    """
    渲染 Uptime 在线状态条的 svg
    返回 svg 文本，宽度，高度
    """
    svg_width = (len(status_list) - 1) * (BAR_WIDTH + BAR_SPACING) + BAR_WIDTH
    svg_height = BAR_HEIGHT
    svg_rects = ('<svg xmlns="http://www.w3.org/2000/svg" fill="#303030"'
                 f' preserveAspectRatio="xMinYMin meet" viewBox="0 0 {svg_width} {svg_height}">\n')

    render_status_list = [-1 if status['label'] == 'black' else float(status['ratio'])
                          for status in status_list]
    render_status_list.reverse()

    for x_offset, status in enumerate(render_status_list):
        bar_color, opacity = get_percentile_color(status)
        svg_rects += (f'<rect x="{x_offset * (BAR_WIDTH + BAR_SPACING)}"'
                      f' width="{BAR_WIDTH}" height="{BAR_HEIGHT}"'
                      f' fill="{bar_color}" fill-opacity="{opacity}" rx="30" ry="30"/>\n')

    svg_rects += '</svg>'

    return svg_rects, svg_width, svg_height
