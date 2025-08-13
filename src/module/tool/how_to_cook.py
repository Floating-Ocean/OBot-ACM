import os
import random

from nonebot import on_command
from nonebot.adapters import Message
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg
from nonebot.rule import to_me
from nonebot_plugin_saa import MessageFactory, AggregatedMessageFactory
from nonebot_plugin_saa import Image as SAAImage

from src.core.constants import Constants
from src.core.util.tools import png2jpg,fuzzy_matching
from src.data.data_cache import get_cached_prefix
from src.data.data_how_to_cook import load_dishes
from src.render.html.render_how_to_cook import render_how_to_cook

_version = "1.5.0"

how_to_cook = on_command("来道菜", aliases={"做菜", "菜", "饿了", "我饿了"}, priority=100,rule=to_me(), block=True)
@how_to_cook.handle()
async def reply_how_to_cook(message:Message = CommandArg()):
    await MessageFactory("正在翻阅菜谱，请稍等").send()
    dishes = load_dishes()
    if len(dishes) == 0:
        await MessageFactory("抱歉，菜谱库为空，请踢一踢管理员").finish()
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
        path = os.path.abspath(png2jpg(f"{cached_prefix}.png"))
        image_bytes = open(path, "rb").read()
        await AggregatedMessageFactory([MessageFactory(f"帮你找到了{query_tag}一个菜谱【{picked}】{query_more_tip}"),
                                        MessageFactory(SAAImage(image_bytes))]).finish()
    except ValueError as e:
        await MessageFactory(f"抱歉，{e}").finish()
    except ActionFailed as e:
        Constants.log.error(f"[obot-how-to-cook]  failed: {e}")
        await MessageFactory(f"发送消息时发生错误，请联系管理员排障").finish()
