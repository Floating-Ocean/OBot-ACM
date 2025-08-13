from nonebot import on_command
from nonebot.adapters import Event
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me

from src.core.bot.decorator import module
from src.core.bot.message import reply
from src.core.constants import Constants

_version = "1.0.0"

reload_conf = on_command("reload_conf", aliases={"配置重载"}, permission=SUPERUSER, rule=to_me(), priority=0,
                         block=True)


@reload_conf.handle()
async def reply_reload_conf(event: Event):
    Constants.reload_conf()
    Constants.log.info("[obot-core] 已重载配置文件")
    await reply(["配置文件已重载"], event, modal_words=False, finish=True)


chat_scene_id = on_command("chat_scene_id", aliases={"对话场景ID"}, rule=to_me(), priority=5, block=True)


@chat_scene_id.handle()
async def reply_chat_scene_id(event: Event):
    await reply([f"当前对话场景ID\n\n{event.get_session_id()}"], event, modal_words=False, finish=True)


my_id = on_command("my_id", aliases={"我的ID"}, rule=to_me(), priority=5, block=True)


@my_id.handle()
async def reply_my_id(event: Event):
    await reply([f'你的ID（不同对话场景下你的ID是不同的）\n\n{event.get_user_id()}'], event, modal_words=False,
                finish=True)

@module(
    name="Bot-Environment",
    version=_version
)
def register_module():
    pass