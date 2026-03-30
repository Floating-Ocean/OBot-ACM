import os
from enum import Enum

from PIL import Image, ImageSequence


class ImgSymmetric(Enum):
    LEFT = 0
    RIGHT = 1
    TOP = 2
    BOTTOM = 3


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

    else:
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


def make_img_sym(img_path: str, way: ImgSymmetric, remove_origin: bool = True) -> str:
    new_path = os.path.splitext(img_path)[0] + '_trans.' + os.path.splitext(img_path)[1]

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

    if remove_origin:
        os.remove(img_path)

    return new_path
