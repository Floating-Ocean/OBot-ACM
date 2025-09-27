import json
import time
import unittest
from dataclasses import asdict
from datetime import datetime

from aiohttp import ClientConnectorSSLError
from botpy.errors import ServerError

from src.core.util.exception import handle_exception, UnauthorizedError, ModuleRuntimeError
from src.core.util.tools import decode_range
from src.platform.collect.cpcfinder import CPCFinder
from src.platform.model import DynamicContest
from src.platform.online.atcoder import AtCoder
from src.platform.online.codeforces import Codeforces, ProbInfo


class Module(unittest.TestCase):

    def test_cf_user_standings(self):
        handle = "FloatingOcean"
        contest_id = "2043"
        standings = Codeforces.get_user_contest_standings(handle, contest_id)
        self.assertIsNotNone(standings)
        contest_info, standings_info = standings

        content = (f"[Codeforces] {handle} 比赛榜单查询\n\n"
                   f"{contest_info}")
        if standings_info is not None:
            if len(standings_info) > 0:
                content += '\n\n'
                content += '\n\n'.join(standings_info)
            else:
                content += '\n\n暂无榜单信息'

        print(content)

    def test_cf_predict(self):
        try:
            with open('data.json', 'w', encoding='utf-8') as json_file:
                self.assertIsNotNone(json_file)
                contest_id = "2043"
                json.dump({handle: asdict(predict)
                           for handle, predict in Codeforces._fetch_contest_predict(contest_id).items()},
                          json_file, ensure_ascii=False, indent=4)
        except Exception as e:
            print(e)

    def test_cf_rand_problem(self):
        l, r = decode_range("2100", (3, 4))
        self.assertNotEqual(l, -1)
        self.assertNotEqual(r, -1)
        print(l, r)

    def test_atc_rand_problem(self):
        contest_type = "common"
        limit = "2100"
        prob = AtCoder.get_prob_filtered(contest_type, limit)
        self.assertIsInstance(prob, dict)
        print(prob)

    def test_error_handle(self):
        print(handle_exception(ServerError('This is a test server error.')))
        print(handle_exception(ClientConnectorSSLError(None, OSError('This is a test client connector ssl error.'))))
        print(handle_exception(UnauthorizedError('阿弥诺斯')))
        print(handle_exception(ModuleRuntimeError('IndexError(...)')))
        self.assertTrue(True)  # 因为没啥好断言的

    def test_contest_json(self):
        contest = DynamicContest(
            platform='ICPC',
            abbr='武汉邀请赛',
            name='2025年ICPC国际大学生程序设计竞赛全国邀请赛（武汉）',
            start_time=int(datetime.strptime("250427100000", "%y%m%d%H%M%S").timestamp()),
            duration=60*60*5,
            supplement='华中科技大学'
        )
        print(json.dumps(asdict(contest), ensure_ascii=False, indent=4))
        self.assertTrue(True)  # 因为没啥好断言的

    @unittest.skip("需要手动提交，仅供手动测试使用")
    def test_cf_binding(self):
        handle = "FloatingOcean"
        establish_time = int(time.time())
        _ = input("发起绑定，请在10分钟内于P1A提交一发CE后任意键继续\n")
        bind_result = Codeforces.validate_binding(handle, establish_time)
        self.assertTrue(bind_result)

    def test_cf_duel_exclude(self):
        duel_a, duel_b = "FloatingOcean", "Kepy"

        excludes = set()
        excludes.update(Codeforces.get_user_submit_prob_id(duel_a))
        excludes.update(Codeforces.get_user_submit_prob_id(duel_b))
        self.assertNotEqual(len(excludes), 0)
        print(len(excludes), excludes)

        pickup_prob = Codeforces.get_prob_filtered(ProbInfo("all", None, False), excludes=excludes)
        self.assertIsInstance(pickup_prob, dict)
        print(pickup_prob)

    def test_cpcfinder(self):
        stu_id = CPCFinder.find_student_id("蒋凌宇", "北京大学")
        self.assertIsInstance(stu_id, str)
        stu_general = CPCFinder.get_student_general(stu_id)
        print(stu_general)
        stu_awards = CPCFinder.get_student_awards(stu_id)
        print(stu_awards)


if __name__ == '__main__':
    unittest.main()
