import pixie
from easy_pixie import StyledString, calculate_height, draw_text, Loc, draw_img, \
    draw_mask_rect

from src.render.pixie.model import Renderer, RenderableSection, SimpleCardRenderer

_CONTENT_WIDTH = 1048
_CELL_PADDING = 32
_CELL_INNER_HORIZONTAL_PADDING = 32
_CELL_INNER_VERTICAL_PADDING = 48


class _ModuleItem(RenderableSection):
    def __init__(self, name: str, version: str, no_limit: bool = False):
        item_width = (_CONTENT_WIDTH - _CELL_PADDING * 2) / 3
        item_width -= _CELL_INNER_HORIZONTAL_PADDING * 2
        self.str_name = StyledString(
            name.replace("-", " "),
            'H', 32, padding_bottom=12, max_width=item_width
        )
        self.str_version = StyledString(
            version.lstrip('v'),
            'B', 20, font_color=(0, 0, 0, 108),
            max_width=-1 if no_limit else item_width
        )
        self._real_width, self._real_height = -1, -1

    def get_height(self):
        return (calculate_height([self.str_name, self.str_version]) +
                _CELL_INNER_VERTICAL_PADDING * 2)

    def set_real_size(self, real_width: int, real_height: int):
        self._real_width = real_width
        self._real_height = real_height

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        vertical_padding = _CELL_INNER_VERTICAL_PADDING

        if min(self._real_width, self._real_height) != -1:
            draw_mask_rect(img, Loc(current_x, current_y, self._real_width, self._real_height),
                           (0, 0, 0, 24), 32)
            vertical_padding = ((self._real_height - self.get_height()) // 2 +
                                _CELL_INNER_VERTICAL_PADDING)

        current_x += _CELL_INNER_HORIZONTAL_PADDING
        current_y += vertical_padding
        current_y = draw_text(img, self.str_name, current_x, current_y)
        current_y = draw_text(img, self.str_version, current_x, current_y)
        current_y += vertical_padding

        return current_y


class _ModuleSection(RenderableSection):
    def __init__(self, core: tuple[str, str], modules: list[tuple[str, str]]):
        self._core_width = _CONTENT_WIDTH
        self._modules_width = (self._core_width - _CELL_PADDING * 2) // 3
        self.section_core = _ModuleItem(core[0], core[1], True)
        self.section_modules_items = [_ModuleItem(name, version) for name, version in modules]
        self.img_chip = Renderer.load_img_resource("Chip", (0, 0, 0))

    def get_height(self):
        height = self.section_core.get_height()
        self.section_core.set_real_size(self._core_width, self.section_core.get_height())

        for it in range(0, len(self.section_modules_items), 3):
            height += _CELL_PADDING
            line_height = max(module.get_height()
                              for module in self.section_modules_items[it:it + 3])
            height += line_height
            for module in self.section_modules_items[it:it + 3]:
                module.set_real_size(self._modules_width, line_height)
        return height

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        img_size = self.section_core.get_height() - 96
        draw_img(img, self.img_chip,
                 Loc(current_x + self._core_width - img_size - 32,
                     current_y + 48, img_size, img_size))

        current_y = self.section_core.render(img, current_x, current_y)
        for it in range(0, len(self.section_modules_items), 3):
            current_y += _CELL_PADDING
            max_y = current_y
            for module in self.section_modules_items[it:it + 3]:
                max_y = max(max_y, module.render(img, current_x, current_y))
                current_x += self._modules_width + _CELL_PADDING
            current_x = x
            current_y = max_y

        return current_y


class _TitleSection(RenderableSection):

    def __init__(self):
        self.img_obot_logo = Renderer.load_img_resource("OBot_Logo", (0, 0, 0))

        # 不支持 letter_spacing 而手动加空格的无奈之举
        self.str_subtitle = StyledString(
            ' '.join("Integrated Bot for Competitive Programming and More"), 'H', 23,
            max_width=1032
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        draw_img(img, self.img_obot_logo, Loc(current_x, current_y, 1030, 128))
        current_y += 124 + 24
        current_y = draw_text(img, self.str_subtitle, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height(self.str_subtitle) + 128 + 24


class AboutRenderer(SimpleCardRenderer):
    """渲染关于页"""

    def __init__(self, core: tuple[str, str], modules: list[tuple[str, str]]):
        super().__init__()
        self.section_core = core
        self.section_modules = modules

    @classmethod
    def _get_content_width(cls) -> int:
        return _CONTENT_WIDTH

    def _render_background_rect(self, img: pixie.Image, background_loc: Loc):
        draw_mask_rect(img, background_loc, (252, 252, 252), 96)

    def _get_render_sections(self) -> list[RenderableSection]:
        section_title = _TitleSection()
        section_module = _ModuleSection(self.section_core, self.section_modules)

        return [section_title, section_module]
