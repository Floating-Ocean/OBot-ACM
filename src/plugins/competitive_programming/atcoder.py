from io import BytesIO

from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.params import Command, CommandArg
from nonebot.log import logger
from nonebot.exception import MatcherException

from src.core.constants import Constants
from src.core.tools import get_simple_qrcode, reply_help
from src.core.help_registry import with_help
from src.core.bot.message import reply, report_exception
from src.platform.cp.atcoder import AtCoder


__atc_version__ = "v1.2.0"

supported_commands = ['pick']#'info','user', 'contests', 'pick']

def register_module():
    pass

async def send_user_info(handle: str, event: MessageEvent):
    await reply([f"[Atcoder] 正在查询 {handle} 的 AtCoder 平台信息，请稍等..."], event, finish=False)

    info, avatar = AtCoder.get_user_info(handle)

    if avatar is None:
        content = (f"[AtCoder] {handle}\n\n"
                   f"{info}")
        await reply([content], event, finish=True)
    else:
        last_contest = AtCoder.get_user_last_contest(handle)
        content = (f"[AtCoder] {handle}\n\n"
                   f"{info}\n\n"
                   f"{last_contest}")
        await reply([content, avatar], event, finish=True)


async def send_prob_filter_tag(contest_type: str, limit: str = None, event: MessageEvent = None) -> bool:
    if event:
        await reply(["正在随机选题，请稍等"], event, finish=False)
    logger.debug(f"type:{contest_type},limit:{limit}")
    chosen_prob = AtCoder.get_prob_filtered(contest_type, limit)
    if isinstance(chosen_prob,int):
        if event:
            await reply([f"clist返回：{chosen_prob}"], event, finish=False)
    if isinstance(chosen_prob, int) and chosen_prob < 0:
        return False

    if isinstance(chosen_prob, int):
        if event:
            await reply(["条件不合理或过于苛刻，无法找到满足条件的题目"], event, finish=True)
        return True

    abbr = chosen_prob['url'].split('/')[-1].capitalize()
    link = chosen_prob['url'].replace('https://atcoder.jp', '')
    content = (f"[AtCoder] 随机选题\n\n"
               f"{abbr} {chosen_prob['name']}\n\n"
               f"链接: [atcoder] {link}")

    if 'rating' in chosen_prob:
        content += f"\n难度: *{chosen_prob['rating']}"

    qr_img = get_simple_qrcode(chosen_prob['url'])
    img_byte = BytesIO()
    qr_img.save(img_byte,format='PNG')
    if event:
        await reply([content, img_byte.getvalue()], event, finish=True)

    return True


async def send_contest(event: MessageEvent):
    await reply([f"正在查询近期 AtCoder 比赛，请稍等"], event, finish=False)

    info = AtCoder.get_recent_contests()

    content = (f"[AtCoder] 近期比赛\n\n"
               f"{info}")

    await reply([content], event, finish=True)

regular_handler = on_command(('atc','help'),rule=to_me(),
                             aliases = {('atc', command) for command in supported_commands},
                             priority=Constants.PLATFORM_PRIOR,block=True)

fullname_handler = on_command(('atcoder','help'),rule=to_me(),
                              aliases = {('atcoder', command) for command in supported_commands},
                              priority=Constants.PLATFORM_PRIOR,block=True)

help_trigger = on_command('atc',rule=to_me(),aliases={'atcoder'},priority=Constants.HELP_PRIOR,block=True)

@help_trigger.handle()
async def handle_help():
    await reply_help("Atcoder")

@regular_handler.handle()
@fullname_handler.handle()
@with_help("Atcoder")
async def handle_regular(event:MessageEvent,command:tuple[str,str]=Command(),message:Message = CommandArg()):
    """
    AtCoder 平台相关功能
    
    可用指令:
    /atc.info [handle] 或 /atc.user [handle]: 查询用户信息
    /atc.pick [contest_type] [难度范围]: 随机选题（contest_type如common、abc、sp等，难度范围可选）
    /atc.contests 或 /atc.contest: 查询近期比赛
    
    别名: /atcoder.[command]
    """
    try:
        func = command[1]
        args = message.extract_plain_text().split()
        if func == "info" or func == "user":
            if len(args) != 1:
                await reply(["请输入正确的指令格式，如\"/atc.info jiangly\""], event, finish=True)
                return
            handle = args[0]
            await send_user_info(handle, event)

        elif func == "pick":
            if not len(args) or not await send_prob_filter_tag(
                    contest_type=args[0],
                    limit=args[1] if len(args) >= 2 else None,
                    event=event):
                func_prefix = f"/atc.pick"
                await reply(["请输入正确的指令格式，题目标签不要带有空格，如:\n\n"
                                    f"{func_prefix} common\n"
                                    f"{func_prefix} abc\n"
                                    f"{func_prefix} sp 1200-1600\n"
                                    f"{func_prefix} all 1800"], event, finish=True)

        elif func == "contest" or func == "contests":
            await send_contest(event)

        else:
            await reply_help("Atcoder","",False)
    except MatcherException:
        raise
    except Exception as e:
        await report_exception(event, "Atcoder", e)
