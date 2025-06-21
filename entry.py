import base64
import faulthandler
import importlib
import os

import nest_asyncio
import psutil
import urllib3

from robot import open_robot_session

LOCK_PATH = os.path.abspath("robot.py.lock")
ENTRY_SCRIPT = os.path.abspath("entry.py")

nest_asyncio.apply()
urllib3.disable_warnings()
faulthandler.enable()

# 加载模块
importlib.import_module("src.module")

if __name__ == '__main__':
    # 包含 pid 的文件锁
    if os.path.exists(LOCK_PATH):
        with open(LOCK_PATH, 'rb') as lock_file:
            old_pid = int(base64.b85decode(lock_file.read()).decode())
            if psutil.pid_exists(old_pid):
                proc = psutil.Process(old_pid)
                # 验证进程身份，避免误杀
                if ("python" in proc.name().lower() and
                        any(ENTRY_SCRIPT in cmd for cmd in proc.cmdline())):
                    psutil.Process(old_pid).kill()

    with open(LOCK_PATH, 'wb') as lock_file:
        lock_file.write(base64.b85encode(str(os.getpid()).encode()))

    open_robot_session()

    os.remove(LOCK_PATH)
