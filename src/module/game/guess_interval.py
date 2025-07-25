import random
import threading
from dataclasses import dataclass
from enum import Enum

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants, HelpStrList
from src.core.util.tools import check_is_int

_GUESS_INTERVAL_HELP = '\n'.join(HelpStrList(Constants.help_contents["guess-interval"]))


class GuessStatus(Enum):
    """记录当前猜数字状态"""
    IDLE = 0
    RUNNING = 1
    ENDED = 2


@dataclass
class GuessInfo:
    status: GuessStatus
    target: int
    bound: tuple[int, int]
    trials: int


_guess_info = {}
_guess_info_lock = threading.Lock()


def start_game(message: RobotMessage):
    current_uuid = message.uuid
    current_info: GuessInfo = _guess_info[current_uuid]

    if current_info.status == GuessStatus.RUNNING:
        message.reply("游戏已经开始，请使用 \"/guess [num]\" 猜测数字，不要带上中括号\n\n"
                      f"目标位于闭区间 [{current_info.bound[0]}, {current_info.bound[1]}] 内")
        return None

    range_min = random.randint(1, 49900)  # 确保至少有100的范围
    range_max = random.randint(range_min + 100, 50000)

    target = random.randint(range_min, range_max)
    current_info = GuessInfo(GuessStatus.RUNNING, target, (range_min, range_max), 0)
    message.reply("区间猜数字开始！使用 \"/guess [num]\" 猜测数字，不要带上中括号\n\n"
                  f"目标位于闭区间 [{range_min}, {range_max}] 内")

    _guess_info[current_uuid] = current_info
    return None


def try_guess(message: RobotMessage):
    current_uuid = message.uuid
    current_info: GuessInfo = _guess_info[current_uuid]

    if _guess_info[current_uuid].status == GuessStatus.IDLE:
        message.reply(f"游戏还未开始\n\n{_GUESS_INTERVAL_HELP}",
                      modal_words=False)
        return None

    if _guess_info[current_uuid].status == GuessStatus.ENDED:
        message.reply(f"上一轮游戏已结束\n\n{_GUESS_INTERVAL_HELP}",
                      modal_words=False)
        return None

    participant_guess_plain = message.tokens[1]

    if not check_is_int(participant_guess_plain):
        if participant_guess_plain in ['stop', '结束', 'end', 'finish']:
            message.reply(f"游戏终止，答案是 {current_info.target}，总共猜了 {current_info.trials} 次")
            _guess_info[current_uuid] = GuessInfo(GuessStatus.ENDED, -1, (-1, -1), -1)
        else:
            message.reply("参数格式错误，请输入数字")
        return None

    participant_guess = int(participant_guess_plain)
    current_info.trials += 1

    if participant_guess == current_info.target:
        ok_bound = current_info.bound[1] - current_info.bound[0] + 1
        ok_possibility = round((100 / ok_bound) * 100) / 100
        message.reply(f"恭喜你猜对了，答案是 {current_info.target}，总共猜了 {current_info.trials} 次\n\n"
                      f"在最后一次猜测中，你在 {ok_bound} 个数中以 {ok_possibility}% 的可能性猜对了答案")
        current_info = GuessInfo(GuessStatus.ENDED, -1, (-1, -1), -1)

    elif participant_guess > current_info.target:
        current_info.bound = (current_info.bound[0],
                              min(participant_guess - 1, current_info.bound[1]))
        message.reply(f"太大了！\n\n"
                      f"目标位于闭区间 [{current_info.bound[0]}, {current_info.bound[1]}] 内，"
                      f"目前总共猜了 {current_info.trials} 次")

    else:
        current_info.bound = (max(participant_guess + 1, current_info.bound[0]),
                              current_info.bound[1])
        message.reply(f"太小了！\n\n"
                      f"目标位于闭区间 [{current_info.bound[0]}, {current_info.bound[1]}] 内，"
                      f"目前总共猜了 {current_info.trials} 次")

    _guess_info[current_uuid] = current_info
    return None


@command(tokens=["guess", "猜数字", "区间猜数字", "interval"], multi_thread=True)
def reply_guess_interval(message: RobotMessage):
    if not 1 <= len(message.tokens) <= 2:
        message.reply(f"参数数量有误\n\n{_GUESS_INTERVAL_HELP}",
                      modal_words=False)
        return None

    with _guess_info_lock:
        current_uuid = message.uuid
        if current_uuid not in _guess_info:
            _guess_info[current_uuid] = GuessInfo(GuessStatus.IDLE, -1, (-1, -1), -1)

        if len(message.tokens) == 1:
            start_game(message)
        else:
            try_guess(message)

        return None


@module(
    name="Guess-Interval",
    version="v1.0.1"
)
def register_module():
    pass
