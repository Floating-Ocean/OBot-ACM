import json
import os
import random
from colorsys import rgb_to_hsv

from PIL import Image
from easy_pixie import choose_text_color, color_to_tuple, change_alpha, hex_to_color
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.main import QRCode

from src.core.bot.command import command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.output_cached import get_cached_prefix
from src.core.util.tools import png2jpg
from src.render.pixie.render_color_card import ColorCardRenderer

_lib_path = Constants.modules_conf.get_lib_path("Color-Rand")
__color_rand_version__ = "v1.1.1"

_colors = []


def register_module():
    pass


def load_colors():
    with open(os.path.join(_lib_path, "chinese_traditional.json"), 'r', encoding="utf-8") as f:
        _colors.clear()
        _colors.extend(json.load(f))


def transform_color(color: dict) -> tuple[str, str, str]:
    hex_text = "#FF" + color["hex"].upper()[1:]
    rgb_text = ", ".join([f"{val}" for val in color["RGB"]])
    h, s, v = rgb_to_hsv(color["RGB"][0], color["RGB"][1], color["RGB"][2])
    hsv_text = ", ".join([f"{val}" for val in [round(h * 360), round(s * 100), int(v)]])
    return hex_text, rgb_text, hsv_text


def add_qrcode(target_path: str, color: dict):
    qr = QRCode(error_correction=1,  # ERROR_CORRECT_L
                box_size=8)

    hex_clean = color["hex"][1:].lower()
    qr.add_data(f"https://gradients.app/zh/color/{hex_clean}")

    font_color = choose_text_color(hex_to_color(color["hex"]))
    font_transparent_color = change_alpha(font_color, 0)
    qrcode_img = qr.make_image(image_factory=StyledPilImage,
                               module_drawer=RoundedModuleDrawer(), eye_drawer=RoundedModuleDrawer(),
                               color_mask=SolidFillColorMask(color_to_tuple(font_transparent_color),
                                                             color_to_tuple(font_color)))

    target_img = Image.open(target_path)
    target_img.paste(qrcode_img, (1215, 618), qrcode_img)
    target_img.save(target_path)


@command(tokens=["color", "颜色", "色", "来个颜色", "来个色卡", "色卡"])
def reply_color_rand(message: RobotMessage):
    cached_prefix = get_cached_prefix('Color-Rand')
    img_path = f"{cached_prefix}.png"

    load_colors()
    picked_color = random.choice(_colors)
    hex_text, rgb_text, hsv_text = transform_color(picked_color)

    color_card = ColorCardRenderer(picked_color, hex_text, rgb_text, hsv_text).render()
    color_card.write_file(img_path)
    add_qrcode(img_path, picked_color)

    name = picked_color["name"]
    pinyin = picked_color["pinyin"]

    message.reply(f"[Color] {name} {pinyin}\nHEX: {hex_text}\nRGB: {rgb_text}\nHSV: {hsv_text}",
                  img_path=png2jpg(img_path), modal_words=False)
