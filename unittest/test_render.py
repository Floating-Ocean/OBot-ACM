import os
import random
import unittest

import pixie
from easy_pixie import draw_full, draw_img, Loc

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

    def test_tetris(self):
        colors = [
            "#000000", "#ec407a", "#ab47bc", "#7986cb", "#29b6f6", "#4db6ac", "#d4e157", "#ffa726"
        ]
        current_map = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0, 0, 0, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0],
            [1, 1, 0, 2, 0, 0, 0, 0, 7, 0, 0, 0, 5, 5, 0, 4, 2, 0, 2, 0, 0, 0, 1, 1],
            [1, 1, 2, 2, 2, 0, 3, 0, 6, 6, 0, 0, 3, 5, 0, 4, 4, 0, 2, 2, 0, 4, 1, 0],
            [4, 5, 5, 6, 6, 0, 3, 1, 1, 7, 7, 0, 3, 5, 7, 7, 4, 0, 2, 4, 4, 4, 0, 3],
            [4, 4, 5, 6, 6, 0, 3, 1, 1, 0, 0, 7, 3, 3, 6, 7, 7, 4, 4, 0, 4, 4, 4, 3],
            [0, 4, 5, 6, 6, 0, 3, 5, 2, 0, 2, 0, 3, 3, 6, 6, 6, 4, 4, 4, 4, 5, 0, 3],
            [0, 4, 4, 4, 4, 2, 0, 2, 0, 2, 2, 2, 1, 1, 6, 1, 1, 5, 5, 5, 1, 1, 1, 0]
        ]

        def tetris_map_to_svg() -> str:
            svg_rects = ('<svg xmlns="http://www.w3.org/2000/svg" fill="#303030"'
                         ' preserveAspectRatio="xMinYMin meet" viewBox="0 0 310 310">\n')
            x_offset, y_offset = 0, 0

            for line in current_map:
                svg_rects += f'<g transform="translate(0, {y_offset * 13})">\n'
                x_offset = 0
                for item in line:
                    svg_rects += (f'<rect x="{x_offset * 13}" width="11" height="11"'
                                  f' fill="{colors[item]}"/>\n')
                    x_offset += 1
                y_offset += 1
                svg_rects += '</g>\n'

            svg_rects += '</svg>'

            return svg_rects

        with open('test_tetris_map_to_svg.svg', 'w') as f:
            tetris_svg = tetris_map_to_svg()
            self.assertIsNotNone(tetris_svg)
            f.write(tetris_svg)

        tetris_map = pixie.read_image('test_tetris_map_to_svg.svg')
        img = pixie.Image(314, 314)
        draw_full(img, (36, 36, 36))
        draw_img(img, tetris_map, Loc(2, 2, 310, 310))
        img.write_file('test_tetris_map_to_svg.png')


if __name__ == '__main__':
    unittest.main()
