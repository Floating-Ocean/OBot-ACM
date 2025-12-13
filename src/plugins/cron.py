from datetime import datetime
import os

from nonebot import on_command,get_bot,require
from nonebot.rule import to_me
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11.event import MessageEvent,GroupMessageEvent
from nonebot.params import Command,CommandArg
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.exception import MatcherException

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_localstore")
from nonebot_plugin_apscheduler import scheduler
from apscheduler.triggers.date import DateTrigger
import nonebot_plugin_localstore as store
from nonebot_plugin_saa import TargetQQGroup,TargetQQPrivate,MessageFactory,AggregatedMessageFactory


from src.core.tools import format_timestamp_diff
from src.core.constants import Constants
from src.core.help_registry import with_help
from src.platform.cp.codeforces import Codeforces
from src.platform.cp.atcoder import AtCoder
from src.platform.cp.nowcoder import NowCoder
from src.platform.model import CompetitivePlatform,Contest
from src.core.tools import reply_help

__cron_version__ = "v1.0.0"

# 插件基本变量初始化
data_dir = store.get_plugin_data_dir()
scheduler.add_jobstore("sqlalchemy",alias="default",url=f"sqlite:///{os.path.join(data_dir,'jobs.sqlite')}")
regular_handler = on_command(
    ('schedule','help'),rule=to_me(),
    aliases={('schedule','add')},
    priority=Constants.CRON_PRIOR)

admin_handler = on_command(
    ('schedule','admin'),rule=to_me(),
    aliases={('schedule','all'),('schedule','removeall'),('schedule','addto')},
    priority=Constants.CRON_PRIOR,permission=SUPERUSER
)

help_trigger = on_command(
    'schedule',
    rule=to_me(),
    priority=Constants.HELP_PRIOR
)



# cron - heartbeat: 定时任务，不受其他模块干扰。每天 0点，6点，12点，18点 向 Bot 的主人发送四次心跳消息。
# 如果需要取消，直接将本函数注释即可。
@scheduler.scheduled_job("cron",hour=6,id="job_ping_6",kwargs={'content':"ping",'id':Constants.bot_owner})
@scheduler.scheduled_job("cron",hour=12,id="job_ping_12",kwargs={'content':"pong",'id':Constants.bot_owner})
@scheduler.scheduled_job("cron",hour=18,id="job_ping_18",kwargs={'content':"pingping",'id':Constants.bot_owner})
@scheduler.scheduled_job("cron",hour=0,id="job_ping_0",kwargs={'content':"pongpong",'id':Constants.bot_owner})
async def heart_beat(content,id):
    logger.info("[CP-Helper] 正在向 Bot 主人发送心跳信息。")
    await MessageFactory(content).send_to(target=TargetQQPrivate(user_id=id),bot=get_bot())


async def add_contest_schedule(platform:str,contestId:str,id:int,isGroup:bool):
    await MessageFactory("[cron] 开始添加定时任务").send()
    platforms = {
        'codeforces':Codeforces,
        'atcoder':AtCoder,
        'nowcoder':NowCoder
    }
    if platform not in platforms.keys():
        await MessageFactory(f"平台有误，目前支持的平台为 Codeforces,Atcoder,Nowcoder").finish()
    platform : CompetitivePlatform = platforms[platform]
    contest : Contest = platform.get_contest(contestId)
    for job in scheduler.get_jobs():
        if job.kwargs['id'] == id and job.kwargs['content'] == f'比赛 {contest.name} 将于 1 天后开始，请注意安排时间~':
            await MessageFactory(f"本场比赛 {contest.name} 对于 {id} 的提醒已经在机器人 schedule 中。").finish()
    scheduler.add_job(notice_contest,"date",run_date=datetime.now(),kwargs={'content':f'比赛 {contest.name} 的定时器已添加。','id':id,'isGroup':isGroup})
    scheduler.add_job(notice_contest,"date",run_date=datetime.fromtimestamp(contest.start_time-86400),kwargs={'content':f'比赛 {contest.name} 将于 1 天后开始，请注意安排时间~','id':id,'isGroup':isGroup})
    scheduler.add_job(notice_contest,"date",run_date=datetime.fromtimestamp(contest.start_time-7200),kwargs={'content':f'比赛 {contest.name} 将于 2 小时后开始，请注意安排时间~','id':id,'isGroup':isGroup})
    scheduler.add_job(notice_contest,"date",run_date=datetime.fromtimestamp(contest.start_time-600),kwargs={'content':f'比赛 {contest.name} 将于 5 分钟后开始，该上号了！','id':id,'isGroup':isGroup})

# cron - notice_contest: /schedule add [platform] [contestId] 的任务执行函数。所有参数来自 /schedule add 传入
# content: 自动生成的提醒文本
# id: 需要提醒的QQ号
# isGroup: QQ号是个人号还是群号
async def notice_contest(content:str,id:int,isGroup):
    if isGroup:
        target=TargetQQGroup(group_id=id)
        await MessageFactory(content).send_to(target=target,bot=get_bot())
    else:
        target = TargetQQPrivate(user_id=id)
        await MessageFactory(content).send_to(target=target,bot=get_bot())

@help_trigger.handle()
async def handle_help():
    await reply_help("cron / 定时模块")

@regular_handler.handle()
@with_help("cron / 定时模块")
async def handle_regular(event:MessageEvent,command:tuple[str,str]=Command(),message:Message = CommandArg()):
    """
    /schedule add [platform] [contestId]: 将比赛 [contestId] 加入调用指令的私聊/群聊提醒列表中。
    """
    try:
        func = command[1]
        args = message.extract_plain_text().split()
        if func == 'add':
            if len(args) != 2:
                await reply_help("cron / 定时模块","输入参数数量不正确，请参照说明重新输入",False)
            platform,contestId = args
            if isinstance(event,GroupMessageEvent):
                await add_contest_schedule(platform,contestId,event.group_id,True)
            else:
                await add_contest_schedule(platform,contestId,event.user_id,True)
    except MatcherException:
        raise
    except Exception as e:
        await reply_help("cron / 定时模块","出现未知异常。请联系管理员。",False)
        
    
@admin_handler.handle()
@with_help("cron / 定时模块", is_admin=True)
async def handle_admin(command:tuple[str,str]=Command(),message:Message = CommandArg()):
    """
    /schedule addto [platform] [contestId] [boardcastTo]: 将比赛 [contestId] 加入[boardcastTo]群聊提醒列表中。
    /schedule all: 返回当前所有的 shedule 任务
    /schedule removeall 删除当前所有的固定时间提醒任务。
    """
    try:
        func = command[1]
        args = message.extract_plain_text().split()
        if func == 'all':
            await AggregatedMessageFactory(MessageFactory("\n".join([f"计划在 {format_timestamp_diff(datetime.now().timestamp()-job.next_run_time.timestamp())} - 发给 {job.kwargs['id']} - {job.kwargs['content']}" for job in scheduler.get_jobs()]))).finish()
        elif func == 'removeall':
            for job in scheduler.get_jobs():
                if isinstance(job.trigger,DateTrigger):
                    job.remove()
            await MessageFactory("全部 schedule 已被清除。").finish()
        elif func == 'addto':
            if len(args) != 3:
                await reply_help("cron / 定时模块","输入参数数量不正确，请参照说明重新输入",True)
            platform,contestId,groupId = args
            await add_contest_schedule(platform,contestId,int(groupId),True)
            await MessageFactory("已成功执行指令").finish()
        else:
            await reply_help("cron / 定时模块","",True)
    except MatcherException:
        raise
    except Exception as e:
        await reply_help("cron / 定时模块","出现未知异常。请联系管理员。",True)

