__modules__ = {}

from typing import Callable


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

    return decorator


def get_all_modules_info() -> list[tuple[str, str]]:
    all_modules_info = []
    for name, version in __modules__.items():
        if isinstance(version, Callable):
            version = version()
        all_modules_info.append((name, version))

    all_modules_info.sort()
    return all_modules_info
