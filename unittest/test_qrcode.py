import random
import unittest

from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.main import QRCode

from src.module.color_rand import load_colors, _colors


class QrCode(unittest.TestCase):
    def test_qrcode_normal(self):
        qr = QRCode(error_correction=0)  # ERROR_CORRECT_M
        load_colors()
        picked_color = random.choice(_colors)
        hex_clean = picked_color["hex"][1:].lower()
        # qr.add_data(f"https://gradients.app/zh/color/{hex_clean}")
        qr.add_data(
            "闻古之贤师，阅卷时未尝苛责于分数。师之板书，若阳春白雪之妙；师之讲授，似高山流水之悦耳，听师之课者，无不钦佩。然期末之卷，难若挟泰山以超北海；而吾辈之学，犹沧海之一粟，此吾之所忧也。")

        img_1 = qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer(), eye_drawer=RoundedModuleDrawer(),
                              color_mask=SolidFillColorMask(back_color=(0, 0, 0, 0), front_color=(0, 0, 0, 255)))
        self.assertIsNotNone(img_1)
        img_1.save("qrcode_normal.png")


if __name__ == '__main__':
    unittest.main()
