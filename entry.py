# botpy 外层日志

import logging
import os

logger_handler = logging.StreamHandler()
logger_handler.setFormatter(logging.Formatter('\033[1;36m[%(levelname)s]\t(%(filename)s:%(lineno)s)%(funcName)s\t\t\033[0m%(message)s'))
logger = logging.getLogger("entry")
logger.setLevel(logging.DEBUG)
logger.addHandler(logger_handler)
logger.propagate = False

# 解决部分 Windows 系统下日志输出颜色显示异常的问题
os.system("")


# 加载核心组件
logger.debug("[obot-init] 载入核心组件中")

import faulthandler
import importlib
import nest_asyncio
import urllib3

nest_asyncio.apply()
urllib3.disable_warnings()
faulthandler.enable()

importlib.import_module("easyocr")  # 这个加载巨慢，预先处理一下
importlib.import_module("src.core")
from src.core.constants import Constants
logger.debug(f'[obot-init] 载入核心 Core {Constants.core_version}-{Constants.git_commit.hash_short}')


# 加载模块
logger.debug("[obot-init] 载入模块中")
importlib.import_module("src.module")
from src.core.bot.decorator import get_command_count, get_module_count
from robot import open_robot_session
logger.debug(f'[obot-init] 已载入 {get_module_count()} 个模块，{get_command_count()} 条指令')

logger.debug("[obot-init] 模块加载完成，正在启动 Bot")


import base64
import psutil

LOCK_PATH = os.path.abspath("robot.py.lock")
ENTRY_SCRIPT = os.path.abspath("entry.py")

# 包含 pid 的文件锁
try:
    if not os.path.exists(LOCK_PATH):
        logger.warning("[obot-init] 锁文件不存在")
    else:
        with open(LOCK_PATH, 'rb') as lock_file:
            old_pid = int(base64.b85decode(lock_file.read()).decode())
            if psutil.pid_exists(old_pid):
                proc = psutil.Process(old_pid)
                # 验证进程身份，避免误杀
                if ("python" in proc.name().lower() and
                        any(ENTRY_SCRIPT in cmd for cmd in proc.cmdline())):
                    proc.kill()
except Exception as e:
    logger.warning("[obot-init] 读取文件锁异常")
    logger.exception(f"[obot-init] {e}")

try:
    with open(LOCK_PATH, 'wb') as lock_file:
        lock_file.write(base64.b85encode(str(os.getpid()).encode()))
except Exception as e:
    logger.warning("[obot-init] 写入文件锁异常")
    logger.exception(f"[obot-init] {e}")

open_robot_session()

# 下面的代码不会被执行，找不到什么方法监听 SIGINT，棘手。
os.remove(LOCK_PATH)
logger.debug("[obot-init] Bot 进程终止")
