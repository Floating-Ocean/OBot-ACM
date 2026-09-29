from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants, HelpStrList
from src.core.util.tools import check_is_int, png2jpg
from src.core.util.output_cache import get_cached_prefix
from src.platform.online.nowcoder import NowCoder
from src.render.pixie.render_contest_list import ContestListRenderer

_NK_HELP = '\n'.join(HelpStrList(Constants.help_contents["nowcoder"]))


def send_user_card(message: RobotMessage, handle: str):
    message.reply(f"正在查询 {handle} 的 NowCoder 信息，请稍等")

    user_card = NowCoder.get_user_card(handle)
    if not user_card:
        message.reply(f"[NowCoder] {handle}\n\n用户不存在", modal_words=False)
        return

    cached_prefix = get_cached_prefix('Platform-ID')
    user_card.write_file(f"{cached_prefix}.png")
    message.reply(f"[NowCoder] {handle}", png2jpg(f"{cached_prefix}.png"), modal_words=False)


def send_contest(message: RobotMessage):
    message.reply("正在查询近期 NowCoder 比赛，请稍等")

    running, upcoming, finished = NowCoder.get_contest_list()

    cached_prefix = get_cached_prefix('Contest-List-Renderer')
    contest_list_img = ContestListRenderer(running, upcoming, finished).render()
    contest_list_img.write_file(f"{cached_prefix}.png")

    message.reply("[NowCoder] 近期比赛", png2jpg(f"{cached_prefix}.png"))


def send_user_contest_standings(message: RobotMessage, search_name: str, contest_name: str):
    message.reply(f"正在查询匹配 {contest_name} 的比赛中 {search_name} 的榜单信息，请稍等")
    content = f"[NowCoder] {search_name} 比赛榜单查询\n\n"

    standings = NowCoder.get_user_contest_standings(search_name, contest_name)
    if not standings:
        content += "比赛不存在"
    else:
        contest_info, standings_info = standings
        content += f"{contest_info}\n\n"
        if len(standings_info) > 0:
            content += '\n\n'.join(standings_info[:10])
            if len(standings_info) > 10:
                content += "\n\n最多展示 10 条榜单信息"
        else:
            content += '暂无榜单信息'

    message.reply(content, modal_words=False)


@command(tokens=['nk', 'nc', 'nowcoder'])
def reply_nk_request(message: RobotMessage):
    try:
        content = message.tokens
        if len(content) < 2:
            message.reply(f'[NowCoder]\n\n{_NK_HELP}', modal_words=False)
            return

        func = content[1]

        if func in ["identity", "id", "card", "info", "user"]:
            if len(content) != 3:
                message.reply(f"请输入正确的指令格式，如\"/nk {func} 329687984\"")
                return

            if not check_is_int(content[2]):
                message.reply("暂不支持使用昵称检索用户，请使用uid")
                return

            send_user_card(message, content[2])

        elif func == "contest" or func == "contests":
            send_contest(message)

        elif func == "status" or func == "stand" or func == "standing" or func == "standings":
            if len(content) != 4:
                message.reply("请输入正确的指令格式，如:\n\n"
                              f"/nc {func} jiangly 2025牛客暑期多校训练营", modal_words=False)
            else:
                send_user_contest_standings(message, content[2], content[3])

        else:
            message.reply(f'[NowCoder]\n\n{_NK_HELP}', modal_words=False)

    except Exception as e:
        message.report_exception('NowCoder', e)


@module(
    name="NowCoder",
    version="v1.4.0"
)
def register_module():
    pass
