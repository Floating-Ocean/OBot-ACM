import os
import random
import unittest

from src.core.constants import Constants
from src.core.util.tools import png2jpg
from src.module.tool.how_to_cook import __how_to_cook_version__
from src.module.tool.color_rand import load_colors, _colors, transform_color, add_qrcode
from src.platform.manual.manual import ManualPlatform
from src.platform.online.atcoder import AtCoder
from src.platform.online.codeforces import Codeforces
from src.platform.online.nowcoder import NowCoder
from src.render.html.render_how_to_cook import render_how_to_cook
from src.render.pixie.render_color_card import ColorCardRenderer
from src.render.pixie.render_contest_list import ContestListRenderer
from src.render.pixie.render_help import HelpRenderer


class Render(unittest.TestCase):

    def test_color_rand(self):
        load_colors()
        picked_color = random.choice(_colors)
        hex_raw_text, rgb_raw_text, hsv_raw_text = transform_color(picked_color)
        color_card = ColorCardRenderer(picked_color, hex_raw_text, rgb_raw_text, hsv_raw_text).render()
        self.assertIsNotNone(color_card)
        color_card.write_file("test_color_rand.png")

    def test_color_qrcode(self):
        load_colors()
        picked_color = random.choice(_colors)
        hex_raw_text, rgb_raw_text, hsv_raw_text = transform_color(picked_color)
        color_card = ColorCardRenderer(picked_color, hex_raw_text, rgb_raw_text, hsv_raw_text).render()
        self.assertIsNotNone(color_card)
        color_card.write_file("test_color_qrcode.png")
        add_qrcode("test_color_qrcode.png", picked_color)
        png2jpg("test_color_qrcode.png")

    def test_contest_list(self):
        upcoming_contests, running_contests, finished_contests = [], [], []
        for platform in [Codeforces, AtCoder, NowCoder, ManualPlatform]:
            upcoming, running, finished = platform.get_contest_list()
            upcoming_contests.extend(upcoming)
            running_contests.extend(running)
            finished_contests.extend(finished)

        upcoming_contests.sort(key=lambda c: c.start_time)
        running_contests.sort(key=lambda c: c.start_time)
        finished_contests.sort(key=lambda c: c.start_time)

        contest_list_img = ContestListRenderer(upcoming_contests, running_contests, finished_contests).render()
        self.assertIsNotNone(contest_list_img)
        contest_list_img.write_file("test_contest_list.png")

    def test_cook_md(self):
        _lib_path = os.path.join(Constants.config["lib_path"], "How-To-Cook")
        dish_path = os.path.join(_lib_path, "lib", "dishes", "vegetable_dish", "西红柿豆腐汤羹", "西红柿豆腐汤羹.md")
        self.assertTrue(os.path.exists(dish_path))
        render_how_to_cook(__how_to_cook_version__, dish_path, "西红柿豆腐汤羹.png")

    def test_help(self):
        help_img = HelpRenderer().render()
        self.assertIsNotNone(help_img)
        help_img.write_file("test_help.png")

if __name__ == '__main__':
    unittest.main()
