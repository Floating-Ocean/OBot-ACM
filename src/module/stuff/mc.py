import random
import re
import time

from src.core.bot.decorator import module, command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.data.data_mc import get_mc_resource

_gamemode_end_tick = {}


def _decode_template(template: str) -> list[tuple[str, str]]:
    pattern = r'{{(.*?)}}'
    parts = re.split(pattern, template)
    segments = []

    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if i % 2 == 0:  # 偶数索引是普通文本
            segments.append(("txt", part))
        else:  # 奇数索引是变量
            segments.append(("var", part))

    return segments


def _fill_template(tokens: list[tuple[str, str]]) -> str:
    variables = {
        "player": ["你"],
        "players_sleeping_percentage": [f"1/{random.randint(2, 100)}"]
    }
    segments = []

    for tp, part in tokens:
        if tp == "txt":
            segments.append(part)
        else:
            if part not in variables:
                variables[part] = get_mc_resource(part)
            segments.append(random.choice(variables[part]))

    return "".join(segments)


def _swap_variable(tokens: list[tuple[str, str]], a: str, b: str) -> list[tuple[str, str]]:
    new_tokens = []
    for tp, part in tokens:
        if tp == "var" and part == a:
            new_tokens.append(("var", b))
        elif tp == "var" and part == b:
            new_tokens.append(("var", a))
        else:
            new_tokens.append((tp, part))
    return new_tokens


@command(tokens=["kill"])
def reply_mc_kill(message: RobotMessage):
    death = get_mc_resource("death")
    chosen = random.choice(death)
    tokens = _decode_template(chosen)

    gamemode = "生存"
    if message.author_id in _gamemode_end_tick:
        mode, end_tick = _gamemode_end_tick[message.author_id]
        if end_tick >= time.time():
            gamemode = mode
            if mode == "创造":
                death = [
                    item for item in death
                    if "{{ mob }}" in item
                ]
                chosen = random.choice(death)
                tokens = _decode_template(chosen)
                tokens = _swap_variable(tokens, "player", "mob")
            elif mode == "旁观者":
                message.reply("你无法在旁观者模式执行该指令")
                return

    Constants.log.info(f"[mc] /kill <{gamemode}> {chosen}")
    message.reply(_fill_template(tokens), modal_words=False)


@command(tokens=["gamemode"])
def reply_mc_gamemode(message: RobotMessage):
    content = message.tokens
    if len(content) < 2:
        message.reply("请指定 MC 游戏模式")
        return

    if content[1] in ['survival', 's', '0', 'default', 'd', '5']:
        gamemode = "生存"
    elif content[1] in ['creative', 'c', '1']:
        gamemode = "创造"
    elif content[1] in ['adventure', 'a', '2']:
        gamemode = "冒险"
    elif content[1] in ['spectator', '6']:
        gamemode = "旁观者"
    else:
        message.reply("非有效 MC 游戏模式")
        return

    if message.author_id in _gamemode_end_tick:
        old_mode, end_tick = _gamemode_end_tick[message.author_id]
        if ((end_tick >= time.time() and old_mode == gamemode) or
                (end_tick < time.time() and gamemode == "生存")):
            message.reply(f"当前已在 {gamemode}模式")
            return

    duration = random.randint(30, 90)
    end_tick = time.time() + duration
    _gamemode_end_tick[message.author_id] = (gamemode, end_tick)
    message.reply(f"已切换到 {gamemode}模式，持续 {duration} 秒")


@module(
    name="Minecraft",
    version="v1.0.1"
)
def register_module():
    pass
