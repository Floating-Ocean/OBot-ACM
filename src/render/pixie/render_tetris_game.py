import pixie
from easy_pixie import StyledString, calculate_height, draw_text, Loc, draw_img, \
    draw_mask_rect, tuple_to_color

from src.core.constants import Constants
from src.render.html.render_tetris_svg import render_tetris_svg
from src.render.pixie.model import Renderer, RenderableSection

_CONTENT_WIDTH = 1024
_TOP_PADDING = 168
_BOTTOM_PADDING = 128
_SIDE_PADDING = 108
_SECTION_PADDING = 108


class _TitleSection(RenderableSection):

    def __init__(self, score: int, map_width: int, trials: int):
        status_text = f'当前得分：{score}，列数：{map_width}，尝试次数：{trials}'
        self.title_text = StyledString(
            "俄罗斯方块", 'H', 96, padding_bottom=4, font_color=(255, 255, 255)
        )
        self.subtitle_text = StyledString(
            status_text, 'H', 28, font_color=(255, 255, 255, 136)
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.title_text, current_x, current_y)
        current_y = draw_text(img, self.subtitle_text, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.title_text, self.subtitle_text])


class _CopyrightSection(RenderableSection):

    def __init__(self):
        self.mild_text_color = (255, 255, 255, 156)
        self.generator_text = StyledString(
            "Tetris Project", 'H', 36, padding_bottom=16,
            font_color=(255, 255, 255, 228)
        )
        self.generation_info_text = StyledString(
            f"A game included in OBot's ACM {Constants.core_version}.",
            'B', 20, line_multiplier=1.32, font_color=self.mild_text_color
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.generator_text, current_x, current_y)
        draw_text(img, self.generation_info_text, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.generator_text, self.generation_info_text])


class _TetrisMapSection(RenderableSection):

    def __init__(self, current_map: list[list[int]], svg_ts_path: str,
                 width: int = -1, height: int = -1):
        self.svg_ts_path = f'{svg_ts_path}.svg'
        tetris_svg, svg_width, svg_height = render_tetris_svg(current_map)
        with open(self.svg_ts_path, 'w') as f:
            f.write(tetris_svg)
        self.tetris_map = pixie.read_image(self.svg_ts_path)

        self._scale_svg(height, svg_height, svg_width, width)

    def _scale_svg(self, height, svg_height, svg_width, width):
        if width == -1 and height == -1:
            width = _CONTENT_WIDTH + 64 - _SIDE_PADDING * 2
        if width == -1:
            width = int(svg_width / svg_height * height)
        if height == -1:
            height = int(svg_height / svg_width * width)
        self.tetris_width, self.tetris_height = width, height

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        draw_img(img, self.tetris_map, Loc(current_x, current_y, self.tetris_width, self.tetris_height))
        current_y += self.tetris_height

        return current_y

    def get_height(self):
        return self.tetris_height


class TetrisGameRenderer(Renderer):
    """渲染俄罗斯方块游戏状态"""

    def __init__(self, current_map: list[list[int]], svg_ts_path: str,
                 score: int, map_width: int, trials: int):
        self.current_map = current_map
        self.svg_ts_path = svg_ts_path
        self.score = score
        self.map_width = map_width
        self.trials = trials

    def render(self) -> pixie.Image:
        title_section = _TitleSection(self.score, self.map_width, self.trials)
        tetris_map_section = _TetrisMapSection(self.current_map, self.svg_ts_path)
        copyright_section = _CopyrightSection()

        render_sections = [title_section, tetris_map_section, copyright_section]

        width, height = (_CONTENT_WIDTH,
                         sum(section.get_height() for section in render_sections) +
                         _SECTION_PADDING * (len(render_sections) - 1) +
                         _TOP_PADDING + _BOTTOM_PADDING)

        img = pixie.Image(width + 64, height + 64)
        img.fill(tuple_to_color((0, 0, 0, 255)))  # 填充白色背景

        draw_mask_rect(img, Loc(32, 32, width, height), (36, 36, 36), 96)

        current_x, current_y = _SIDE_PADDING, _TOP_PADDING - _SECTION_PADDING

        for section in render_sections:
            current_y += _SECTION_PADDING
            current_y = section.render(img, current_x, current_y)

        return img
