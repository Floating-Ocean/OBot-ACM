from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters import Message
from nonebot.params import CommandArg, Command
from nonebot.log import logger
from nonebot.exception import MatcherException

from nonebot_plugin_saa import Image, TargetQQPrivate
from io import BytesIO
import copy
import random
import string
import threading
import time
from dataclasses import dataclass

from nonebot.adapters.onebot.v11.event import MessageEvent
from src.core.constants import Constants
from src.core.tools import check_is_int, get_simple_qrcode, png2jpg, reply_help, format_int_delta, format_timestamp, format_seconds
from src.core.help_registry import with_help
from src.platform.cp.codeforces import Codeforces, ProbInfo
from src.core.bot.message import reply, report_exception, send
from src.data.data_duel_cf import CFUser, get_binding, establish_binding, accept_binding, settle_duel, unbind
from src.data.model.binding import BindStatus


__cf_version__ = "v3.0.0"

supported_commands = ['info', 'user', 'recent', 'contests', 'status',
                      'standing', 'pick', 'tags', 'tag', 'duel', 'bind', 'unbind']


def register_module():
    pass


async def send_user_info(handle: str, event: MessageEvent):
    await reply([f"[Codeforces] 正在查询 {handle} 的 Codeforces 平台信息，请稍等..."], event, finish=False)

    info, avatar = Codeforces.get_user_info(handle)

    if avatar is None:
        content = (f"[Codeforces] {handle}\n\n"
                   f"{info}")
        await reply([content], event, finish=True)
    else:
        last_contest = Codeforces.get_user_last_contest(handle)
        last_submit = Codeforces.get_user_last_submit(handle)
        total_sums, weekly_sums, daily_sums = Codeforces.get_user_submit_counts(
            handle)
        daily = "今日暂无过题" if daily_sums == 0 else f"今日通过 {daily_sums} 题"
        weekly = "" if weekly_sums == 0 else f"，本周共通过 {weekly_sums} 题"
        content = (f"[Codeforces] {handle}\n\n"
                   f"{info}\n"
                   f"通过题数: {total_sums}\n\n"
                   f"{last_contest}\n\n"
                   f"{daily}{weekly}\n"
                   f"{last_submit}")
        await reply([content, avatar], event, finish=True)


async def send_user_last_submit(handle: str, count: int, event: MessageEvent):
    await reply([f"[Codeforces] 正在查询 {handle} 的 Codeforces 提交记录，请稍等..."], event, finish=False)

    info, _ = Codeforces.get_user_info(handle)

    if info is None:
        content = (f"[Codeforces] {handle}\n\n"
                   f"用户不存在")
    else:
        last_submit = Codeforces.get_user_last_submit(handle, count)
        content = (f"[Codeforces] {handle}\n\n"
                   f"{last_submit}")

    await reply([content], event, finish=True)


async def send_contest(event: MessageEvent):
    await reply([f"[Codeforces] 正在查询近期 Codeforces 比赛，请稍等..."], event, finish=False)

    contest_list = Codeforces._fetch_contest_list_all()
    if contest_list is None:
        content = "[Codeforces] 查询异常"
    else:
        upcoming = [c for c in contest_list if c['phase'] == 'BEFORE']
        content = "[Codeforces] 近期比赛\n\n"
        if len(upcoming) > 0:
            for contest in upcoming[:5]:  # 只显示前5个
                content += f"[{contest['id']}] {contest['name']}\n"
                content += f"开始时间: {format_timestamp(contest['startTimeSeconds'])}\n"
                content += f"持续时间: {format_seconds(contest['durationSeconds'])}\n\n"
        else:
            content += "暂无即将开始的比赛"

    await reply([content], event, finish=True)


async def send_user_contest_standings(handle: str, contest_id: str, event: MessageEvent):
    await reply([f"[Codeforces Standings] 正在查询编号为 {contest_id} 的比赛中 {handle} 的榜单信息，请稍等...\n"
                 f"查询对象为参赛者时将会给出 Rating 变化预估，但可能需要更久的时间"], event, finish=False)

    contest_info, standings_info = Codeforces.get_user_contest_standings(
        handle, contest_id)

    content = (f"[Codeforces] {handle} 比赛榜单查询\n\n"
               f"{contest_info}")
    if standings_info is not None:
        if len(standings_info) > 0:
            content += '\n\n'
            content += '\n\n'.join(standings_info)
        else:
            content += '\n\n暂无榜单信息'

    await reply([content], event, finish=True)


async def send_prob_filter_tag(tag: str, limit: str = None, newer: bool = False, event: MessageEvent = None) -> bool:
    if event:
        await reply(["[Codeforces Pick] 正在随机选题，请稍等..."], event, finish=False)

    async def on_tag_chosen_callback(x: str):
        if event:
            await reply([x], event, finish=False)

    chosen_prob = await Codeforces.get_prob_filtered(tag, limit, newer, on_tag_chosen=on_tag_chosen_callback)

    if isinstance(chosen_prob, int) and chosen_prob < 0:
        return False

    if isinstance(chosen_prob, int):
        if event:
            await reply(["[Codeforces Pick] 条件不合理或过于苛刻，无法找到满足条件的题目..."], event, finish=True)
        return False
    tags = ', '.join(chosen_prob['tags'])
    content = (f"[Codeforces] 随机选题\n\n"
               f"P{chosen_prob['contestId']}{chosen_prob['index']} {chosen_prob['name']}\n\n"
               f"链接: [codeforces] /contest/{chosen_prob['contestId']}/problem/{chosen_prob['index']}\n"
               f"标签: {tags}")

    if 'rating' in chosen_prob:
        content += f"\n难度: *{chosen_prob['rating']}"

    qr_img = get_simple_qrcode(
        f"https://codeforces.com/contest/{chosen_prob['contestId']}/problem/{chosen_prob['index']}")
    img_byte = BytesIO()
    qr_img.save(img_byte, format='PNG')
    if event:
        await reply([content, img_byte.getvalue()], event, finish=True)

    return True


async def send_prob_tags(event: MessageEvent):
    await reply(["[Codeforces] 正在查询 Codeforces 平台的所有问题标签，请稍等..."], event, finish=False)
    prob_tags = Codeforces.get_prob_tags_all()
    if prob_tags is None:
        content = "查询异常"
    else:
        content = "\n[Codeforces] 问题标签:\n"
        for tag in prob_tags:
            content += "\n" + tag

    await reply([content], event, finish=True)


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
    is_private: bool = False  # 发起者是否为私聊


_duelist_info: dict[str, DuelistInfo] = {}
_duel_pairing_info: dict[str, PairingInfo] = {}
_duelist_info_lock = threading.Lock()
_duel_pairing_info_lock = threading.Lock()


def _check_duelist_fresh(user_id: str, event: MessageEvent) -> int:
    with _duelist_info_lock:
        if user_id in _duelist_info:
            return -1
    return 0


async def send_binding(event: MessageEvent):
    user_id = str(event.user_id)
    user = get_binding(user_id)
    reply_tip = ""
    if user.bind_status == BindStatus.UNBOUNDED:
        await reply(["你当前未绑定任何 Codeforces 账号，请使用 /cf bind [handle] 进行绑定"], event, finish=True)
        return
    if user.bind_status == BindStatus.BINDING:
        validate_status = Codeforces.validate_binding(
            user.handle, user.establish_binding_time)
        if validate_status:
            validate_status &= (accept_binding(user_id, user) == 0)
        if not validate_status:
            await reply(["绑定失败，请确保你使用了正确的账号，并在绑定开始的 10 分钟内完成了提交"], event, finish=True)
            return
        reply_tip = "绑定成功！\n"

    await reply([f"{reply_tip}你当前绑定的账号 [{user.handle}]\n\n"
                 f"潜力值：{user.ptt}\n"
                 f"对战数：{len(user.contest_history)}"], event, finish=True)


async def start_binding(handle: str, event: MessageEvent):
    user_id = str(event.user_id)
    user = get_binding(user_id)

    user_info = Codeforces.get_user_info(handle)
    if user_info[0] == "用户不存在":
        await reply([f"用户 [{handle}] 不存在，请检查用户名是否正确"], event, finish=True)
        return

    establish_status = establish_binding(user_id, user, handle)
    if establish_status == -1:
        await reply(["你已经开始绑定，请不要重复操作"], event, finish=True)
        return
    if establish_status == -2:
        await reply(["你已经绑定账号，请不要重复绑定。\n"
                     "如需切换账号，请先使用 /cf unbind 进行解绑。解绑后你的对战数据会保留。"], event, finish=True)
        return

    qr_img = get_simple_qrcode("https://codeforces.com/contest/1/submit")
    img_byte = BytesIO()
    qr_img.save(img_byte, format='PNG')

    await reply([f"你当前正在绑定 [{handle}]\n\n"
                 "请在 10 分钟内，使用该账号在 P1A 提交一发 CE (编译错误)\n"
                 "提交成功后，请回复 /cf bind 以确认绑定",
                 img_byte.getvalue()], event, finish=True)


async def start_unbinding(event: MessageEvent):
    user_id = str(event.user_id)
    user = get_binding(user_id)
    unbind_status = unbind(user_id, user)
    if unbind_status == -1:
        await reply(["你还未绑定账号，无法解绑"], event, finish=True)
        return

    await reply(["解绑成功"], event, finish=True)


async def start_duel_pairing(prob_info: ProbInfo, event: MessageEvent):
    user_id = str(event.user_id)
    if _check_duelist_fresh(user_id, event) != 0:
        await reply(["你已经在对战中，请不要重复发起"], event, finish=True)
        return

    validation_status = Codeforces.validate_prob_filtered(prob_info,
                                                          on_tag_chosen=lambda x: None)
    if not validation_status:
        await reply(["请输入正确的指令格式，题目标签不要带有空格，如:\n\n"
                     "/cf duel start dp 1700-1900 new\n"
                     "/cf duel start dfs-and-similar\n"
                     "/cf duel start all 1800"], event, finish=True)
        return

    with _duel_pairing_info_lock:
        old_pair_code = next((pair_code
                              for pair_code, info in _duel_pairing_info.items()
                              if info.user_id == user_id),
                             None)
        if old_pair_code is not None:
            await reply(["你已经发起对战请求，请不要重复操作\n\n"
                         f"上一次请求的配对码为 {old_pair_code}"], event, finish=True)
            return

        pair_code = ""
        while len(pair_code) == 0 or pair_code in _duel_pairing_info:
            pair_code = ''.join(random.choices(string.hexdigits, k=6))

        # 判断是否为私聊（没有 group_id 即为私聊）
        is_private = not hasattr(event, 'group_id') or getattr(
            event, 'group_id', None) is None
        _duel_pairing_info[pair_code] = PairingInfo(
            user_id, prob_info, is_private)

    await reply(["已发起对战请求，请对手发送下面的指令以接受对战\n\n"
                 f"/cf duel accept {pair_code}"], event, finish=True)


async def accept_duel_pairing(pair_code: str, event: MessageEvent):
    user_id = str(event.user_id)
    user = get_binding(user_id)
    if _check_duelist_fresh(user_id, event) != 0:
        await reply(["你已经在对战中，请不要重复发起"], event, finish=True)
        return

    with _duel_pairing_info_lock:
        if pair_code not in _duel_pairing_info:
            await reply(["配对码无效，建议直接复制粘贴"], event, finish=True)
            return
        pairing_info = copy.deepcopy(_duel_pairing_info[pair_code])
        del _duel_pairing_info[pair_code]

    opponent_id = pairing_info.user_id
    opponent = get_binding(opponent_id)

    # 检查是否是自己和自己对战
    if user_id == opponent_id:
        await reply(["不能和自己对战"], event, finish=True)
        return

    # 验证对手绑定状态
    if opponent.bind_status != BindStatus.BOUND:
        await reply(["对手账号状态异常，无法开始对战"], event, finish=True)
        return

    if user.bind_status != BindStatus.BOUND:
        await reply(["你还没有绑定账号，请使用 /cf bind [handle] 进行绑定"], event, finish=True)
        return

    await reply(["成功接受对战，正在进行随机选题"], event, finish=False)

    r_a, r_b = Codeforces.get_user_rating(
        user.handle), Codeforces.get_user_rating(opponent.handle)
    if r_a is None:
        await reply(["你的账号状态异常，无法开始对战"], event, finish=True)
        return
    if r_b is None:
        await reply(["对手的账号状态异常，无法开始对战"], event, finish=True)
        return

    r_avg = (r_a + r_b) // 2

    excludes = set()
    excludes.update(Codeforces.get_user_submit_prob_id(user.handle))
    excludes.update(Codeforces.get_user_submit_prob_id(opponent.handle))

    prob_info = pairing_info.prob_info

    # 使用带 fallback 的统一选题函数
    chosen_prob = Codeforces.get_prob_filtered_with_fallback(
        prob_info, excludes, r_avg)

    if not chosen_prob:
        await reply(["随机选题异常，请稍后重新发起对战"], event, finish=True)
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

    tags = ', '.join(chosen_prob['tags'])
    content = (f"[Codeforces] 随机选题\n\n"
               f"P{chosen_prob['contestId']}{chosen_prob['index']} {chosen_prob['name']}\n\n"
               f"链接: [codeforces] /contest/{chosen_prob['contestId']}/problem/{chosen_prob['index']}\n"
               f"标签: {tags}")

    if 'rating' in chosen_prob:
        content += f"\n难度: *{chosen_prob['rating']}"

    qr_img = get_simple_qrcode(
        f"https://codeforces.com/contest/{chosen_prob['contestId']}/problem/{chosen_prob['index']}")
    img_byte = BytesIO()
    qr_img.save(img_byte, format='PNG')
    img_bytes = img_byte.getvalue()  # 保存字节数据以便多次使用

    # 判断当前接受者是否为私聊
    accepter_is_private = not hasattr(event, 'group_id') or getattr(
        event, 'group_id', None) is None

    # 如果双方都是私聊，也需要给发起者发送题目
    if pairing_info.is_private and accepter_is_private:
        opponent_target = TargetQQPrivate(user_id=int(opponent_id))
        await send(["对战开始！\n\n"
                    "任意一方通过后发送 /cf duel finish 即可进行结算\n"
                    "若双方均通过，则根据 ICPC 罚时规则进行结算",
                    content, img_bytes], opponent_target)

    await reply(["对战开始！\n\n"
                 "任意一方通过后发送 /cf duel finish 即可进行结算\n"
                 "若双方均通过，则根据 ICPC 罚时规则进行结算",
                 content, img_bytes], event, finish=True)


async def finish_duel(event: MessageEvent):
    user_id = str(event.user_id)
    user = get_binding(user_id)

    with _duelist_info_lock:
        if user_id not in _duelist_info:
            await reply(["你没有在对战中，无法结束对战"], event, finish=True)
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
            await reply(["获取提交状态失败，请稍后重试"], event, finish=True)
            return

        ac_me, penalty_me = status_me
        ac_op, penalty_op = status_op
        del _duelist_info[user_id]
        del _duelist_info[opponent_id]

    if not ac_me and not ac_op:
        await reply(["对战结束，无人过题"], event, finish=True)
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

    settle_duel(user_id, user, opponent_id, opponent, outcome,
                duel_info.problem.get('rating', 1500))

    # 计算潜力值变化
    user_delta = user.contest_history[-1] - \
        user.contest_history[-2] if len(user.contest_history) >= 2 else 0
    opponent_delta = opponent.contest_history[-1] - opponent.contest_history[-2] if len(
        opponent.contest_history) >= 2 else 0

    await reply([f'对战结束，判定为 {"你获胜" if outcome == 0 else "对方获胜" if outcome == 1 else "平局"}\n\n'
                 f'你: {"通过" if ac_me else "未通过"}，罚时 {penalty_me}'
                 f'，潜力值变化 {format_int_delta(user_delta)}\n'
                 f'对方: {"通过" if ac_op else "未通过"}，罚时 {penalty_op}'
                 f'，潜力值变化 {format_int_delta(opponent_delta)}'],
                event, finish=True)


regular_handler = on_command(('cf', 'help'), rule=to_me(),
                             aliases={('cf', command)
                                      for command in supported_commands},
                             priority=Constants.PLATFORM_PRIOR, block=True)

fullname_handler = on_command(('codeforces', 'help'), rule=to_me(),
                              aliases={('codeforces', command)
                                       for command in supported_commands},
                              priority=Constants.PLATFORM_PRIOR, block=True)

help_trigger = on_command('cf', rule=to_me(), aliases={
                          'codeforces'}, priority=Constants.HELP_PRIOR, block=True)


@help_trigger.handle()
@with_help("Codeforces")
async def handle_help():
    """
    显示 Codeforces 模块的帮助信息
    指令: /cf, /codeforces
    """
    await reply_help("Codeforces")


@regular_handler.handle()
@fullname_handler.handle()
@with_help("Codeforces")
async def handle_regular(event: MessageEvent, command: tuple[str, str] = Command(), message: Message = CommandArg()):
    """
    Codeforces 平台相关功能

    可用指令:
    /cf.info [handle] 或 /cf.user [handle]: 查询用户信息
    /cf.recent [handle] [count]: 查询用户最近提交记录（count可选，默认5，最多100）
    /cf.contests: 查询近期比赛
    /cf.status [handle] [contestId] 或 /cf.standing [handle] [contestId]: 查询用户在比赛中的排名
    /cf.pick [tag|all] [难度范围] [new]: 随机选题（tag为标签或all，难度范围如1700-1900，new表示仅新题）
    /cf.tags 或 /cf.tag: 显示所有可用标签
    /cf.bind [handle]: 绑定 Codeforces 账号
    /cf.unbind: 解绑 Codeforces 账号
    /cf.duel start [标签|all] (难度) (new): 开始对战
    /cf.duel accept [pair_code]: 同意对战请求
    /cf.duel finish: 结束本次对战

    别名: /codeforces.[command]
    """
    try:
        func = command[1]
        args = message.extract_plain_text().split()
        if func == "info" or func == "user":
            if len(args) != 1:
                await reply([f"请输入正确的指令格式，如\"/cf.{func} jiangly\""], event, finish=True)
            handle = args[0]
            await send_user_info(handle, event)

        elif func == "recent":
            if len(args) not in [1, 2]:
                await reply(["请输入正确的指令格式，如\"/cf.recent jiangly 5\""], event, finish=True)
            handle = args[0]
            count = 5
            if len(args) == 2:
                if not (check_is_int(args[1]) and int(args[1]) > 0 and int(args[1]) <= 100):
                    await reply(["请输入正确的查询参数，允许查询最多100条近期数据。"], event, finish=True)
                else:
                    count = int(args[1])
            await send_user_last_submit(handle, count, event)

        elif func == "contests":
            await send_contest(event)

        elif func == "status" or func == "standing":
            if len(args) != 2:
                await reply(["请输入正确的指令格式，如:\n\n"
                             f"/cf.{func} jiangly 2057"], event, finish=True)
            else:
                handle, contestId = args
                await send_user_contest_standings(handle, contestId, event)
        elif func == "pick":
            # [标签|all] (难度) (new)
            tag = args[0]
            limit = args[1] if len(args) >= 3 and args[1] != "new" else None
            newer = False
            for arg in args:
                newer = newer or arg == 'new'
            if len(args) < 2 or not await send_prob_filter_tag(tag=tag, limit=limit, newer=newer, event=event):
                func_prefix = f"/cf pick"
                await reply(["请输入正确的指令格式，题目标签不要带有空格，如:\n\n"
                             f"{func_prefix} dp 1700-1900 new\n"
                             f"{func_prefix} dfs-and-similar\n"
                             f"{func_prefix} all 1800"], event, finish=True)
        elif func == "tags" or func == 'tag':
            await send_prob_tags(event)
        elif func == "bind":
            if len(args) == 0:
                await send_binding(event)
            else:
                await start_binding(args[0], event)
        elif func == "unbind":
            await start_unbinding(event)
        elif func == "duel":
            user_id = str(event.user_id)
            user = get_binding(user_id)
            if user.bind_status != BindStatus.BOUND:
                await reply(["你还没有绑定账号，请使用 /cf bind [handle] 进行绑定"], event, finish=True)
            elif len(args) >= 1 and args[0] == "finish":
                await finish_duel(event)
            elif len(args) >= 2 and args[0] == "accept":
                await accept_duel_pairing(args[1], event)
            elif len(args) >= 2 and args[0] == "start":
                tag = args[1]
                limit = args[2] if len(
                    args) >= 3 and args[2] != "new" else None
                newer = False
                for arg in args:
                    newer = newer or arg == 'new'
                await start_duel_pairing(ProbInfo(
                    tag=tag,
                    limit=limit,
                    newer=newer
                ), event)
            else:
                await reply(['Codeforces 对战模块\n\n'
                             '/cf duel start [标签|all] (难度) (new): '
                             '开始对战，题目从 Codeforces 上随机选取. 标签中间不能有空格，支持模糊匹配. 难度为整数或一个区间，格式为 xxx-xxx. '
                             '末尾加上 new 参数则会忽视 P1000A 以前的题.\n'
                             '/cf duel accept [pair_code]: 同意对战请求\n'
                             '/cf duel finish: 结束本次对战'], event, finish=True)
        else:
            await reply_help("Codeforces", "", False)
    except Exception as e:
        await report_exception(event, "Codeforces", e)
