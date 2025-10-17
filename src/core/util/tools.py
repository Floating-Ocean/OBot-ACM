import datetime
import hashlib
import os
import random
import re
import shlex
import ssl
import string
import subprocess
import sys
import time

import cv2
import numpy as np
import requests
from PIL import Image
from lxml import etree
from lxml.etree import Element
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.main import QRCode
from requests import Response
from requests.adapters import HTTPAdapter

from src.core.constants import Constants


def run_py_file(payload: str, cwd: str, log_ignore_regex: str | None = None) -> str:
    Constants.log.info(f'[shell] cd "{cwd}"')
    Constants.log.info(f'[shell] python -X utf8 {payload}')

    args = [sys.executable, '-X', 'utf8'] + shlex.split(payload)
    with subprocess.Popen(args, bufsize=1,
                          stdin=subprocess.PIPE, stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
                          cwd=cwd, universal_newlines=True, encoding='utf-8') as cmd:
        ignore_re = re.compile(log_ignore_regex) if log_ignore_regex else None
        info_lines: list[str] = []
        while True:  # 实时输出
            line = cmd.stdout.readline()
            if not line:
                if cmd.poll() is not None:  # 判断子进程是否结束
                    break
                continue
            line = line.rstrip('\r\n')
            if not (ignore_re and ignore_re.search(line)):
                Constants.log.info(f"[shell] {line}")
                info_lines.append(line)

            if cmd.poll() is not None:  # 判断子进程是否结束
                break

        # 处理剩余的输出
        remaining_output = cmd.stdout.read()
        if remaining_output:
            remaining_lines = remaining_output.splitlines()
            for line in remaining_lines:
                line = line.rstrip('\r\n')
                if line and not (ignore_re and ignore_re.search(line)):
                    Constants.log.info(f"[shell] {line}")
                    info_lines.append(line)

    return '\n'.join(info_lines)


def clean_unsafe_shell_str(origin_str: str) -> str:
    """清除所有终端中的特殊字符"""
    # 去除危险元字符 &, <, >, ^, ;, $, *, ?, \, ", ', `, (), {}, [], #, ~, |
    pattern = r'[&<>^;$*?\\\"\'`()\{\}\[\]#~|]'
    sanitized = re.sub(pattern, '', origin_str)
    # 防止把值当作选项解析 --xx, -X
    sanitized = re.sub(r'^-+', '', sanitized)
    return sanitized


def fetch_url(url: str, inject_headers: dict = None, payload: dict = None,
              method: str = 'post', accept_codes: list[int] | None = None) -> Response:
    if accept_codes is None:
        accept_codes = [200]

    proxies = {}  # 配置代理
    general_conf = Constants.modules_conf.general
    if ('http_proxy' in general_conf and
            general_conf['http_proxy'] is not None and len(general_conf['http_proxy']) > 0):
        proxies['http'] = general_conf['http_proxy']
    if ('https_proxy' in general_conf and
            general_conf['https_proxy'] is not None and len(general_conf['https_proxy']) > 0):
        proxies['https'] = general_conf['https_proxy']
    if len(proxies) == 0:
        proxies = None

    try:
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/91.0.4472.77 Safari/537.36",
            'Connection': 'close'
        }
        if inject_headers is not None:
            for k, v in inject_headers.items():
                headers[k] = v

        method = method.lower()
        if method == 'post':
            response = requests.post(url, headers=headers, proxies=proxies, json=payload)
        elif method == 'get':
            response = requests.get(url, headers=headers, proxies=proxies)
        else:
            raise ValueError("Parameter method must be either 'post' or 'get'.")

    except Exception as e:
        # 交给外层异常处理
        raise ConnectionError(f"Failed to connect {url}: {e}") from e

    code = response.status_code
    Constants.log.info(f"[network] {code} | {url}")

    if code not in accept_codes:
        raise ConnectionError(f"Failed to connect {url}, code {code}.")

    return response


def fetch_url_text(url: str, inject_headers: dict = None, payload: dict = None,
                   method: str = 'post', accept_codes: list[int] | None = None) -> str:
    response = fetch_url(url, inject_headers, payload, method, accept_codes)
    return response.text


def fetch_url_json(url: str, inject_headers: dict = None, payload: dict = None,
                   method: str = 'post', accept_codes: list[int] | None = None) -> dict:
    response = fetch_url(url, inject_headers, payload, method, accept_codes)
    try:
        return response.json()
    except ValueError as e:
        raise ValueError(f"Invalid JSON from {url}") from e


def fetch_url_element(url: str, accept_codes: list[int] | None = None) -> Element:
    response = fetch_url(url, method='get', accept_codes=accept_codes)
    return etree.HTML(response.text)


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
        elif days >= 14:
            weeks = days // 7
            info = f"{weeks}周"
        else:
            info = f"{days}天"

    return f"{info}{'后' if diff < 0 else '前'}"


def format_timestamp(timestamp: int, chinese_weekday_format: bool = True) -> str:
    # fix: 修复在 windows 上设置 locale 导致的堆异常
    weekdays = (['周一', '周二', '周三', '周四', '周五', '周六', '周日'] if chinese_weekday_format else
                ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
    tm = time.localtime(timestamp)
    weekday = weekdays[tm.tm_wday]
    return time.strftime('%y/%m/%d ', tm) + f'{weekday} ' + time.strftime('%H:%M:%S', tm)


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


def download_img(url: str, file_path: str) -> bool:
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
    if remove_origin:
        os.remove(path)
    return new_path


def get_md5(path: str) -> str:
    md5 = hashlib.md5()
    with open(path, 'rb') as file:
        md5.update(file.read())
    return md5.hexdigest()


def md5_to_base62(md5_hash: str) -> str:
    """将 MD5 转换为 Base62 格式，字符集[a-zA-Z0-9]"""
    if len(md5_hash) != 32:
        raise ValueError("Invalid md5 length, must be a hex string of 32 characters long")
    try:
        num = int(md5_hash, 16)
    except ValueError as e:
        raise ValueError(f"Invalid md5 format, must be hexadecimal: {e}") from e
    base62_charset = string.ascii_letters + string.digits
    if num == 0:
        return base62_charset[0]
    base62_str = ""
    while num > 0:
        num, remainder = divmod(num, 62)
        base62_str = base62_charset[remainder] + base62_str
    return base62_str


def base62_to_md5(base62_str: str) -> str:
    """将 Base62 转换为 MD5，字符集[a-zA-Z0-9]"""
    base62_charset = string.ascii_letters + string.digits
    if not base62_str or len(base62_str) > 22:
        raise ValueError("Invalid length for base62 to transform into md5")
    invalid_chars = [c for c in base62_str if c not in base62_charset]
    if invalid_chars:
        raise ValueError(f"Invalid charset: {''.join(invalid_chars)}，only [A-Za-z0-9] allowed")
    num = 0
    for char in base62_str:
        num = num * 62 + base62_charset.index(char)
    hex_str = format(num, '032x')
    return hex_str


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


def get_today_timestamp_range() -> tuple[int, int]:
    return get_today_start_timestamp(), get_today_start_timestamp() + 24 * 60 * 60


def get_a_month_timestamp_range() -> tuple[int, int]:
    return get_today_start_timestamp(), get_today_start_timestamp() + 31 * 24 * 60 * 60


def get_simple_qrcode(content: str) -> Image:
    qr = QRCode()
    qr.add_data(content)
    return qr.make_image(image_factory=StyledPilImage,
                         module_drawer=RoundedModuleDrawer(), eye_drawer=RoundedModuleDrawer())


def format_int_delta(delta: int) -> str:
    if delta >= 0:
        return f"+{delta}"
    else:
        return f"{delta}"


def decode_range(range_str: str, length: tuple[int, int]) -> tuple[int, int]:
    if length[0] > length[1]:
        return -1, -1

    if range_str is None:
        min_point, max_point = 0, 0
    else:
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


def check_intersect(range1: tuple[int, int], range2: tuple[int, int]) -> bool:
    return max(range1[0], range2[0]) <= min(range1[1], range2[1])


def patch_https_url(url: str) -> str:
    if url.startswith('//'):
        return f'https:{url}'
    if not url.startswith('https://'):
        return f'https://{url}'
    return url


def read_image_with_opencv(file_path: str, grayscale: bool = False) -> np.ndarray:
    """读取可能被篡改后缀的图片，并返回 OpenCV 兼容的 numpy 数组"""
    try:
        with Image.open(file_path) as img:
            # GIF提取第一帧
            if img.format == 'GIF':
                img.seek(0)
                if img.mode in ('P', 'L', 'RGBA'):
                    img = img.convert('RGB')

            elif img.mode == 'RGBA':
                img = img.convert('RGB')  # 移除透明通道

            if grayscale:
                img = img.convert('L')  # 转换为灰度
                cv_image = np.array(img)
            else:
                cv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            return cv_image

    except Exception as e:
        raise RuntimeError(f"Failed to load cv image: {e}") from e


def reverse_str_by_line(original_str: str) -> str:
    mirrored = original_str.translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "∀qƆpƎℲפHIſʞ˥WNOԀQɹS┴∩ΛMX⅄Zɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz"
    ))
    return '\n'.join([line[::-1] for line in mirrored.split('\n')])


def april_fool_magic(original_str: str) -> str:
    if datetime.datetime.today().month == 4 and datetime.datetime.today().day == 1:
        return reverse_str_by_line(original_str)
    return original_str


def is_valid_date(date_str: str, fmt: str) -> bool:
    try:
        datetime.datetime.strptime(date_str, fmt)
        return True
    except ValueError:
        return False


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
