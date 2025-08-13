from nonebot import on_command
from nonebot.adapters import Event, Message
from nonebot.params import CommandArg

from src.core.bot.decorator import module
from src.core.bot.message import reply
from src.core.constants import Constants, HelpStrList
from src.core.util.tools import png2jpg, download_img
from src.data.data_cache import get_cached_prefix
from src.platform.online.nowcoder import NowCoder

_NK_HELP = '\n'.join(HelpStrList(Constants.help_contents["nowcoder"]))

id_query = on_command(('nk', 'id'), aliases={('nc', 'id'), ('nowcoder', 'id'), ('nk', 'identity'), ('nc', 'identity'),
                                             ('nowcoder', 'identity'), ('nk', 'card'), ('nc', 'card'),
                                             ('nowcoder', 'card')}, priority=50, block=True)

info_query = on_command(('nk', 'info'), aliases={('nc', 'info'), ('nowcoder', 'info'), ('nk', 'user'), ('nc', 'user'),
                                                 ('nowcoder', 'user')}, priority=50, block=True)

contest_query = on_command(('nk', 'contest'),
                           aliases={('nc', 'contest'), ('nowcoder', 'contest'), ('nk', 'contests'), ('nc', 'contests'),
                                    ('nowcoder', 'contests')}, priority=50, block=True)

help_query = on_command('nk', aliases={'nc', 'nowcoder'}, priority=500, block=True)


@id_query.handle()
async def send_user_id_card(event: Event, message: Message = CommandArg()):
    if message.extract_plain_text().strip() == "":
        await reply(['请输入用户的 NowCoder ID，如"/nk id 11111111"'], event, modal_words=False, finish=True)
    handle = message.extract_plain_text().strip()
    await reply([f"正在查询 {handle} 的 NowCoder 基础信息，请稍等"], event, modal_words=False, finish=False)

    id_card = NowCoder.get_user_id_card(handle)

    if isinstance(id_card, str):
        content = [f"[NowCoder ID] {handle}",
                   f"{id_card}"]
        await reply(content, event, False, True)
    else:
        cached_prefix = get_cached_prefix('Platform-ID')
        id_card.write_file(f"{cached_prefix}.png")
        await reply([f"[NowCoder] {handle}", png2jpg(f"{cached_prefix}.png")], event, False, True)


@info_query.handle()
async def send_user_info(event: Event, message: Message = CommandArg()):
    if message.extract_plain_text().strip() == "":
        await reply(['请输入用户的 NowCoder ID，如"/nk info 11111111"'], event, modal_words=False, finish=True)
    handle = message.extract_plain_text().strip()
    await reply([f"正在查询 {handle} 的 NowCoder 平台信息，请稍等"], event, modal_words=False, finish=False)

    info, avatar = NowCoder.get_user_info(handle)
    if avatar is None:
        content = [f"[NowCoder] {handle}\n\n"
            , f"{info}"]
    else:
        cached_prefix = get_cached_prefix('nowcoder-platform')
        download_img(avatar, f"{cached_prefix}.png")
        last_contest = NowCoder.get_user_last_contest(handle)
        content = [f"[NowCoder] {handle}\n\n",
                   f"{info}\n\n",
                   f"{last_contest}", png2jpg(f"{cached_prefix}.png")]

    await reply(content, event, modal_words=False, finish=True)


@contest_query.handle()
async def send_contest(event: Event):
    await reply(["正在查询近期 NowCoder 比赛，请稍等"], event, finish=False)
    info = NowCoder.get_recent_contests()
    await reply([f"[NowCoder] 近期比赛\n\n", f"{info}"], event, modal_words=False)


@help_query.handle()
async def send_help(event: Event):
    await reply([f'[NowCoder]\n\n{_NK_HELP}'], event, False, True)


@module(
    name="NowCoder",
    version="v1.2.1"
)
def register_module():
    pass
