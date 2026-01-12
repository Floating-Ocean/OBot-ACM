import os
import shutil
from datetime import datetime, timedelta

from src.core.constants import Constants
from src.core.util.tools import check_is_float

_cache_path = Constants.modules_conf.get_cache_path()


def clean_cache_hours_ago(category: str):
    category_path = os.path.join(_cache_path, category)
    if not os.path.exists(category_path):
        return

    one_hour_ago = datetime.now() - timedelta(hours=1)
    for filename in os.listdir(category_path):
        prefix = filename.rsplit('.', 1)[0]
        if check_is_float(prefix):
            file_mtime = datetime.fromtimestamp(float(prefix))
            if file_mtime < one_hour_ago:  # 清理一小时前的缓存
                file_path = os.path.join(category_path, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # 支持子文件夹的清除
                except Exception as e:
                    Constants.log.warning(f"[caching] 清除缓存 {file_path} 失败")
                    Constants.log.exception(f"[caching] {e}")


def get_cached_prefix(category: str):
    clean_cache_hours_ago(category)

    category_path = os.path.join(_cache_path, category)
    os.makedirs(os.path.join(_cache_path, category), exist_ok=True)

    return os.path.join(_cache_path, category, f"{datetime.now().timestamp()}")
