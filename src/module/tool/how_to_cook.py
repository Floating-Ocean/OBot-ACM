from src.core.bot.decorator import command, module
from src.core.bot.interact import reply_fuzzy_matching
from src.core.bot.message import RobotMessage
from src.core.util.tools import png2jpg
from src.data.data_cache import get_cached_prefix
from src.data.data_how_to_cook import load_dishes
from src.render.html.render_how_to_cook import render_how_to_cook

_version = "1.5.0"


@command(tokens=['来道菜', '做菜', '菜', '饿了', '我饿了'])
def reply_how_to_cook(message: RobotMessage):
    message.reply("正在翻菜谱，请稍等")
    dishes = load_dishes()

    if len(dishes) == 0:
        message.reply("抱歉，菜谱库为空，请踢一踢管理员")
        return

    def reply_ok(query_tag: str, query_more_tip: str, picked: str):
        cached_prefix = get_cached_prefix('How-To-Cook')
        render_how_to_cook(_version, dishes[picked], f"{cached_prefix}.png")
        message.reply(f"帮你找到了{query_tag}一个菜谱【{picked}】{query_more_tip}",
                      png2jpg(f"{cached_prefix}.png"))

    reply_fuzzy_matching(message, list(dishes.keys()), "菜谱", 1, reply_ok)


@module(
    name="How-to-Cook",
    version=_version
)
def register_module():
    pass
