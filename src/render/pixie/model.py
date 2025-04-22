import abc
import os
from abc import abstractmethod
from datetime import datetime

import pixie
from easy_pixie import load_img, apply_tint, change_img_alpha

from src.core.constants import Constants

_lib_path = os.path.join(Constants.config["lib_path"], "Render-Images")
_img_load_cache: dict[str, tuple[float, pixie.Image]] = {}


class Renderer(abc.ABC):
    """图片渲染基类"""

    @abstractmethod
    def render(self) -> pixie.Image:
        pass

    @classmethod
    def load_img_resource(cls, img_name: str, tint_color: pixie.Color | tuple[int, ...] = None,
                          tint_ratio: int = 1, alpha_ratio: float = -1) -> pixie.Image:
        img_path = os.path.join(_lib_path, f"{img_name}.png")
        if not os.path.exists(img_path):
            img_path = os.path.join(_lib_path, "Unknown.png")

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
