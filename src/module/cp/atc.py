from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants, HelpStrList
from src.core.util.tools import get_simple_qrcode, png2jpg
from src.data.data_cache import get_cached_prefix
from src.platform.online.atcoder import AtCoder
from src.render.pixie.render_contest_list import ContestListRenderer

_ATC_HELP = '\n'.join(HelpStrList(Constants.help_contents["atcoder"]))


def send_user_id_card(message: RobotMessage, handle: str):
    message.reply(f"正在查询 {handle} 的 AtCoder 基础信息，请稍等")

    id_card = AtCoder.get_user_id_card(handle)

    if not id_card:
        content = (f"[AtCoder ID] {handle}\n\n"
                   "用户不存在")
        message.reply(content, modal_words=False)
    else:
        cached_prefix = get_cached_prefix('Platform-ID')
        id_card.write_file(f"{cached_prefix}.png")
        message.reply(f"[AtCoder] {handle}", png2jpg(f"{cached_prefix}.png"), modal_words=False)


def send_user_info(message: RobotMessage, handle: str):
    message.reply(f"正在查询 {handle} 的 AtCoder 平台信息，请稍等")

    user = AtCoder.get_user_info(handle)
    if user is None:
        content = (f"[AtCoder] {handle}\n\n"
                   "用户不存在")
        avatar = None
    else:
        info, avatar = user
        last_contest = AtCoder.get_user_last_contest(handle)
        content = (f"[AtCoder] {handle}\n\n"
                   f"{info}\n\n"
                   f"{last_contest}")

    message.reply(content, img_url=avatar, modal_words=False)


def send_prob_filter_tag(message: RobotMessage, contest_type: str, limit: str = None) -> bool:
    message.reply("正在随机选题，请稍等")

    chosen_prob = AtCoder.get_prob_filtered(contest_type, limit)

    if isinstance(chosen_prob, int) and chosen_prob < 0:
        return False

    if isinstance(chosen_prob, int):
        message.reply("条件不合理或过于苛刻，无法找到满足条件的题目")
        return True

    abbr = chosen_prob['url'].split('/')[-1].capitalize()
    link = chosen_prob['url'].replace('https://atcoder.jp', '')
    content = (f"[AtCoder] 随机选题\n\n"
               f"{abbr} {chosen_prob['name']}\n\n"
               f"链接: [atcoder] {link}")

    if 'rating' in chosen_prob:
        content += f"\n难度: *{chosen_prob['rating']}"

    cached_prefix = get_cached_prefix('QRCode-Generator')
    qr_img = get_simple_qrcode(chosen_prob['url'])
    qr_img.save(f"{cached_prefix}.png")

    message.reply(content, png2jpg(f"{cached_prefix}.png"), modal_words=False)

    return True


def send_contest(message: RobotMessage):
    message.reply("正在查询近期 AtCoder 比赛，请稍等")

    running, upcoming, finished = AtCoder.get_contest_list()

    cached_prefix = get_cached_prefix('Contest-List-Renderer')
    contest_list_img = ContestListRenderer(running, upcoming, finished).render()
    contest_list_img.write_file(f"{cached_prefix}.png")

    message.reply("[AtCoder] 近期比赛", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['atc', 'atcoder'])
def reply_atc_request(message: RobotMessage):
    try:
        content = message.tokens
        if len(content) < 2:
            message.reply(f'[AtCoder]\n\n{_ATC_HELP}', modal_words=False)
            return

        func = content[1]

        if func == "identity" or func == "id" or func == "card":
            if len(content) != 3:
                message.reply(f"请输入正确的指令格式，如\"/atc {func} jiangly\"")
                return

            send_user_id_card(message, content[2])

        elif func == "info" or func == "user":
            if len(content) != 3:
                message.reply(f"请输入正确的指令格式，如\"/atc {func} jiangly\"")
                return

            send_user_info(message, content[2])

        elif func == "pick" or func == "prob" or func == "problem" or (
                content[0] == "/rand" and func == "atc"):  # 让此处能被 /rand 模块调用
            if len(content) < 3 or not send_prob_filter_tag(
                    message=message,
                    contest_type=content[2],
                    limit=content[3] if len(content) >= 4 else None
            ):
                func_prefix = f"/atc {func}"
                if func == "atc":
                    func_prefix = "/rand atc"
                message.reply("请输入正确的指令格式，题目标签不要带有空格，如:\n\n"
                              f"{func_prefix} common\n"
                              f"{func_prefix} abc\n"
                              f"{func_prefix} sp 1200-1600\n"
                              f"{func_prefix} all 1800", modal_words=False)

        elif func == "contest" or func == "contests":
            send_contest(message)

        else:
            message.reply(f'[AtCoder]\n\n{_ATC_HELP}', modal_words=False)

    except Exception as e:
        message.report_exception('AtCoder', e)


@module(
    name="AtCoder",
    version="v1.4.0"
)
def register_module():
    pass
