import re

from src.core.bot.decorator import module, command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.tools import run_py_file
from src.platform.collect.cpcfinder import CPCFinder

_oierdb_lib_path = Constants.modules_conf.get_lib_path("OIerDb")

@command(tokens=['test'])
def test(message: RobotMessage):
    oierdb_daily_update_job()

def oierdb_daily_update_job():
    Constants.log.info('[oierdb] 每日数据库更新任务开始')
    run_py_file('main.py', _oierdb_lib_path, log_ignore_regex=r'.*%.*\|.*\|.*')
    Constants.log.info('[oierdb] 每日数据库更新任务完成')


def _format_cpc_rank(official: bool, rank: int, official_rank: int) -> str:
    if official:
        return f"#{official_rank}({rank})"
    else:
        return f"*{rank}"


@command(tokens=['cpcfinder', 'xcpcfinder', 'cpcfind', 'xcpcfind', 'cpcfd', 'xcpcfd'])
def reply_cpcfinder(message: RobotMessage):
    try:
        content = re.sub(r'<@!\d+>', '', message.content).strip().split()
        if len(content) != 3:
            message.reply('请输入两个参数，分别代表选手姓名和学校，如：\n\n'
                          f'{content[0]} 蒋凌宇 北京大学', modal_words=False)
            return

        stu_name, stu_school = content[1], content[2]

        message.reply('正在查询 XCPC 选手信息，请稍等')
        stu_id = CPCFinder.find_student_id(stu_name, stu_school)

        if isinstance(stu_id, int):
            if stu_id < 0:
                message.reply('查询异常，请稍后重试')
            elif stu_id == 0:
                message.reply('未找到该选手信息')
            elif stu_id == 1:
                message.reply('目前只支持查询单一用户，请缩小查询范围')
            return

        stu_general = CPCFinder.get_student_general(stu_id)
        stu_awards = CPCFinder.get_student_awards(stu_id)

        if isinstance(stu_general, int) or isinstance(stu_awards, int):
            message.reply('查询异常，请稍后重试')
            return

        stu_info = ("[CPCFinder] 选手查询\n\n"
                    f"{stu_general.name} / {stu_general.school}\n\n"
                    f"冠军: {stu_general.champion} / 亚军: {stu_general.sec} / 季军: {stu_general.thi}\n"
                    f"金牌: {stu_general.gold} / 银牌: {stu_general.silver} / 铜牌: {stu_general.bronze}\n\n"
                    "获奖信息: \n")

        awards = [
            (
                f"[{stu_award.medal}] {stu_award.contest_name}\n"
                f"{_format_cpc_rank(stu_award.official, stu_award.rank, stu_award.official_rank)} "
                f"{stu_award.team_name}\n"
                f"@{stu_award.place} {stu_award.date}"
            )
            for stu_award in stu_awards
        ]

        stu_info += '\n'.join(awards)
        message.reply(stu_info, modal_words=False)

    except Exception as e:
        message.report_exception('Contestant.CPCFinder', e)


@module(
    name="Contestant-Finder",
    version="v1.0.1"
)
def register_module():
    pass
