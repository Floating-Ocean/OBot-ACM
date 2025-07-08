import json
import os
from datetime import datetime

from src.core.bot.command import command
from src.core.bot.message import RobotMessage
from src.core.bot.module import module
from src.core.bot.perm import PermissionLevel
from src.core.constants import Constants
from src.core.util.tools import is_valid_date, check_is_int
from src.platform.model import DynamicContest

_lib_path = Constants.modules_conf.get_lib_path("Contest-List-Renderer")


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

    contest = {
        "platform": platform,
        "abbr": abbr,
        "name": name,
        "start_time": start_time,
        "duration": duration,
        "supplement": supplement,
    }

    manual_contests_path = os.path.join(_lib_path, 'manual_contests.json')
    try:
        # 检查文件是否存在，不存在则创建
        if not os.path.exists(manual_contests_path):
            with open(manual_contests_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
        with open(manual_contests_path, 'r+', encoding='utf-8') as f:
            manual_contests = json.load(f)

        # 检查比赛是否已存在
        for existing_contest in manual_contests:
            if (existing_contest.get('platform') == platform and
                    existing_contest.get('name') == name and
                    existing_contest.get('start_time') == start_time):
                message.reply("该比赛已存在，导入失败")
                return

        manual_contests.append(contest)

        with open(manual_contests_path, 'w', encoding='utf-8') as f:
            json.dump(manual_contests, f, ensure_ascii=False, indent=4)

        message.reply("导入比赛成功，比赛解析为\n\n" +
                      DynamicContest(**contest).format(), modal_words=False)

    except Exception as e:
        message.reply("出现错误，导入比赛失败")
        Constants.log.warn("[manual] 导入自定义比赛失败.")
        Constants.log.error(f"[manual] {e}")


@module(
    name="Contest-List-Renderer",
    version="v1.0.1"
)
def register_module():
    pass
