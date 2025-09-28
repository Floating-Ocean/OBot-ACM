import re

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants, HelpStrList
from src.core.util.tools import check_is_int, png2jpg
from src.data.data_cache import get_cached_prefix
from src.platform.online.nowcoder import NowCoder
from src.render.pixie.render_contest_list import ContestListRenderer

_NK_HELP = '\n'.join(HelpStrList(Constants.help_contents["nowcoder"]))


def send_user_id_card(message: RobotMessage, handle: str):
    message.reply(f"正在查询 {handle} 的 NowCoder 基础信息，请稍等")

    id_card = NowCoder.get_user_id_card(handle)
    if not id_card:
        content = (f"[NowCoder ID] {handle}"
                   "用户不存在")
        message.reply(content, modal_words=False)
    else:
        cached_prefix = get_cached_prefix('Platform-ID')
        id_card.write_file(f"{cached_prefix}.png")
        message.reply(f"[NowCoder] {handle}", png2jpg(f"{cached_prefix}.png"), modal_words=False)


def send_user_info(message: RobotMessage, handle: str):
    message.reply(f"正在查询 {handle} 的 NowCoder 平台信息，请稍等")

    user = NowCoder.get_user_info(handle)
    if not user:
        content = (f"[NowCoder] {handle}\n\n"
                   "用户不存在")
        avatar = None
    else:
        info, avatar = user
        last_contest = NowCoder.get_user_last_contest(handle)
        content = (f"[NowCoder] {handle}\n\n"
                   f"{info}\n\n"
                   f"{last_contest}")

    message.reply(content, img_url=avatar, modal_words=False)


def send_contest(message: RobotMessage):
    message.reply("正在查询近期 NowCoder 比赛，请稍等")

    running, upcoming, finished = NowCoder.get_contest_list()

    cached_prefix = get_cached_prefix('Contest-List-Renderer')
    contest_list_img = ContestListRenderer(running, upcoming, finished).render()
    contest_list_img.write_file(f"{cached_prefix}.png")

    message.reply("[NowCoder] 近期比赛", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['nk', 'nc', 'nowcoder'])
def reply_nk_request(message: RobotMessage):
    try:
        content = re.sub(r'<@!\d+>', '', message.content).strip().split()
        if len(content) < 2:
            message.reply(f'[NowCoder]\n\n{_NK_HELP}', modal_words=False)
            return

        func = content[1]

        if func == "identity" or func == "id" or func == "card":
            if len(content) != 3:
                message.reply(f"请输入正确的指令格式，如\"/nk {func} 329687984\"")
                return

            if not check_is_int(content[2]):
                message.reply("暂不支持使用昵称检索用户，请使用uid")
                return

            send_user_id_card(message, content[2])

        elif func == "info" or func == "user":
            if len(content) != 3:
                message.reply(f"请输入正确的指令格式，如\"/nk {func} 329687984\"")
                return

            if not check_is_int(content[2]):
                message.reply("暂不支持使用昵称检索用户，请使用uid")
                return

            send_user_info(message, content[2])

        elif func == "contest" or func == "contests":
            send_contest(message)

        else:
            message.reply(f'[NowCoder]\n\n{_NK_HELP}', modal_words=False)

    except Exception as e:
        message.report_exception('NowCoder', e)


@module(
    name="NowCoder",
    version="v1.3.0"
)
def register_module():
    pass
