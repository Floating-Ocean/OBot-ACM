import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import easyocr
from thefuzz import process

from src.core.bot.decorator import command, PermissionLevel, module
from src.core.bot.interact import reply_fuzzy_matching
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.output_cache import get_cached_prefix
from src.core.util.tools import read_image_with_opencv, base62_to_md5, md5_to_base62, png2jpg
from src.data.data_pick_one import get_pick_one_data, get_img_parser, save_img_parser, list_img, \
    get_img_full_path, accept_attachment, list_auditable, PickOne, accept_audit, \
    get_category_stat, pick_preview_imgs, match_hash_id_prefix, list_parser_hash_ids
from src.render.pixie.render_pick_one import (PickOneRenderer, PickOnePreviewRenderer,
                                              _PREVIEW_COUNT)

_MAX_COMMENT_LENGTH = 32

_ocr_reader = easyocr.Reader(['en', 'ch_sim'], gpu=True, verbose=False)
_ocr_reader_lock = threading.Lock()
_ocr_thread_pool = ThreadPoolExecutor(max_workers=os.cpu_count(),
                                      thread_name_prefix="OCR Worker Thread Pool")

_parser_locks: dict[str, threading.Lock] = {}
_locks_dict_lock = threading.Lock()

_last_pick_img: dict[str, tuple[float, str, str]] = {}  # 指定对话场景上一次提起的图片
# 指定对话场景、指定类别上一次预览展示过的图片
_last_preview_ids: dict[str, dict[str, list[str]]] = {}


def _get_parser_lock(img_key: str) -> threading.Lock:
    with _locks_dict_lock:
        if img_key not in _parser_locks:
            _parser_locks[img_key] = threading.Lock()
        return _parser_locks[img_key]


def _parse_task(img_key: str, name: str, full_path: str):
    try:
        correct_img = read_image_with_opencv(full_path)  # 修复全都修改为 gif 的兼容性问题
        Constants.log.info(f"[ocr] 正在识别 {name}")

        with _ocr_reader_lock:
            ocr_text = ''.join(_ocr_reader.readtext(correct_img, detail=0))

        with _get_parser_lock(img_key):
            data = get_img_parser(img_key)
            if name not in data:
                raise ValueError(f"Invalid ocr source: {name}")

            data[name]['ocr_text'] = ocr_text
            save_img_parser(img_key, data)
            Constants.log.info(f"[ocr] 成功识别 {name}")

    except Exception as e:
        Constants.log.warning("[ocr] 识别出错")
        Constants.log.exception(f"[ocr] {e}")


def _parse_img(img_key: str):
    """解析图片文字"""
    parse_tasks = []

    with _get_parser_lock(img_key):
        old_data = get_img_parser(img_key)
        data = {}

        for name, full_path in list_img(img_key):
            if name in old_data:
                parser_data = old_data[name]
                if isinstance(parser_data, str):
                    parser_data = {
                        'ocr_text': parser_data,
                        'add_time': os.stat(full_path).st_mtime,
                        'likes': 0,
                        'comments': [],
                        'pickup_times': 0
                    }
                data[name] = parser_data
            else:
                data[name] = {
                    'ocr_text': "",
                    'add_time': time.time(),
                    'likes': 0,
                    'comments': [],
                    'pickup_times': 0
                }
                parse_tasks.append((name, full_path))

        save_img_parser(img_key, data)

    if parse_tasks:
        Constants.log.info(f"[ocr] 发起 {len(parse_tasks)} 个识别任务")
        for task in parse_tasks:
            _ocr_thread_pool.submit(_parse_task, img_key, task[0], task[1])


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


def _resolve_img_id(message: RobotMessage, img_key: str, prefix: str,
                    category_ids: list[str]) -> str | None:
    """把 ID 前缀解析成完整 ID；匹配不唯一或匹配不到时直接回复提示"""
    matched = match_hash_id_prefix(
        _last_preview_ids.get(message.uuid, {}).get(img_key, []),
        category_ids, prefix.strip())
    if len(matched) == 1:
        return matched[0]

    if matched:
        message.reply(f"[Pick-One] 存在多个匹配，请提供更长的 ID 前缀")
        return None

    message.reply(f"[Pick-One] 没有找到 ID 前缀为 {prefix} 的表情包，请检查后重试")
    return None


def _reply_picked_img(message: RobotMessage, data: PickOne, img_key: str, img_parser: dict,
                      picked: str, query_tag: str, query_more_tip: str = ""):
    """回复单张表情包，并记为该对话场景上一次提起的图片"""
    hash_id = md5_to_base62(picked.rsplit('.', 1)[0])
    parse_info = img_parser[picked]
    comments = (
        "" if not parse_info['comments'] else
        ("评论: \n" + ('\n'.join(f"{idx + 1}. {content}" for idx, content in
                                 enumerate(parse_info['comments']))) + "\n")
    )
    add_time = time.strftime('%y/%m/%d %H:%M:%S',
                             time.localtime(parse_info['add_time']))

    # 记录提起次数
    parse_info['pickup_times'] += 1
    img_parser[picked] = parse_info
    save_img_parser(img_key, img_parser)

    if query_more_tip:
        query_more_tip = f"\n{query_more_tip}"
    message.reply(f"[Pick-One] 来了只{query_tag}{data.conf[img_key].id}\n\n"
                  f"ID: {hash_id}\n"
                  f"点赞: {parse_info['likes']} 次\n{comments}"
                  f"提起次数: {parse_info['pickup_times']} 次\n"
                  f"添加时间: {add_time}{query_more_tip}",
                  img_path=get_img_full_path(img_key, picked), modal_words=False)

    _last_pick_img[message.uuid] = time.time(), img_key, hash_id


def _reply_pick_one_list(message: RobotMessage, data: PickOne):
    cached_prefix = get_cached_prefix('Pick-One-Renderer')
    PickOneRenderer(data).render().write_file(f"{cached_prefix}.png")

    total_count = sum(count for _, count in data.ids)
    message.reply(f"[Pick-One] 目前可以来只...",
                  img_path=png2jpg(f"{cached_prefix}.png"), modal_words=False)


@command(tokens=["预览来只*", "看看来只*", "来只图鉴*", "preview*"])
def reply_pick_one_preview(message: RobotMessage):
    data = get_pick_one_data()
    if len(message.tokens) >= 2:
        img_key = _decode_img_key(data, message.tokens[1].lower())
        if img_key is None:
            _reply_pick_one_list(message, data)
            return
    else:
        # 不指定类别时从有内容的中挑
        counts = dict(data.ids)
        img_key = random.choice([key for key, conf in data.conf.items()
                                 if counts.get(conf.id, 0) > 0])

    imgs = get_category_stat(img_key)
    if not imgs:
        message.reply(f"[Pick-One] 这个类别还没有表情包哦，"
                      f"发送 /添加来只 {img_key} 并附带图片即可添加.", modal_words=False)
        return

    if len(message.tokens) >= 3:  # 指定 ID 前缀时直接给出对应的表情包
        hash_id = _resolve_img_id(message, img_key, message.tokens[2],
                                  [stat.hash_id for stat in imgs])
        if hash_id is None:
            return

        with _get_parser_lock(img_key):
            img_parser = _get_specified_img_parser(message, img_key, hash_id)
            if img_parser is None:
                return

            _reply_picked_img(message, data, img_key, img_parser,
                              f"{base62_to_md5(hash_id)}.gif", "指定的")
        return

    preview_imgs = pick_preview_imgs(imgs, _PREVIEW_COUNT)
    _last_preview_ids.setdefault(message.uuid, {})[img_key] = \
        [stat.hash_id for stat in preview_imgs]
    renderer = PickOnePreviewRenderer(data, img_key, preview_imgs)

    cached_prefix = get_cached_prefix('Pick-One-Renderer')
    renderer.render().write_file(f"{cached_prefix}.png")

    message.reply(f"[Pick-One] {data.conf[img_key].id} 预览图\n\n"
                  f"发送 /预览来只 {img_key} 加 ID 前缀可直接获取对应表情包",
                  img_path=png2jpg(f"{cached_prefix}.png"), modal_words=False)


@command(tokens=["来只*"])
def reply_pick_one(message: RobotMessage):
    data = get_pick_one_data()
    what = message.tokens[1].lower() if len(message.tokens) >= 2 else None

    img_key = _decode_img_key(data, what)
    if img_key is None:
        _reply_pick_one_list(message, data)
        return

    current_config = data.conf[img_key]

    # 支持文字检索
    _parse_img(img_key)

    with _get_parser_lock(img_key):
        img_parser = get_img_parser(img_key)

        def reply_ok(query_tag: str, query_more_tip: str, picked: str):
            """回复模糊匹配的表情包"""
            _reply_picked_img(message, data, img_key, img_parser, picked,
                              query_tag, query_more_tip)

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
    if len(message.tokens) < 2:
        message.reply("[Pick-One] 请指定需要添加的图片的关键词")
        return

    data = get_pick_one_data()
    need_audit = not message.user_permission_level.is_mod()
    what = message.tokens[1].lower()

    if what in data.match_dict:
        img_key = data.match_dict[what]
        cnt, ok, duplicate = accept_attachment(img_key, need_audit, message.attachments)

        if cnt == 0:
            message.reply("[Pick-One] 未识别到图片，请将图片和指令发送在同一条消息中")
        else:
            _parse_img(img_key)
            failed_info = ""
            if duplicate > 0:
                failed_info += f"，重复 {duplicate} 张"
            if cnt - ok - duplicate > 0:
                failed_info += f"，失败 {cnt - ok - duplicate} 张"

            suffix = "审核队列中，等待 Bot 管理员审核" if need_audit else "中"
            main_info = f"已添加 {ok} 张图片至 {img_key} {suffix}" if ok > 0 else "没有图片被添加"
            message.reply(f"[Pick-One] {main_info}{failed_info}")

    elif what == '比赛':  # 人文关怀一下
        message.reply("猜你想找：/导入比赛", modal_words=False)

    else:
        message.reply(f"[Pick-One] 关键词 {what} 未被记录，请联系 Bot 管理员添加")


def _check_edit_img_parser(data: PickOne, message: RobotMessage, action: str) -> bool:
    """初步检查修改 parser.json 的操作的合法性"""
    if len(message.tokens) < 2:
        message.reply(f"[Pick-One] 请指定想要{action}的图片的关键词")
        return False

    if len(message.tokens) < 3:
        message.reply(f"[Pick-One] 请指定想要{action}的图片的 ID")
        return False

    what = message.tokens[1].lower()
    if what not in data.match_dict:
        message.reply(f"[Pick-One] 关键词 {what} 未被记录，请联系 Bot 管理员添加")
        return False

    return True


def _get_specified_img_parser(message: RobotMessage, img_key: str, hash_id_b62: str) -> dict | None:
    """获取指定的 parser.json，并继续检查合法性"""
    hash_id = base62_to_md5(hash_id_b62)
    parser_key = f"{hash_id}.gif"

    img_parser = get_img_parser(img_key)
    if parser_key not in img_parser:
        message.reply("[Pick-One] ID 不存在，建议查询后直接复制粘贴")
        return None

    # 兼容旧版字符串结构（按需升级）
    value = img_parser[parser_key]
    if isinstance(value, str):
        full_path = get_img_full_path(img_key, parser_key)
        img_parser[parser_key] = {
            'ocr_text': value,
            'add_time': os.stat(full_path).st_mtime,
            'likes': 0,
            'comments': [],
            'pickup_times': 0
        }
        save_img_parser(img_key, img_parser)

    return img_parser


def _check_last_picked(message: RobotMessage, command_help: str) -> bool:
    _last_pick_img.setdefault(message.uuid, (0, "", ""))
    last_pick_time, _, _ = _last_pick_img[message.uuid]

    if time.time() - last_pick_time > 24 * 60 * 60:  # 一天内即可
        message.reply("[Pick-One] 找不到一天内上一次提起的图片，请使用下面的指令格式进行指定\n\n"
                      f"{command_help}", modal_words=False)
        return False
    return True


def _reply_like_one(message: RobotMessage, img_key: str, hash_id_b62: str):
    with _get_parser_lock(img_key):
        hash_id_b62 = _resolve_img_id(message, img_key, hash_id_b62,
                                      list_parser_hash_ids(get_img_parser(img_key)))
        if hash_id_b62 is None:
            return

        img_parser = _get_specified_img_parser(message, img_key, hash_id_b62)
        if img_parser is None:
            return

        hash_id = base62_to_md5(hash_id_b62)
        parser_key = f"{hash_id}.gif"

        likes = img_parser[parser_key]['likes'] + 1
        img_parser[parser_key]['likes'] = likes
        save_img_parser(img_key, img_parser)

    message.reply(f"[Pick-One] 点赞成功，目前有 {likes} 个赞")


@command(tokens=["点赞", "喜欢", "爱", "love", "like"])
def reply_like_one_last(message: RobotMessage):
    if not _check_last_picked(message, command_help="/点赞来只 [what] [id]"):
        return

    _, img_key, hash_id_b62 = _last_pick_img[message.uuid]
    _reply_like_one(message, img_key, hash_id_b62)


@command(tokens=["点赞来只*", "喜欢来只*", "爱来只*"])
def reply_like_one_specific(message: RobotMessage):
    data = get_pick_one_data()
    if not _check_edit_img_parser(data, message, "点赞"):
        return

    what = message.tokens[1].lower()
    img_key = data.match_dict[what]

    _reply_like_one(message, img_key, message.tokens[2].strip())


def _reply_comment_one(message: RobotMessage, img_key: str, hash_id_b62: str, comment: str):
    with _get_parser_lock(img_key):
        hash_id_b62 = _resolve_img_id(message, img_key, hash_id_b62,
                                      list_parser_hash_ids(get_img_parser(img_key)))
        if hash_id_b62 is None:
            return

        img_parser = _get_specified_img_parser(message, img_key, hash_id_b62)
        if img_parser is None:
            return

        hash_id = base62_to_md5(hash_id_b62)
        parser_key = f"{hash_id}.gif"

        if len(comment) > _MAX_COMMENT_LENGTH:
            message.reply(f"[Pick-One] 评论字数过长，请限制在 {_MAX_COMMENT_LENGTH} 个字符内")
            return

        if comment in img_parser[parser_key]['comments']:
            message.reply("[Pick-One] 评论重复，添加失败")
            return

        comments = img_parser[parser_key]['comments']
        comments.append(comment)
        img_parser[parser_key]['comments'] = comments
        save_img_parser(img_key, img_parser)

    message.reply(f"[Pick-One] 评论成功，目前有 {len(comments)} 个评论")


@command(tokens=["评论", "回复", "comment", "say", "reply"])
def reply_comment_one_last(message: RobotMessage):
    if not _check_last_picked(message, command_help="/评论来只 [what] [id] [comment]"):
        return

    if len(message.tokens) < 2:
        message.reply("[Pick-One] 请输入评论内容")
        return

    _, img_key, hash_id_b62 = _last_pick_img[message.uuid]
    _reply_comment_one(message, img_key, hash_id_b62, message.tokens[1].strip())


@command(tokens=["评论来只*", "回复来只*"])
def reply_comment_one_specific(message: RobotMessage):
    data = get_pick_one_data()
    if not _check_edit_img_parser(data, message, "评论"):
        return

    what = message.tokens[1].lower()
    img_key = data.match_dict[what]

    if len(message.tokens) < 4:
        message.reply("[Pick-One] 请输入评论内容")
        return

    _reply_comment_one(message, img_key, message.tokens[2].strip(), message.tokens[3].strip())


@command(tokens=["审核来只", "同意来只", "accept", "audit", "ac"], permission_level=PermissionLevel.MOD)
def reply_audit_accept(message: RobotMessage):
    cnt = 0
    ok_status: dict[str, int] = {}

    for img_key in list_auditable():
        cnt += accept_audit(img_key, ok_status)
        _parse_img(img_key)

    if cnt == 0:
        message.reply("[Pick-One] 没有需要审核的图片")
    else:
        failed_info = ""
        ok = sum(ok_status.values())
        if cnt - ok > 0:
            failed_info += f"，失败 {cnt - ok} 张"

        audit_detail = '\n'.join([f"[{tag}] {ok_count} 张" for tag, ok_count in ok_status.items()])
        info = (f"[Pick-One] 已审核 {ok} 张图片{failed_info}\n\n{audit_detail}" if ok > 0 else
                f"没有图片被添加{failed_info}")
        message.reply(info, modal_words=False)


@module(
    name="Pick-One",
    version="v5.7.0"
)
def register_module():
    pass
