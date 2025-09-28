import copy
import random
import re
import string
import threading
import time
from dataclasses import dataclass

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants, HelpStrList
from src.core.util.tools import check_is_int, get_simple_qrcode, png2jpg, format_int_delta
from src.data.data_cache import get_cached_prefix
from src.data.data_duel_cf import CFUser, get_binding, establish_binding, accept_binding, settle_duel, unbind
from src.data.model.binding import BindStatus
from src.platform.online.codeforces import Codeforces, ProbInfo
from src.render.pixie.render_contest_list import ContestListRenderer

_CF_HELP = '\n'.join(HelpStrList(Constants.help_contents["codeforces"]))
_CF_DUEL_HELP = '\n'.join([
    ("/cf duel start [标签|all] (难度) (new): "
     "开始对战，题目从 Codeforces 上随机选取. 标签中间不能有空格，支持模糊匹配. 难度为整数或一个区间，格式为 xxx-xxx. "
     "末尾加上 new 参数则会忽视 P1000A 以前的题."),
    "/cf duel accept [pair_code]: 同意对战请求",
    "/cf duel finish: 结束本次对战"
])


@dataclass
class DuelistInfo:
    user_data: CFUser
    opponent_user_id: str
    problem: dict
    establish_time: int


@dataclass
class PairingInfo:
    user_id: str
    prob_info: ProbInfo


_duelist_info: dict[str, DuelistInfo] = {}
_duel_pairing_info: dict[str, PairingInfo] = {}
_duelist_info_lock = threading.Lock()
_duel_pairing_info_lock = threading.Lock()


def send_binding(message: RobotMessage):
    user = get_binding(message.author_id)
    reply_tip = ""
    if user.bind_status == BindStatus.UNBOUNDED:
        message.reply("你当前未绑定任何 Codeforces 账号，请使用 /cf bind [handle] 进行绑定")
        return
    if user.bind_status == BindStatus.BINDING:
        validate_status = Codeforces.validate_binding(user.handle, user.establish_binding_time)
        if validate_status:
            validate_status &= (accept_binding(message.author_id, user) == 0)
        if not validate_status:
            message.reply("绑定失败，请确保你使用了正确的账号，并在绑定开始的 10 分钟内完成了提交")
            return
        reply_tip = "绑定成功！\n"

    message.reply(f"{reply_tip}你当前绑定的账号 [{user.handle}]\n\n"
                  f"潜力值：{user.ptt}\n"
                  f"对战数：{len(user.contest_history)}", modal_words=False)


def send_user_id_card(message: RobotMessage, handle: str):
    message.reply(f"正在查询 {handle} 的 Codeforces 基础信息，请稍等")

    id_card = Codeforces.get_user_id_card(handle)
    if not id_card:
        content = (f"[Codeforces ID] {handle}\n\n"
                   "用户不存在")
        message.reply(content, modal_words=False)
    else:
        cached_prefix = get_cached_prefix('Platform-ID')
        id_card.write_file(f"{cached_prefix}.png")
        message.reply(f"[Codeforces] {handle}", png2jpg(f"{cached_prefix}.png"), modal_words=False)


def send_user_info(message: RobotMessage, handle: str):
    message.reply(f"正在查询 {handle} 的 Codeforces 平台信息，请稍等")

    user = Codeforces.get_user_info(handle)
    if not user:
        content = (f"[Codeforces] {handle}\n\n"
                   "用户不存在")
        avatar = None
    else:
        info, avatar = user
        last_contest = Codeforces.get_user_last_contest(handle)
        last_submit = Codeforces.get_user_last_submit(handle)
        total_sums, weekly_sums, daily_sums = Codeforces.get_user_submit_counts(handle)
        daily = "今日暂无过题" if daily_sums == 0 else f"今日通过 {daily_sums} 题"
        weekly = "" if weekly_sums == 0 else f"，本周共通过 {weekly_sums} 题"
        content = (f"[Codeforces] {handle}\n\n"
                   f"{info}\n"
                   f"通过题数: {total_sums}\n\n"
                   f"{last_contest}\n\n"
                   f"{daily}{weekly}\n"
                   f"{last_submit}")

    message.reply(content, img_url=avatar, modal_words=False)


def send_user_last_submit(message: RobotMessage, handle: str, count: int):
    message.reply(f"正在查询 {handle} 的 Codeforces 提交记录，请稍等")

    user = Codeforces.get_user_info(handle)
    if not user:
        content = (f"[Codeforces] {handle}\n\n"
                   "用户不存在")
    else:
        last_submit = Codeforces.get_user_last_submit(handle, count)
        if not last_submit:
            last_submit = "查询异常"
        content = (f"[Codeforces] {handle}\n\n"
                   f"{last_submit}")

    message.reply(content, modal_words=False)


def send_prob_tags(message: RobotMessage):
    message.reply("正在查询 Codeforces 平台的所有问题标签，请稍等")

    prob_tags = Codeforces.get_prob_tags_all()
    content = "[Codeforces] 问题标签:\n" + "\n".join(prob_tags)

    message.reply(content, modal_words=False)


def send_prob_filter_tag(message: RobotMessage, prob_info: ProbInfo) -> bool:
    message.reply("正在随机选题，请稍等")

    validation_status = Codeforces.validate_prob_filtered(prob_info,
                                                          on_tag_chosen=lambda x: message.reply(x))
    if not validation_status:
        return False

    chosen_prob = Codeforces.get_prob_filtered(prob_info)

    if not chosen_prob:
        message.reply("条件不合理或过于苛刻，无法找到满足条件的题目")
        return True

    send_prob_link(message, chosen_prob)
    return True


def send_prob_link(message: RobotMessage, chosen_prob: dict, hide_tag: bool = False):
    tags = ', '.join(chosen_prob['tags'])
    content = (f"[Codeforces] 随机选题\n\n"
               f"P{chosen_prob['contestId']}{chosen_prob['index']} {chosen_prob['name']}\n\n"
               f"链接: [codeforces] /contest/{chosen_prob['contestId']}/problem/{chosen_prob['index']}")
    if not hide_tag:
        content += f"\n标签: {tags}"
    if 'rating' in chosen_prob:
        content += f"\n难度: *{chosen_prob['rating']}"

    cached_prefix = get_cached_prefix('QRCode-Generator')
    qr_img = get_simple_qrcode(
        f"https://codeforces.com/contest/{chosen_prob['contestId']}/problem/{chosen_prob['index']}")
    qr_img.save(f"{cached_prefix}.png")

    message.reply(content, png2jpg(f"{cached_prefix}.png"), modal_words=False)


def send_contest(message: RobotMessage):
    message.reply("正在查询近期 Codeforces 比赛，请稍等")

    running, upcoming, finished = Codeforces.get_contest_list()

    cached_prefix = get_cached_prefix('Contest-List-Renderer')
    contest_list_img = ContestListRenderer(running, upcoming, finished).render()
    contest_list_img.write_file(f"{cached_prefix}.png")

    message.reply("[Codeforces] 近期比赛", png2jpg(f"{cached_prefix}.png"))


def send_user_contest_standings(message: RobotMessage, handle: str, contest_id: str):
    message.reply(f"正在查询编号为 {contest_id} 的比赛中 {handle} 的榜单信息，请稍等。\n"
                  f"查询对象为参赛者时将会给出 Rating 变化预估，但可能需要更久的时间")
    content = f"[Codeforces] {handle} 比赛榜单查询\n\n"

    user = Codeforces.get_user_info(handle)
    if not user:
        content += "用户不存在"
    else:
        standings = Codeforces.get_user_contest_standings(handle, contest_id)
        if not standings:
            content += "比赛不存在"
        else:
            contest_info, standings_info = standings
            content += f"{contest_info}\n\n"
            if len(standings_info) > 0:
                content += '\n\n'.join(standings_info)
            else:
                content += '暂无榜单信息'

    message.reply(content, modal_words=False)


def send_logo(message: RobotMessage):
    message.reply("[Codeforces] 网站当前的图标", img_url=Codeforces.logo_url)


def send_prob_pick_help(message: RobotMessage, func_prefix: str):
    message.reply("请输入正确的指令格式，题目标签不要带有空格，如:\n\n"
                  f"{func_prefix} dp 1700-1900 new\n"
                  f"{func_prefix} dfs-and-similar\n"
                  f"{func_prefix} all 1800", modal_words=False)


def start_binding(message: RobotMessage, handle: str):
    user = get_binding(message.author_id)

    user_info = Codeforces.get_user_info(handle)
    if not user_info:
        message.reply(f"用户 [{handle}] 不存在，请检查用户名是否正确")
        return

    establish_status = establish_binding(message.author_id, user, handle)
    if establish_status == -1:
        message.reply("你已经开始绑定，请不要重复操作")
        return
    if establish_status == -2:
        message.reply("你已经绑定账号，请不要重复绑定。\n"
                      "如需切换账号，请先使用 /cf unbind 进行解绑。解绑后你的对战数据会保留。", modal_words=False)
        return

    cached_prefix = get_cached_prefix('QRCode-Generator')
    qr_img = get_simple_qrcode("https://codeforces.com/contest/1/submit")
    qr_img.save(f"{cached_prefix}.png")

    message.reply(f"你当前正在绑定 [{handle}]\n\n"
                  "请在 10 分钟内，使用该账号在 P1A 提交一发 CE (编译错误)\n"
                  "提交成功后，请回复 /cf bind 以确认绑定",
                  png2jpg(f"{cached_prefix}.png"), modal_words=False)


def start_unbinding(message: RobotMessage):
    user = get_binding(message.author_id)
    unbind_status = unbind(message.author_id, user)
    if unbind_status == -1:
        message.reply("你还未绑定账号，无法解绑")
        return

    message.reply("解绑成功")


def _check_duelist_fresh(message: RobotMessage) -> int:
    user_id = message.author_id
    with _duelist_info_lock:
        if user_id in _duelist_info:
            message.reply("你已经在对战中，请不要重复发起")
            return -1
    return 0


def start_duel_pairing(message: RobotMessage, prob_info: ProbInfo):
    user_id = message.author_id
    if _check_duelist_fresh(message) != 0:
        return

    validation_status = Codeforces.validate_prob_filtered(prob_info,
                                                          on_tag_chosen=lambda x: message.reply(x))
    if not validation_status:
        send_prob_pick_help(message, "/cf duel start")
        return

    with _duel_pairing_info_lock:
        old_pair_code = next((pair_code
                              for pair_code, info in _duel_pairing_info.items()
                              if info.user_id == user_id),
                             None)
        if old_pair_code is not None:
            message.reply("你已经发起对战请求，请不要重复操作\n\n"
                          f"上一次请求的配对码为 {old_pair_code}", modal_words=False)
            return

        pair_code = ""
        while len(pair_code) == 0 or pair_code in _duel_pairing_info:
            pair_code = ''.join(random.choices(string.hexdigits, k=6))

        _duel_pairing_info[pair_code] = PairingInfo(user_id, prob_info)

    message.reply("已发起对战请求，请对手发送下面的指令以接受对战\n\n"
                  f"/cf duel accept {pair_code}", modal_words=False)


def accept_duel_pairing(message: RobotMessage, pair_code: str):
    user_id = message.author_id
    user = get_binding(user_id)
    if _check_duelist_fresh(message) != 0:
        return

    with _duel_pairing_info_lock:
        if pair_code not in _duel_pairing_info:
            message.reply("配对码无效，建议直接复制粘贴")
            return
        pairing_info = copy.deepcopy(_duel_pairing_info[pair_code])
        del _duel_pairing_info[pair_code]

    opponent_id = pairing_info.user_id
    opponent = get_binding(opponent_id)

    # 验证对手绑定状态
    if opponent.bind_status != BindStatus.BOUND:
        message.reply("对手账号状态异常，无法开始对战")
        return

    message.reply("成功接受对战，正在进行随机选题")

    r_a, r_b = Codeforces.get_user_rating(user.handle), Codeforces.get_user_rating(opponent.handle)
    if r_a is None:
        message.reply("你的账号状态异常，无法开始对战")
    if r_b is None:
        message.reply("对手的账号状态异常，无法开始对战")

    r_avg = (r_a + r_b) // 2

    excludes = set()
    excludes.update(Codeforces.get_user_submit_prob_id(user.handle))
    excludes.update(Codeforces.get_user_submit_prob_id(opponent.handle))

    prob_info = pairing_info.prob_info

    changed_limit = False
    if prob_info.limit is None:
        prob_info.limit = f"{max(800, r_avg - 250)}-{min(3000, r_avg + 250)}"
        changed_limit = True

    chosen_prob = Codeforces.get_prob_filtered(prob_info, excludes)

    if not chosen_prob and changed_limit:
        prob_info.limit = "800-3000"  # 一定要有范围，否则会选到没难度标级的新题
        chosen_prob = Codeforces.get_prob_filtered(prob_info, excludes)

    if not chosen_prob:
        message.reply("条件不合理或过于苛刻，无法找到满足条件的题目，正在进行随机选题")
        prob_info.tag = "all"
        prob_info.limit = f"{max(800, r_avg - 250)}-{min(3000, r_avg + 250)}"
        prob_info.newer = True
        chosen_prob = Codeforces.get_prob_filtered(prob_info, excludes)

    if not chosen_prob:
        message.reply("随机选题异常，请稍后重新发起对战")
        return

    duel_establish_time = int(time.time())

    with _duelist_info_lock:
        _duelist_info[user_id] = DuelistInfo(
            user_data=user,
            opponent_user_id=opponent_id,
            problem=chosen_prob,
            establish_time=duel_establish_time
        )
        _duelist_info[opponent_id] = DuelistInfo(
            user_data=opponent,
            opponent_user_id=user_id,
            problem=chosen_prob,
            establish_time=duel_establish_time
        )

    message.reply("对战开始！\n\n"
                  "任意一方通过后发送 /cf duel finish 即可进行结算\n"
                  "若双方均通过，则根据 ICPC 罚时规则进行结算")
    send_prob_link(message, chosen_prob)


def finish_duel(message: RobotMessage):
    user_id = message.author_id
    user = get_binding(user_id)

    with _duelist_info_lock:
        if user_id not in _duelist_info:
            message.reply("你没有在对战中，无法结束对战")
            return

        duel_info = copy.deepcopy(_duelist_info[user_id])
        opponent_id = duel_info.opponent_user_id
        opponent = get_binding(duel_info.opponent_user_id)
        status_me = Codeforces.get_prob_status(user.handle,
                                               duel_info.establish_time,
                                               duel_info.problem['contestId'],
                                               duel_info.problem['index'])
        status_op = Codeforces.get_prob_status(opponent.handle,
                                               duel_info.establish_time,
                                               duel_info.problem['contestId'],
                                               duel_info.problem['index'])
        if not status_me or not status_op:
            message.reply("获取提交状态失败，请稍后重试")
            return

        ac_me, penalty_me = status_me
        ac_op, penalty_op = status_op
        del _duelist_info[user_id]
        del _duelist_info[opponent_id]

    if not ac_me and not ac_op:
        message.reply("对战结束，无人过题")
        return

    if ac_me and not ac_op:
        outcome = 0
    elif ac_op and not ac_me:
        outcome = 1
    else:
        if penalty_me < penalty_op:
            outcome = 0
        elif penalty_me > penalty_op:
            outcome = 1
        else:
            outcome = 2

    settle_duel(user_id, user, opponent_id, opponent, outcome, duel_info.problem['rating'])
    message.reply(f'对战结束，判定为 {"你获胜" if outcome == 0 else "对方获胜" if outcome == 1 else "平局"}\n\n'
                  f'你: {"通过" if ac_me else "未通过"}，罚时 {penalty_me}'
                  f'，潜力值变化 {format_int_delta(user.contest_history[-1])}\n'
                  f'对方: {"通过" if ac_op else "未通过"}，罚时 {penalty_op}'
                  f'，潜力值变化 {format_int_delta(opponent.contest_history[-1])}',
                  modal_words=False)


@command(tokens=['cf', 'codeforces'])
def reply_cf_request(message: RobotMessage):
    try:
        content = re.sub(r'<@!\d+>', '', message.content).strip().split()
        if len(content) < 2:
            message.reply(f'[Codeforces]\n\n{_CF_HELP}', modal_words=False)
            return

        func = content[1]

        if func == "identity" or func == "id" or func == "card":
            if len(content) != 3:
                message.reply(f"请输入正确的指令格式，如\"/cf {func} jiangly\"")
                return

            send_user_id_card(message, content[2])

        elif func == "info" or func == "user":
            if len(content) != 3:
                message.reply(f"请输入正确的指令格式，如\"/cf {func} jiangly\"")
                return

            send_user_info(message, content[2])

        elif func == "recent":
            if len(content) not in [3, 4]:
                message.reply("请输入正确的指令格式，如\"/cf recent jiangly 5\"")
                return

            if len(content) == 4 and (len(content[3]) >= 3 or not check_is_int(content[3]) or int(content[3]) <= 0):
                message.reply("参数错误，请输入 [1, 99] 内的整数")
                return

            send_user_last_submit(message, content[2], int(content[3]) if len(content) == 4 else 5)

        elif func == "pick" or func == "prob" or func == "problem" or (
                content[0] == "/rand" and func == "cf"):  # 让此处能被 /rand 模块调用
            if len(content) < 3 or not send_prob_filter_tag(
                    message=message,
                    prob_info=ProbInfo(
                        tag=content[2],
                        limit=content[3] if len(content) >= 4 and content[3] != "new" else None,
                        newer=content[3] == "new" if len(content) == 4 else (
                                content[4] == "new" if len(content) == 5 else False)
                    )
            ):
                func_prefix = f"/cf {func}"
                if func == "cf":
                    func_prefix = "/rand cf"
                send_prob_pick_help(message, func_prefix)

        elif func == "contest" or func == "contests":
            send_contest(message)

        elif func == "status" or func == "stand" or func == "standing" or func == "standings":
            if len(content) != 4:
                message.reply("请输入正确的指令格式，如:\n\n"
                              f"/cf {func} jiangly 2057", modal_words=False)
            else:
                send_user_contest_standings(message, content[2], content[3])

        elif func == "tag" or func == "tags":
            send_prob_tags(message)

        elif func == "logo" or func == "icon":
            send_logo(message)

        elif func == "bind":
            if len(content) == 2:
                send_binding(message)
            else:
                start_binding(message, content[2])

        elif func == "unbind":
            start_unbinding(message)

        elif func == "duel":
            user_id = message.author_id
            user = get_binding(user_id)
            if user.bind_status != BindStatus.BOUND:
                message.reply("你还没有绑定账号，请使用 /cf bind [handle] 进行绑定")
                return
            if len(content) == 3 and content[2] == "finish":
                finish_duel(message)
            elif len(content) == 4 and content[2] == "accept":
                accept_duel_pairing(message, content[3])
            elif len(content) >= 4 and content[2] == "start":
                start_duel_pairing(message, ProbInfo(
                    tag=content[3],
                    limit=content[4] if len(content) >= 5 and content[4] != "new" else None,
                    newer=content[4] == "new" if len(content) == 5 else (
                        content[5] == "new" if len(content) == 6 else False)
                ))
            else:
                message.reply(f'Codeforces 对战模块\n\n{_CF_DUEL_HELP}')

        else:
            message.reply(f'[Codeforces]\n\n{_CF_HELP}', modal_words=False)

    except Exception as e:
        message.report_exception('Codeforces', e)


@module(
    name="Codeforces",
    version="v5.1.0"
)
def register_module():
    pass
