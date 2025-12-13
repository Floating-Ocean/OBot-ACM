from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters import Message
from nonebot.params import CommandArg,Command
from nonebot.log import logger
from nonebot.exception import MatcherException

from nonebot_plugin_saa import Image
from io import BytesIO

from nonebot.adapters.onebot.v11.event import MessageEvent
from src.core.constants import Constants
from src.core.tools import check_is_int, get_simple_qrcode, png2jpg,reply_help
from src.core.help_registry import with_help
from src.platform.cp.codeforces import Codeforces
from src.core.bot.message import reply, report_exception


__cf_version__ = "v3.0.0"

supported_commands = ['info', 'user', 'recent', 'contests', 'status', 'standing', 'pick', 'tags', 'tag']

def register_module():
    pass


async def send_user_info(handle: str, event: MessageEvent):
    await reply([f"[Codeforces] 正在查询 {handle} 的 Codeforces 平台信息，请稍等..."], event, finish=False)

    info, avatar = Codeforces.get_user_info(handle)

    if avatar is None:
        content = (f"[Codeforces] {handle}\n\n"
                   f"{info}")
        await reply([content], event, finish=True)
    else:
        last_contest = Codeforces.get_user_last_contest(handle)
        last_submit = Codeforces.get_user_last_submit(handle)
        total_sums, weekly_sums, daily_sums = Codeforces.get_user_submit_counts(handle)
        daily = "今日暂无过题" if daily_sums == 0 else f"今日通过 {daily_sums} 题"
        weekly = "" if weekly_sums == 0 else f"，本周共通过 {weekly_sums} 题"
        content = (f"[Codeforces] {handle}\n\n"
                   f"{info}\n"
                   f"通过题数: {total_sums}\n\n"
                   f"{last_contest}\n\n"
                   f"{daily}{weekly}\n"
                   f"{last_submit}")
        await reply([content, avatar], event, finish=True)


async def send_user_last_submit(handle: str, count: int, event: MessageEvent):
    await reply([f"[Codeforces] 正在查询 {handle} 的 Codeforces 提交记录，请稍等..."], event, finish=False)

    info, _ = Codeforces.get_user_info(handle)

    if info is None:
        content = (f"[Codeforces] {handle}\n\n"
                   f"用户不存在")
    else:
        last_submit = Codeforces.get_user_last_submit(handle, count)
        content = (f"[Codeforces] {handle}\n\n"
                   f"{last_submit}")

    await reply([content], event, finish=True)




async def send_contest(event: MessageEvent):
    await reply([f"[Codeforces] 正在查询近期 Codeforces 比赛，请稍等..."], event, finish=False)

    info = Codeforces.get_recent_contests()

    content = (f"[Codeforces] 近期比赛\n\n"
               f"{info}")

    await reply([content], event, finish=True)


async def send_user_contest_standings(handle: str, contest_id: str, event: MessageEvent):
    await reply([f"[Codeforces Standings] 正在查询编号为 {contest_id} 的比赛中 {handle} 的榜单信息，请稍等...\n"
                        f"查询对象为参赛者时将会给出 Rating 变化预估，但可能需要更久的时间"], event, finish=False)

    contest_info, standings_info = Codeforces.get_user_contest_standings(handle, contest_id)

    content = (f"[Codeforces] {handle} 比赛榜单查询\n\n"
               f"{contest_info}")
    if standings_info is not None:
        if len(standings_info) > 0:
            content += '\n\n'
            content += '\n\n'.join(standings_info)
        else:
            content += '\n\n暂无榜单信息'

    await reply([content], event, finish=True)

async def send_prob_filter_tag(tag: str, limit: str = None, newer: bool = False, event: MessageEvent = None) -> bool:
    if event:
        await reply(["[Codeforces Pick] 正在随机选题，请稍等..."], event, finish=False)

    async def on_tag_chosen_callback(x: str):
        if event:
            await reply([x], event, finish=False)

    chosen_prob = await Codeforces.get_prob_filtered(tag, limit, newer, on_tag_chosen=on_tag_chosen_callback)

    if isinstance(chosen_prob, int) and chosen_prob < 0:
        return False

    if isinstance(chosen_prob, int):
        if event:
            await reply(["[Codeforces Pick] 条件不合理或过于苛刻，无法找到满足条件的题目..."], event, finish=True)
        return False
    tags = ', '.join(chosen_prob['tags'])
    content = (f"[Codeforces] 随机选题\n\n"
               f"P{chosen_prob['contestId']}{chosen_prob['index']} {chosen_prob['name']}\n\n"
               f"链接: [codeforces] /contest/{chosen_prob['contestId']}/problem/{chosen_prob['index']}\n"
               f"标签: {tags}")

    if 'rating' in chosen_prob:
        content += f"\n难度: *{chosen_prob['rating']}"

    qr_img = get_simple_qrcode(
        f"https://codeforces.com/contest/{chosen_prob['contestId']}/problem/{chosen_prob['index']}")
    img_byte = BytesIO()
    qr_img.save(img_byte,format='PNG')
    if event:
        await reply([content, img_byte.getvalue()], event, finish=True)

    return True

async def send_prob_tags(event: MessageEvent):
    await reply(["[Codeforces] 正在查询 Codeforces 平台的所有问题标签，请稍等..."], event, finish=False)
    prob_tags = Codeforces.get_prob_tags_all()
    if prob_tags is None:
        content = "查询异常"
    else:
        content = "\n[Codeforces] 问题标签:\n"
        for tag in prob_tags:
            content += "\n" + tag

    await reply([content], event, finish=True)

regular_handler = on_command(('cf','help'),rule=to_me(),
                             aliases = {('cf', command) for command in supported_commands},
                             priority=Constants.PLATFORM_PRIOR,block=True)

fullname_handler = on_command(('codeforces','help'),rule=to_me(),
                              aliases = {('codeforces', command) for command in supported_commands},
                              priority=Constants.PLATFORM_PRIOR,block=True)

help_trigger = on_command('cf',rule=to_me(),aliases={'codeforces'},priority=Constants.HELP_PRIOR,block=True)

@help_trigger.handle()
@with_help("Codeforces")
async def handle_help():
    """
    显示 Codeforces 模块的帮助信息
    指令: /cf, /codeforces
    """
    await reply_help("Codeforces")

@regular_handler.handle()
@fullname_handler.handle()
@with_help("Codeforces")
async def handle_regular(event:MessageEvent,command:tuple[str,str]=Command(),message:Message = CommandArg()):
    """
    Codeforces 平台相关功能
    
    可用指令:
    /cf.info [handle] 或 /cf.user [handle]: 查询用户信息
    /cf.recent [handle] [count]: 查询用户最近提交记录（count可选，默认5，最多100）
    /cf.contests: 查询近期比赛
    /cf.status [handle] [contestId] 或 /cf.standing [handle] [contestId]: 查询用户在比赛中的排名
    /cf.pick [tag|all] [难度范围] [new]: 随机选题（tag为标签或all，难度范围如1700-1900，new表示仅新题）
    /cf.tags 或 /cf.tag: 显示所有可用标签
    
    别名: /codeforces.[command]
    """
    try:
        func = command[1]
        args = message.extract_plain_text().split()
        if func == "info" or func == "user":
            if len(args) != 1:
                await reply([f"请输入正确的指令格式，如\"/cf.{func} jiangly\""], event, finish=True)
            handle = args[0]
            await send_user_info(handle, event)

        elif func == "recent":
            if len(args) not in [1,2]:
                await reply(["请输入正确的指令格式，如\"/cf.recent jiangly 5\""], event, finish=True)
            handle = args[0]
            count = 5
            if len(args) == 2:
                if not(check_is_int(args[1]) and int(args[1]) > 0 and int(args[1]) <= 100):
                    await reply(["请输入正确的查询参数，允许查询最多100条近期数据。"], event, finish=True)
                else:
                    count = int(args[1])
            await send_user_last_submit(handle,count, event)

        elif func == "contests":
            await send_contest(event)

        elif func == "status" or func == "standing":
            if len(args) != 2:
                await reply(["请输入正确的指令格式，如:\n\n"
                                    f"/cf.{func} jiangly 2057"], event, finish=True)
            else:
                handle,contestId = args
                await send_user_contest_standings(handle,contestId, event)
        elif func == "pick":
            # [标签|all] (难度) (new)
            tag = args[0]
            limit = args[1] if len(args) >= 3 and args[1] != "new" else None
            newer = False
            for arg in args:
                newer = newer or arg == 'new'
            if len(args) < 2 or not await send_prob_filter_tag(tag=tag,limit=limit,newer=newer,event=event):
                func_prefix = f"/cf pick"
                await reply(["请输入正确的指令格式，题目标签不要带有空格，如:\n\n"
                                    f"{func_prefix} dp 1700-1900 new\n"
                                    f"{func_prefix} dfs-and-similar\n"
                                    f"{func_prefix} all 1800"], event, finish=True)
        elif func == "tags" or func == 'tag':
            await send_prob_tags(event)
        else:
            await reply_help("Codeforces","",False)
    except MatcherException:
        raise
    except Exception as e:
        await report_exception(event, "Codeforces", e)
