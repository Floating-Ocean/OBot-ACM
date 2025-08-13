import asyncio
import random

from nonebot import on_command
from nonebot.adapters import Event, Message
from nonebot.params import CommandArg
from nonebot.rule import to_me
from thefuzz import process

from src.core.bot.decorator import get_all_modules_info, module
from src.core.bot.message import reply
from src.core.constants import Constants
from src.core.util.tools import png2jpg, get_simple_qrcode, check_intersect, get_today_timestamp_range
from src.data.data_cache import get_cached_prefix
from src.platform.manual.manual import ManualPlatform
from src.platform.online.atcoder import AtCoder
from src.platform.online.codeforces import Codeforces
from src.platform.online.nowcoder import NowCoder
from src.render.pixie.render_about import AboutRenderer
from src.render.pixie.render_contest_list import ContestListRenderer
from src.render.pixie.render_help import HelpRenderer

_version = "1.0.0"

today_contests_1 = on_command(("contest", "today"),
                              aliases={("contests", "today"), ("比赛", "today"), ("比赛", "今日"), ("比赛", "今天")},
                              priority=50, block=True, rule=to_me())
today_contests_2 = on_command("今日比赛", aliases={"今日的比赛", "今天比赛", "今天的比赛"}, priority=50, block=True,
                              rule=to_me())
recent_contests_1 = on_command(("contest", "recent"),
                               aliases={("contests", "recent"), ("比赛", "近期"), ("比赛", "最近")}, priority=50,
                               block=True, rule=to_me())
recent_contests_2 = on_command("近期比赛", aliases={"最近比赛", "最近的比赛"}, priority=50, block=True, rule=to_me())


@today_contests_1.handle()
@today_contests_2.handle()
async def reply_today_contests(event: Event, message: Message = CommandArg()):
    platform = message.extract_plain_text().strip().lower()
    await reply_contests(event, platform, True)


@recent_contests_1.handle()
@recent_contests_2.handle()
async def reply_recent_contests(event: Event, message: Message = CommandArg()):
    platform = message.extract_plain_text().strip().lower()
    await reply_contests(event, platform, False)


async def reply_contests(event: Event, platform: str, is_today: bool):
    queries = []
    if platform == "":
        queries = [AtCoder, Codeforces, NowCoder, ManualPlatform]
    else:
        closest_type = process.extract(platform, [
            "cf", "codeforces", "atc", "atcoder", "牛客", "nk", "nc", "nowcoder",
            "ccpc", "icpc", "other", "其他", "misc", "杂项", "manual", "手动"], limit=1)[0]
        if closest_type[1] >= 60:
            if closest_type[0] in ["cf", "codeforces"]:
                queries = [Codeforces]
            elif closest_type[0] in ["atc", "atcoder"]:
                queries = [AtCoder]
            elif closest_type[0] in ["ccpc", "icpc", "other", "其他", "misc", "杂项", "manual", "手动"]:
                queries = [ManualPlatform]
            else:
                queries = [NowCoder]
    tip_time_range = '今日' if is_today else '近期'
    if len(queries) == 1:
        await reply([f"正在查询{tip_time_range}{queries[0].platform_name}比赛，请稍等"], event, modal_words=False,
                    finish=False)
    else:
        await reply([f"正在查询{tip_time_range}比赛，请稍等"], event, modal_words=False,
                    finish=False)
    running_contests, upcoming_contests, finished_contests = [], [], []
    for platform in queries:
        running, upcoming, finished = platform.get_contest_list()
        running_contests.extend(running)
        upcoming_contests.extend(upcoming)
        finished_contests.extend(finished)

    running_contests.sort(key=lambda c: c.start_time)
    upcoming_contests.sort(key=lambda c: c.start_time)
    finished_contests.sort(key=lambda c: c.start_time)

    if is_today:
        running_contests = [contest for contest in running_contests if check_intersect(
            range1=get_today_timestamp_range(),
            range2=(contest.start_time, contest.start_time + contest.duration)
        )]
        upcoming_contests = [contest for contest in upcoming_contests if check_intersect(
            range1=get_today_timestamp_range(),
            range2=(contest.start_time, contest.start_time + contest.duration)
        )]
        finished_contests = [contest for contest in finished_contests if check_intersect(
            range1=get_today_timestamp_range(),
            range2=(contest.start_time, contest.start_time + contest.duration)
        )]

    cached_prefix = get_cached_prefix('Contest-List-Renderer')
    contest_list_img = ContestListRenderer(running_contests, upcoming_contests, finished_contests).render()
    contest_list_img.write_file(f"{cached_prefix}.png")
    await reply([f"以下是当前查询到的{tip_time_range}比赛列表", png2jpg(f"{cached_prefix}.png")], event,
                modal_words=False, finish=True)


generate_qr = on_command("qrcode", aliases={"qr", "二维码", "码"}, rule=to_me(), priority=100, block=True)


@generate_qr.handle()
async def reply_qrcode(event: Event, message: Message = CommandArg()):
    content = message.extract_plain_text().strip()
    if len(content) == 0:
        await reply(["请提供需要生成二维码的内容"], event)

    cached_prefix = get_cached_prefix('QRCode-Generator')
    qr_img = get_simple_qrcode(content)
    qr_img.save(f"{cached_prefix}.png")
    await reply(["生成了一个二维码", png2jpg(f"{cached_prefix}.png")], event)


sleep = on_command("sleep", aliases={"晚安", "睡觉", "睡觉去了"}, rule=to_me(), priority=200, block=True)


@sleep.handle()
async def reply_mc_sleep(event: Event):
    """
    Minecraft主题的睡觉命令处理器
    随机回复睡觉相关的游戏消息，并可能延时发送"早上好"
    """
    actions = [
        "你的床爆炸了",
        "你被床弹飞了",
        "你的床已被破坏",
        "你现在不能休息，周围有怪物在游荡",
        "你现在不能休息，周围有玩家在游荡",
        "你只能在夜间或雷暴中入睡",
        "你只能在白天或晴天中入睡",
        f"正在等待 1/{random.randint(2, 100)} 名玩家入睡",
        "晚安"
    ]
    chosen_action = random.choice(actions)
    await reply([chosen_action], event, modal_words=False, finish=chosen_action != "晚安")
    await asyncio.sleep(random.randint(30, 120))
    await reply(["早上好！"], event, modal_words=False, finish=True)


help_command = on_command("help", aliases={"helps", "instruction", "instructions", "帮助"}, rule=to_me(), priority=100,
                          block=True)


@help_command.handle()
async def reply_help(event: Event):
    await reply(["正在生成帮助手册，请稍等"], event=event, finish=False)
    cached_prefix = get_cached_prefix('Help-Renderer')
    contest_list_img = HelpRenderer().render()
    contest_list_img.write_file(f"{cached_prefix}.png")
    await reply(["帮助手册", png2jpg(f"{cached_prefix}.png")], event=event)


about_command = on_command("about", aliases={"版本", "关于"}, rule=to_me(), priority=100, block=True)


@about_command.handle()
async def reply_about(event: Event):
    await reply(["正在生成各模块版本信息，请稍等"], event=event, finish=False)
    cached_prefix = get_cached_prefix('About-Renderer')
    about_img = AboutRenderer(
        ("OBot Core", f"{Constants.core_version}-{Constants.git_commit_hash}"),
        get_all_modules_info()
    ).render()
    about_img.write_file(f"{cached_prefix}.png")
    await reply(["当前各模块版本", png2jpg(f"{cached_prefix}.png")], event=event)

@module(
    name="General-Interaction",
    version=_version
)
def register_module():
    pass