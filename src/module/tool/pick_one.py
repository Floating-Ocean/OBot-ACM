import random

import easyocr
from thefuzz import process

from src.core.bot.decorator import command, PermissionLevel, module
from src.core.bot.interact import reply_fuzzy_matching
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.tools import read_image_with_opencv
from src.data.data_pick_one import get_pick_one_data, get_img_parser, save_img_parser, list_img, \
    get_img_full_path, accept_attachment, list_auditable, PickOne, accept_audit


def _parse_img(message: RobotMessage, img_key: str, notified: bool = False):
    """解析图片文字"""
    ocr_reader = None
    old_data = get_img_parser(img_key)
    data = {}

    for name, full_path in list_img(img_key):
        if name in old_data:
            data[name] = old_data[name]
        else:
            if not notified:
                message.reply("图片处理中，请稍等\n若等待时间较长，可尝试重新发送消息")
                notified = True
            try:
                if ocr_reader is None:
                    ocr_reader = easyocr.Reader(['en', 'ch_sim'], gpu=True)
                correct_img = read_image_with_opencv(full_path)  # 修复全都修改为 gif 的兼容性问题
                Constants.log.info(f"[ocr] 正在识别 {full_path}")
                ocr_result = ''.join(ocr_reader.readtext(correct_img, detail=0))
                data[name] = ocr_result
            except Exception as e:
                Constants.log.warning("[ocr] 识别出错.")
                Constants.log.exception(f"[ocr] {e}")
                data[name] = ""

    save_img_parser(img_key, data)


def _decode_img_key(data: PickOne, what: str) -> str | None:
    if what is None:
        return None  # 省的下面还要再跑
    elif what == "rand" or what == "随便" or what == "随机":
        img_key = random.choice(list(data.conf.keys()))
    elif what in data.match_dict:
        img_key = data.match_dict[what]
    else:  # 支持一下模糊匹配
        matches = process.extract(what, data.match_dict.keys(), limit=1)
        if len(matches) == 0 or matches[0][1] < 60:
            return None
        img_key = data.match_dict[matches[0][0]]
    return img_key


@command(tokens=["来只*"])
def reply_pick_one(message: RobotMessage):
    data = get_pick_one_data()
    what = message.tokens[1].lower() if len(message.tokens) >= 2 else None

    img_key = _decode_img_key(data, what)
    if img_key is None:
        img_help = "目前可以来只:\n\n"
        img_help += ", ".join([_id for _id, _len in data.ids])
        message.reply(img_help, modal_words=False)
        return

    current_config = data.conf[img_key]

    # 支持文字检索
    _parse_img(message, img_key)
    img_parser = get_img_parser(img_key)

    def reply_ok(query_tag: str, query_more_tip: str, picked: str):
        message.reply(f"来了一只{query_tag}{current_config.id}{query_more_tip}",
                      img_path=get_img_full_path(img_key, picked))

    reply_fuzzy_matching(message, img_parser, f"{current_config.id} 的图片", 2, reply_ok)


@command(tokens=["随机来只", "随便来只"])
def reply_pick_one_rand(message: RobotMessage):
    message.tokens = ["/来只", "rand"]
    reply_pick_one(message)


@command(tokens=["capoo", "咖波"])
def reply_pick_one_capoo(message: RobotMessage):
    message.tokens = ["/来只", "capoo"]
    reply_pick_one(message)


@command(tokens=["添加来只*", "添加*"])
def reply_save_one(message: RobotMessage):
    data = get_pick_one_data()

    if len(message.tokens) < 2:
        message.reply("请指定需要添加的图片的关键词")
        return

    need_audit = not message.user_permission_level.is_mod()
    what = message.tokens[1].lower()

    if what in data.match_dict:
        img_key = data.match_dict[what]
        cnt, ok, duplicate = accept_attachment(img_key, need_audit, message.attachments)

        if cnt == 0:
            message.reply("未识别到图片，请将图片和指令发送在同一条消息中")
        else:
            _parse_img(message, img_key)
            failed_info = ""
            if duplicate > 0:
                failed_info += f"，重复 {duplicate} 张"
            if cnt - ok - duplicate > 0:
                failed_info += f"，失败 {cnt - ok - duplicate} 张"

            audit_suffix = "审核队列" if need_audit else ""
            main_info = "非Bot管理员添加的图片需要审核。\n" if need_audit else ""
            main_info += f"已添加 {ok} 张图片至 {img_key} {audit_suffix}中" if ok > 0 else "没有图片被添加"
            message.reply(f"{main_info}{failed_info}")

    elif what == '比赛':  # 人文关怀一下
        message.reply("猜你想找：/导入比赛", modal_words=False)

    else:
        img_help = f"关键词 {what} 未被记录，请联系bot管理员添加" if len(what) > 0 else "请指定需要添加的图片的关键词"
        message.reply(img_help)


@command(tokens=["审核来只", "同意来只", "accept", "audit"], permission_level=PermissionLevel.MOD)
def reply_audit_accept(message: RobotMessage):
    cnt = 0
    ok_status: dict[str, int] = {}

    notified = False
    for img_key in list_auditable():
        cnt += accept_audit(img_key, ok_status)
        _parse_img(message, img_key, notified)
        notified = True

    if cnt == 0:
        message.reply("没有需要审核的图片")
    else:
        failed_info = ""
        ok = sum(ok_status.values())
        if cnt - ok > 0:
            failed_info += f"，失败 {cnt - ok} 张"

        audit_detail = '\n'.join([f"[{tag}] {ok_count} 张" for tag, ok_count in ok_status.items()])
        info = f"已审核 {ok} 张图片{failed_info}\n\n{audit_detail}" if ok > 0 else f"没有图片被添加{failed_info}"
        message.reply(info, modal_words=False)


@module(
    name="Pick-One",
    version="v3.3.0"
)
def register_module():
    pass
