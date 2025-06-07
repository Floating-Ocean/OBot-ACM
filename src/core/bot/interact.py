import random
import re
import secrets
import time
from typing import Callable

from pypinyin import pinyin, Style
from thefuzz import process

from src.core.bot.command import command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.output_cached import get_cached_prefix
from src.core.util.tools import png2jpg, get_simple_qrcode, check_intersect, get_today_timestamp_range, check_is_int
from src.platform.manual.manual import ManualPlatform
from src.platform.online.atcoder import AtCoder
from src.platform.online.codeforces import Codeforces
from src.platform.online.nowcoder import NowCoder
from src.render.pixie.render_contest_list import ContestListRenderer
from src.render.pixie.render_help import HelpRenderer


_fixed_reply = {
    "ping": "pong",
    "活着吗": "你猜捏",
    "似了吗": "？",
    "死了吗": "？？？"
}


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
                query_more_tip += f"，共有 {len(picked_tuple)} 个候选"
                if len(picked_tuple) > 1:
                    query_more_tip += "，可以在指令后追加编号参数查询更多"

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


@command(tokens=list(_fixed_reply.keys()))
def reply_fixed(message: RobotMessage):
    message.reply(_fixed_reply.get(message.tokens[0][1:], ""), modal_words=False)


@command(tokens=['contest', 'contests', '比赛', '近日比赛', '最近的比赛', '今天比赛', '今天的比赛', '今日比赛',
                 '今日的比赛'])
def reply_recent_contests(message: RobotMessage):
    query_today = message.tokens[0] in ['/今天比赛', '/今天的比赛', '/今日比赛', '/今日的比赛']
    if len(message.tokens) >= 3 and message.tokens[1] == 'today':
        query_today = True
        message.tokens[1] = message.tokens[2]
    queries = [AtCoder, Codeforces, NowCoder, ManualPlatform]
    if len(message.tokens) >= 2:
        if message.tokens[1] == 'today':
            query_today = True
        else:
            closest_type = process.extract(message.tokens[1].lower(), [
                "cf", "codeforces", "atc", "atcoder", "牛客", "nk", "nc", "nowcoder",
                "ccpc", "icpc", "other", "其他", "misc", "杂项", "manual", "手动"], limit=1)[0]
            if closest_type[1] >= 60:
                if closest_type[0] in ["cf", "codeforces"]:
                    queries = [Codeforces]
                elif closest_type[0] in ["atc", "atcoder"]:
                    queries = [AtCoder]
                elif closest_type[0] in ["ccpc", "icpc", "other", "其他", "misc", "杂项", "manual", "手动"]:
                    queries = [ManualPlatform]
                else:
                    queries = [NowCoder]
    tip_time_range = '今日' if query_today else '近期'
    if len(queries) == 1:
        message.reply(f"正在查询{tip_time_range} {queries[0].platform_name} 比赛，请稍等")
    else:
        message.reply(f"正在查询{tip_time_range}比赛，请稍等")

    running_contests, upcoming_contests, finished_contests = [], [], []
    for platform in queries:
        running, upcoming, finished = platform.get_contest_list()
        running_contests.extend(running)
        upcoming_contests.extend(upcoming)
        finished_contests.extend(finished)

    running_contests.sort(key=lambda c: c.start_time)
    upcoming_contests.sort(key=lambda c: c.start_time)
    finished_contests.sort(key=lambda c: c.start_time)

    if query_today:
        running_contests = [contest for contest in running_contests if check_intersect(
            range1=get_today_timestamp_range(),
            range2=(contest.start_time, contest.start_time + contest.duration)
        )]
        upcoming_contests = [contest for contest in upcoming_contests if check_intersect(
            range1=get_today_timestamp_range(),
            range2=(contest.start_time, contest.start_time + contest.duration)
        )]
        finished_contests = [contest for contest in finished_contests if check_intersect(
            range1=get_today_timestamp_range(),
            range2=(contest.start_time, contest.start_time + contest.duration)
        )]

    cached_prefix = get_cached_prefix('Contest-List-Renderer')
    contest_list_img = ContestListRenderer(running_contests, upcoming_contests, finished_contests).render()
    contest_list_img.write_file(f"{cached_prefix}.png")

    message.reply(f"{tip_time_range}比赛", png2jpg(f"{cached_prefix}.png"))


@command(tokens=["qr", "qrcode", "二维码", "码"])
def reply_qrcode(message: RobotMessage):
    content = re.sub(r'<@!\d+>', '', message.content).strip()
    content = re.sub(rf'{message.tokens[0]}', '', content, count=1).strip()
    if len(content) == 0:
        message.reply("请输入要转化为二维码的内容")
        return

    cached_prefix = get_cached_prefix('QRCode-Generator')
    qr_img = get_simple_qrcode(content)
    qr_img.save(f"{cached_prefix}.png")

    message.reply("生成了一个二维码", png2jpg(f"{cached_prefix}.png"))


@command(tokens=["晚安", "睡觉", "睡觉去了"], is_command=False)
def reply_mc_sleep(message: RobotMessage):
    """
    Minecraft主题的睡觉命令处理器
    随机回复睡觉相关的游戏消息，并可能延时发送"早上好"
    """
    actions = [
        "你的床爆炸了",
        "你被床弹飞了",
        "你的床已被破坏",
        "你现在不能休息，周围有怪物在游荡",
        "你现在不能休息，周围有玩家在游荡",
        "你只能在夜间或雷暴中入睡",
        "你只能在白天或晴天中入睡",
        f"正在等待 1/{random.randint(2, 100)} 名玩家入睡",
        "晚安"
    ]
    chosen_action = random.choice(actions)
    message.reply(chosen_action, modal_words=False)

    if chosen_action == "晚安":
        time.sleep(random.randint(30, 120))
        message.reply("早上好")


@command(tokens=["sleep"])
def reply_mc_sleep_as_cmd(message: RobotMessage):
    """
    Minecraft主题的睡觉命令处理器的指令调用版
    """
    reply_mc_sleep(message)


@command(tokens=['help', 'helps', 'instruction', 'instructions', '帮助'])
def reply_help(message: RobotMessage):
    message.reply("O宝正在画画，稍等一下")

    cached_prefix = get_cached_prefix('Help-Renderer')
    contest_list_img = HelpRenderer().render()
    contest_list_img.write_file(f"{cached_prefix}.png")

    message.reply("帮助手册", png2jpg(f"{cached_prefix}.png"))
