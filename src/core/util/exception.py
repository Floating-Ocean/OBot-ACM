from aiohttp import ClientError
from botpy.errors import ServerError


class UnauthorizedError(PermissionError):
    """ Not enough permissions. """

    def __init__(self, *args):
        super().__init__(*args)


class ModuleRuntimeError(OSError):
    """ Module runtime errors. """

    def __init__(self, *args):
        super().__init__(*args)


exception_handle_rules = {
    (TimeoutError, ConnectionError, ClientError, ServerError): {
        'detail': False,
        'message': '网络不稳定，请稍后重试'
    },
    UnauthorizedError: {
        'detail': True,
        'message': '访问受限，请联系管理员'
    }
}


def handle_exception(e: Exception):
    error_reply = "出现未知异常，请联系管理员"

    for error_type, config in exception_handle_rules.items():
        if isinstance(e, error_type):
            error_reply = config['message']
            if config['detail']:
                error_reply += "\n\n" + repr(e)

    return error_reply
