import os

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OnebotAdapter
from nonebot import require
from nonebot_plugin_saa import MessageFactory, TargetQQPrivate

from src.core.bot.decorator import module
from src.core.constants import Constants

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_localstore")
from nonebot_plugin_apscheduler import scheduler
import nonebot_plugin_localstore as store
require("src.module.cp.peeper")
from src.module.cp.peeper import daily_update_job

_version = "1.0.0"

data_dir = store.get_plugin_data_dir()
scheduler.add_jobstore("sqlalchemy",alias="default",url=f"sqlite:///{os.path.join(data_dir,'jobs.sqlite')}")

@scheduler.scheduled_job("cron", id="peeper_daily_update", hour=0, minute=0, second=1)
async def peeper_daily_update():
    await daily_update_job()
@scheduler.scheduled_job("cron",hour=6,id="job_ping_6",kwargs={'content':"ping",'id':Constants.role_conf['heartbeat_id']})
@scheduler.scheduled_job("cron",hour=12,id="job_ping_12",kwargs={'content':"pong",'id':Constants.role_conf['heartbeat_id']})
@scheduler.scheduled_job("cron",hour=18,id="job_ping_18",kwargs={'content':"pingping",'id':Constants.role_conf['heartbeat_id']})
@scheduler.scheduled_job("cron",hour=0,id="job_ping_0",kwargs={'content':"pongpong",'id':Constants.role_conf['heartbeat_id']})
async def heart_beat(content,id):
    for bot_name in nonebot.get_adapter(OnebotAdapter).bots:
        bot = nonebot.get_bots().get(bot_name)
        if bot is not None:
            Constants.log.info(f"[obot-heartbeat] Onebot 主人 {id} 的 Bot {bot.self_id} 正在发送心跳信息。")
            await MessageFactory(content).send_to(target=TargetQQPrivate(user_id=id),bot=bot)
            return

@module(
    name="Cron",
    version=_version
)
def register_module():
    pass