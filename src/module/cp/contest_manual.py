from dataclasses import asdict
from datetime import datetime

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.bot.perm import PermissionLevel
from src.core.util.tools import is_valid_date, check_is_int
from src.data.data_contest_manual import ManualContest, save_contest
from src.platform.model import DynamicContest


@command(tokens=["导入比赛"], permission_level=PermissionLevel.MOD)
def reply_manual_add_contest(message: RobotMessage):
    help_content = ("/导入比赛 [platform] [abbr] [name] [start_time] [duration] [supplement]\n\n"
                    "示例：/导入比赛 ICPC 武汉邀请赛 2025年ICPC国际大学生程序设计竞赛全国邀请赛（武汉） 250427100000 18000 华中科技大学\n\n"
                    "注意，start_time包含年月日时分秒，且均为两位，duration单位为秒")
    if len(message.tokens) != 7:
        message.reply("参数数量有误\n\n"
                      f"{help_content}")
        return

    platform, abbr, name, start_time_raw, duration_raw, supplement = message.tokens[1:]

    date_format = "%y%m%d%H%M%S"
    if not is_valid_date(start_time_raw, date_format):
        message.reply("start_time 格式错误\n\n"
                      f"{help_content}")
        return
    start_time = int(datetime.strptime(start_time_raw, date_format).timestamp())

    if not check_is_int(duration_raw):
        message.reply("duration 必须为整数\n\n"
                      f"{help_content}")
        return
    duration = int(duration_raw)
    if duration <= 0:
        message.reply("duration 必须为正整数\n\n"
                      f"{help_content}")
        return

    contest = ManualContest(platform, abbr, name, start_time, duration, supplement)
    save_status = save_contest(contest)

    if save_status:
        message.reply("导入比赛成功，比赛解析为\n\n" +
                      DynamicContest(**asdict(contest)).format(), modal_words=False)
    else:
        message.reply("该比赛已存在，导入失败")


@module(
    name="Contest-List-Renderer",
    version="v1.1.0"
)
def register_module():
    pass
