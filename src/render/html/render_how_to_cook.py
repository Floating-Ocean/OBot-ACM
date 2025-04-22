import os
from datetime import datetime

from easy_pixie import pick_gradient_color, GradientColor, darken_color, hex_to_color, color_to_hex

from src.core.constants import Constants
from src.render.html.markdown import render_md_html

_lib_path = os.path.join(Constants.config["lib_path"], "How-To-Cook")
_css_path = os.path.join(_lib_path, "style", "index.css")


def _format_gradient_color(gradient: GradientColor) -> str:
    if len(gradient.color_list) == 2:
        return f"from({gradient.color_list[0]}), to({gradient.color_list[1]})"
    elif len(gradient.color_list) == 3:
        return f"from({gradient.color_list[0]}), color-stop(50%, {gradient.color_list[1]}), to({gradient.color_list[2]})"
    else:
        raise RuntimeError(f"Unsupported gradient color: {gradient.color_list}")


def render_how_to_cook(how_to_cook_version: str, dish_path: str, output_path: str):
    gradient_color = pick_gradient_color()
    accent_dark_color = darken_color(hex_to_color(gradient_color.color_list[0]), 0.3)
    extra_body = f"""
        <div class="tip-container">
            <p class="tip-name">Tips: </p>
            <p class="tip-detail">菜谱来自 Anduin2017/HowToCook 开源项目，祝你好运</p>
        </div>
        <div class="copyright-container">
            <div class="tool-container">
                <p class="tool-name">How to Cook</p>
                <p class="tool-version">{how_to_cook_version}</p>
            </div>
            <p class="generation-info">Generated at {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}.<br>
                                       Initiated by OBot's ACM {Constants.core_version}.<br>
                                       {gradient_color.name}.</p>
        </div>
        """
    render_md_html(dish_path, _css_path, output_path, extra_body,
                   color_stops=_format_gradient_color(gradient_color),
                   accent_dark_color=color_to_hex(accent_dark_color, include_alpha=False))
