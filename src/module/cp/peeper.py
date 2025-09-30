import copy
import json
import os
import re
from dataclasses import dataclass

from thefuzz import process

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.exception import ModuleRuntimeError
from src.core.util.tools import run_py_file, escape_mail_url, png2jpg, check_is_int, clean_unsafe_shell_str
from src.data.data_cache import get_cached_prefix

_lib_path = Constants.modules_conf.get_lib_path("Peeper-Board-Generator")
_allowed_id_re = re.compile(r'^[A-Za-z0-9_-]+$')


@dataclass
class PeeperConfigs:
    default_conf: dict
    conf_dict: dict[str, dict]  # conf_id -> conf
    uuid_dict: dict[str, dict]  # uuid -> conf


def _classify_verdicts(content: str) -> str:
    alias_to_full = {
        "ac": ["accepted", "ac"],
        "wa": ["wrong answer", "rejected", "wa", "rj"],
        "tle": ["time exceeded", "time limit exceeded", "tle", "te"],
        "mle": ["memory exceeded", "memory limit exceeded", "mle", "me"],
        "ole": ["output exceeded", "output limit exceeded", "ole", "oe"],
        "hkd": ["hacked", "challenged", "hk", "hkd", "hc"],
        "re": ["runtime error", "re"],
        "ce": ["compile error", "ce"],
        "se": ["system error", "se"],
        "fe": ["format error", "fe"],
    }
    full_to_alias = {val: key for key, alters in alias_to_full.items() for val in alters}
    # 模糊匹配
    matches = process.extract(content.lower(), full_to_alias.keys(), limit=1)[0]
    if matches[1] < 60:
        return ""

    return full_to_alias[matches[0]].upper()


def _wrap_conf_id(conf_id: str, conf: dict) -> dict:
    """为不同的配置文件设置不同的id，避免冲突"""
    new_conf = copy.deepcopy(conf)
    # 仅允许 [A-Za-z0-9_-]，防止 shell 注入与路径歧义
    if not _allowed_id_re.fullmatch(conf_id or ''):
        raise RuntimeError(f"Invalid obot_conf_id: {conf_id!r}")
    if not _allowed_id_re.fullmatch(str(conf.get("id", ""))):
        raise RuntimeError(f"Invalid id in config {conf_id!r}: {conf.get('id')!r}")
    new_conf_id = f'{conf_id}_{conf["id"]}'
    new_conf["id"] = new_conf_id
    return new_conf


def _generate_peeper_conf(execute_conf: list) -> PeeperConfigs:
    required = {"obot_conf_id": str, "obot_apply_to": list, "obot_is_private": bool}

    def _validate(i: int, check_conf: dict):
        for k, tp in required.items():
            if k not in check_conf:
                raise RuntimeError(f"Missing `{k}` in peeper.configs[{i}]")
            if not isinstance(check_conf[k], tp):
                raise RuntimeError(
                    f"Invalid type for `{k}` in peeper.configs[{i}]: "
                    f"expect {tp}, got {type(check_conf[k])}"
                )
        if not check_conf["obot_conf_id"]:
            raise RuntimeError(f"`obot_conf_id` cannot be empty in peeper.configs[{i}]")
        if any(not isinstance(u, str) or not u for u in check_conf["obot_apply_to"]):
            raise RuntimeError(
                f"`obot_apply_to` must be non-empty strings in peeper.configs[{i}]"
            )

    if len(execute_conf) == 0:
        raise RuntimeError("No config found.")

    conf_dict, uuid_dict = {}, {}
    default_conf = None
    for idx, conf in enumerate(execute_conf):
        _validate(idx, conf)
        conf_id = conf["obot_conf_id"]
        if conf_id in conf_dict:
            raise RuntimeError(f"Duplicate config ids detected for {conf_id}.")

        wrapped = _wrap_conf_id(conf_id, conf)
        conf_dict[conf_id] = wrapped
        for uuid in wrapped["obot_apply_to"]:
            if uuid in uuid_dict:
                raise RuntimeError(
                    "Duplicate configs detected in "
                    f"{uuid_dict[uuid]['obot_conf_id']} and {conf_id} "
                    f"for {uuid}."
                )
            uuid_dict[uuid] = wrapped
        if idx == 0:  # 选取第一个作为默认
            default_conf = wrapped

    return PeeperConfigs(default_conf, conf_dict, uuid_dict)


def _get_specified_conf(message: RobotMessage | None, conf_id: str = None) -> dict | None:
    execute_conf = Constants.modules_conf.peeper["configs"]
    peeper_conf = _generate_peeper_conf(execute_conf)

    # 不管 conf_id
    if not message:
        return peeper_conf.default_conf

    # 优先处理指定 conf_id 的请求
    if conf_id:
        matched = conf_id in peeper_conf.conf_dict
        if matched:
            matched = (not peeper_conf.conf_dict[conf_id]["obot_is_private"] or  # 排除私有
                       message.uuid in peeper_conf.conf_dict[conf_id]["obot_apply_to"])  # 但不排除自己
        if not matched:
            all_ids = '\n'.join([_id for _id, conf in peeper_conf.conf_dict.items()
                                 if (not conf["obot_is_private"] or
                                     message.uuid in conf["obot_apply_to"])])
            ids_text = f"可用榜单：\n{all_ids}" if all_ids else "无可用榜单"
            message.reply(f"未匹配到榜单，此操作只支持精确匹配，请确认输入正确性以及榜单是否私有，目前{ids_text}",
                          modal_words=False)
            return None
        return peeper_conf.conf_dict[conf_id]

    # 匹配消息 uuid
    if message.uuid not in peeper_conf.uuid_dict:
        Constants.log.warning(f"[peeper] 未匹配到榜单，默认选取 {peeper_conf.default_conf['obot_conf_id']}")
        return peeper_conf.default_conf

    chosen_conf = peeper_conf.uuid_dict[message.uuid]
    Constants.log.warning(f"[peeper] 匹配榜单 {chosen_conf['obot_conf_id']}")
    return chosen_conf


def _cache_conf_payload(conf: dict) -> str:
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    with open(f"{cached_prefix}.json", "w", encoding="utf-8") as f:
        json.dump([conf], f, ensure_ascii=False, indent=4)

    return f"{cached_prefix}.json"


def _call_lib_method_with_conf(conf: dict, prop: str, no_id: bool = False) -> str:
    """
    执行 Peeper-Board-Generator 内的指令，指定配置文件
    """
    traceback = ""
    payload = _cache_conf_payload(conf)
    for _ in range(2):  # 尝试2次
        id_prop = "" if no_id else f'--id "{conf["id"]}" '
        # prop 中的变量只有 Constants.config 中的路径，已在 robot.py 中事先检查
        result = run_py_file(f'main.py {id_prop}{prop} --config "{payload}"', _lib_path)
        try:
            with open(os.path.join(_lib_path, "last_traceback.log"), "r", encoding='utf-8') as f:
                traceback = f.read()
                if traceback.strip() == "ok":
                    return result
        except FileNotFoundError as e:
            raise ModuleRuntimeError("last_traceback.log not found.") from e

    lines = [ln for ln in traceback.splitlines() if ln.strip()]
    raise ModuleRuntimeError(lines[-1] if lines else "Unknown error, empty last traceback.")


def _call_lib_method(message: RobotMessage | None, prop: str,
                     no_id: bool = False, conf_id: str = None) -> str | None:
    """
    执行 Peeper-Board-Generator 内的指令，可选择是否脱离聊天环境执行，指定配置文件 id
    """
    execute_conf = _get_specified_conf(message, conf_id)
    if not execute_conf:
        return None

    try:
        result = _call_lib_method_with_conf(execute_conf, prop, no_id)
    except ModuleRuntimeError as e:
        result = None
        if message:
            message.report_exception('Peeper-Board-Generator', e)
        else:
            Constants.log.warning("[peeper] 已忽略一个异常")
            Constants.log.exception(f"[peeper] {e}")

    return result


def peeper_daily_update_job():
    execute_conf = Constants.modules_conf.peeper["configs"]
    peeper_conf = _generate_peeper_conf(execute_conf)
    Constants.log.info(f'[peeper] 每日榜单更新任务开始，检测到 {len(peeper_conf.conf_dict)} 个榜单')

    for conf_id, conf in peeper_conf.conf_dict.items():
        Constants.log.info(f'[peeper] 正在更新 {conf_id}')
        cached_prefix = get_cached_prefix('Peeper-Board-Generator')
        try:
            _call_lib_method_with_conf(conf, f'--full --output "{cached_prefix}.png"')
        except ModuleRuntimeError as e:
            Constants.log.warning(f"[peeper] 更新每日榜单失败，配置文件为 {conf_id}")
            Constants.log.exception(f"[peeper] {e}")

    Constants.log.info("[peeper] 每日榜单更新任务完成")


def _send_user_info(message: RobotMessage, content: str, by_name: bool = False):
    type_name = "用户名" if by_name else " uid "
    type_id = "name" if by_name else "uid"
    message.reply(f"正在查询{type_name}为 {content} 的用户数据，请稍等")

    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = _call_lib_method(message,
                           f'--query_{type_id} "{content}" --output "{cached_prefix}.txt"')
    if run is None:
        return

    with open(f"{cached_prefix}.txt", "r", encoding="utf-8") as f:
        result = escape_mail_url(f.read())
        message.reply(f"[{type_id.capitalize()} {content}]\n\n{result}", modal_words=False)


@command(tokens=['评测榜单', 'verdict'])
def send_now_board_with_verdict(message: RobotMessage):
    content = message.tokens[1] if len(message.tokens) >= 2 else ""
    conf_id = message.tokens[2] if len(message.tokens) >= 3 else None
    verdict = _classify_verdicts(content)
    if verdict == "":
        message.reply("请在 /评测榜单 后面添加正确的参数，如 ac, Accepted, TimeExceeded, WrongAnswer")
        return

    message.reply(f"正在查询今日 {verdict} 榜单，请稍等")

    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = _call_lib_method(message,
                           f'--now --separate_cols --verdict "{verdict}" '
                           f'--output "{cached_prefix}.png"', conf_id=conf_id)
    if run is None:
        return

    message.reply(f"今日 {verdict} 榜单", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['今日题数', 'today'])
def send_today_board(message: RobotMessage):
    conf_id = message.tokens[1] if len(message.tokens) >= 2 else None
    message.reply("正在查询今日题数，请稍等")

    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = _call_lib_method(message,
                           f'--now --separate_cols --output "{cached_prefix}.png"',
                           conf_id=conf_id)
    if run is None:
        return

    message.reply("今日题数", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['昨日总榜', 'yesterday', 'full'])
def send_yesterday_board(message: RobotMessage):
    conf_id = message.tokens[1] if len(message.tokens) >= 2 else None
    message.reply("正在查询昨日总榜，请稍等")

    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = _call_lib_method(message,
                           f'--full --separate_cols --output "{cached_prefix}.png"',
                           conf_id=conf_id)
    if run is None:
        return

    message.reply("昨日卷王天梯榜", png2jpg(f"{cached_prefix}.png"))


def get_version_info() -> str:
    cached_prefix = get_cached_prefix('Peeper-Board-Generator')
    run = _call_lib_method(None,  # 留空选择默认
                           f'--version --output "{cached_prefix}.txt"', no_id=True)
    if run is None:
        return "Unknown"

    with (open(f"{cached_prefix}.txt", "r", encoding="utf-8") as f):
        result = f.read()
        version = result.split(' ', 1)
        if len(version) != 2:
            raise ModuleRuntimeError(f"Invalid version: {result}")
        return version[1]


@command(tokens=['user'])
def send_oj_user(message: RobotMessage):
    content = message.tokens
    if len(content) < 3:
        message.reply("请输入三个参数，第三个参数前要加空格，比如说\"/user id 1\"，\"/user name Hydro\"")
        return
    if len(content) > 3:
        message.reply("请输入三个参数，第三个参数不要加上空格")
        return
    if content[1] == "id" and (len(content[2]) > 9 or not check_is_int(content[2])):
        message.reply("参数错误，id必须为整数")
        return
    if content[1] == "id" or content[1] == "name":
        target = clean_unsafe_shell_str(content[2])  # 修复注入攻击
        if target:
            _send_user_info(message, target, by_name=(content[1] == "name"))
            return

    message.reply("请输入正确的参数，如\"/user id ...\", \"/user name ...\"")


@module(
    name="Peeper-Board-Generator",
    version=get_version_info
)
def register_module():
    pass
