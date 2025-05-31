from src.core.bot.perm import PermissionLevel

__commands__ = {}


def command(tokens: list, permission_level: PermissionLevel = PermissionLevel.USER,
            is_command: bool = True, need_check_exclude: bool = False):
    """
        创建一条命令。

        :param tokens: 指令的调用名
        :param permission_level: 执行需要的权限等级，默认为USER，代表用户都可执行，MOD为内容审核用户，ADMIN为管理员
        :param is_command: 代表该条指令需不需要前置 "/"
        :param need_check_exclude: 代表该条指令是否需要检查群号白名单
    """

    if tokens is None:
        tokens = []

    def decorator(func):
        module_name = func.__module__  # 根据函数注册的位置分类处理
        if module_name not in __commands__:
            __commands__[module_name] = {}

        for token in tokens:
            token_name = f'/{token}' if is_command else f'{token}'
            __commands__[module_name][token_name] = (
                func, permission_level, is_command, need_check_exclude)
        return func

    return decorator
