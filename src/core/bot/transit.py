import datetime
import queue
import threading
import time
import traceback
from dataclasses import dataclass

from src.core.bot.command import __commands__
from src.core.bot.interact import reply_key_words, no_reply
from src.core.bot.message import RobotMessage, MessageType
from src.core.constants import Constants
from src.core.util.exception import UnauthorizedError


_query_queue: dict[str, queue.Queue] = {}
_count_queue: dict[str, queue.Queue] = {}
_work_thread_life: dict[str, int] = {"default.manual": -1}
_terminate_lock = threading.Lock()
_terminate_signal = False

_MAINTAINING_SIGNAL = False


@dataclass(frozen=True)
class MessageID:
    """
    消息的身份，包含所属模块，命令名，和是否多线程
    """
    module: str
    command: str
    multi_thread: bool = False


def get_message_id(message: RobotMessage) -> MessageID:
    """
    获取消息的身份
    """
    try:
        content = message.tokens

        if len(content) == 0 and not message.is_guild_public():
            return MessageID("default.manual", "reply_key_words_empty")

        func = content[0].lower()
        for module in __commands__:
            module_commands = __commands__[module]
            for cmd in module_commands:
                starts_with = cmd[-1] == '*' and func.startswith(cmd[:-1])
                if starts_with or cmd == func:
                    original_command, _, is_command, _, multi_thread = module_commands[cmd]

                    if not is_command and message.is_guild_public():
                        # 对频道无at消息的过滤，避免spam
                        continue

                    if multi_thread:
                        # 多线程时，同一上下文一个线程
                        worker_id = f"{module}_{message.uuid}"
                        _work_thread_life[worker_id] = 60 * 60  # 一小时生命周期
                        return MessageID(module, cmd, True)

                    _work_thread_life[module] = -1
                    return MessageID(module, cmd)

        # 如果是频道无at消息可能是发错了或者并非用户希望的处理对象
        if message.is_guild_public():
            return MessageID("default.manual", "no_reply")

        if '/' in func:
            return MessageID("default.manual", "reply_not_implemented")
        else:
            return MessageID("default.manual", "reply_key_words_func")

    except Exception as e:
        message.report_exception('Core.Transit', traceback.format_exc(), e)
        return MessageID("default.manual", "no_reply")


def distribute_message(message: RobotMessage):
    """
    分发消息
    """
    if _MAINTAINING_SIGNAL:
        message.reply("O宝维护中，晚点再来吧\n\n"
                      f"OBot's ACM {Constants.core_version}\n"
                      f"{datetime.datetime.now()}\n", modal_words=False)
        return

    message_id = get_message_id(message)
    worker_id = message_id.module
    if message_id.multi_thread:
        worker_id = f"{message_id.module}_{message.uuid}"

    if (worker_id not in _count_queue
            or worker_id not in _query_queue):
        _count_queue[worker_id] = queue.Queue()
        _query_queue[worker_id] = queue.Queue()

        # 启动对应工作线程
        threading.Thread(target=queue_up_handler,
                         args=[worker_id],
                         name=f"Work Thread ({worker_id})").start()

    _count_queue[worker_id].put(1)
    size = _count_queue[worker_id].qsize()
    if size > 1:
        message.reply(f"已加入处理队列，前方还有 {size - 1} 个请求")
    _query_queue[worker_id].put((message, message_id))


def handle_message(message: RobotMessage, message_id: MessageID):
    """
    处理消息
    """
    try:
        fixed_handlers = {
            None: (no_reply, {}),
            MessageID("default.manual", "no_reply"): (no_reply, {}),
            MessageID("default.manual", "reply_not_implemented"): (
                message.reply,
                {"content": "其他指令还在开发中"}
            ),
            MessageID("default.manual", "reply_key_words_empty"): (
                reply_key_words,
                {"message": message, "content": ""}
            ),
            MessageID("default.manual", "reply_key_words_func"): (
                reply_key_words,
                {"message": message, "content": "" if len(message.tokens) == 0 else message.tokens[0].lower()}
            ),
        }

        if message_id in fixed_handlers:
            handler_func, handler_kwargs = fixed_handlers[message_id]
            handler_func(**handler_kwargs)
            return None

        func = message.tokens[0].lower()

        (original_command, execute_level,
         is_command, need_to_check_exclude, _) = __commands__[message_id.module][message_id.command]

        if message.user_permission_level < execute_level:
            Constants.log.info(f'{message.author_id} attempted to call {message_id.command} but failed.')
            raise UnauthorizedError("权限不足，操作被拒绝" if func != "/去死" else "阿米诺斯")

        if need_to_check_exclude and (message.message_type == MessageType.GROUP and
                                      message.message.group_openid in Constants.config['exclude_group_id']):
            Constants.log.info(
                f'{message.message.group_openid} was banned to call {message_id.command}.')
            raise UnauthorizedError("榜单功能被禁用")

        try:
            starts_with = message_id.command[-1] == '*' and func.startswith(message_id.command[:-1])
            if starts_with:
                name = message_id.command[:-1]
                replaced = func.replace(name, '')
                message.tokens = [name] + ([replaced] if replaced else []) + message.tokens[1:]
            original_command(message)
        except Exception as e:
            message.report_exception(f'{message_id.module}.{message_id.command}',
                                     traceback.format_exc(), e)
        return None

    except Exception as e:
        message.report_exception('Core.Transit', traceback.format_exc(), e)
        return None


def clear_message_queue():
    global _terminate_signal
    with _terminate_lock:
        _terminate_signal = True
    for module, module_query_queue in _query_queue.items():
        while not module_query_queue.empty():
            try:
                queued_message: tuple[RobotMessage, MessageID] = (module_query_queue.get_nowait())
                message, message_id = queued_message
            except queue.Empty:
                break
            message.reply("O宝被爆了！等待一段时间后再试试")


def queue_up_handler(worker_id: str):
    Constants.log.info(f'Work thread {worker_id} started.')

    life = _work_thread_life[worker_id]
    terminate_time = time.time() + life if life >= 0 else -1

    global _terminate_signal

    while True:
        if terminate_time != -1 and time.time() >= terminate_time:
            # 生命周期时间到的自动退出
            break

        with _terminate_lock:
            is_terminate = _terminate_signal
        if is_terminate:
            # 机器人重启时的强制退出
            break

        try:
            queued_message: tuple[RobotMessage, MessageID] = _query_queue[worker_id].get(timeout=1)  # 这里需要timeout，不然会一直阻塞
            message, message_id = queued_message

            handle_message(message, message_id)
            _count_queue[worker_id].get()
        except queue.Empty:
            pass

    del _count_queue[worker_id]
    del _query_queue[worker_id]
    Constants.log.info(f'Work thread {worker_id} terminated.')
