from nonebot import get_loaded_plugins, on_command

from nonebot.adapters import Message
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg,Command

from pathlib import Path
import json
from nonebot.log import logger
import nonebot_plugin_localstore as store
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.exception import MatcherException
from src.core.help_registry import with_help
from src.core.bot.message import reply, report_exception
data_dir = store.get_data_dir("cubplugins")

def initdata(conf_name,bashdata:dict | list={"status":1}):
    conf_path = Path(data_dir / conf_name).absolute()
    config_init(conf_path,conf_name,"plugin_data",bashdata)
    return True

def rdata(conf_name):
    conf_path = Path(data_dir / conf_name).absolute()
    with open(conf_path, "r", encoding="utf-8") as f:
        data = json.loads(f.read())
    return data

def wdata(conf_name:str,data:dict):
    conf_path = Path(data_dir / conf_name).absolute()
    with open(conf_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=4,ensure_ascii=False))
    return True

def config_init(_path_ ,conf_name:str ,module_name:str="None" ,data:dict | list ={"status":1}):
    if _path_.is_file():
        logger.opt(colors=True).debug(f"[cubutil]>>><W>{module_name}</>>>>{conf_name}-OK!")
    else:
        logger.opt(colors=True).debug(f"[cubutil]>>><W>{module_name}</>>>>Create-{conf_name}!")
        with open(_path_, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=4 ,ensure_ascii=False))
            f.close()

conf_name="cubplugins_permission.json"
bashdata={'global':[],'group-global':[]}
initdata(conf_name,bashdata)


class cubplugins_permission:
    cubplugins_P = rdata(conf_name)

    def __init__(self):
        pass
    
    def savedata(self):
        '''保存数据至本地文件
        '''
        wdata(conf_name,self.cubplugins_P)
    
    def checkperm(self , modulename:str , user_id:str ):
        '''
        检查对用户是否阻断响应 True 阻断 False 响应
        
        返回  是否阻断bool  阻断模式 ["allow","black","white"]
        '''
        globaldata = self.cubplugins_P.get('global',[])
        #白名单检查，优先级最高
        if user_id in self.cubplugins_P.get("!-"+modulename,[]):
            return False , "white"
        #全局拉黑检查
        if user_id in globaldata:
            return True , "black"
        #插件响应检查
        data = self.cubplugins_P.get(modulename,[])
        if user_id in data or '0' in data:
            return True , "black"
        return False , "allow"
    
    def checkpermgroup(self , modulename:str , group_id:str ):
        '''
        检查对群组是否阻断响应 True 阻断 False 响应
        
        返回  是否阻断bool  阻断模式 ["allow","black","white"]
        '''
        groupdata = self.cubplugins_P.get('group-global',[])
        #白名单检查，优先级最高
        if group_id in self.cubplugins_P.get("!-group-"+modulename,[]):
            return False , "white"
        #全局拉黑检查
        if group_id in groupdata:
            return True , "black"
        #插件响应检查
        data = self.cubplugins_P.get('group-'+modulename,[])
        if group_id in data:
            return True , "black"
        return False , "allow"
    
    def setperm(self , modulename:str , user_id:str , allow : bool =False):
        '''
        设定权限
        modulename : 插件名称 (组模式则为group-xxx)(白名单为!-xxx/!-group-xxx)
        user_id : 用户id (组模式传入组ID)
        allow : 是否允许响应 (False将id加入名单列表,True为删除id)
        '''
        if self.cubplugins_P.get(modulename,None) == None:
            self.cubplugins_P[modulename] =[]
        data = self.cubplugins_P[modulename]
        check = False
        if allow:
            if user_id in data:
                data.remove(user_id)
                check = True
        else:
            if user_id not in data:
                data.append(user_id)
                check = True
        if check:
            self.savedata()
        return check

cubp = cubplugins_permission()

#/manage ban-plug entertainment uxxxxxx / gxxxxxx
ban_plug_handler = on_command(
    ('manage','ban-plug'),rule=to_me(),
    aliases={('manage','unban-plug')},block=True,priority=1,
    permission=SUPERUSER)
@ban_plug_handler.handle()
@with_help("插件权限管理", is_admin=True)
async def _(event: MessageEvent, command = Command(),message : Message = CommandArg()):
    """
    管理插件的用户/群组权限（仅管理员可用）
    
    指令:
    /manage ban-plug [模块名] [用户ID/群ID]: 封禁用户或群组对指定模块的使用权限
    /manage unban-plug [模块名] [用户ID/群ID]: 解封用户或群组对指定模块的使用权限
    
    参数说明:
    - 模块名: 插件名称，可使用"全局"或"all"表示全局封禁
    - 用户ID: 直接输入QQ号，如 123456789
    - 群ID: 以g开头的群号，如 g123456789
    
    示例:
    /manage ban-plug entertainment 123456789
    /manage ban-plug global g123456789
    /manage unban-plug entertainment 123456789
    """
    try:
        args = message.extract_plain_text().split()
        logger.debug(args)
        moduleName,id=args
        isGroup = True if id[0] == 'g' else False
        id=id[1:]
        if moduleName.startswith("nonebot_plugin_"):
            moduleName = moduleName.replace("nonebot_plugin_", "")
        pluginslist = [plugin.name.replace("nonebot_plugin_", "") 
                        if plugin.name.startswith("nonebot_plugin_") else plugin.name for plugin in get_loaded_plugins()]
        
        if moduleName in ["全局","all"] :
            moduleName = "global"
        elif moduleName not in pluginslist:
            await reply([f"[Management - Plug-Permission]不存在模块 {moduleName} 。"], event, finish=True)
        response = f'[Management - Plug-Permission] {moduleName} 对 {"群" if isGroup else "用户"} {id} {"解禁" if command[1] == "unban-plug" else "封禁"}'
        if isGroup:
            moduleName = "group-"+moduleName
        ret = cubp.setperm(moduleName,id,command[1] == 'unban-plug')
        response += "操作成功" if ret else "操作失败，请检查是否已经进行过该操作。"
        await reply([response], event, finish=True)
    except MatcherException:
        raise
    except Exception as e:
        await report_exception(event, "插件权限管理", e)