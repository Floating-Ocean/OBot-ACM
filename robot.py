import importlib

import nonebot
from nonebot import get_loaded_plugins
from nonebot.adapters.onebot.v11 import Adapter as V11Adapter
from nonebot.adapters.qq import Adapter as QQAdapter
from src.core.constants import Constants

# 初始化 NoneBot
nonebot.init(superusers=Constants.role_conf['admin_id'],command_sep={' '})

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(V11Adapter)
driver.register_adapter(QQAdapter)

# nonebot.load_plugins("src/module")
nonebot.load_plugin("src.module.maintain")
nonebot.load_plugin("src.module.cron")
nonebot.load_plugin("src.module.tool.how_to_cook")
nonebot.load_plugin("src.module.interact")
nonebot.load_plugin("src.module.cp.nk")
nonebot.load_plugin("src.module.cp.atc")
nonebot.load_plugin("src.module.cp.contest_manual")
nonebot.load_plugin("src.module.cp.peeper")
if __name__ == "__main__":
    # 注册模块版本信息
    for plugin in get_loaded_plugins():
        if plugin.module_name.startswith("src"):
            getattr(importlib.import_module(plugin.module_name),"register_module")()
    nonebot.run()