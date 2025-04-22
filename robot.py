import os
import queue
import re
import sys
import threading
import time
from typing import Union, List

import botpy
from apscheduler.schedulers.blocking import BlockingScheduler
from botpy import Client, Intents
from botpy.message import Message, GroupMessage, C2CMessage

from src.core.bot.command import command, PermissionLevel
from src.core.constants import Constants
from src.core.bot.interact import RobotMessage, call_handle_message
from src.module.peeper import daily_update_job, noon_report_job

_query_queue = queue.Queue()
_count_queue = queue.Queue()
_terminate_lock = threading.Lock()
_terminate_signal = False

daily_sched = BlockingScheduler()
noon_sched = BlockingScheduler()


def daily_sched_thread():
    daily_sched.add_job(daily_update_job, "cron", hour=0, minute=0, args=[])
    daily_sched.start()


def noon_sched_thread(client: Client):
    noon_sched.add_job(noon_report_job, "cron", hour=13, minute=0, args=[client])
    noon_sched.start()


@command(tokens=["去死", "重启", "restart", "reboot"], permission_level=PermissionLevel.ADMIN)
def reply_restart_bot(message: RobotMessage):
    message.reply("好的捏，捏？欸我怎么似了" if message.tokens[0] == '/去死' else "好的捏，正在重启bot")
    Constants.log.info("Clearing message queue...")
    clear_message_queue()
    time.sleep(2)  # 等待 message 通知消息线程发送回复
    Constants.log.info("Restarting bot...")
    os.execl(sys.executable, sys.executable, *sys.argv)


def clear_message_queue():
    global _terminate_signal
    with _terminate_lock:
        _terminate_signal = True
    while not _query_queue.empty():
        try:
            message: RobotMessage = _query_queue.get_nowait()
        except queue.Empty:
            break
        message.reply("O宝被爆了！等待一段时间后再试试")


def queue_up_handler():
    global _terminate_signal
    while True:
        with _terminate_lock:
            is_terminate = _terminate_signal
        if is_terminate:
            break
        message: RobotMessage = _query_queue.get()
        call_handle_message(message)
        _count_queue.get()


def join_in_message(message: RobotMessage):
    _count_queue.put(1)
    size = _count_queue.qsize()
    if size > 1:
        message.reply(f"已加入处理队列，前方还有 {size - 1} 个请求")
    _query_queue.put(message)


class MyClient(Client):
    def __init__(self, intents: Intents, timeout: int = 5, is_sandbox=False,
                 log_config: Union[str, dict] = None, log_format: str = None, log_level: int = None,
                 bot_log: Union[bool, None] = True, ext_handlers: Union[dict, List[dict], bool] = True):
        super().__init__(intents, timeout, is_sandbox, log_config, log_format, log_level, bot_log, ext_handlers)

    async def on_ready(self):
        Constants.log.info(f"robot 「{self.robot.name}」 on_ready!")

    async def on_at_message_create(self, message: Message):
        Constants.log.info(
            f"{self.robot.name} receive public message {message.content} {message.attachments} "
            f"from {message.channel_id}")
        packed_message = RobotMessage(self.api)
        packed_message.setup_guild_message(self.loop, message)
        join_in_message(packed_message)

    async def on_message_create(self, message: Message):
        Constants.log.info(
            f"{self.robot.name} receive global message {message.content} {message.attachments} "
            f"from {message.channel_id}")
        content = message.content

        packed_message = RobotMessage(self.api)
        packed_message.setup_guild_message(self.loop, message, is_public=True)

        if not re.search(r'<@!\d+>', content):
            join_in_message(packed_message)

    async def on_group_at_message_create(self, message: GroupMessage):
        Constants.log.info(
            f"{self.robot.name} receive group message {message.content} {message.attachments} "
            f"from {message.group_openid}")
        packed_message = RobotMessage(self.api)
        packed_message.setup_group_message(self.loop, message)
        join_in_message(packed_message)

    async def on_c2c_message_create(self, message: C2CMessage):
        Constants.log.info(
            f"{self.robot.name} receive private message {message.content} {message.attachments} "
            f"from {message.author.user_openid}")
        packed_message = RobotMessage(self.api)
        packed_message.setup_c2c_message(self.loop, message)
        join_in_message(packed_message)


def check_path_in_config():
    for path in ["lib_path", "output_path"]:
        if not os.path.isdir(Constants.config[path]):
            raise FileNotFoundError(Constants.config[path])


def open_robot_session():
    # 检查配置文件中的目录是否合法，防止错误配置和命令意外执行
    check_path_in_config()

    threading.Thread(target=queue_up_handler, args=[]).start()

    intents = botpy.Intents.default()  # 对目前已支持的所有事件进行监听
    client = MyClient(intents=intents, timeout=60)

    # 更新每日排行榜
    threading.Thread(target=daily_sched_thread, args=[]).start()
    
    # 午间推送机制
    threading.Thread(target=noon_sched_thread, args=[client]).start()

    client.run(appid=Constants.config["appid"], secret=Constants.config["secret"])
