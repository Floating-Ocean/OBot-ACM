import logging
from typing import Callable

__modules__ = {}



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


def get_command_count() -> int:
    """获取当前注册的指令总数"""
    return sum(len(module_commands) for module_commands in __commands__.values())


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
