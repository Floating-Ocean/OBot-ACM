import nonebot
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
if __name__ == "__main__":
    nonebot.run()