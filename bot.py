import nonebot
from nonebot.adapters.onebot.v11 import Adapter as V11Adapter
from src.core.constants import Constants

# 初始化 NoneBot
nonebot.init(superusers=Constants.SUPERUSERS, command_sep={' '})

import src.core.plugin_loader  # noqa: F401

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(V11Adapter)

nonebot.load_plugins("src/plugins")

if __name__ == "__main__":
    nonebot.run()
