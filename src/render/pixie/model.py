import abc
import os
from datetime import datetime

import pixie
from easy_pixie import load_img, apply_tint, change_img_alpha, draw_img, Loc, tuple_to_color, pick_gradient_color, \
    GradientDirection, draw_gradient_rect, draw_mask_rect

from src.core.constants import Constants

_lib_path = Constants.modules_conf.get_lib_path("Render-Images")
_img_load_cache: dict[str, tuple[float, pixie.Image]] = {}

_CONTENT_WIDTH = 916
_CONTAINER_PADDING = 32
_TOP_PADDING = 136
_BOTTOM_PADDING = 152
_SIDE_PADDING = 96
_COLUMN_PADDING = 192
_SECTION_PADDING = 108


class Renderer(abc.ABC):
    """
    图片渲染基类
    成员命名规范：渲染组件公开，可用命名前缀: str_, img_, section_；中间量私有
    """

    @abc.abstractmethod
    def render(self) -> pixie.Image:
        pass

    @classmethod
    def load_img_resource(cls, img_name: str, tint_color: pixie.Color | tuple[int, ...] = None,
                          tint_ratio: int = 1, alpha_ratio: float = -1,
                          size: tuple[int, int] = None) -> pixie.Image:
        img_path = os.path.join(_lib_path, f"{img_name}.png")
        if not os.path.exists(img_path):
            img_path = os.path.join(_lib_path, "Dot.png")

        # 防止 Unknown 也不存在
        if not os.path.exists(img_path):
            raise FileNotFoundError("Img resource or placeholder not found")

        # 缓存机制
        img_loaded = None
        if size:  # 带上尺寸缓存
            img_name = f"{img_name}?sz={str(size)}"
        if img_name in _img_load_cache:
            last_load_time, img = _img_load_cache[img_name]
            if datetime.now().timestamp() - last_load_time <= 30 * 60:  # 缓存半小时
                img_loaded = img
        if not img_loaded:
            img_loaded = load_img(img_path)
            if size:
                img_loaded = img_loaded.resize(*size)
            _img_load_cache[img_name] = datetime.now().timestamp(), img_loaded

        if tint_color:
            img_loaded = apply_tint(img_loaded, tint_color, tint_ratio)
        if alpha_ratio != -1:
            img_loaded = change_img_alpha(img_loaded, alpha_ratio)

        return img_loaded


class RenderableSection(abc.ABC):
    """图片渲染分块基类"""

    def get_columns(self):
        """占几列，重写本方法以实现多列"""
        return 1

    @abc.abstractmethod
    def render(self, img: pixie.Image, x: int, y: int) -> int:
        pass

    @abc.abstractmethod
    def get_height(self):
        pass


class RenderableSvgSection(RenderableSection, abc.ABC):

    @abc.abstractmethod
    def _generate_svg(self) -> tuple[str, int, int]:
        """渲染 svg，获取文本，宽度，高度"""
        pass

    @abc.abstractmethod
    def _get_max_width(self) -> int:
        """获取可伸展最大宽度"""
        pass

    def __init__(self, svg_ts_path: str, width: int = -1, height: int = -1):
        svg_ts_path = f'{svg_ts_path}.svg'  # 此处默认路径唯一，不会导致资源竞争
        svg, self._original_width, self._original_height = self._generate_svg()
        try:
            with open(svg_ts_path, 'w') as f:
                f.write(svg)
            self.img_svg = pixie.read_image(svg_ts_path)
        finally:
            try:
                os.remove(svg_ts_path)
            except OSError as e:
                Constants.log.warning("Remove temp svg file failed")
                Constants.log.error(e)

        # 计算目标尺寸和居中偏移
        self._calculate_dimensions(width, height)

    def _calculate_dimensions(self, target_width, target_height):
        aspect_ratio = self._original_width / self._original_height

        if target_width == -1 and target_height == -1:
            target_width = self._get_max_width()

        if target_width == -1:
            self._render_width = int(target_height * aspect_ratio)
            self._render_height = target_height
        elif target_height == -1:
            self._render_width = target_width
            self._render_height = int(target_width / aspect_ratio)
        else:
            # 同时指定宽高时，居中显示而非拉伸
            container_ratio = target_width / target_height
            if aspect_ratio > container_ratio:
                self._render_width = target_width
                self._render_height = int(target_width / aspect_ratio)
            else:
                self._render_height = target_height
                self._render_width = int(target_height * aspect_ratio)

        self._container_width = target_width if target_width != -1 else self._render_width
        self._container_height = target_height if target_height != -1 else self._render_height

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_x += (self._container_width - self._render_width) // 2
        current_y += (self._container_height - self._render_height) // 2

        draw_img(img, self.img_svg,
                 Loc(current_x, current_y, self._render_width, self._render_height))
        current_y = y + self._container_height

        return current_y

    def get_height(self):
        return self._container_height


class SimpleCardRenderer(Renderer, abc.ABC):
    """简单的卡片渲染"""
    def __init__(self):
        self._gradient_color = pick_gradient_color()

    @abc.abstractmethod
    def _get_render_sections(self) -> list[RenderableSection]:
        pass

    @classmethod
    def _get_background_color(cls) -> pixie.Color:
        return tuple_to_color((0, 0, 0))

    @classmethod
    def _get_mask_color(cls) -> pixie.Color:
        return tuple_to_color((255, 255, 255, 178))

    @classmethod
    def _get_content_width(cls) -> int:
        return _CONTENT_WIDTH

    def _render_background_rect(self, img: pixie.Image, background_loc: Loc):
        draw_gradient_rect(img, background_loc, self._gradient_color,
                           GradientDirection.DIAGONAL_RIGHT_TO_LEFT, 96)
        draw_mask_rect(img, background_loc, self._get_mask_color(), 96)

    def render(self) -> pixie.Image:
        render_sections = self._get_render_sections()
        if not render_sections:
            raise ValueError('Nothing to render')

        max_column = max(section.get_columns() for section in render_sections)

        width = ((_CONTAINER_PADDING + _SIDE_PADDING) * 2 +
                 self._get_content_width() * max_column + _COLUMN_PADDING * (max_column - 1))
        height = (_CONTAINER_PADDING * 2 + _TOP_PADDING + _BOTTOM_PADDING +
                  sum(section.get_height() for section in render_sections) +
                  _SECTION_PADDING * (len(render_sections) - 1))

        img = pixie.Image(width, height)
        img.fill(self._get_background_color())

        background_loc = Loc(_CONTAINER_PADDING, _CONTAINER_PADDING,
                             width - _CONTAINER_PADDING * 2, height - _CONTAINER_PADDING * 2)
        self._render_background_rect(img, background_loc)

        current_x = _CONTAINER_PADDING + _SIDE_PADDING
        current_y = _CONTAINER_PADDING + _TOP_PADDING - _SECTION_PADDING

        for section in render_sections:
            current_y += _SECTION_PADDING
            current_y = section.render(img, current_x, current_y)

        return img
