import pixie
from easy_pixie import StyledString, calculate_height, draw_text, Loc, draw_img, \
    draw_mask_rect, tuple_to_color

from src.core.constants import Constants
from src.render.svg.render_tetris_map import render_tetris_map
from src.render.pixie.model import Renderer, RenderableSection, RenderableSvgSection

_CONTENT_WIDTH = 1024
_TOP_PADDING = 168
_BOTTOM_PADDING = 128
_SIDE_PADDING = 108
_SECTION_PADDING = 108

_NEXT_BLOCK_CONTENT_WIDTH = int(_CONTENT_WIDTH * 1.5)
_NEXT_BLOCK_SIZE = 292
_NEXT_BLOCK_PADDING = 72


class _StatusTitleSection(RenderableSection):

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


class _TetrisMapSection(RenderableSvgSection):

    def _get_max_width(self) -> int:
        return _CONTENT_WIDTH + 64 - _SIDE_PADDING * 2

    def _generate_svg(self) -> tuple[str, int, int]:
        return render_tetris_map(self.current_map)

    def __init__(self, current_map: list[list[int]], svg_ts_path: str,
                 width: int = -1, height: int = -1):
        self.current_map = current_map
        super().__init__(svg_ts_path, width, height)


class _TetrisNextSection(RenderableSection):

    def __init__(self, next_block: dict, svg_ts_path: str):
        perms = next_block["perm"]
        self.tetris_maps = [
            _TetrisMapSection(perms[d],
                              f'{svg_ts_path}_{d}',
                              _NEXT_BLOCK_SIZE, _NEXT_BLOCK_SIZE)
            for d in range(len(perms))
        ]

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        for idx, tetris_map in enumerate(self.tetris_maps):
            if idx == len(self.tetris_maps) - 1:
                current_y = tetris_map.render(img, current_x, current_y)
            else:
                tetris_map.render(img, current_x, current_y)
                current_x += _NEXT_BLOCK_SIZE + _NEXT_BLOCK_PADDING

        return current_y

    def get_height(self):
        return _NEXT_BLOCK_SIZE


class _NextTitleSection(RenderableSection):

    def __init__(self, next_block: dict):
        self.title_text = StyledString(
            "下一个方块", 'H', 96, padding_bottom=4, font_color=(255, 255, 255)
        )
        self.subtitle_text = StyledString(
            f'{next_block["name"]}，顺时针旋转后的方块如下', 'H', 28,
            font_color=(255, 255, 255, 136)
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.title_text, current_x, current_y)
        current_y = draw_text(img, self.subtitle_text, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.title_text, self.subtitle_text])


class TetrisGameRenderer(Renderer):
    """渲染俄罗斯方块游戏状态"""

    def __init__(self, current_map: list[list[int]], svg_ts_path: str,
                 score: int, trials: int):
        self.current_map = current_map
        self.svg_ts_path = svg_ts_path
        self.score = score
        self.map_width = len(current_map[0])
        self.trials = trials

    def render(self) -> pixie.Image:
        title_section = _StatusTitleSection(self.score, self.map_width, self.trials)
        tetris_map_section = _TetrisMapSection(self.current_map, self.svg_ts_path)
        copyright_section = _CopyrightSection()

        render_sections = [title_section, tetris_map_section, copyright_section]

        width, height = (_CONTENT_WIDTH,
                         sum(section.get_height() for section in render_sections) +
                         _SECTION_PADDING * (len(render_sections) - 1) +
                         _TOP_PADDING + _BOTTOM_PADDING)

        img = pixie.Image(width + 64, height + 64)
        img.fill(tuple_to_color((0, 0, 0, 255)))  # 填充背景

        draw_mask_rect(img, Loc(32, 32, width, height), (52, 52, 52), 96)

        current_x, current_y = _SIDE_PADDING, _TOP_PADDING - _SECTION_PADDING

        for section in render_sections:
            current_y += _SECTION_PADDING
            current_y = section.render(img, current_x, current_y)

        return img


class TetrisNextBlockRenderer(Renderer):
    """渲染俄罗斯方块的下一个方块"""

    def __init__(self, next_block: dict, svg_ts_path: str):
        self.next_block = next_block
        self.svg_ts_path = svg_ts_path

    def render(self) -> pixie.Image:
        title_section = _NextTitleSection(self.next_block)
        next_section = _TetrisNextSection(self.next_block, self.svg_ts_path)
        copyright_section = _CopyrightSection()

        render_sections = [title_section, next_section, copyright_section]

        width, height = (_NEXT_BLOCK_CONTENT_WIDTH,
                         sum(section.get_height() for section in render_sections) +
                         _SECTION_PADDING * (len(render_sections) - 1) +
                         _TOP_PADDING + _BOTTOM_PADDING)

        img = pixie.Image(width + 64, height + 64)
        img.fill(tuple_to_color((0, 0, 0, 255)))  # 填充背景

        draw_mask_rect(img, Loc(32, 32, width, height), (52, 52, 52), 96)

        current_x, current_y = _SIDE_PADDING, _TOP_PADDING - _SECTION_PADDING

        for section in render_sections:
            current_y += _SECTION_PADDING
            current_y = section.render(img, current_x, current_y)

        return img
