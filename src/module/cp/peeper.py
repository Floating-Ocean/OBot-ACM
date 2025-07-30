import copy
import json
import os

from thefuzz import process

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.exception import ModuleRuntimeError
from src.core.util.tools import run_shell, escape_mail_url, png2jpg, check_is_int
from src.data.data_cache import get_cached_prefix

_lib_path = Constants.modules_conf.get_lib_path("Peeper-Board-Generator")


def _classify_verdicts(content: str) -> str:
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


def _wrap_conf_id(uuid: str, conf: dict) -> dict:
    """为不同的群设置不同的id，避免冲突"""
    new_conf = copy.deepcopy(conf)
    conf_id = f'{uuid}_{conf["id"]}'
    new_conf["id"] = conf_id
    return new_conf


def _get_specified_conf(specified_uuid: str) -> dict:
    execute_conf = Constants.modules_conf.peeper["configs"]

    default_conf = None
    for uuid, conf in execute_conf.items():
        if conf["use_as_default"]:
            if default_conf is not None:
                raise RuntimeError("Duplicate default configs detected in "
                                   f"{default_conf['id']} and {conf['id']}.")
            default_conf = _wrap_conf_id(uuid, conf)
    if default_conf is None:
        raise RuntimeError("No default config found.")

    if len(specified_uuid) > 0:
        if specified_uuid in execute_conf:
            return _wrap_conf_id(specified_uuid, execute_conf[specified_uuid])
        Constants.log.warn("[peeper] 未配置榜单来源，默认选取 FJNUACM Online Judge")

    return default_conf


def _cache_conf_payload(conf: dict) -> str:
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    with open(f"{cached_prefix}.json", "w", encoding="utf-8") as f:
        json.dump([conf], f, ensure_ascii=False, indent=4)

    return f"{cached_prefix}.json"


def _call_lib_method(message: RobotMessage | str, prop: str,
                     no_id: bool = False) -> str | None:
    """
    执行 Peeper-Board-Generator 内的指令，message 可指定消息本体或消息 uuid，后者不会进行异常反馈
    """
    uuid = message.uuid if isinstance(message, RobotMessage) else message
    execute_conf = _get_specified_conf(uuid)

    traceback = ""
    for _t in range(2):  # 尝试2次
        id_prop = "" if no_id else f'--id {execute_conf["id"]} '
        # prop 中的变量只有 Constants.config 中的路径，已在 robot.py 中事先检查
        result = run_shell(f'cd {_lib_path} & python main.py {id_prop}{prop} '
                           f'--config {_cache_conf_payload(execute_conf)}')

        with open(os.path.join(_lib_path, "last_traceback.log"), "r", encoding='utf-8') as f:
            traceback = f.read()
            if traceback == "ok":
                return result

    if isinstance(message, RobotMessage):
        message.report_exception('Peeper-Board-Generator',
                                 ModuleRuntimeError(traceback.split('\n')[-2]))

    return None


def daily_update_job():
    all_uuid = Constants.modules_conf.peeper["configs"].keys()
    Constants.log.info(f'[peeper] 每日榜单更新任务开始，检测到 {len(all_uuid)} 个榜单')

    for uuid in all_uuid:
        cached_prefix = get_cached_prefix('Peeper-Board-Generator')
        _call_lib_method(uuid, f"--full --output {cached_prefix}.png")

    Constants.log.info("[peeper] 每日榜单更新任务完成")


def _send_user_info(message: RobotMessage, content: str, by_name: bool = False):
    type_name = "用户名" if by_name else " uid "
    type_id = "name" if by_name else "uid"
    message.reply(f"正在查询{type_name}为 {content} 的用户数据，请稍等")

    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = _call_lib_method(message, f"--query_{type_id} {content} --output {cached_prefix}.txt")
    if run is None:
        return

    with open(f"{cached_prefix}.txt", "r", encoding="utf-8") as f:
        result = escape_mail_url(f.read())
        message.reply(f"[{type_id.capitalize()} {content}]\n\n{result}", modal_words=False)


@command(tokens=['评测榜单', 'verdict'])
def send_now_board_with_verdict(message: RobotMessage):
    content = message.tokens[1] if len(message.tokens) == 2 else ""
    single_col = (message.tokens[2] == "single") if len(
        message.tokens) == 3 else False
    verdict = _classify_verdicts(content)
    if verdict == "":
        message.reply("请在 /评测榜单 后面添加正确的参数，如 ac, Accepted, TimeExceeded, WrongAnswer")
        return

    message.reply(f"正在查询今日 {verdict} 榜单，请稍等")

    single_arg = "" if single_col else " --separate_cols"
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = _call_lib_method(message,
                           f"--now {single_arg} --verdict {verdict} --output {cached_prefix}.png")
    if run is None:
        return

    message.reply(f"今日 {verdict} 榜单", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['今日题数', 'today'])
def send_today_board(message: RobotMessage):
    single_col = (message.tokens[1] == "single") \
        if len(message.tokens) == 2 else False
    message.reply("正在查询今日题数，请稍等")

    single_arg = "" if single_col else " --separate_cols"
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = _call_lib_method(message, f"--now {single_arg} --output {cached_prefix}.png")
    if run is None:
        return

    message.reply("今日题数", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['昨日总榜', 'yesterday', 'full'])
def send_yesterday_board(message: RobotMessage):
    single_col = (message.tokens[1] == "single") \
        if len(message.tokens) == 2 else False
    message.reply("正在查询昨日总榜，请稍等")

    single_arg = "" if single_col else " --separate_cols"
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = _call_lib_method(message, f"--full {single_arg} --output {cached_prefix}.png")
    if run is None:
        return

    message.reply("昨日卷王天梯榜", png2jpg(f"{cached_prefix}.png"))


def get_version_info() -> str:
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = _call_lib_method("",  # 留空 uuid，选择默认
                           f"--version --output {cached_prefix}.txt", no_id=True)
    if run is None:
        return "Unknown"

    with open(f"{cached_prefix}.txt", "r", encoding="utf-8") as f:
        result = f.read()
        return result.split(' ', 1)[1]


@command(tokens=['user'])
def send_oj_user(message: RobotMessage):
    content = message.tokens
    if len(content) < 3:
        return message.reply("请输入三个参数，第三个参数前要加空格，比如说\"/user id 1\"，\"/user name Hydro\"")
    if len(content) > 3:
        return message.reply("请输入三个参数，第三个参数不要加上空格")
    if content[1] == "id" and (len(content[2]) > 9 or not check_is_int(content[2])):
        return message.reply("参数错误，id必须为整数")
    if content[1] == "id" or content[1] == "name":
        _send_user_info(message, content[2], by_name=(content[1] == "name"))
        return None
    else:
        message.reply("请输入正确的参数，如\"/user id ...\", \"/user name ...\"")
        return None


@module(
    name="Peeper-Board-Generator",
    version=get_version_info
)
def register_module():
    pass
