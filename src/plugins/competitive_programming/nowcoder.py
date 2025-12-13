from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.params import Command, CommandArg
from nonebot.log import logger
from nonebot.exception import MatcherException

from src.core.constants import Constants
from src.core.tools import check_is_int, reply_help
from src.core.help_registry import with_help
from src.core.bot.message import reply, report_exception
from src.platform.cp.nowcoder import NowCoder

__nk_version__ = "v1.1.0"


supported_commands = ['info','user','contests']

def register_module():
    pass

regular_handler = on_command(('nk','help'),rule=to_me(),
                             aliases = {('nk', command) for command in supported_commands},
                             priority=Constants.PLATFORM_PRIOR,block=True)

alias_handler = on_command(('nc','help'),rule=to_me(),
                             aliases = {('nc', command) for command in supported_commands},
                             priority=Constants.PLATFORM_PRIOR,block=True)

fullname_handler = on_command(('nowcoder','help'),rule=to_me(),
                              aliases = {('nowcoder', command) for command in supported_commands},
                              priority=Constants.PLATFORM_PRIOR,block=True)

help_trigger = on_command('nowcoder',rule=to_me(),aliases={'nk','nc'},priority=Constants.HELP_PRIOR,block=True)

@help_trigger.handle()
async def handle_help():
    await reply_help("Nowcoder")

async def send_user_info(handle: str, event: MessageEvent):
    await reply([f"正在查询 {handle} 的 NowCoder 平台信息，请稍等"], event, finish=False)

    info, avatar = NowCoder.get_user_info(handle)

    if avatar is None:
        content = (f"[NowCoder] {handle}\n\n"
                   f"{info}")
        await reply([content], event, finish=True)
    else:
        last_contest = NowCoder.get_user_last_contest(handle)
        content = (f"[NowCoder] {handle}\n\n"
                   f"{info}\n\n"
                   f"{last_contest}")
        await reply([content, avatar], event, finish=True)


async def send_contest(event: MessageEvent):
    await reply([f"正在查询近期 NowCoder 比赛，请稍等"], event, finish=False)

    info = NowCoder.get_recent_contests()

    content = (f"[NowCoder] 近期比赛\n\n"
               f"{info}")

    await reply([content], event, finish=True)


@regular_handler.handle()
@alias_handler.handle()
@fullname_handler.handle()
@with_help("Nowcoder")
async def handle_regular(event:MessageEvent,command:tuple[str,str]=Command(),message:Message = CommandArg()):
    """
    NowCoder 平台相关功能
    
    可用指令:
    /nk.info [uid] 或 /nk.user [uid]: 查询用户信息（需使用uid，不支持昵称）
    /nk.contests 或 /nk.contest: 查询近期比赛
    
    别名: /nc.[command], /nowcoder.[command]
    """
    try:
        func = command[1]
        args = message.extract_plain_text().split()
        if func == "info" or func == "user":
            if len(args) != 1:
                await reply(["请输入正确的指令格式，如\"/nk info 815516497\""], event, finish=True)
            uid = args[0]
            if not check_is_int(uid):
                await reply(["暂不支持使用昵称检索用户，请使用uid"], event, finish=True)

            await send_user_info(uid, event)

        elif func == "contest" or func == "contests":
            await send_contest(event)
        else:
            await reply_help("Nowcoder","",False)
    except MatcherException:
        raise
    except Exception as e:
        await report_exception(event, "Nowcoder", e)
