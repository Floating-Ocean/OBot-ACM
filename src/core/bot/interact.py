import random
import secrets
from typing import Callable

from pypinyin import pinyin, Style
from thefuzz import process

from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.tools import check_is_int


def no_reply():
    """
    无回复
    """
    pass


def reply_key_words(message: RobotMessage, content: str):
    """
    回复关键词匹配，精确到拼音
    """
    random.shuffle(Constants.key_words)  # 多个关键词时的处理
    reply = random.choice(["你干嘛", "干什么", "咋了", "how", "what"])

    for asks, answers in Constants.key_words:
        for ask in asks:
            ask_pinyin = ''.join(word[0] for word in pinyin(ask, Style.NORMAL))
            ctx_pinyin = ''.join(word[0] for word in pinyin(content.lower(), Style.NORMAL))
            if ask_pinyin in ctx_pinyin:
                reply = random.choice(answers)

    message.reply(reply)


def reply_fuzzy_matching(message: RobotMessage, target: list | dict, target_name: str, query_idx: int,
                         reply_ok: Callable[[str, str, str], None]):
    """
    模糊匹配，支持下标查询

    :param message: 消息
    :param target: 匹配列表
    :param target_name: 列表名称
    :param query_idx: 待匹配文本在消息中的下标
    :param reply_ok: 匹配成功时调用，参数列表：[匹配程度文本, 提示文本, 选取的对象]，无返回值
    """
    if len(target) == 0:
        message.reply(f"这里还没有 {target_name}")
    else:
        query_tag, query_more_tip = "", ""

        if len(message.tokens) > query_idx:
            match_results = process.extract(message.tokens[query_idx], target, limit=5)
            if isinstance(target, dict):
                # 传递 dict 时会返回 tuple(value, ratio, key)
                picked_tuple = [(result[2], result[1]) for result in match_results if result[1] >= 20]  # 相似度至少 20%
            else:
                picked_tuple = [(result[0], result[1]) for result in match_results if result[1] >= 20]
            if len(picked_tuple) == 0:
                message.reply(f"这里还没有满足条件的 {target_name}")
                return

            pick_idx = 1
            if len(message.tokens) > query_idx + 1:
                if (not check_is_int(message.tokens[query_idx + 1]) or
                        int(message.tokens[query_idx + 1]) > len(picked_tuple)):
                    message.reply(f"这里还没有满足条件且编号对应的 {target_name}")
                    return
                pick_idx = int(message.tokens[query_idx + 1])
                if pick_idx == 0:
                    message.reply("从 1 开始编号呢，不是从 0 开始")
                    return

            picked, ratio = picked_tuple[pick_idx - 1]
            query_more_tip = f"\n标签匹配度 {ratio}%"
            if len(message.tokens) > query_idx + 1:
                query_more_tip += f"，在 {len(picked_tuple)} 个候选中排名第 {pick_idx} "
            else:
                query_more_tip += f"，共 {len(picked_tuple)} 个候选"
                if len(picked_tuple) > 1:
                    query_more_tip += "，可在指令后追加编号参数查询更多"

            if ratio >= 95:  # 简单的评价反馈
                query_tag = "完美满足条件的"
            elif ratio >= 60:
                query_tag = "满足条件的"
            elif ratio >= 35:
                query_tag = "比较满足条件的"
            else:
                query_tag = "可能不太满足条件的"
        else:
            rnd_idx = secrets.randbelow(len(target))  # 加强随机性
            if isinstance(target, dict):
                picked = list(target.keys())[rnd_idx]
            else:
                picked = target[rnd_idx]

        reply_ok(query_tag, query_more_tip, picked)
