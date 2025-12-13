from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11.event import MessageEvent

from src.core.constants import Constants
from src.core.bot.message import reply
from src.core.help_registry import with_help

ping = on_command("活着吗",rule=to_me(),aliases={'死了吗','似了吗','ping'},priority=0,block=True)

@ping.handle()
@with_help("简单响应")
async def handle_ping(event: MessageEvent):
    """
    检查机器人是否在线
    指令: /活着吗, /死了吗, /似了吗, /ping
    """
    await reply(["你猜呢"], event, finish=True)

swear = on_command("傻逼",rule=to_me(),aliases={'智障','制杖','SB','sb','脑瘫','nt'},priority=100,block=True)

@swear.handle()
@with_help("简单响应")
async def handle_swear(event: MessageEvent):
    """
    对不当言论的回应
    指令: /傻逼, /智障, /制杖, /SB, /sb, /脑瘫, /nt
    """
    await reply(["你干嘛害哎呦"], event, finish=True)

help = on_command("help",rule=to_me(),aliases={'帮助'},priority=0,block=True)
@help.handle()
@with_help("简单响应")
async def handle_help(event: MessageEvent):
    """
    显示所有可用指令的帮助信息
    指令: /help, /帮助
    """
    await reply([Constants.merged_help_content], event, finish=True)

