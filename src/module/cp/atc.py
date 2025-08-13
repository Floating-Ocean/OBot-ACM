from nonebot import on_command
from nonebot.adapters import Event, Message
from nonebot.params import CommandArg

from src.core.bot.decorator import module
from src.core.bot.message import reply
from src.core.constants import Constants, HelpStrList
from src.core.util.tools import get_simple_qrcode, png2jpg, download_img
from src.data.data_cache import get_cached_prefix
from src.platform.online.atcoder import AtCoder

_ATC_HELP = '\n'.join(HelpStrList(Constants.help_contents["atcoder"]))

id_query = on_command(('atc', 'id'), aliases={('atcoder', 'id'), ('atc', 'identity'), ('atcoder', 'identity'),
                                              ('atc', 'card'), ('atcoder', 'card')}, priority=50, block=True)

info_query = on_command(('atc', 'info'), aliases={('atcoder', 'info'), ('atc', 'user'), ('atcoder', 'user')},
                        priority=50, block=True)

contest_query = on_command(('atc', 'contest'),
                           aliases={('atcoder', 'contest'), ('atc', 'contests'), ('atcoder', 'contests')}, priority=50,
                           block=True)

random_pick_query = on_command(('atc', 'pick'),
                               aliases={('atcoder', 'pick'), ('atc', 'prob'), ('atcoder', 'prob'), ('atc', 'problem'),
                                        ('atcoder', 'problem')}, priority=50, block=True)

help_query = on_command('atc', aliases={'atcoder'}, priority=500, block=True)


@id_query.handle()
async def send_user_id_card(event: Event, message: Message = CommandArg()):
    if message.extract_plain_text().strip() == "":
        await reply(['请输入用户的 AtCoder ID，如"/atc id jiangly"'], event, modal_words=False, finish=True)
    handle = message.extract_plain_text().strip()
    await reply([f"正在查询 {handle} 的 AtCoder 基础信息，请稍等"], event, modal_words=False, finish=False)

    id_card = AtCoder.get_user_id_card(handle)

    if isinstance(id_card, str):
        content = [f"[AtCoder ID] {handle}", f"{id_card}"]
        await reply(content, event, False, True)
    else:
        cached_prefix = get_cached_prefix('Platform-ID')
        id_card.write_file(f"{cached_prefix}.png")
        await reply([f"[AtCoder] {handle}", png2jpg(f"{cached_prefix}.png")], event, False, True)


@info_query.handle()
async def send_user_info(event: Event, message: Message = CommandArg()):
    if message.extract_plain_text().strip() == "":
        await reply(['请输入用户的 AtCoder ID，如"/atc info jiangly"'], event, modal_words=False, finish=True)
    handle = message.extract_plain_text().strip()
    await reply([f"正在查询 {handle} 的 AtCoder 平台信息，请稍等"], event, modal_words=False, finish=False)

    info, avatar = AtCoder.get_user_info(handle)
    if avatar is None:
        content = [f"[AtCoder] {handle}\n\n", f"{info}"]
    else:
        cached_prefix = get_cached_prefix('atcoder-platform')
        download_img(avatar, f"{cached_prefix}.png")
        last_contest = AtCoder.get_user_last_contest(handle)
        content = [f"[AtCoder] {handle}\n\n",
                   f"{info}\n\n",
                   f"{last_contest}", png2jpg(f"{cached_prefix}.png")]

    await reply(content, event, modal_words=False, finish=True)


@random_pick_query.handle()
async def send_random_pick(event: Event, message: Message = CommandArg()):
    if message.extract_plain_text().strip() == "":
        await reply(['请输入正确的指令格式，题目标签不要带有空格，如:\n\n'
                     '/atc pick common\n'
                     '/atc pick abc\n'
                     '/atc pick sp 1200-1600\n'
                     '/atc pick all 1800'], event, modal_words=False, finish=True)
        return
    await reply(["正在随机选题，请稍等"], event, modal_words=False, finish=False)
    content = message.extract_plain_text().strip().split()
    if len(content) == 1:
        problem_tag = content[0]
        limit = None
    else:
        problem_tag, limit = content
    chosen_prob = AtCoder.get_prob_filtered(problem_tag, limit)
    if isinstance(chosen_prob, int) and chosen_prob < 0:
        await reply(["条件不合理或过于苛刻，无法找到满足条件的题目"], event, modal_words=False, finish=True)
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
    await reply([*content, png2jpg(f"{cached_prefix}.png")], event, modal_words=False, finish=True)


@contest_query.handle()
async def send_contest(event: Event):
    await reply(["正在查询近期 AtCoder 比赛，请稍等"], event, finish=False)
    info = AtCoder.get_recent_contests()
    await reply([f"[AtCoder] 近期比赛\n\n", f"{info}"], event, modal_words=False)


@help_query.handle()
async def send_help(event: Event):
    await reply([f'[AtCoder]\n\n{_ATC_HELP}'], event, False, True)


@module(
    name="AtCoder",
    version="v1.3.1"
)
def register_module():
    pass
