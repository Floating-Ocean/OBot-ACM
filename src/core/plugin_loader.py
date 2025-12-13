"""
插件依赖预加载模块
集中管理所有必需的插件依赖，确保它们在插件加载前被优先预加载

注意：此模块应该在 nonebot.init() 之后、load_plugins() 之前被导入
"""
from nonebot import require

# 集中管理所有必需的插件依赖
# 当此模块被导入时，这些 require() 会被执行
require("nonebot_plugin_apscheduler")
require("nonebot_plugin_localstore")
require("nonebot_plugin_saa")
require("nonebot_plugin_session")
require("nonebot_plugin_alconna")
