import logging
from dataclasses import dataclass
from typing import Callable

from src.core.bot.message import MessageType
from src.core.bot.perm import PermissionLevel

__commands_primary__: dict[str, dict[str, str]] = {}
__commands__: dict[str, dict[str, tuple[Callable, PermissionLevel, bool, bool]]] = {}
__modules__: dict[str, str | Callable[[], str]] = {}


@dataclass(frozen=True)
class ScheduledJobInfo:
    """定时主动消息任务的元数据"""
    func: Callable
    cron: str                       # 标准5段cron表达式，如 "0 9 * * *"
    message_type: MessageType       # GUILD / DIRECT / GROUP / C2C
    target: str                     # 目标标识符 (channel_id / guild_id / group_openid / openid)
    module_name: str


__scheduled_jobs__: dict[str, list[ScheduledJobInfo]] = {}


def command(tokens: list, permission_level: PermissionLevel = PermissionLevel.USER,
            is_command: bool = True, multi_thread: bool = False):
    """
        创建一条命令。

        :param tokens: 指令的调用名
        :param permission_level: 执行需要的权限等级，默认为USER，代表用户都可执行，MOD为内容审核用户，ADMIN为管理员
        :param is_command: 代表该条指令需不需要前置 "/"
        :param multi_thread: 同一文件下注册的函数是否只有一个工作线程，若为多线程则同文件同上下文（如同一群组）只有一个工作线程

        multi_thread为真时，线程生命周期最多一小时
    """

    def decorator(func):
        if not tokens:
            raise ValueError(f'Function {func.__name__} requires tokens')

        module_name = func.__module__ or "default.unknown"  # 根据函数注册的位置分类处理

        __commands__.setdefault(module_name, {})
        __commands_primary__.setdefault(module_name, {})
        primary_token_name = (f'/{tokens[0]}' if is_command else f'{tokens[0]}').lower()
        __commands_primary__[module_name][primary_token_name] = func.__name__  # 记录第一个 token 对应的方法

        for token in tokens:
            token_name = (f'/{token}' if is_command else f'{token}').lower()  # 忽略大小写直接匹配
            __commands__[module_name][token_name] = (
                func, permission_level, is_command, multi_thread)
        return func

    return decorator


def module(name: str,
           version: str | Callable[[], str]):
    """
        注册一个模块。

        :param name: 模块名
        :param version: 模块版本号，可以为返回版本号的函数
    """

    def decorator(func):
        __modules__[name] = version
        return func

    logging.getLogger("entry").debug(f'[obot-init] 载入模块 {name} '
                                     f'{version if isinstance(version, str) else "v_dynamic"}')

    return decorator


def _parse_uuid(uuid: str) -> tuple[MessageType, str]:
    """从 uuid 解析消息类型和目标 ID，uuid 格式为 {prefix}_{id}"""
    uuid_prefix_map = {
        "guild_": MessageType.GUILD,
        "direct_": MessageType.DIRECT,
        "group_": MessageType.GROUP,
        "c2c_": MessageType.C2C,
    }
    for prefix, msg_type in uuid_prefix_map.items():
        if uuid.startswith(prefix):
            return msg_type, uuid[len(prefix):]
    raise ValueError(f"Invalid uuid: {uuid!r}, "
                     f"must start with guild_/direct_/group_/c2c_")


def scheduled(cron: str, targets: list[str]):
    """
        注册一条定时主动消息任务。

        :param cron: 标准5段cron表达式，如 "0 9 * * *" (分 时 日 月 周)
        :param targets: 目标 uuid 列表，格式为 {prefix}_{id}
                        可通过 /chat_scene_id 获取：
                        guild_{channel_id}   -> 频道消息
                        direct_{guild_id}    -> 频道私信
                        group_{group_openid} -> 群聊消息
                        c2c_{openid}         -> 私聊消息
    """

    def decorator(func):
        if not targets:
            raise ValueError(f'Function {func.__name__} requires at least one target')

        module_name = func.__module__ or "default.unknown"

        __scheduled_jobs__.setdefault(module_name, [])
        for uuid in targets:
            message_type, target_id = _parse_uuid(uuid)
            __scheduled_jobs__[module_name].append(
                ScheduledJobInfo(func=func, cron=cron, message_type=message_type,
                                 target=target_id, module_name=module_name))
        return func

    return decorator


def get_command_count() -> int:
    """获取当前注册的主指令数量 (不包括别名)"""
    return sum(len(module_commands) for module_commands in __commands_primary__.values())


def get_command_alias_count() -> int:
    """获取当前注册的指令别名总数"""
    return (sum(len(module_commands) for module_commands in __commands__.values()) -
            get_command_count())


def get_module_count() -> int:
    """获取当前注册的模块总数"""
    return len(__modules__)


def get_all_modules_info() -> list[tuple[str, str]]:
    """获取当前注册的模块信息"""
    all_modules_info = []
    for name, version in __modules__.items():
        if isinstance(version, Callable):
            version = version()
        all_modules_info.append((name, version))

    all_modules_info.sort()
    return all_modules_info


def get_scheduled_job_count() -> int:
    """获取当前注册的定时任务总数"""
    return sum(len(jobs) for jobs in __scheduled_jobs__.values())


def get_scheduled_jobs_info() -> list[tuple[str, str, str, str]]:
    """获取所有已注册定时任务信息: [(module, func_name, cron, target), ...]"""
    result = []
    for module_name, jobs in __scheduled_jobs__.items():
        for job in jobs:
            result.append((module_name, job.func.__name__, job.cron, job.target))
    return sorted(result)
