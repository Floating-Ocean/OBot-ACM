import json
import os
import random

import easyocr
from thefuzz import process

from src.core.bot.command import command, PermissionLevel
from src.core.bot.message import RobotMessage
from src.core.bot.interact import reply_fuzzy_matching
from src.core.constants import Constants
from src.core.util.tools import save_img, rand_str_len32, get_md5, read_image_with_opencv

_lib_path = os.path.join(Constants.config["lib_path"], "Pick-One")
__pick_one_version__ = "v3.1.0"

_lib_config, _match_dict, _ids = {}, {}, []


def register_module():
    pass


def _get_img_dir_path(img_key: str, audit: bool = False) -> str:
    dir_path = os.path.join(_lib_path, "__AUDIT__", img_key) if audit else os.path.join(_lib_path, img_key)
    if not os.path.exists(dir_path):  # 保证目录存在
        os.makedirs(dir_path)
    return dir_path


def load_pick_one_config():
    with open(os.path.join(_lib_path, "config.json"), 'r', encoding="utf-8") as f:
        _lib_config.clear(), _ids.clear(), _match_dict.clear()
        _lib_config.update(json.load(f))
        for key, value in _lib_config.items():  # 方便匹配
            _ids.append([value['_id'], len(os.listdir(os.path.join(_lib_path, key)))])
            for keys in value['key']:
                _match_dict[keys] = key
        _ids.sort(key=lambda s: s[1], reverse=True)  # 按图片数量降序排序


def parse_img(message: RobotMessage, img_key: str):
    """解析图片文字"""
    dir_path = _get_img_dir_path(img_key)
    img_list = [img for img in os.listdir(dir_path) if img.endswith(".gif")]

    paser_path = os.path.join(dir_path, "parser.json")
    old_parsed = {}
    if os.path.exists(paser_path):
        try:
            with open(paser_path, 'r', encoding="utf-8") as f:
                old_parsed = json.load(f)
        except Exception as e:
            Constants.log.error(f"parser.json invalid: {e}")
            old_parsed = {}

    parsed = {}
    notified = False
    ocr_reader = None
    for img in img_list:
        if img in old_parsed:
            parsed[img] = old_parsed[img]
        else:
            if not notified:
                message.reply("图片处理中，请稍等\n若等待时间较长，可尝试重新发送消息")
                notified = True
            try:
                if ocr_reader is None:
                    ocr_reader = easyocr.Reader(['en', 'ch_sim'])
                correct_img = read_image_with_opencv(os.path.join(dir_path, img))  # 修复全都修改为 gif 的兼容性问题
                Constants.log.info(f"正在识别 {os.path.join(dir_path, img)}")
                ocr_result = ''.join(ocr_reader.readtext(correct_img, detail=0))
                parsed[img] = ocr_result
            except Exception as e:
                Constants.log.error(f"OCR failed: {e}")
                parsed[img] = ""

    try:
        with open(paser_path, 'w', encoding="utf-8") as f:
            f.write(json.dumps(parsed, ensure_ascii=False, indent=4))
    except Exception as e:
        Constants.log.error(f"Save parser.json failed: {e}")


def get_img_parser(img_key: str) -> dict:
    dir_path = _get_img_dir_path(img_key)
    paser_path = os.path.join(dir_path, "parser.json")
    parsed = None
    if os.path.exists(paser_path):
        with open(paser_path, 'r', encoding="utf-8") as f:
            try:
                parsed = json.load(f)
            except json.JSONDecodeError as e:
                Constants.log.warn(f"parser.json invalid: {e}")
                return {}
    if not parsed or len(parsed) == 0:
        Constants.log.warn("parser.json invalid")
        return {}
    return parsed


_what_dict = {
    '随机来只': 'rand',
    '随便来只': 'rand',
    'capoo': 'capoo',
    '咖波': 'capoo',
}


@command(tokens=["来只*"] + list(_what_dict.keys()))
def pick_one(message: RobotMessage):
    load_pick_one_config()

    func = message.tokens[0][1:]
    what = _what_dict[func] if func in _what_dict else (
        message.tokens[1].lower() if len(message.tokens) >= 2 else "")
    query_idx = 1 if func in _what_dict else 2  # 查询指定表情包
    if what == "rand" or what == "随便" or what == "随机":
        current_key = random.choice(list(_lib_config.keys()))
    elif what in _match_dict:
        current_key = _match_dict[what]
    else:  # 支持一下模糊匹配
        matches = process.extract(what, _match_dict.keys(), limit=1)[0]
        if matches[1] < 60:
            img_help = "目前可以来只:\n\n"
            img_help += ", ".join([_id for _id, _len in _ids])
            message.reply(img_help, modal_words=False)
            return
        current_key = _match_dict[matches[0]]

    current_config = _lib_config[current_key]
    dir_path = _get_img_dir_path(current_key)

    parse_img(message, current_key)
    img_parser = get_img_parser(current_key)

    def reply_ok(query_tag: str, query_more_tip: str, picked: str):
        message.reply(f"来了一只{query_tag}{current_config['_id']}{query_more_tip}", img_path=os.path.join(dir_path, picked))

    reply_fuzzy_matching(message, img_parser, f"{current_config['_id']} 的图片", query_idx, reply_ok)


@command(tokens=["添加来只*", "添加*"])
def save_one(message: RobotMessage):
    load_pick_one_config()

    if len(message.tokens) < 2:
        message.reply("请指定需要添加的图片的关键词")
        return

    need_audit = not message.user_permission_level.is_mod()
    what = message.tokens[1].lower()

    if what in _match_dict:
        current_key = _match_dict[what]
        dir_path = _get_img_dir_path(current_key, need_audit)
        real_dir_path = _get_img_dir_path(current_key, audit=False)
        cnt, ok, duplicate = len(message.attachments), 0, 0

        for attach in message.attachments:
            if not attach.__dict__['content_type'].startswith('image'):
                continue  # 不是图片

            file_path = os.path.join(dir_path, f"{rand_str_len32()}.gif")
            response = save_img(attach.__dict__['url'], file_path)

            if response:
                md5 = get_md5(file_path)

                if (os.path.exists(os.path.join(real_dir_path, f"{md5}.gif")) or
                        os.path.exists(os.path.join(dir_path, f"{md5}.gif"))):
                    os.remove(file_path)
                    duplicate += 1  # 图片重复
                    continue

                os.rename(file_path, os.path.join(dir_path, f"{md5}.gif"))
                ok += 1

        if cnt == 0:
            message.reply("未识别到图片，请将图片和指令发送在同一条消息中")
        else:
            parse_img(message, current_key)
            failed_info = ""
            if duplicate > 0:
                failed_info += f"，重复 {duplicate} 张"
            if cnt - ok - duplicate > 0:
                failed_info += f"，失败 {cnt - ok - duplicate} 张"

            audit_suffix = "审核队列" if need_audit else ""
            main_info = "非Bot管理员添加的图片需要审核。\n" if need_audit else ""
            main_info += f"已添加 {ok} 张图片至 {current_key} {audit_suffix}中" if ok > 0 else "没有图片被添加"
            message.reply(f"{main_info}{failed_info}")

    else:
        img_help = f"关键词 {what} 未被记录，请联系bot管理员添加" if len(what) > 0 else "请指定需要添加的图片的关键词"
        message.reply(img_help)


@command(tokens=["审核来只", "同意来只", "accept", "audit"], permission_level=PermissionLevel.MOD)
def audit_accept(message: RobotMessage):
    load_pick_one_config()

    audit_dir_path = _get_img_dir_path("__AUDIT__")
    tags = [tag for tag in os.listdir(audit_dir_path)
            if os.path.isdir(os.path.join(audit_dir_path, tag))]  # 遍历文件夹
    cnt, ok = 0, 0
    ok_dict: dict[str, int] = {}

    for tag in tags:
        if not os.path.exists(os.path.join(_lib_path, tag)):
            continue

        dir_path = _get_img_dir_path(tag, audit=True)
        real_dir_path = _get_img_dir_path(tag, audit=False)
        img_list = [img for img in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, img))]

        for img in img_list:
            cnt += 1
            if os.path.exists(os.path.join(real_dir_path, img)):
                continue  # 图片重复
            os.rename(os.path.join(dir_path, img), os.path.join(real_dir_path, img))
            ok += 1
            ok_dict[tag] = ok_dict.get(tag, 0) + 1

        parse_img(message, tag)

    if cnt == 0:
        message.reply("没有需要审核的图片")
    else:
        failed_info = ""
        if cnt - ok > 0:
            failed_info += f"，失败 {cnt - ok} 张"

        audit_detail = '\n'.join([f"[{tag}] {ok_count} 张" for tag, ok_count in ok_dict.items()])
        info = f"已审核 {ok} 张图片{failed_info}\n\n{audit_detail}" if ok > 0 else f"没有图片被添加{failed_info}"
        message.reply(info, modal_words=False)
