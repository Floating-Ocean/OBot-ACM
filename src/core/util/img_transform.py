import os
from enum import Enum

from PIL import Image, ImageSequence

from src.core.util.output_cache import get_cached_prefix


class ImgSymmetric(Enum):
    INHERIT = -1
    LEFT = 0
    RIGHT = 1
    TOP = 2
    BOTTOM = 3


apply_transform: dict[str, tuple[ImgSymmetric, int]] = {}


def _sym_img(img: Image.Image, way: ImgSymmetric) -> Image.Image:
    new_img = Image.new("RGBA", (img.width, img.height))

    if way in (ImgSymmetric.LEFT, ImgSymmetric.RIGHT):
        mirrored = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if way == ImgSymmetric.LEFT:
            l_part = img.crop((0, 0, img.width // 2, img.height))
            r_part = mirrored.crop(((img.width + 1) // 2, 0, img.width, img.height))
        else:
            l_part = mirrored.crop((0, 0, img.width // 2, img.height))
            r_part = img.crop(((img.width + 1) // 2, 0, img.width, img.height))

        new_img.paste(l_part, (0, 0))
        new_img.paste(r_part, (img.width // 2, 0))
        return new_img.crop((0, 0, img.width // 2 * 2, img.height))

    elif way in (ImgSymmetric.TOP, ImgSymmetric.BOTTOM):
        mirrored = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        if way == ImgSymmetric.TOP:
            t_part = img.crop((0, 0, img.width, img.height // 2))
            b_part = mirrored.crop((0, (img.height + 1) // 2, img.width, img.height))
        else:
            t_part = mirrored.crop((0, 0, img.width, img.height // 2))
            b_part = img.crop((0, (img.height + 1) // 2, img.width, img.height))

        new_img.paste(t_part, (0, 0))
        new_img.paste(b_part, (0, img.height // 2))
        return new_img.crop((0, 0, img.width, img.height // 2 * 2))

    else:
        return img


def make_img_sym(img_path: str, way: ImgSymmetric, output_prefix: str) -> str:
    new_path = f"{output_prefix}{os.path.splitext(img_path)[1]}"

    with Image.open(img_path) as im:
        is_animated = getattr(im, "is_animated", False) and im.format == "GIF"
        if not is_animated:
            new_img = _sym_img(im.convert("RGBA"), way)
            if im.format in ("JPEG", "JPG"):
                new_img.convert("RGB").save(new_path, format="JPEG")
            else:
                new_img.save(new_path, format="PNG")

        else:
            # GIF 动图处理
            frames = []
            durations = []
            for frame in ImageSequence.Iterator(im):
                new_frame = _sym_img(frame.convert("RGBA"), way)
                frames.append(new_frame)
                # 帧间隔时间，默认 100ms
                duration = frame.info.get("duration", 100)
                durations.append(duration)

            frames[0].save(
                new_path,
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
                disposal=2,
                format="GIF"
            )

    return new_path


def patch_img_transform(author: str, img_path: str) -> str:
    way = ImgSymmetric.INHERIT
    if author in apply_transform:
        cached_way, cnt = apply_transform[author]
        if cnt > 0:
            cnt -= 1
            way = cached_way
            apply_transform[author] = (cached_way, cnt)

    if way == ImgSymmetric.INHERIT:
        return img_path
    else:
        cached_prefix = get_cached_prefix('Img-Transform')
        return make_img_sym(img_path, way, cached_prefix)
