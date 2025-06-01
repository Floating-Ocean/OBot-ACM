import os
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
from src.core.bot.interact import RobotMessage
from src.core.bot.transit import clear_message_queue, distribute_message
from src.core.constants import Constants
from src.module.peeper import daily_update_job, noon_report_job

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
    Constants.log.info("[obot] 正在清空消息队列")
    clear_message_queue()
    time.sleep(2)  # 等待 message 通知消息线程发送回复
    Constants.log.info("[obot] 正在重启")
    os.execl(sys.executable, sys.executable, *sys.argv)


class MyClient(Client):
    def __init__(self, intents: Intents, timeout: int = 5, is_sandbox=False,
                 log_config: Union[str, dict] = None, log_format: str = None, log_level: int = None,
                 bot_log: Union[bool, None] = True, ext_handlers: Union[dict, List[dict], bool] = True):
        super().__init__(intents, timeout, is_sandbox, log_config, log_format, log_level, bot_log, ext_handlers)

    async def on_ready(self):
        Constants.log.info(f"[obot] 机器人上线，版本 {Constants.core_version}.")

    async def on_at_message_create(self, message: Message):
        attachment_info = (f" | {message.attachments}"
                           if len(message.attachments) > 0 else "")
        Constants.log.info(f"[obot] 在频道 {message.channel_id} "
                           f"收到@消息: {message.content}"
                           f"{attachment_info}")
        packed_message = RobotMessage(self.api)
        packed_message.setup_guild_message(self.loop, message)
        distribute_message(packed_message)

    async def on_message_create(self, message: Message):
        attachment_info = (f" | {message.attachments}"
                           if len(message.attachments) > 0 else "")
        Constants.log.info(f"[obot] 在频道 {message.channel_id} "
                           f"收到公共消息: {message.content}"
                           f"{attachment_info}")
        content = message.content

        packed_message = RobotMessage(self.api)
        packed_message.setup_guild_message(self.loop, message, is_public=True)

        if not re.search(r'<@!\d+>', content):
            distribute_message(packed_message)

    async def on_group_at_message_create(self, message: GroupMessage):
        attachment_info = (f" | {message.attachments}"
                           if len(message.attachments) > 0 else "")
        Constants.log.info(f"[obot] 在群聊 {message.group_openid} "
                           f"收到消息: {message.content}"
                           f"{attachment_info}")
        packed_message = RobotMessage(self.api)
        packed_message.setup_group_message(self.loop, message)
        distribute_message(packed_message)

    async def on_c2c_message_create(self, message: C2CMessage):
        attachment_info = (f" | {message.attachments}"
                           if len(message.attachments) > 0 else "")
        Constants.log.info(f"[obot] 在用户 {message.author.user_openid} "
                           f"收到私聊消息: {message.content}"
                           f"{attachment_info}")
        packed_message = RobotMessage(self.api)
        packed_message.setup_c2c_message(self.loop, message)
        distribute_message(packed_message)


def check_path_in_config():
    for path in ["lib_path", "output_path"]:
        if not os.path.isdir(Constants.config[path]):
            raise FileNotFoundError(Constants.config[path])


def open_robot_session():
    # 检查配置文件中的目录是否合法，防止错误配置和命令意外执行
    check_path_in_config()

    intents = botpy.Intents.default()  # 对目前已支持的所有事件进行监听
    client = MyClient(intents=intents, timeout=60)

    # 更新每日排行榜
    threading.Thread(target=daily_sched_thread, args=[]).start()
    
    # 午间推送机制
    threading.Thread(target=noon_sched_thread, args=[client]).start()

    client.run(appid=Constants.config["appid"], secret=Constants.config["secret"])
