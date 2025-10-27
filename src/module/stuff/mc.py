import enum
import random
import re
import time

from src.core.bot.decorator import module, command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.data.data_mc import get_mc_resource

_status_gamemode: dict[str, tuple["GameMode", float]] = {}
_status_effect: dict[str, dict[str, float]] = {}


class GameMode(enum.Enum):
    SURVIVAL = "生存"
    CREATIVE = "创造"
    ADVENTURE = "冒险"
    SPECTATOR = "旁观者"


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


def _format_duration(tick: float) -> str:
    sec = max(int(tick - time.time()), 0)
    minutes, seconds = divmod(sec, 60)
    return f"{int(minutes):02d}:{int(seconds):02d}"


def _get_gamemode(message: RobotMessage) -> tuple[GameMode, float]:
    gamemode = (GameMode.SURVIVAL, 0)
    if message.author_id in _status_gamemode:
        mode, end_tick = _status_gamemode[message.author_id]
        if end_tick >= time.time():
            gamemode = (mode, end_tick)
    return gamemode


def _get_effects(message: RobotMessage) -> dict[str, float]:
    effects = {}
    if message.author_id in _status_effect:
        for effect in _status_effect[message.author_id].items():
            effect_name, end_tick = effect
            if end_tick >= time.time():
                effects[effect_name] = end_tick
    return effects


@command(tokens=["gamemode"])
def reply_mc_gamemode(message: RobotMessage):
    content = message.tokens
    if len(content) < 2:
        message.reply("[MC-Mode] 请指定 MC 游戏模式")
        return

    if content[1] in ['survival', 's', '0', 'default', 'd', '5']:
        gamemode = GameMode.SURVIVAL
    elif content[1] in ['creative', 'c', '1']:
        gamemode = GameMode.CREATIVE
    elif content[1] in ['adventure', 'a', '2']:
        gamemode = GameMode.ADVENTURE
    elif content[1] in ['spectator', '6']:
        gamemode = GameMode.SPECTATOR
    else:
        message.reply("[MC-Mode] 非有效 MC 游戏模式")
        return

    if message.author_id in _status_gamemode:
        old_mode, end_tick = _status_gamemode[message.author_id]
        if ((end_tick >= time.time() and old_mode == gamemode) or
                (end_tick < time.time() and gamemode == "生存")):
            message.reply(f"[MC-Mode] 当前已在 {gamemode}模式")
            return

    tips = ""
    if gamemode == GameMode.SPECTATOR:
        effects = _get_effects(message)
        if effects:
            _status_effect[message.author_id] = {}
            tips = f"\n\n已清除你身上的 {len(effects)} 个效果"

    duration = random.randint(30, 90)
    end_tick = time.time() + duration
    _status_gamemode[message.author_id] = (gamemode, end_tick)
    message.reply(f"[MC-Mode] 已切换到 {gamemode}模式，持续 {duration} 秒{tips}", modal_words=False)


@command(tokens=["kill"])
def reply_mc_kill(message: RobotMessage):
    death = get_mc_resource("death")
    chosen = random.choice(death)
    tokens = _decode_template(chosen)

    gamemode, _ = _get_gamemode(message)
    if gamemode == GameMode.CREATIVE:
        death = [
            item for item in death
            if "{{ mob }}" in item
        ]
        chosen = random.choice(death)
        tokens = _decode_template(chosen)
        tokens = _swap_variable(tokens, "player", "mob")
    elif gamemode == GameMode.SPECTATOR:
        message.reply("[MC-Kill] 你无法在旁观者模式执行该指令")
        return

    tips = ""
    effects = _get_effects(message)
    if effects:
        _status_effect[message.author_id] = {}
        tips = f"\n\n已清除你身上的 {len(effects)} 个效果"

    Constants.log.info(f"[MC-Kill] <{gamemode}> {chosen}")
    message.reply(f"[MC-Kill] {_fill_template(tokens)}{tips}", modal_words=False)


@command(tokens=["effect"])
def reply_mc_effect(message: RobotMessage):
    content = message.tokens

    gamemode, _ = _get_gamemode(message)
    if gamemode == GameMode.SPECTATOR:
        message.reply("[MC-Effect] 你无法在旁观者模式执行该指令")
        return

    effects = _get_effects(message)
    if len(content) >= 2:
        func = content[1]
        if func == "clear":
            _status_effect[message.author_id] = {}
            message.reply(f"[MC-Effect] 已清除你身上的 {len(effects)} 个效果")
            return
        if func in ["status", "now"]:
            if not effects:
                message.reply("[MC-Effect] 你身上没有状态效果")
                return
            effects_str = "\n".join([
                f"[{_effect[0]}] {_format_duration(_effect[1])}"
                for _effect in effects.items()
            ])
            message.reply(f"[MC-Effect] 你身上共有 {len(effects)} 个效果\n\n"
                          f"{effects_str}", modal_words=False)
            return
        message.reply(f"[MC-Effect] 目前不支持指定状态效果")
        return

    effect = get_mc_resource("effect_detailed")
    chosen = random.choice(effect)

    chosen_name = chosen["name"]
    chosen_effect = chosen["effect"]
    if isinstance(chosen_effect, list):
        chosen_effect = "\n".join(chosen_effect)

    duration = random.randint(5, 99 * 60 - 1)
    if "瞬间" in chosen_name:
        duration = 0
    end_tick = time.time() + duration

    tips = "已添加状态效果"
    if chosen_name in effects:
        end_tick = effects[chosen_name] + duration
        tips = "已延长状态效果"

    effects[chosen_name] = end_tick
    _status_effect[message.author_id] = effects

    message.reply(f"[MC-Effect] {tips}\n\n"
                  f"[{chosen_name}] {_format_duration(end_tick)}\n\n"
                  f"{chosen_effect}", modal_words=False)


@module(
    name="Minecraft",
    version="v1.1.0"
)
def register_module():
    pass
