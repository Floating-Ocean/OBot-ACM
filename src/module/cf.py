import re
import traceback

from src.core.bot.command import command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.output_cached import get_cached_prefix
from src.core.util.tools import check_is_int, get_simple_qrcode, png2jpg
from src.platform.online.codeforces import Codeforces

__cf_version__ = "v3.1.2"


def register_module():
    pass


def send_user_id_card(message: RobotMessage, handle: str):
    message.reply(f"正在查询 {handle} 的 Codeforces 基础信息，请稍等")

    id_card = Codeforces.get_user_id_card(handle)

    if isinstance(id_card, str):
        content = (f"[Codeforces ID] {handle}"
                   f"{id_card}")
        message.reply(content, modal_words=False)
    else:
        cached_prefix = get_cached_prefix('Platform-ID')
        id_card.write_file(f"{cached_prefix}.png")
        message.reply(f"[Codeforces] {handle}", png2jpg(f"{cached_prefix}.png"), modal_words=False)


def send_user_info(message: RobotMessage, handle: str):
    message.reply(f"正在查询 {handle} 的 Codeforces 平台信息，请稍等")

    info, avatar = Codeforces.get_user_info(handle)

    if avatar is None:
        content = (f"[Codeforces] {handle}\n\n"
                   f"{info}")
    else:
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

    info, _ = Codeforces.get_user_info(handle)

    if info is None:
        content = (f"[Codeforces] {handle}\n\n"
                   f"用户不存在")
    else:
        last_submit = Codeforces.get_user_last_submit(handle, count)
        content = (f"[Codeforces] {handle}\n\n"
                   f"{last_submit}")

    message.reply(content, modal_words=False)


def send_prob_tags(message: RobotMessage):
    message.reply("正在查询 Codeforces 平台的所有问题标签，请稍等")

    prob_tags = Codeforces.get_prob_tags_all()

    if prob_tags is None:
        content = "查询异常"
    else:
        content = "\n[Codeforces] 问题标签:\n"
        for tag in prob_tags:
            content += "\n" + tag

    message.reply(content, modal_words=False)


def send_prob_filter_tag(message: RobotMessage, tag: str, limit: str = None, newer: bool = False) -> bool:
    message.reply("正在随机选题，请稍等")

    chosen_prob = Codeforces.get_prob_filtered(tag, limit, newer,
                                               on_tag_chosen=lambda x: message.reply(x))

    if isinstance(chosen_prob, int) and chosen_prob < 0:
        return False

    if isinstance(chosen_prob, int):
        message.reply("条件不合理或过于苛刻，无法找到满足条件的题目")
        return True

    tags = ', '.join(chosen_prob['tags'])
    content = (f"[Codeforces] 随机选题\n\n"
               f"P{chosen_prob['contestId']}{chosen_prob['index']} {chosen_prob['name']}\n\n"
               f"链接: [codeforces] /contest/{chosen_prob['contestId']}/problem/{chosen_prob['index']}\n"
               f"标签: {tags}")

    if 'rating' in chosen_prob:
        content += f"\n难度: *{chosen_prob['rating']}"

    cached_prefix = get_cached_prefix('QRCode-Generator')
    qr_img = get_simple_qrcode(
        f"https://codeforces.com/contest/{chosen_prob['contestId']}/problem/{chosen_prob['index']}")
    qr_img.save(f"{cached_prefix}.png")

    message.reply(content, png2jpg(f"{cached_prefix}.png"), modal_words=False)

    return True


def send_contest(message: RobotMessage):
    message.reply(f"正在查询近期 Codeforces 比赛，请稍等")

    info = Codeforces.get_recent_contests()

    content = (f"[Codeforces] 近期比赛\n\n"
               f"{info}")

    message.reply(content, modal_words=False)


def send_user_contest_standings(message: RobotMessage, handle: str, contest_id: str):
    message.reply(f"正在查询编号为 {contest_id} 的比赛中 {handle} 的榜单信息，请稍等。\n"
                        f"查询对象为参赛者时将会给出 Rating 变化预估，但可能需要更久的时间")

    contest_info, standings_info = Codeforces.get_user_contest_standings(handle, contest_id)

    content = (f"[Codeforces] {handle} 比赛榜单查询\n\n"
               f"{contest_info}")
    if standings_info is not None:
        if len(standings_info) > 0:
            content += '\n\n'
            content += '\n\n'.join(standings_info)
        else:
            content += '\n\n暂无榜单信息'

    message.reply(content, modal_words=False)


def send_logo(message: RobotMessage):
    message.reply("[Codeforces] 网站当前的图标", img_url=Codeforces.logo_url)


@command(tokens=['cf', 'codeforces'])
def reply_cf_request(message: RobotMessage):
    try:
        content = re.sub(r'<@!\d+>', '', message.content).strip().split()
        if len(content) < 2:
            message.reply(f'[Codeforces]\n\n{Constants.help_contents["codeforces"]}', modal_words=False)
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
                    tag=content[2],
                    limit=content[3] if len(content) >= 4 and content[3] != "new" else None,
                    newer=content[3] == "new" if len(content) == 4 else (
                            content[4] == "new" if len(content) == 5 else False)
            ):
                func_prefix = f"/cf {func}"
                if func == "cf":
                    func_prefix = "/rand cf"
                message.reply("请输入正确的指令格式，题目标签不要带有空格，如:\n\n"
                                    f"{func_prefix} dp 1700-1900 new\n"
                                    f"{func_prefix} dfs-and-similar\n"
                                    f"{func_prefix} all 1800", modal_words=False)

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

        else:
            message.reply(f'[Codeforces]\n\n{Constants.help_contents["codeforces"]}', modal_words=False)

    except Exception as e:
        message.report_exception('Codeforces', traceback.format_exc(), e)
