from aiohttp import ClientError

try:
    from nonebot.adapters.onebot.v11.exception import ActionFailed
    _has_nonebot_errors = True
except ImportError:
    _has_nonebot_errors = False


class UnauthorizedError(PermissionError):
    """ Not enough permissions. """

    def __init__(self, *args):
        super().__init__(*args)


class ModuleRuntimeError(OSError):
    """ Module runtime errors. """

    def __init__(self, *args):
        super().__init__(*args)


exception_handle_rules = {
    (TimeoutError, ConnectionError, ClientError): {
        'detail': False,
        'message': '网络不稳定，请稍后重试'
    },
    UnauthorizedError: {
        'detail': True,
        'message': '访问受限，请联系管理员'
    }
}

if _has_nonebot_errors:
    exception_handle_rules[ActionFailed] = {
        'detail': False,
        'message': '操作失败，请稍后重试'
    }


def handle_exception(e: Exception):
    error_reply = "出现未知异常，请联系管理员"

    current_exception = e
    while current_exception is not None:
        for error_type, config in exception_handle_rules.items():
            if isinstance(current_exception, error_type):
                error_reply = config['message']
                if config['detail']:
                    error_reply += "\n\n" + repr(current_exception)
                return error_reply  # 找到第一个匹配就返回

        current_exception = getattr(current_exception, '__cause__', None)

    # 没有找到匹配的异常
    return error_reply

