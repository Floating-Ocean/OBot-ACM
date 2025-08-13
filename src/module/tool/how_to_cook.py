import random

from nonebot import on_command
from nonebot.adapters import Message,Event
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg
from nonebot.rule import to_me
from nonebot_plugin_saa import MessageFactory

from src.core.constants import Constants
from src.core.bot.message import reply
from src.core.util.tools import png2jpg,fuzzy_matching
from src.data.data_cache import get_cached_prefix
from src.data.data_how_to_cook import load_dishes
from src.render.html.render_how_to_cook import render_how_to_cook

_version = "1.5.0"

how_to_cook = on_command("来道菜", aliases={"做菜", "菜", "饿了", "我饿了"}, priority=100,rule=to_me(), block=True)
@how_to_cook.handle()
async def reply_how_to_cook(event:Event,message:Message = CommandArg()):
    await reply(["正在翻阅菜谱，请稍等"],event,finish = False)
    dishes = load_dishes()
    if len(dishes) == 0:
        await reply(["抱歉，菜谱库为空，请踢一踢管理员"], event, finish=True)
    try:
        args = message.extract_plain_text().split()
        if len(args) == 0:
            picked = random.choice(list(dishes.keys()))
            query_tag = "随机"
            query_more_tip = "，你可以输入菜名来获取特定菜谱"
        else:
            dish = args[0]
            index = 1
            if len(args) == 2:
                index = int(args[1])
            query_tag, query_more_tip, picked = fuzzy_matching(list(dishes.keys()),dish,index)
        cached_prefix = get_cached_prefix('How-To-Cook')
        render_how_to_cook(_version, dishes[picked], f"{cached_prefix}.png")
        await reply([f"帮你找到了{query_tag}一个菜谱【{picked}】{query_more_tip}",png2jpg(f"{cached_prefix}.png",False)], event, finish=True)
    except ValueError as e:
        await MessageFactory(f"抱歉，{e}").finish()
    except ActionFailed as e:
        Constants.log.error(f"[obot-how-to-cook]  failed: {e}")
        await reply([f"发送消息时发生错误，请联系管理员排障"], event, finish=True)
