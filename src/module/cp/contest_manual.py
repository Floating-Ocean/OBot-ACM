from dataclasses import asdict
from datetime import datetime

from nonebot import on_command
from nonebot.adapters import Message,Event
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me

from src.core.bot.decorator import module
from src.core.bot.message import reply
from src.core.util.tools import is_valid_date, check_is_int
from src.data.data_contest_manual import ManualContest, save_contest
from src.platform.model import DynamicContest

add_manual_contest = on_command("导入比赛", aliases={"import_contest"}, priority=0,rule=to_me(),block=True,permission=SUPERUSER)
@add_manual_contest.handle()
async def reply_manual_add_contest(event:Event,message:Message = CommandArg()):
    help_content = ("/导入比赛 [platform] [abbr] [name] [start_time] [duration] [supplement]\n\n"
                    "示例：/导入比赛 ICPC 武汉邀请赛 2025年ICPC国际大学生程序设计竞赛全国邀请赛（武汉） 250427100000 18000 华中科技大学\n\n"
                    "注意，start_time包含年月日时分秒，且均为两位，duration单位为秒")
    content = message.extract_plain_text().strip().split(" ")
    if len(content) != 6:
        await reply(["参数数量有误\n\n",f"{help_content}"],event,False,True)

    platform, abbr, name, start_time_raw, duration_raw, supplement = content

    date_format = "%y%m%d%H%M%S"
    if not is_valid_date(start_time_raw, date_format):
        await reply(["start_time 格式有误\n\n",f"{help_content}"],event,False,True)
    start_time = int(datetime.strptime(start_time_raw, date_format).timestamp())

    if not check_is_int(duration_raw) or int(duration_raw) <= 0:
        await reply(["duration 应该为正整数\n\n", f"{help_content}"], event, False, True)

    duration = int(duration_raw)
    contest = ManualContest(platform, abbr, name, start_time, duration, supplement)
    save_status = save_contest(contest)

    if save_status:
        await reply(["导入比赛成功，比赛解析为\n\n", f"{DynamicContest(**asdict(contest)).format()}"], event, False, True)
    else:
        await reply(["该比赛已存在，导入失败"], event, False, True)


@module(
    name="Contest-List-Renderer",
    version="v1.1.0"
)
def register_module():
    pass
