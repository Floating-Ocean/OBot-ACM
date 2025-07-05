BLOCK_SIZE = 24
BLOCK_SPACING = 5

_colors = ["#000000", "#ec407a", "#ab47bc", "#7986cb", "#29b6f6",
           "#4db6ac", "#d4e157", "#ffa726", "#282828"]


def render_tetris_map(tetris_map: list[list[int]]) -> tuple[str, int, int]:
    """
    渲染俄罗斯方块当前状态的 svg
    返回 svg 文本，宽度，高度
    """
    if len(tetris_map) == 0 or len(tetris_map[0]) == 0:
        raise ValueError("Tetris map can't be empty")

    svg_width = (len(tetris_map[0]) - 1) * (BLOCK_SIZE + BLOCK_SPACING) + BLOCK_SIZE
    svg_height = (len(tetris_map) - 1) * (BLOCK_SIZE + BLOCK_SPACING) + BLOCK_SIZE
    svg_rects = ('<svg xmlns="http://www.w3.org/2000/svg" fill="#303030"'
                 f' preserveAspectRatio="xMinYMin meet" viewBox="0 0 {svg_width} {svg_height}">\n')

    for y_offset, line in enumerate(tetris_map):
        svg_rects += f'<g transform="translate(0, {y_offset * (BLOCK_SIZE + BLOCK_SPACING)})">\n'
        for x_offset, block in enumerate(line):
            if block == 0 and (x_offset + y_offset) % 2 == 1:  # 棋盘式背景
                block = 8
            svg_rects += (f'<rect x="{x_offset * (BLOCK_SIZE + BLOCK_SPACING)}"'
                          f' width="{BLOCK_SIZE}" height="{BLOCK_SIZE}"'
                          f' fill="{_colors[block]}"/>\n')
        svg_rects += '</g>\n'

    svg_rects += '</svg>'

    return svg_rects, svg_width, svg_height
