import json
import unittest

from dataclasses import asdict

from src.platform.online.atcoder import AtCoder
from src.platform.online.codeforces import Codeforces
from src.platform.online.nowcoder import NowCoder
from src.platform.collect.clist import Clist
from test.file_output import get_output_path


class Platform(unittest.TestCase):
    def test_codeforces_contest_list(self):
        p = Codeforces.get_contest_list()
        self.assertIsNotNone(p)
        for tp in p:
            print(json.dumps([asdict(d) for d in tp], indent=4, ensure_ascii=False))

    def test_atcoder_contest_list(self):
        p = AtCoder.get_contest_list()
        self.assertIsNotNone(p)
        for tp in p:
            print(json.dumps([asdict(d) for d in tp], indent=4, ensure_ascii=False))

    def test_nowcoder_contest_list(self):
        p = NowCoder.get_contest_list()
        self.assertIsNotNone(p)
        for tp in p:
            print(json.dumps([asdict(d) for d in tp], indent=4, ensure_ascii=False))

    def test_atcoder_user(self):
        handle = "FluctuateOcean"
        p = AtCoder.get_user_info(handle)
        self.assertIsNotNone(p)

    def test_clist(self):
        problems = Clist.api("problem", resource_id=93, rating__gte=800, rating__lte=1000,
                             url__regex=r'^(?!https:\/\/atcoder\.jp\/contests\/(abc|arc|agc|ahc)).*')
        self.assertIsNotNone(problems)
        print(json.dumps(problems, indent=4, ensure_ascii=False))

    def test_nowcoder_user(self):
        handle = "144128559"
        p = NowCoder.get_user_info(handle)
        print(p[0])
        print(p[1])
        self.assertIsNotNone(p)

    def test_nowcoder_user_last_contest(self):
        handle = "144128559"
        p = NowCoder.get_user_last_contest(handle)
        print(p)
        self.assertIsNotNone(p)

    def test_codeforces_user_card(self):
        test_handles = ['floatingocean', 'qwedc001', 'jiangly', 'Lingyu0qwq', 'I_am_real_wx', 'BingYu2023', 'C10udz']
        for handle in test_handles:
            img = Codeforces.get_user_id_card(handle)
            self.assertIsNotNone(img)
            img.write_file(get_output_path(f"platform_cf_user_card_{handle}.png"))

    def test_atcoder_user_card(self):
        test_handles = ['floatingocean', 'qwedc001', 'jiangly', 'Lingyu0qwq']
        for handle in test_handles:
            img = AtCoder.get_user_id_card(handle)
            self.assertIsNotNone(img)
            img.write_file(get_output_path(f"platform_atc_user_card_{handle}.png"))

    def test_nowcoder_user_card(self):
        test_handles = ['144128559', '140690880', '737857302', '329687984', '815516497', '882260751']
        for handle in test_handles:
            img = NowCoder.get_user_id_card(handle)
            self.assertIsNotNone(img)
            img.write_file(get_output_path(f"platform_nk_user_card_{handle}.png"))

    def test_nowcoder_contest_search(self):
        test_names = ['福建师范', '牛客周赛', '牛客国庆集训派对']
        for name in test_names:
            contest = NowCoder._get_specified_contest(name)
            self.assertIsNotNone(contest)
            contest_id, contest_info = contest
            print(contest_id)
            print(contest_info)

    def test_nowcoder_contest_standing(self):
        test_names = ['寒假', '周赛', '6']
        for name in test_names:
            standing = NowCoder.get_user_contest_standings("福建师范", name)
            self.assertIsNotNone(standing)
            contest_info, standings_info = standing
            print(contest_info)
            print(standings_info)


if __name__ == '__main__':
    unittest.main()
