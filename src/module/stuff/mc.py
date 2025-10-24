import random
import re

from src.core.bot.decorator import module, command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.data.data_mc import get_mc_resource


def _decode_template(template: str) -> str:
    pattern = r'{{(.*?)}}'
    variables = {
        "player": "你",
        "players_sleeping_percentage": f"1/{random.randint(2, 100)}"
    }
    parts = re.split(pattern, template)
    segments = []

    for i, part in enumerate(parts):
        if i % 2 == 0:  # 偶数索引是普通文本
            if part:
                segments.append(part)
        else:  # 奇数索引是变量
            var_name = part.strip()
            if var_name not in variables:
                variables[var_name] = random.choice(get_mc_resource(var_name))
            segments.append(variables[var_name])

    return "".join(segments)


@command(tokens=["kill"])
def reply_mc_kill(message: RobotMessage):
    death = get_mc_resource("death")
    message.reply(_decode_template(random.choice(death)), modal_words=False)


@module(
    name="Minecraft",
    version="v1.0.0"
)
def register_module():
    pass
