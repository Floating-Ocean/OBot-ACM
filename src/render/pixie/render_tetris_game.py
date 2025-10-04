import pixie
from easy_pixie import StyledString, calculate_height, draw_text, Loc, draw_mask_rect

from src.core.constants import Constants
from src.render.pixie.model import RenderableSection, RenderableSvgSection, SimpleCardRenderer
from src.render.svg.render_tetris_map import render_tetris_map

_CONTENT_WIDTH = 916
_NEXT_BLOCK_CONTENT_WIDTH = int(_CONTENT_WIDTH * 1.5)
_NEXT_BLOCK_PADDING = 72
_NEXT_BLOCK_SIZE = (_NEXT_BLOCK_CONTENT_WIDTH - 3 * _NEXT_BLOCK_PADDING) // 4


class _StatusTitleSection(RenderableSection):

    def __init__(self, score: int, map_width: int, trials: int):
        status_text = f'当前得分：{score}，列数：{map_width}，尝试次数：{trials}'
        self.str_title = StyledString(
            "俄罗斯方块", 'H', 96, padding_bottom=4, font_color=(255, 255, 255)
        )
        self.str_subtitle = StyledString(
            status_text, 'H', 28, font_color=(255, 255, 255, 136)
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.str_title, current_x, current_y)
        current_y = draw_text(img, self.str_subtitle, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_title, self.str_subtitle])


class _CopyrightSection(RenderableSection):

    def __init__(self):
        mild_text_color = (255, 255, 255, 156)
        self.str_generator = StyledString(
            "Tetris Project", 'H', 36, padding_bottom=16,
            font_color=(255, 255, 255, 228)
        )
        self.str_generation = StyledString(
            f"A game included in OBot's ACM {Constants.core_version}.",
            'B', 20, line_multiplier=1.32, font_color=mild_text_color
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.str_generator, current_x, current_y)
        draw_text(img, self.str_generation, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_generator, self.str_generation])


class _TetrisMapSection(RenderableSvgSection):

    def _get_max_width(self) -> int:
        return _CONTENT_WIDTH

    def _generate_svg(self) -> tuple[str, int, int]:
        return render_tetris_map(self._current_map)

    def __init__(self, current_map: list[list[int]], svg_ts_path: str,
                 width: int = -1, height: int = -1):
        self._current_map = current_map
        super().__init__(svg_ts_path, width, height)


class _TetrisNextSection(RenderableSection):

    def __init__(self, next_block: dict, svg_ts_path: str):
        perms = next_block["perm"]
        self.section_tetris_maps = [
            _TetrisMapSection(perms[d],
                              f'{svg_ts_path}_{d}',
                              _NEXT_BLOCK_SIZE, _NEXT_BLOCK_SIZE)
            for d in range(len(perms))
        ]

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        for idx, tetris_map in enumerate(self.section_tetris_maps):
            if idx == len(self.section_tetris_maps) - 1:
                current_y = tetris_map.render(img, current_x, current_y)
            else:
                tetris_map.render(img, current_x, current_y)
                current_x += _NEXT_BLOCK_SIZE + _NEXT_BLOCK_PADDING

        return current_y

    def get_height(self):
        return _NEXT_BLOCK_SIZE


class _NextTitleSection(RenderableSection):

    def __init__(self, next_block: dict):
        self.str_title = StyledString(
            "下一个方块", 'H', 96, padding_bottom=4, font_color=(255, 255, 255)
        )
        self.str_subtitle = StyledString(
            f'{next_block["name"]}，顺时针旋转后的方块如下', 'H', 28,
            font_color=(255, 255, 255, 136)
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.str_title, current_x, current_y)
        current_y = draw_text(img, self.str_subtitle, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_title, self.str_subtitle])


class TetrisGameRenderer(SimpleCardRenderer):
    """渲染俄罗斯方块游戏状态"""

    def __init__(self, current_map: list[list[int]], svg_ts_path: str, score: int, trials: int):
        super().__init__()
        if not current_map or not current_map[0]:
            raise ValueError('Invalid tetris map')
        self._current_map = current_map
        self._svg_ts_path = svg_ts_path
        self._score = score
        self._map_width = len(current_map[0])
        self._trials = trials

    def _render_background_rect(self, img: pixie.Image, background_loc: Loc):
        draw_mask_rect(img, background_loc, (52, 52, 52), 96)

    def _get_render_sections(self) -> list[RenderableSection]:
        section_title = _StatusTitleSection(self._score, self._map_width, self._trials)
        section_tetris_map = _TetrisMapSection(self._current_map, self._svg_ts_path)
        section_copyright = _CopyrightSection()

        return [section_title, section_tetris_map, section_copyright]


class TetrisNextBlockRenderer(SimpleCardRenderer):
    """渲染俄罗斯方块的下一个方块"""

    def __init__(self, next_block: dict, svg_ts_path: str):
        super().__init__()
        self._next_block = next_block
        self._svg_ts_path = svg_ts_path

    @classmethod
    def _get_content_width(cls) -> int:
        return _NEXT_BLOCK_CONTENT_WIDTH

    def _render_background_rect(self, img: pixie.Image, background_loc: Loc):
        draw_mask_rect(img, background_loc, (52, 52, 52), 96)

    def _get_render_sections(self) -> list[RenderableSection]:
        section_title = _NextTitleSection(self._next_block)
        section_next = _TetrisNextSection(self._next_block, self._svg_ts_path)
        section_copyright = _CopyrightSection()

        return [section_title, section_next, section_copyright]
