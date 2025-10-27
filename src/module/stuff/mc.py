import asyncio
import datetime
import enum
import math
import random
import re
import time

from src.core.bot.decorator import module, command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.data.data_mc import get_mc_resource

_status_gamemode: dict[str, tuple["GameMode", float]] = {}
_status_effect: dict[str, dict[str, float]] = {}
_status_sleep: dict[str, float] = {}


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
                (end_tick < time.time() and gamemode == GameMode.SURVIVAL)):
            message.reply(f"[MC-Mode] 当前已在 {gamemode.value}模式")
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
    message.reply(f"[MC-Mode] 已切换到 {gamemode.value}模式，持续 {duration} 秒{tips}", modal_words=False)


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
        message.reply("[MC-Effect] 目前不支持指定状态效果")
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
        # 限制最大持续时长
        max_end_tick = time.time() + 99 * 60 * 5
        end_tick = min(end_tick, max_end_tick)
        tips = "已延长状态效果"

    effects[chosen_name] = end_tick
    _status_effect[message.author_id] = effects

    message.reply(f"[MC-Effect] {tips}\n\n"
                  f"[{chosen_name}] {_format_duration(end_tick)}\n\n"
                  f"{chosen_effect}", modal_words=False)


def _get_time_based_prob():
    """返回一个基于时间的概率值，晚上时概率更高"""
    current_time = datetime.datetime.now().time()
    total_minutes = current_time.hour * 60 + current_time.minute
    rad = (total_minutes / 1440.0) * 2 * math.pi
    # 使用余弦函数，午夜时概率最高，正午时概率最低
    prob = 0.12 + 0.08 * math.cos(rad)  # 范围: [0.04, 0.2]
    return prob


async def _reply_wakeup_with_sleep(message: RobotMessage, duration: int):
    """实现一个无阻塞的睡觉"""
    Constants.log.info(f"[MC-Sleep] 发起睡觉，时长 {duration} 秒")
    await asyncio.sleep(duration)
    message.reply("[MC-Sleep] 早上好")


@command(tokens=["sleep"])
def reply_mc_sleep(message: RobotMessage):
    """
    包含 Minecraft 主题的睡觉命令处理器
    随机回复睡觉相关的游戏消息，并可能延时发送"早上好"
    """
    content = message.tokens

    gamemode, _ = _get_gamemode(message)
    if gamemode == GameMode.SPECTATOR:
        message.reply("[MC-Sleep] 你无法在旁观者模式执行该指令")
        return

    if message.uuid in _status_sleep and time.time() < _status_sleep[message.uuid]:
        message.reply("[MC-Sleep] O宝睡着了，等会儿再来吧", modal_words=False)
        return

    joking_reasons = [
        "这张床爆炸了",
        "你被床弹飞了",
        "这张床已被破坏",
        "你现在不能休息，周围有玩家在游荡",
        "你现在不能休息，周围有流浪拴绳在游荡",
        "你现在不能休息，周围有白色僵尸在游荡",
        "你只能在白天或晴天中入睡",
        "守夜村民抢走了你的床，你被赶下来了",
        "闪电五雷轰，你的床被烧没了",
        "你的木板不太够，做不了床",
        "你的羊毛不太够，做不了床",
        "O宝刚刚喝了杯咖啡，完全睡不着",
        "O宝正在敲代码，你先睡吧",
        "O宝现在不困，你先睡吧",
        "O宝正在学习，你先睡吧"
    ]
    mc_reasons = get_mc_resource("sleep_failed")
    reasons = [joking_reasons, mc_reasons, ["晚安"]]

    sleep_prob = _get_time_based_prob()
    if len(content) >= 2:
        reason_type = content[1]
        if reason_type == "joking":
            reasons_prob = [1 - sleep_prob, 0, sleep_prob]
        elif reason_type == "mc":
            reasons_prob = [0, 1 - sleep_prob, sleep_prob]
        else:
            message.reply("[MC-Sleep] 参数错误，只支持 joking 和 mc")
            return
    else:
        reasons_prob = [(1 - sleep_prob) / 2, 1 - (1 - sleep_prob) / 2 - sleep_prob, sleep_prob]

    chosen_type = random.choices(reasons, weights=reasons_prob)[0]
    chosen = random.choice(chosen_type)
    tokens = _decode_template(chosen)
    Constants.log.info(f"[MC-Sleep] <sleep_prob:{sleep_prob * 100:.2f}%> {chosen}")
    message.reply(f"[MC-Sleep] {_fill_template(tokens)}", modal_words=False)

    if chosen == "晚安":
        sleep_duration = random.randint(30, 120)
        _sleep_awake_tick = time.time() + sleep_duration
        _status_sleep[message.uuid] = _sleep_awake_tick
        asyncio.run_coroutine_threadsafe(
            _reply_wakeup_with_sleep(message, sleep_duration),
            message.loop
        )


@module(
    name="Minecraft",
    version="v1.2.0"
)
def register_module():
    pass
