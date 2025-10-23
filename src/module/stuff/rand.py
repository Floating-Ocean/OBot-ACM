import re

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.constants import HelpStrList
from src.core.util.tools import check_is_int, fetch_url_text
from src.module.cp.atc import reply_atc_request
from src.module.cp.cf import reply_cf_request
from src.module.stuff.color import reply_color_rand
from src.module.stuff.misc import reply_hitokoto

_RAND_HELP = '\n'.join(HelpStrList(Constants.help_contents["random"]))


def get_rand_num(range_min: int, range_max: int) -> int:
    url = ("https://www.random.org/integers/?num=1&"
           f"min={range_min}&max={range_max}&col=1&base=10&format=plain&rnd=new")
    data = fetch_url_text(url, method='get')
    return int(data)


def get_rand_seq(range_max: int) -> str:
    url = ("https://www.random.org/integer-sets/?sets=1&"
           f"num={range_max}&min=1&max={range_max}&seqnos=off&commas=on&order=index&"
           "format=plain&rnd=new")
    data = fetch_url_text(url, method='get')
    return data


@command(tokens=["选择", "rand", "shuffle", "打乱"])
def reply_rand_request(message: RobotMessage):
    try:
        content = message.tokens
        if len(content) < 2 and not content[0].startswith("/选择"):
            message.reply(f'[Random]\n\n{_RAND_HELP}', modal_words=False)
            return

        if content[0] == "/shuffle" or content[0] == "/打乱":
            if len(content) != 2:
                message.reply(f"请输入正确的指令格式，比如说\"/{content[0]} 这是一句话\"")
            content_len = len(content[1])
            rnd_perm = get_rand_seq(content_len).split(", ")
            rnd_content = "".join([content[1][int(x) - 1] for x in rnd_perm])
            message.reply(f"[Random Shuffle]\n\n{rnd_content}", modal_words=False)
            return

        func = content[0][3::].strip() if len(content) == 1 else content[1]

        if content[0].startswith("/选择"):
            if len(func) == 0:
                message.reply("请指定要选择范围，用 \"还是\" 或逗号分隔")
                return

            select_from = re.split("还是|,|，", func)
            select_len = len(select_from)
            selected_idx = get_rand_num(0, select_len - 1)
            message.reply(f"我觉得第{selected_idx}个更好")

        elif func == "num" or func == "int":
            if (len(content) != 4 or
                    (not check_is_int(content[2])) or (not check_is_int(content[3]))):
                message.reply("请输入正确的指令格式，比如说\"/rand num 1 100\"")
                return

            if max(len(content[2]), len(content[3])) <= 10:
                range_min, range_max = int(content[2]), int(content[3])
                if max(abs(range_min), abs(range_max)) <= 1_000_000_000:
                    if range_min > range_max:
                        range_min, range_max = range_max, range_min
                    result = get_rand_num(range_min, range_max)
                    split_str = "\n\n" if result >= 10_000 else " "
                    message.reply(f"[Rand Number]{split_str}{result}", modal_words=False)
                    return

            message.reply("参数过大，请输入 [-1e9, 1e9] 内的整数")

        elif func == "seq":
            if len(content) != 3 or not check_is_int(content[2]):
                message.reply("请输入正确的指令格式，比如说\"/rand seq 10\"")
                return

            if len(content[2]) <= 4:
                range_max = int(content[2])
                if 1 <= range_max <= 500:
                    result = get_rand_seq(range_max).replace("\n", "")
                    message.reply(f"[Rand Sequence]\n\n[{result}]", modal_words=False)
                    return

            message.reply("参数错误，请输入 [1, 500] 内的数字")

        elif func == "word" or func == "hitokoto" or func == "sentence":
            reply_hitokoto(message)

        elif func == "color":
            reply_color_rand(message)

        elif func == "cf":
            reply_cf_request(message)

        elif func == "atc":
            reply_atc_request(message)

        else:
            message.reply(f'[Random]\n\n{_RAND_HELP}', modal_words=False)

    except Exception as e:
        message.report_exception('Random', e)


@module(
    name="Random",
    version="v3.2.0"
)
def register_module():
    pass
