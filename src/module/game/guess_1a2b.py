import random
import threading
from dataclasses import dataclass, field
from enum import Enum

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants, HelpStrList
from src.core.util.output_cache import get_cached_prefix
from src.core.util.tools import check_is_int, png2jpg
from src.render.pixie.render_guess_1a2b import Guess1A2BRecord, Guess1A2BRenderer

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
    history: list[Guess1A2BRecord] = field(default_factory=list)


_guess_info: dict[str, GuessInfo] = {}
_guess_info_lock = threading.Lock()


def _calculate_ab(guess: str, target: str) -> tuple[int, int]:
    """计算猜测结果：A 为数字与位置都正确的个数，B 为数字正确但位置不对的个数"""
    a = sum(1 for guess_digit, target_digit in zip(guess, target)
            if guess_digit == target_digit)
    b = sum(1 for guess_digit in guess if guess_digit in target) - a
    return a, b


def _validate_guess(guess: str, target_len: int) -> str | None:
    """校验猜测格式，合法时返回 None，否则返回错误提示"""
    # check_is_int 会接受 -123 / +1234 / 全角数字 / 1_234 等写法，这里只认 ASCII 数字
    if not (guess.isascii() and guess.isdigit()):
        return "参数格式错误，请输入数字"

    if guess[0] == '0':
        return "目标数字不包含前导0"

    if len(set(guess)) != len(guess):
        return "目标数字由不同的数组成"

    if len(guess) != target_len:
        return f"目标数字为 {target_len} 位数"

    return None


def _render_board(current_info: GuessInfo) -> str:
    """渲染当前对局状态，返回可发送的图片路径"""
    cached_prefix = get_cached_prefix('Guess-1A2B')
    img_path = f"{cached_prefix}.png"

    ended = current_info.status == GuessStatus.ENDED
    correct = (ended and current_info.history and
               current_info.history[-1].a == len(current_info.target))
    board_img = Guess1A2BRenderer(
        len(current_info.target), current_info.history,
        answer=current_info.target if ended else "",
        correct=correct
    ).render()
    board_img.write_file(img_path)
    return png2jpg(img_path)


def _reply_with_board(message: RobotMessage, content: str, current_info: GuessInfo):
    message.reply(content, img_path=_render_board(current_info))


def start_game(message: RobotMessage):
    current_uuid = message.uuid
    current_info: GuessInfo = _guess_info[current_uuid]

    if current_info.status == GuessStatus.RUNNING:
        _reply_with_board(
            message,
            "游戏已经开始，请使用 \"/1a2b [num]\" 猜测数字，不要带上中括号\n\n"
            f"目标为 {len(current_info.target)} 位数",
            current_info
        )
        return

    target_len = random.randint(4, 6)
    first_digit = random.choice("123456789")  # 避免出现前导0
    remaining_digits = random.sample([d for d in "0123456789" if d != first_digit],
                                     target_len - 1)
    target = first_digit + ''.join(remaining_digits)

    current_info = GuessInfo(GuessStatus.RUNNING, target, 0)
    _guess_info[current_uuid] = current_info

    _reply_with_board(
        message,
        "1a2b 游戏开始！使用 \"/1a2b [num]\" 猜测数字，不要带上中括号\n\n"
        f"目标为 {len(current_info.target)} 位数",
        current_info
    )


def try_guess(message: RobotMessage):
    current_uuid = message.uuid
    current_info: GuessInfo = _guess_info[current_uuid]

    if current_info.status == GuessStatus.IDLE:
        message.reply(f"游戏还未开始\n\n{_GUESS_1A2B_HELP}",
                      modal_words=False)
        return

    participant_guess = message.tokens[1]

    if current_info.status == GuessStatus.ENDED:
        message.reply(f"上一轮游戏已结束\n\n{_GUESS_1A2B_HELP}",
                      modal_words=False)
        return

    if not check_is_int(participant_guess):
        if participant_guess in ['stop', '结束', 'end', 'finish']:
            current_info.status = GuessStatus.ENDED
            _reply_with_board(
                message,
                f"游戏终止，答案是 {current_info.target}，总共猜了 {current_info.trials} 次",
                current_info
            )
        else:
            message.reply("参数格式错误，请输入数字")
        return

    error_message = _validate_guess(participant_guess, len(current_info.target))
    if error_message:
        message.reply(error_message)
        return

    a, b = _calculate_ab(participant_guess, current_info.target)
    current_info.trials += 1
    current_info.history.append(Guess1A2BRecord(participant_guess, a, b))

    if participant_guess == current_info.target:
        current_info.status = GuessStatus.ENDED
        _reply_with_board(
            message,
            f"恭喜你猜对了，答案是 {current_info.target}，总共猜了 {current_info.trials} 次",
            current_info
        )
    else:
        _reply_with_board(
            message,
            f"{participant_guess} => {a}A{b}B\n\n"
            f"{a} 个数相同且位置也正确，{b} 个数相同但位置不一样\n"
            f"目前总共猜了 {current_info.trials} 次",
            current_info
        )


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
    version="v1.1.0"
)
def register_module():
    pass
