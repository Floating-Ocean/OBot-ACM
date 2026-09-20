import os
import random
import re
import unittest
from datetime import date, timedelta

from src.core.bot.decorator import get_all_modules_info
from src.core.constants import Constants
from src.core.util.tools import png2jpg, fetch_url_json
from src.data.data_color import get_colors
from src.data.data_pick_one import (get_pick_one_data, get_category_stat,
                                   pick_preview_imgs)
from src.module.game.tetris import BLOCKS
from src.module.stuff.color import transform_color, add_qrcode
from src.platform.manual.manual import ManualPlatform
from src.platform.online.atcoder import AtCoder
from src.platform.online.codeforces import Codeforces
from src.platform.online.nowcoder import NowCoder
from src.render.html.render_how_to_cook import render_how_to_cook
from src.render.pixie.render_about import AboutRenderer
from src.render.pixie.render_color_card import ColorCardRenderer, COLOR_QRCODE_COORD
from src.render.pixie.render_contest_list import ContestListRenderer
from src.render.pixie.render_help import HelpRenderer
from src.render.pixie.render_pick_one import PickOneRenderer, PickOnePreviewRenderer
from src.render.pixie.render_tetris_game import TetrisGameRenderer, TetrisNextBlockRenderer
from src.render.pixie.render_uptime import UptimeRenderer
from src.render.svg.render_uptime_status import (render_uptime_status, get_percentile_color,
                                                 BAR_HEIGHT, BAR_RADIUS, BAR_SPACING,
                                                 BAR_WIDTH)
from test.file_output import get_output_path


class Render(unittest.TestCase):

    def test_color_rand(self):
        colors = get_colors("chinese_traditional")
        picked_color = random.choice(colors)
        hex_raw_text, rgb_raw_text, hsv_raw_text = transform_color(picked_color)
        color_card = ColorCardRenderer(picked_color, hex_raw_text, rgb_raw_text, hsv_raw_text).render()
        self.assertIsNotNone(color_card)
        color_card.write_file(get_output_path("render_color_rand.png"))

    def test_color_qrcode(self):
        colors = get_colors("chinese_traditional")
        picked_color = random.choice(colors)
        hex_raw_text, rgb_raw_text, hsv_raw_text = transform_color(picked_color)
        color_card = ColorCardRenderer(picked_color, hex_raw_text, rgb_raw_text, hsv_raw_text).render()
        self.assertIsNotNone(color_card)
        png_path = get_output_path("render_color_qrcode.png")
        color_card.write_file(png_path)
        add_qrcode(png_path, picked_color, COLOR_QRCODE_COORD)
        png2jpg(png_path)

    def test_contest_list(self):
        running_contests, upcoming_contests, finished_contests = [], [], []
        for platform in [Codeforces, AtCoder, NowCoder, ManualPlatform]:
            running, upcoming, finished = platform.get_contest_list()
            running_contests.extend(running)
            upcoming_contests.extend(upcoming)
            finished_contests.extend(finished)

        contest_list_img = ContestListRenderer(running_contests, upcoming_contests, finished_contests).render()
        self.assertIsNotNone(contest_list_img)
        contest_list_img.write_file(get_output_path("render_contest_list.png"))

    def test_manual_only_contest_list(self):
        running_contests, upcoming_contests, finished_contests = [], [], []
        for platform in [ManualPlatform]:
            running, upcoming, finished = platform.get_contest_list()
            running_contests.extend(running)
            upcoming_contests.extend(upcoming)
            finished_contests.extend(finished)

        contest_list_img = ContestListRenderer(running_contests, upcoming_contests, finished_contests).render()
        self.assertIsNotNone(contest_list_img)
        contest_list_img.write_file(get_output_path("render_manual_only_contest_list.png"))

    def test_cook_md(self):
        _lib_path = Constants.modules_conf.get_lib_path("How-To-Cook")
        dish_path = os.path.join(_lib_path, "dishes", "vegetable_dish", "西红柿豆腐汤羹", "西红柿豆腐汤羹.md")
        self.assertTrue(os.path.exists(dish_path))
        render_how_to_cook("1.5.0", dish_path, get_output_path("render_cook_md.png"))

    def test_help(self):
        help_img = HelpRenderer().render()
        self.assertIsNotNone(help_img)
        help_img.write_file(get_output_path("render_help.png"))

    def test_pick_one(self):
        pick_one_img = PickOneRenderer(get_pick_one_data()).render()
        self.assertIsNotNone(pick_one_img)
        pick_one_img.write_file(get_output_path("render_pick_one.png"))

    def test_pick_one_preview(self):
        data = get_pick_one_data()

        # 挑一个数量多的和一个只有一张的；空类别不再画图，由命令层文字回复
        for img_key in ("capoo", "orzjh"):
            imgs = get_category_stat(img_key)
            self.assertTrue(imgs, f"{img_key} 应当有表情包")
            renderer = PickOnePreviewRenderer(
                data, img_key, pick_preview_imgs(imgs))

            preview_img = renderer.render()
            self.assertIsNotNone(preview_img)
            preview_img.write_file(get_output_path(f"render_pick_one_preview_{img_key}.png"))

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

        tetris_game_img = TetrisGameRenderer(current_map, get_output_path("render_tetris_map_to_svg"),
                                             45, 153).render()
        self.assertIsNotNone(tetris_game_img)
        tetris_game_img.write_file(get_output_path("render_tetris_game.png"))

    def test_tetris_next_block(self):
        for idx, block in enumerate(BLOCKS):
            tetris_next_block_img = TetrisNextBlockRenderer(block,
                                                            get_output_path(f"render_tetris_next_{idx}")).render()
            self.assertIsNotNone(tetris_next_block_img)
            tetris_next_block_img.write_file(get_output_path(f"render_tetris_next_block_{idx}.png"))

    def test_uptime(self):
        status = fetch_url_json("https://stats.uptimerobot.com/api/getMonitorList/BAPG4sPMZr",
                                method='GET')
        uptime_img = UptimeRenderer(status, get_output_path("render_uptime_monitor")).render()
        self.assertIsNotNone(uptime_img)
        uptime_img.write_file(get_output_path("render_uptime.png"))

    _MOCK_UPTIME_DAYS = 90  # 与线上接口一致，保证 mock 出来的卡片列数和真实的一致

    @classmethod
    def _mock_daily_ratios(cls, ratios: list) -> list[dict]:
        """构造 UptimeRobot 的 dailyRatios 字段，None 表示当天无数据"""
        first_day = date(2026, 1, 1)
        return [{"date": str(first_day + timedelta(days=day)),
                 "ratio": "0.000" if ratio is None else f"{ratio:.3f}",
                 "label": "black" if ratio is None else "poor"}
                for day, ratio in enumerate(ratios)]

    @classmethod
    def _mock_uptime_status(cls) -> dict:
        """模拟一份 UptimeRobot 返回：一个正常、一个异常、一个暂停"""
        days = cls._MOCK_UPTIME_DAYS
        return {
            "statistics": {"counts": {"up": 1, "down": 1, "paused": 1, "total": 3}},
            "psp": {"monitors": [
                {"name": "AtCoder", "statusClass": "success",
                 "dailyRatios": cls._mock_daily_ratios([100] * days)},
                # 中间一段掉线，其中一天完全不可用
                {"name": "Codeforces", "statusClass": "danger",
                 "dailyRatios": cls._mock_daily_ratios(
                     [100] * 60 + [99.2, 97.5, 88.2, 61.4, 0] + [100] * (days - 65))},
                {"name": "Luogu", "statusClass": "paused",
                 "dailyRatios": cls._mock_daily_ratios([None] * 6 + [100] * (days - 6))},
            ]},
        }

    def test_uptime_mock_some_down(self):
        """不联网的 mock 渲染：存在异常服务时标题为“部分服务异常”，该监控项显示红色“异常”"""
        status = self._mock_uptime_status()
        self.assertGreater(status["statistics"]["counts"]["down"], 0)
        for monitor in status["psp"]["monitors"]:
            self.assertEqual(len(monitor["dailyRatios"]), self._MOCK_UPTIME_DAYS)

        uptime_img = UptimeRenderer(status, get_output_path("render_uptime_mock")).render()
        self.assertIsNotNone(uptime_img)
        uptime_img.write_file(get_output_path("render_uptime_mock.png"))

        # 异常监控项的柱子按当天可用性着色，停摆当天（0%）为红色
        danger_monitor = status["psp"]["monitors"][1]
        self.assertEqual(danger_monitor["statusClass"], "danger")
        svg, _, _ = render_uptime_status(danger_monitor["dailyRatios"])
        self.assertIn(f'fill="{get_percentile_color(0)}"', svg)

    def test_uptime_status_bar_height(self):
        """竖条为进度条：可用性越低柱子越矮，且高可用区间的差距被拉开；无数据当天为灰色满高占位条"""
        status = [{"ratio": ratio, "label": "poor"}
                  for ratio in ("100.000", "99.000", "95.000", "50.000", "0.000")]
        status.append({"ratio": "0.000", "label": "black"})

        svg, width, height = render_uptime_status(status)
        self.assertEqual(height, BAR_HEIGHT)
        self.assertEqual(width, (len(status) - 1) * (BAR_WIDTH + BAR_SPACING) + BAR_WIDTH)

        bars = sorted(
            (float(bar_x), float(bar_height), bar_color)
            for bar_x, bar_height, bar_color in re.findall(
                r'<rect x="([\d.]+)" y="[\d.]+" width="[\d.]+" height="([\d.]+)"'
                r'[^>]*fill="(#[0-9a-f]{6})"', svg)
        )
        self.assertEqual(len(bars), len(status))

        heights = [bar_height for _, bar_height, _ in bars]
        self.assertEqual(heights[0], BAR_HEIGHT)  # 100% 铺满整根柱子
        self.assertEqual(heights[:5], sorted(heights[:5], reverse=True))  # 可用性越低越矮
        # 高可用区间被拉开：99% 与 100% 的高度差远大于线性映射下的 1%
        self.assertGreater(BAR_HEIGHT - heights[1], BAR_HEIGHT * 0.03)
        # 极低可用性仍保留一个圆头的高度，不会缩成一条线
        self.assertGreaterEqual(heights[4], BAR_RADIUS)
        # 无数据当天是满高的灰色占位条
        self.assertEqual(heights[5], BAR_HEIGHT)

    def test_about(self):
        about_img = AboutRenderer(
            ("OBot Core", f"{Constants.core_version}-{Constants.git_commit.hash_short}"),
            get_all_modules_info()
        ).render()
        self.assertIsNotNone(about_img)
        about_img.write_file(get_output_path("render_about.png"))

if __name__ == '__main__':
    unittest.main()
