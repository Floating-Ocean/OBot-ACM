import os
from datetime import datetime, timedelta

from src.core.constants import Constants
from src.core.util.tools import check_is_float

_output_path = Constants.modules_conf.general["output_path"]


def clean_tmp_hours_ago(category: str):
    category_path = os.path.join(_output_path, category)
    if not os.path.exists(category_path):
        return

    one_hour_ago = datetime.now() - timedelta(hours=1)
    for filename in os.listdir(category_path):
        prefix = filename.rsplit('.', 1)[0]
        if check_is_float(prefix):
            file_mtime = datetime.fromtimestamp(float(prefix))
            if file_mtime < one_hour_ago:  # 清理一小时前的缓存
                os.remove(os.path.join(category_path, filename))


def get_cached_prefix(category: str):
    clean_tmp_hours_ago(category)

    category_path = os.path.join(_output_path, category)
    if not os.path.exists(category_path):
        os.makedirs(os.path.join(_output_path, category))

    return os.path.join(_output_path, category, f"{datetime.now().timestamp()}")
