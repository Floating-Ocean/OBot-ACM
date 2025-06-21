import base64
import os
import subprocess
import sys

import psutil
from apscheduler.schedulers.blocking import BlockingScheduler

from src.core.constants import Constants

_daemon_scheduler = BlockingScheduler()
_python_exec = "pythonw" if sys.platform == "win32" else "python3"

LOCK_PATH = os.path.abspath("robot.py.lock")
ENTRY_SCRIPT = os.path.abspath("entry.py")
CHECK_INTERVAL = 60


def open_entry():
    try:
        subprocess.Popen([_python_exec, ENTRY_SCRIPT],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception as e:
        Constants.log.error(f"[daemon] 启动失败: {str(e)}")
    else:
        Constants.log.info("[daemon] 进程创建完成")


def check_process_job():
    try:
        if os.path.exists(LOCK_PATH):
            try:
                with open(LOCK_PATH, "rb") as lock_file:
                    raw_data = lock_file.read()
                    if not raw_data:
                        Constants.log.warning("[daemon] 锁文件为空")
                        raise psutil.NoSuchProcess(-1)

                    try:
                        pid = int(base64.b85decode(raw_data).decode())
                    except Exception as e:
                        Constants.log.error(f"[daemon] 锁文件解析失败: {str(e)}")
                        raise psutil.NoSuchProcess(-1)

                    if psutil.pid_exists(pid):
                        proc = psutil.Process(pid)
                        # 僵尸进程处理
                        if proc.status() == psutil.STATUS_ZOMBIE:
                            proc.kill()
                            Constants.log.info("[daemon] 已清理僵尸进程")
                            raise psutil.NoSuchProcess(pid)

                        # 验证进程身份
                        if ("python" in proc.name().lower() and
                                any(ENTRY_SCRIPT in cmd for cmd in proc.cmdline())):
                            return

            except psutil.NoSuchProcess:
                pass

        Constants.log.info("[daemon] 进程不存在，正在创建")
        open_entry()

    except Exception as e:
        Constants.log.error(f"[daemon] 检查进程异常: {str(e)}")


if __name__ == '__main__':
    try:
        Constants.log.info("[daemon] 守护进程开始运行")
        check_process_job()
        _daemon_scheduler.add_job(check_process_job, "interval", seconds=CHECK_INTERVAL)
        _daemon_scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        Constants.log.info("[daemon] 守护进程开始终止")
        _daemon_scheduler.shutdown(wait=False)

    finally:
        Constants.log.info("[daemon] 守护进程已停止")
