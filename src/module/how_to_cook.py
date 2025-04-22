import os

from src.core.bot.command import command
from src.core.bot.interact import reply_fuzzy_matching
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.output_cached import get_cached_prefix
from src.core.util.tools import png2jpg
from src.render.html.render_how_to_cook import render_how_to_cook

_lib_path = os.path.join(Constants.config["lib_path"], "How-To-Cook")
__how_to_cook_version__ = "v1.4.0"

_dishes_path = os.path.join(_lib_path, "lib", "dishes")

_dishes: dict[str, str] = {}


def register_module():
    pass


def _load_dishes():
    _dishes.clear()
    for root, _, files in os.walk(_dishes_path):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)
                dish_name = os.path.splitext(file)[0]
                _dishes[dish_name] = full_path


@command(tokens=['来道菜', '做菜', '菜', '饿了', '我饿了'])
def reply_how_to_cook(message: RobotMessage):
    message.reply("正在翻菜谱，请稍等")

    _load_dishes()

    if not _dishes:
        message.reply("抱歉，菜谱库为空，请踢一踢管理员")
        return

    def reply_ok(query_tag: str, query_more_tip: str, picked: str):
        cached_prefix = get_cached_prefix('How-To-Cook')
        render_how_to_cook(__how_to_cook_version__, _dishes[picked], f"{cached_prefix}.png")
        message.reply(f"帮你找到了{query_tag}一个菜谱【{picked}】{query_more_tip}", png2jpg(f"{cached_prefix}.png"))

    reply_fuzzy_matching(message, list(_dishes.keys()), "菜谱", 1, reply_ok)
