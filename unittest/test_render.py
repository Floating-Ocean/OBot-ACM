import os
import random
import unittest

from src.core.bot.decorator import get_all_modules_info
from src.core.constants import Constants
from src.core.util.tools import png2jpg, fetch_url_json
from src.data.data_color_rand import get_colors
from src.module.game.tetris import BLOCKS
from src.module.tool.rand import transform_color, add_qrcode
from src.platform.manual.manual import ManualPlatform
from src.platform.online.atcoder import AtCoder
from src.platform.online.codeforces import Codeforces
from src.platform.online.nowcoder import NowCoder
from src.render.html.render_how_to_cook import render_how_to_cook
from src.render.pixie.render_about import AboutRenderer
from src.render.pixie.render_color_card import ColorCardRenderer, COLOR_QRCODE_COORD
from src.render.pixie.render_contest_list import ContestListRenderer
from src.render.pixie.render_help import HelpRenderer
from src.render.pixie.render_tetris_game import TetrisGameRenderer, TetrisNextBlockRenderer
from src.render.pixie.render_uptime import UptimeRenderer


class Render(unittest.TestCase):

    def test_color_rand(self):
        colors = get_colors("chinese_traditional")
        picked_color = random.choice(colors)
        hex_raw_text, rgb_raw_text, hsv_raw_text = transform_color(picked_color)
        color_card = ColorCardRenderer(picked_color, hex_raw_text, rgb_raw_text, hsv_raw_text).render()
        self.assertIsNotNone(color_card)
        color_card.write_file("test_color_rand.png")

    def test_color_qrcode(self):
        colors = get_colors("chinese_traditional")
        picked_color = random.choice(colors)
        hex_raw_text, rgb_raw_text, hsv_raw_text = transform_color(picked_color)
        color_card = ColorCardRenderer(picked_color, hex_raw_text, rgb_raw_text, hsv_raw_text).render()
        self.assertIsNotNone(color_card)
        color_card.write_file("test_color_qrcode.png")
        add_qrcode("test_color_qrcode.png", picked_color, COLOR_QRCODE_COORD)
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
        _lib_path = Constants.modules_conf.get_lib_path("How-To-Cook")
        dish_path = os.path.join(_lib_path, "lib", "dishes", "vegetable_dish", "西红柿豆腐汤羹", "西红柿豆腐汤羹.md")
        self.assertTrue(os.path.exists(dish_path))
        render_how_to_cook("1.5.0", dish_path, "西红柿豆腐汤羹.png")

    def test_help(self):
        help_img = HelpRenderer().render()
        self.assertIsNotNone(help_img)
        help_img.write_file("test_help.png")

    def test_tetris_game(self):
        current_map = [[0] * 24 for _ in range(16)]
        current_map.extend([
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0, 0, 0, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0],
            [1, 1, 0, 2, 0, 0, 0, 0, 7, 0, 0, 0, 5, 5, 0, 4, 2, 0, 2, 0, 0, 0, 1, 1],
            [1, 1, 2, 2, 2, 0, 3, 0, 6, 6, 0, 0, 3, 5, 0, 4, 4, 0, 2, 2, 0, 4, 1, 0],
            [4, 5, 5, 6, 6, 0, 3, 1, 1, 7, 7, 0, 3, 5, 7, 7, 4, 0, 2, 4, 4, 4, 0, 3],
            [4, 4, 5, 6, 6, 0, 3, 1, 1, 0, 0, 7, 3, 3, 6, 7, 7, 4, 4, 0, 4, 4, 4, 3],
            [0, 4, 5, 6, 6, 0, 3, 5, 2, 0, 2, 0, 3, 3, 6, 6, 6, 4, 4, 4, 4, 5, 0, 3],
            [0, 4, 4, 4, 4, 2, 0, 2, 0, 2, 2, 2, 1, 1, 6, 1, 1, 5, 5, 5, 1, 1, 1, 0]
        ])

        tetris_game_img = TetrisGameRenderer(current_map, 'test_tetris_map_to_svg',
                                             45, 153).render()
        self.assertIsNotNone(tetris_game_img)
        tetris_game_img.write_file("test_tetris_game.png")

    def test_tetris_next_block(self):
        for idx, block in enumerate(BLOCKS):
            tetris_next_block_img = TetrisNextBlockRenderer(block,
                                                            f'test_tetris_next_{idx}').render()
            self.assertIsNotNone(tetris_next_block_img)
            tetris_next_block_img.write_file(f"test_tetris_next_block_{idx}.png")

    def test_uptime(self):
        status = fetch_url_json("https://stats.uptimerobot.com/api/getMonitorList/BAPG4sPMZr",
                                method='GET')
        uptime_img = UptimeRenderer(status, 'test_uptime_monitor').render()
        self.assertIsNotNone(uptime_img)
        uptime_img.write_file("test_uptime.png")

    def test_about(self):
        about_img = AboutRenderer(
            ("OBot Core", Constants.core_version),
            get_all_modules_info()
        ).render()
        self.assertIsNotNone(about_img)
        about_img.write_file("test_about.png")

if __name__ == '__main__':
    unittest.main()
