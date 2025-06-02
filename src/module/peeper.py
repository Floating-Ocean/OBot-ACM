import asyncio
import datetime
import os

from botpy import Client
from thefuzz import process

from src.core.bot.command import command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.exception import ModuleRuntimeError
from src.core.util.output_cached import get_cached_prefix
from src.core.util.tools import run_shell, escape_mail_url, png2jpg, check_is_int
from src.module.atc import __atc_version__
from src.module.cf import __cf_version__
from src.module.color_rand import __color_rand_version__
from src.module.contest_manual import __contest_list_renderer_version__
from src.module.how_to_cook import __how_to_cook_version__
from src.module.nk import __nk_version__
from src.module.pick_one import __pick_one_version__
from src.module.rand import __rand_version__

_lib_path = os.path.join(Constants.config["lib_path"], "Peeper-Board-Generator")


def register_module():
    pass


def classify_verdicts(content: str) -> str:
    alias_to_full = {
        "ac": ["accepted", "ac"],
        "wa": ["wrong answer", "rejected", "wa", "rj"],
        "tle": ["time exceeded", "time limit exceeded", "tle", "te"],
        "mle": ["memory exceeded", "memory limit exceeded", "mle", "me"],
        "ole": ["output exceeded", "output limit exceeded", "ole", "oe"],
        "hc": ["hacked", "hc"],
        "re": ["runtime error", "re"],
        "ce": ["compile error", "ce"],
        "se": ["system error", "se"],
        "fe": ["format error", "se"],
    }
    full_to_alias = {val: key for key, alters in alias_to_full.items() for val in alters}
    # 模糊匹配
    matches = process.extract(content.lower(), full_to_alias.keys(), limit=1)[0]
    if matches[1] < 60:
        return ""

    return full_to_alias[matches[0]].upper()


def execute_lib_method(prop: str, message: RobotMessage | None, no_id: bool) -> str | None:
    traceback = ""
    for _t in range(2):  # 尝试2次
        id_prop = "" if no_id else "--id hydro "
        # prop 中的变量只有 Constants.config 中的路径，已在 robot.py 中事先检查
        result = run_shell(f"cd {_lib_path} & python main.py {id_prop}{prop}")

        with open(os.path.join(_lib_path, "last_traceback.log"), "r", encoding='utf-8') as f:
            traceback = f.read()
            if traceback == "ok":
                return result

    if message is not None:
        message.report_exception('Peeper-Board-Generator', traceback,
                                 ModuleRuntimeError(traceback.split('\n')[-2]))

    return None


def call_lib_method(message: RobotMessage, prop: str, no_id: bool = False) -> str | None:
    return execute_lib_method(prop, message, no_id)


def call_lib_method_directly(prop: str) -> str | None:
    return execute_lib_method(prop, None, False)


def daily_update_job():
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    call_lib_method_directly(f"--full --output {cached_prefix}.png")


def noon_report_job(client: Client):
    # 因为只有这里需要主动推送所以写函数里了
    def push_message(content: str, file_image: str | None = None):
        Constants.log.info(f"[obot-int] 发起推送: {content}")
        asyncio.run_coroutine_threadsafe(
            client.api.post_message(channel_id=Constants.config['push_channel'],
                                    content=content,
                                    file_image=file_image),
            client.loop
        )

    today = datetime.datetime.now().strftime("%Y/%m/%d")
    oneday = datetime.timedelta(days=1)
    yesterday = (datetime.datetime.now() - oneday).strftime("%Y/%m/%d")

    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = call_lib_method_directly(f"--full --output {cached_prefix}.png")
    if run is None:
        push_message(content="推送昨日卷王天梯榜失败")
    else:
        push_message(content=f"{yesterday} 卷王天梯榜", file_image=png2jpg(f"{cached_prefix}.png"))

    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = call_lib_method_directly(f"--now --output {cached_prefix}.png")
    if run is None:
        push_message(content="推送今日题数失败")
    else:
        push_message(content=f"{today} 半天做题总榜",
                     file_image=png2jpg(f"{cached_prefix}.png"))


def send_user_info(message: RobotMessage, content: str, by_name: bool = False):
    type_name = "用户名" if by_name else " uid "
    type_id = "name" if by_name else "uid"
    message.reply(f"正在查询{type_name}为 {content} 的用户数据，请稍等")

    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = call_lib_method(message, f"--query_{type_id} {content} --output {cached_prefix}.txt")
    if run is None:
        return

    with open(f"{cached_prefix}.txt", encoding="utf-8") as f:
        result = escape_mail_url(f.read())
        message.reply(f"[{type_id.capitalize()} {content}]\n\n{result}", modal_words=False)


@command(tokens=['评测榜单', 'verdict'], need_check_exclude=True)
def send_now_board_with_verdict(message: RobotMessage):
    content = message.tokens[1] if len(message.tokens) == 2 else ""
    single_col = (message.tokens[2] == "single") if len(
        message.tokens) == 3 else False
    verdict = classify_verdicts(content)
    if verdict == "":
        message.reply(f"请在 /评测榜单 后面添加正确的参数，如 ac, Accepted, TimeExceeded, WrongAnswer")
        return

    message.reply(f"正在查询今日 {verdict} 榜单，请稍等")

    single_arg = "" if single_col else " --separate_cols"
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = call_lib_method(message,
                          f"--now {single_arg} --verdict {verdict} --output {cached_prefix}.png")
    if run is None:
        return

    message.reply(f"今日 {verdict} 榜单", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['今日题数', 'today'], need_check_exclude=True)
def send_today_board(message: RobotMessage):
    single_col = (message.tokens[1] == "single") \
        if len(message.tokens) == 2 else False
    message.reply(f"正在查询今日题数，请稍等")

    single_arg = "" if single_col else " --separate_cols"
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = call_lib_method(message, f"--now {single_arg} --output {cached_prefix}.png")
    if run is None:
        return

    message.reply("今日题数", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['昨日总榜', 'yesterday', 'full'], need_check_exclude=True)
def send_yesterday_board(message: RobotMessage):
    single_col = (message.tokens[1] == "single") \
        if len(message.tokens) == 2 else False
    message.reply(f"正在查询昨日总榜，请稍等")

    single_arg = "" if single_col else " --separate_cols"
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = call_lib_method(message, f"--full {single_arg} --output {cached_prefix}.png")
    if run is None:
        return

    message.reply("昨日卷王天梯榜", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['api'])
def send_version_info(message: RobotMessage):
    message.reply(f"正在查询各模块版本，请稍等")

    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = call_lib_method(message, f"--version --output {cached_prefix}.txt", no_id=True)
    if run is None:
        return

    with open(f"{cached_prefix}.txt", encoding="utf-8") as f:
        result = f.read()
        message.reply(f"[API Version]\n\n"
                      f"Core {Constants.core_version}\n"
                      f"AtCoder {__atc_version__}\n"
                      f"Codeforces {__cf_version__}\n"
                      f"Color-Rand {__color_rand_version__}\n"
                      f"Contest-List-Renderer {__contest_list_renderer_version__}\n"
                      f"How-To-Cook {__how_to_cook_version__}\n"
                      f"NowCoder {__nk_version__}\n"
                      f"{result}\n"
                      f"Pick-One {__pick_one_version__}\n"
                      f"Random {__rand_version__}", modal_words=False)


@command(tokens=['user'], need_check_exclude=True)
def oj_user(message: RobotMessage):
    content = message.tokens
    if len(content) < 3:
        return message.reply("请输入三个参数，第三个参数前要加空格，比如说\"/user id 1\"，\"/user name Hydro\"")
    if len(content) > 3:
        return message.reply("请输入三个参数，第三个参数不要加上空格")
    if content[1] == "id" and (len(content[2]) > 9 or not check_is_int(content[2])):
        return message.reply("参数错误，id必须为整数")
    if content[1] == "id" or content[1] == "name":
        send_user_info(message, content[2], by_name=(content[1] == "name"))
        return None
    else:
        message.reply("请输入正确的参数，如\"/user id ...\", \"/user name ...\"")
        return None
