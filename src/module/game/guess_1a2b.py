import random
import threading
from dataclasses import dataclass
from enum import Enum

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants, HelpStrList
from src.core.util.tools import check_is_int

_GUESS_1A2B_HELP = '\n'.join(HelpStrList(Constants.help_contents["guess-1a2b"]))


class GuessStatus(Enum):
    """记录当前猜数字状态"""
    IDLE = 0
    RUNNING = 1
    ENDED = 2


@dataclass
class GuessInfo:
    status: GuessStatus
    target: str
    trials: int


_guess_info = {}
_guess_info_lock = threading.Lock()


def start_game(message: RobotMessage):
    current_uuid = message.uuid
    current_info: GuessInfo = _guess_info[current_uuid]

    if current_info.status == GuessStatus.RUNNING:
        message.reply("游戏已经开始，请使用 \"/1a2b [num]\" 猜测数字，不要带上中括号\n\n"
                      f"目标为 {len(current_info.target)} 位数")
        return None

    target_len = random.randint(4, 6)
    first_digit = random.choice("123456789")  # 避免出现前导0
    remaining_digits = random.sample([d for d in "0123456789" if d != first_digit],
                                     target_len - 1)
    target = first_digit + ''.join(remaining_digits)

    current_info = GuessInfo(GuessStatus.RUNNING, target, 0)
    message.reply("1a2b 游戏开始！使用 \"/1a2b [num]\" 猜测数字，不要带上中括号\n\n"
                  f"目标为 {len(current_info.target)} 位数")

    _guess_info[current_uuid] = current_info
    return None


def try_guess(message: RobotMessage):
    current_uuid = message.uuid
    current_info: GuessInfo = _guess_info[current_uuid]

    if _guess_info[current_uuid].status == GuessStatus.IDLE:
        message.reply(f"游戏还未开始\n\n{_GUESS_1A2B_HELP}",
                      modal_words=False)
        return None

    if _guess_info[current_uuid].status == GuessStatus.ENDED:
        message.reply(f"上一轮游戏已结束\n\n{_GUESS_1A2B_HELP}",
                      modal_words=False)
        return None

    participant_guess = message.tokens[1]

    if not check_is_int(participant_guess):
        if participant_guess in ['stop', '结束', 'end', 'finish']:
            message.reply(f"游戏终止，答案是 {current_info.target}，总共猜了 {current_info.trials} 次")
            _guess_info[current_uuid] = GuessInfo(GuessStatus.ENDED, "", -1)
        else:
            message.reply("参数格式错误，请输入数字")
        return None

    if participant_guess[0] == '0':
        message.reply("目标数字不包含前导0")
        return None

    if len(set(participant_guess)) != len(participant_guess):
        message.reply("目标数字由不同的数组成")
        return None

    if len(participant_guess) != len(current_info.target):
        message.reply(f"目标数字为 {len(current_info.target)} 位数")
        return None

    current_info.trials += 1

    if participant_guess == current_info.target:
        message.reply(f"恭喜你猜对了，答案是 {current_info.target}，总共猜了 {current_info.trials} 次")
        current_info = GuessInfo(GuessStatus.ENDED, "", -1)

    else:
        p, q = 0, 0
        for pa, ju in zip(participant_guess, current_info.target):
            if pa == ju:
                p += 1
            elif pa in current_info.target:
                q += 1
        message.reply(f"{participant_guess} => {p}A{q}B\n\n"
                      f"{p} 个数相同且位置也正确，{q} 个数相同但位置不一样\n"
                      f"目前总共猜了 {current_info.trials} 次")

    _guess_info[current_uuid] = current_info
    return None


@command(tokens=["1a2b", "1a2b猜数字", "ab"], multi_thread=True)
def reply_guess_1a2b(message: RobotMessage):
    if not 1 <= len(message.tokens) <= 2:
        message.reply(f"参数数量有误\n\n{_GUESS_1A2B_HELP}",
                      modal_words=False)
        return None

    with _guess_info_lock:
        current_uuid = message.uuid
        if current_uuid not in _guess_info:
            _guess_info[current_uuid] = GuessInfo(GuessStatus.IDLE, "", -1)

        if len(message.tokens) == 1:
            start_game(message)
        else:
            try_guess(message)

        return None


@module(
    name="Guess-1A2B",
    version="v1.0.1"
)
def register_module():
    pass
