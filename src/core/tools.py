import asyncio
import datetime
import hashlib
import os
import random
import re
import ssl
import string
import subprocess
import time
from asyncio import AbstractEventLoop

import numpy as np
import requests
from PIL import Image
from PIL.Image import Resampling
from lxml import etree
from lxml.etree import Element
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.main import QRCode
from requests.adapters import HTTPAdapter

from src.core.constants import Constants
from src.core.help_registry import HelpRegistry

from nonebot_plugin_saa import MessageFactory,AggregatedMessageFactory

def run_shell(shell: str) -> str:
    Constants.log.info(shell)
    cmd = subprocess.Popen(shell, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                           universal_newlines=True, shell=True, bufsize=1)
    info = ""
    # 实时输出
    while True:
        line = cmd.stderr.readline().strip()
        Constants.log.info(line)
        info += line

        if line == "" or subprocess.Popen.poll(cmd) == 0:  # 判断子进程是否结束
            break

    return info


def run_async(loop: AbstractEventLoop, func: any):
    asyncio.set_event_loop(loop)
    task = loop.create_task(func)
    loop.run_until_complete(task)
    return task.result()


def fetch_html(url: str, payload: dict = None) -> Element:
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/91.0.4472.77 Safari/537.36",
    }
    response = requests.get(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise ConnectionError(f"Filed to connect {url}, code {response.status_code}. with message {response.text}")

    return etree.HTML(response.text)


def fetch_json(url: str, inject_headers: dict = None, payload: dict = None, throw: bool = True,
               method: str = 'post') -> dict | int:
    code = 200
    try:
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/91.0.4472.77 Safari/537.36",
            'Connection': 'close'
        }
        if inject_headers is not None:
            for k, v in inject_headers.items():
                headers[k] = v

        if method == 'post':
            response = requests.post(url, headers=headers, json=payload)
        elif method == 'get':
            response = requests.get(url, headers=headers)
        else:
            raise ValueError("Parameter method must be either 'post' or 'get'.")

        code = response.status_code

        if code != 200 and throw:
            raise ConnectionError(f"Filed to connect {url}, code {code}.")

        return response.json()
    except Exception as e:
        if throw:
            raise e
        return code


def format_timestamp_diff(diff: int) -> str:
    abs_diff = abs(diff)
    if abs_diff == 0:
        return "刚刚"

    if abs_diff < 60:
        info = f"{abs_diff}秒"
    elif abs_diff < 3600:
        minutes = abs_diff // 60
        info = f"{minutes}分钟"
    elif abs_diff < 86400:
        hours = abs_diff // 3600
        info = f"{hours}小时"
    else:
        days = abs_diff // 86400
        if days >= 365:
            years = days // 365
            info = f"{years}年"
        elif days >= 30:
            months = days // 30
            info = f"{months}个月"
        elif days >= 7:
            weeks = days // 7
            info = f"{weeks}周"
        else:
            info = f"{days}天"

    return f"{info}{'后' if diff < 0 else '前'}"


def format_timestamp(timestamp: int) -> str:
    return time.strftime('%y/%m/%d %H:%M:%S', time.localtime(timestamp))


def format_seconds(seconds: int) -> str:
    units_in_seconds = [
        ['天', 365 * 24 * 3600, 24 * 3600],
        ['小时', 24 * 3600, 3600],
        ['分钟', 3600, 60],
        ['秒', 60, 1]
    ]
    return ''.join([f" {seconds % u_mod // u_div} {name}"
                    for name, u_mod, u_div in units_in_seconds if seconds % u_mod // u_div > 0]).strip()


def escape_mail_url(content: str) -> str:
    email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{1,})'
    return re.sub(email_pattern, lambda x: x.group().replace('.', ' . '), content)


def check_is_int(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def check_is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


async def save_img(url: str, file_path: str) -> bool:
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/91.0.4472.77 Safari/537.36"
    }
    url = patch_https_url(url)

    sess = requests.session()
    sess.mount("https://", SSLAdapter())  # 将上面定义的SSLAdapter 应用起来

    response = sess.get(url, headers=headers, verify=False)  # 阻止ssl验证

    if response.status_code == 200:
        parent_path = os.path.dirname(file_path)
        if not os.path.exists(parent_path):
            os.makedirs(parent_path)

        with open(file_path, "wb") as f:
            f.write(response.content)
            f.close()

        return True

    return False


def png2jpg(path: str, remove_origin: bool = True) -> str:
    img = Image.open(path)
    new_path = os.path.splitext(path)[0] + '.jpg'
    img.convert('RGB').save(new_path)
    resampling_img(new_path)
    if remove_origin:
        os.remove(path)
    return new_path


def get_md5(path: str) -> str:
    md5 = hashlib.md5()
    file = open(path, 'rb')
    md5.update(file.read())
    file.close()
    return md5.hexdigest()


def rand_str_len32() -> str:
    return ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])


def get_today_start_timestamp() -> int:
    today = datetime.datetime.now().date()
    today_start = datetime.datetime.combine(today, datetime.time.min)
    timestamp = int(today_start.timestamp())
    return timestamp


def get_week_start_timestamp() -> int:
    today = datetime.datetime.now()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    week_start = datetime.datetime.combine(start_of_week.date(), datetime.time.min)
    timestamp = int(week_start.timestamp())
    return timestamp


def get_simple_qrcode(content: str) -> Image:
    qr = QRCode()
    qr.add_data(content)
    return qr.make_image(image_factory=StyledPilImage,
                         module_drawer=RoundedModuleDrawer(), eye_drawer=RoundedModuleDrawer())


def resampling_img(img_path: str):
    image = Image.open(img_path)
    image = np.array(image)
    scaled_image = np.zeros((image.shape[0] * 4, image.shape[1] * 4, 3), dtype=np.uint8)
    for i in range(4):
        for j in range(4):
            scaled_image[i::4, j::4] = image
    final_image = Image.fromarray(scaled_image)
    final_image = final_image.resize((image.shape[1], image.shape[0]), resample=Resampling.LANCZOS, reducing_gap=3.0)
    final_image.save(img_path)


def format_int_delta(delta: int) -> str:
    if delta >= 0:
        return f"+{delta}"
    else:
        return f"{delta}"


def decode_range(range_str: str, length: tuple[int, int]) -> tuple[int, int]:
    if length[0] > length[1]:
        return -1, -1

    min_point, max_point = 0, 0

    if range_str is not None:
        # 检查格式是否为 dddd-dddd 或 dddd
        if not re.match("^[0-9]+-[0-9]+$", range_str) and not re.match("^[0-9]+$", range_str):
            return -2, -2
        # 检查范围数值是否合法
        field_validate = True
        if "-" in range_str:
            field_validate &= length[0] * 2 + 1 <= len(range_str) <= length[1] * 2 + 1
            [min_point, max_point] = list(map(int, range_str.split("-")))
        else:
            field_validate &= length[0] <= len(range_str) <= length[1]
            min_point = max_point = int(range_str)
        if not field_validate:
            return -3, -3

    return min_point, max_point


def patch_https_url(url: str) -> str:
    if url.startswith('//'):
        return f'https:{url}'
    if not url.startswith('https://'):
        return f'https://{url}'
    return url


class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        """
        tls1.3 不再支持RSA KEY exchange，py3.10 增加TLS的默认安全设置。可能导致握手失败。
        使用 `ssl_context.set_ciphers('DEFAULT')` DEFAULT 老的加密设置。
        """
        ssl_context = ssl.create_default_context()
        ssl_context.set_ciphers('DEFAULT')
        ssl_context.check_hostname = False  # 避免在请求时 verify=False 设置时报错， 如果设置需要校验证书可去掉该行。
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2  # 最小版本设置成1.2 可去掉低版本的警告
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2  # 最大版本设置成1.2
        kwargs["ssl_context"] = ssl_context
        return super().init_poolmanager(*args, **kwargs)

async def reply_help(module,content="",isAdmin=False):
    messages = []
    if content != "":
        messages.append(MessageFactory(content))
    if isAdmin:
        messages.append(MessageFactory(f"[{module} (admin)]"))
        help_text = HelpRegistry.get_help(module, is_admin=True) or ''
        messages.append(MessageFactory(help_text))
    else:
        messages.append(MessageFactory(f"[{module}]"))
        help_text = HelpRegistry.get_help(module, is_admin=False) or ''
        messages.append(MessageFactory(help_text))
    await AggregatedMessageFactory(messages).finish()