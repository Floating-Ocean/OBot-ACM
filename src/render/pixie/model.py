import abc
import os
from abc import abstractmethod
from datetime import datetime

import pixie
from easy_pixie import load_img, apply_tint, change_img_alpha, draw_img, Loc

from src.core.constants import Constants

_lib_path = Constants.modules_conf.get_lib_path("Render-Images")
_img_load_cache: dict[str, tuple[float, pixie.Image]] = {}


class Renderer(abc.ABC):
    """
    图片渲染基类
    成员命名规范：渲染组件公开，可用命名前缀: str_, img_, section_；中间量私有
    """

    @abstractmethod
    def render(self) -> pixie.Image:
        pass

    @classmethod
    def load_img_resource(cls, img_name: str, tint_color: pixie.Color | tuple[int, ...] = None,
                          tint_ratio: int = 1, alpha_ratio: float = -1) -> pixie.Image:
        img_path = os.path.join(_lib_path, f"{img_name}.png")
        if not os.path.exists(img_path):
            img_path = os.path.join(_lib_path, "Dot.png")

        # 防止 Unknown 也不存在
        if not os.path.exists(img_path):
            raise FileNotFoundError("Img resource or placeholder not found")

        # 缓存机制
        img_loaded = None
        if img_name in _img_load_cache:
            last_load_time, img = _img_load_cache[img_name]
            if datetime.now().timestamp() - last_load_time <= 30 * 60:  # 缓存半小时
                img_loaded = img
        if not img_loaded:
            img_loaded = load_img(img_path)
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

    @abstractmethod
    def render(self, img: pixie.Image, x: int, y: int) -> int:
        pass

    @abstractmethod
    def get_height(self):
        pass


class RenderableSvgSection(RenderableSection, abc.ABC):

    @abstractmethod
    def _generate_svg(self) -> tuple[str, int, int]:
        """渲染 svg，获取文本，宽度，高度"""
        pass

    @abstractmethod
    def _get_max_width(self) -> int:
        """获取可伸展最大宽度"""
        pass

    def __init__(self, svg_ts_path: str, width: int = -1, height: int = -1):
        svg_ts_path = f'{svg_ts_path}.svg'
        svg, self._original_width, self._original_height = self._generate_svg()
        with open(svg_ts_path, 'w') as f:
            f.write(svg)
        self.img_svg = pixie.read_image(svg_ts_path)

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
