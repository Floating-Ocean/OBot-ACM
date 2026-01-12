import random
from colorsys import rgb_to_hsv

from PIL import Image
from easy_pixie import choose_text_color, color_to_tuple, change_alpha, hex_to_color
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.main import QRCode

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.util.tools import png2jpg
from src.data.data_cache import get_cached_prefix
from src.data.data_color import get_colors, Colors
from src.render.pixie.render_color_card import ColorCardRenderer, COLOR_QRCODE_COORD


def transform_color(color: Colors) -> tuple[str, str, str]:
    hex_text = "#FF" + color.color.upper()[1:]
    rgb = color_to_tuple(hex_to_color(hex_text), include_alpha=False)
    rgb_text = ", ".join(str(val) for val in rgb)
    # 归一化
    r_norm, g_norm, b_norm = (val / 255 for val in rgb)
    h, s, v = rgb_to_hsv(r_norm, g_norm, b_norm)
    hsv_text = ", ".join(str(val) for val in [round(h * 360), round(s * 100), round(v * 100)])
    return hex_text, rgb_text, hsv_text


def add_qrcode(target_path: str, color: Colors, paste_coord: tuple[int, int]):
    qr = QRCode(error_correction=1,  # ERROR_CORRECT_L
                box_size=8)

    hex_clean = color.color[1:].lower()
    qr.add_data(f"https://gradients.app/zh/color/{hex_clean}")

    font_color = choose_text_color(hex_to_color(color.color))
    font_transparent_color = change_alpha(font_color, 0)
    qrcode_img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        eye_drawer=RoundedModuleDrawer(),
        color_mask=SolidFillColorMask(
            back_color=color_to_tuple(font_transparent_color),
            front_color=color_to_tuple(font_color)
        )
    ).get_image()

    target_img = Image.open(target_path)
    target_img.paste(qrcode_img, paste_coord, qrcode_img)
    target_img.save(target_path)


@command(tokens=["color", "颜色", "色", "来个颜色", "来个色卡", "色卡"])
def reply_color_rand(message: RobotMessage):
    chosen_type = "chinese_traditional"
    content = message.tokens
    if len(content) > 1:
        arg = content[1].strip().lower().replace("_", "-")
        if arg in ["chi", "chinese", "zh", "chinese-traditional",
                   "中", "中国", "中国传统", "中国色", "中国传统颜色"]:
            chosen_type = "chinese_traditional"
        elif arg in ["jp", "japanese", "rb", "nippon", "nippon-traditional",
                     "日", "日本", "日本传统", "日本色", "日本传统颜色"]:
            chosen_type = "nippon_traditional"
        else:
            message.reply("目前仅支持 中国传统颜色 和 日本传统颜色 哦", modal_words=False)
            return

    cached_prefix = get_cached_prefix('Color-Rand')
    img_path = f"{cached_prefix}.png"

    colors = get_colors(chosen_type)
    if not colors:
        message.reply("颜色数据集为空，请踢一踢管理员")
        return

    picked_color = random.choice(colors)
    hex_text, rgb_text, hsv_text = transform_color(picked_color)

    color_card = ColorCardRenderer(picked_color, hex_text, rgb_text, hsv_text).render()
    color_card.write_file(img_path)
    add_qrcode(img_path, picked_color, COLOR_QRCODE_COORD)

    name = picked_color.name
    color_id = picked_color.id

    message.reply(f"[Color] {name} {color_id}\nHEX: {hex_text}\nRGB: {rgb_text}\nHSV: {hsv_text}",
                  img_path=png2jpg(img_path), modal_words=False)


@module(
    name="Color",
    version="v3.1.0"
)
def register_module():
    pass
