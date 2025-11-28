import os
import re
import shutil

from thefuzz import process

from src.core.bot.decorator import command, get_all_modules_info, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.lib.huo_zi_yin_shua import HuoZiYinShua
from src.core.util.tools import png2jpg, get_simple_qrcode, check_intersect, get_today_timestamp_range, fetch_url_json
from src.data.data_cache import get_cached_prefix
from src.module.stuff.mc import reply_mc_sleep
from src.platform.manual.manual import ManualPlatform
from src.platform.online.atcoder import AtCoder
from src.platform.online.codeforces import Codeforces
from src.platform.online.nowcoder import NowCoder
from src.render.pixie.render_about import AboutRenderer
from src.render.pixie.render_contest_list import ContestListRenderer
from src.render.pixie.render_help import HelpRenderer

_FIXED_REPLY = {
    "ping": "pong",
    "活着吗": "你猜捏",
    "似了吗": "？",
    "死了吗": "？？？"
}

_project_dir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
)


@command(tokens=list(_FIXED_REPLY.keys()))
def reply_fixed(message: RobotMessage):
    message.reply(_FIXED_REPLY.get(message.tokens[0][1:], ""), modal_words=False)


@command(tokens=['contest', 'contests', '比赛', '近日比赛', '最近的比赛', '今天比赛', '今天的比赛', '今日比赛',
                 '今日的比赛'])
def reply_recent_contests(message: RobotMessage):
    query_today = message.tokens[0] in ['/今天比赛', '/今天的比赛', '/今日比赛', '/今日的比赛']
    queries = [AtCoder, Codeforces, NowCoder, ManualPlatform]
    if len(message.tokens) >= 2:
        if message.tokens[1] == 'today':
            query_today = True
        else:
            platform_arg = message.tokens[1]
            if len(message.tokens) >= 3 and message.tokens[1] == 'today':
                query_today = True
                platform_arg = message.tokens[2]
            closest_type = process.extract(platform_arg.lower(), [
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
    token_pattern = re.escape(message.tokens[0])
    content = re.sub(token_pattern, '', content, count=1).strip()
    if len(content) == 0:
        message.reply("请输入要转化为二维码的内容")
        return

    cached_prefix = get_cached_prefix('QRCode-Generator')
    qr_img = get_simple_qrcode(content)
    qr_img.save(f"{cached_prefix}.png")

    message.reply("生成了一个二维码", png2jpg(f"{cached_prefix}.png"))


@command(tokens=["晚安", "睡觉", "睡觉去了"], is_command=False)
def reply_sleep(message: RobotMessage):
    reply_mc_sleep(message)


@command(tokens=['help', 'helps', 'instruction', 'instructions', '帮助'])
def reply_help(message: RobotMessage):
    cached_prefix = get_cached_prefix('Help-Renderer')

    if len(message.tokens) > 1 and message.tokens[1] in ['r', 'render', 'd', 'draw']:
        message.reply("O宝正在画画，稍等一下")
        contest_list_img = HelpRenderer().render()
        contest_list_img.write_file(f"{cached_prefix}.png")

    else:
        file_name = os.path.join(_project_dir, "img", "command_instructions.png")
        if not os.path.exists(file_name):
            message.reply("未找到预设的帮助手册图片，可追加 render 参数重新绘制")
            return
        shutil.copy(file_name, f"{cached_prefix}.png")

    message.reply("帮助手册", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['api', 'about', '版本', '关于'])
def reply_about(message: RobotMessage):
    message.reply("O宝正在画画，稍等一下")

    cached_prefix = get_cached_prefix('About-Renderer')
    about_img = AboutRenderer(
        ("OBot Core", f"{Constants.core_version}-{Constants.git_commit.hash_short}"),
        get_all_modules_info()
    ).render()
    about_img.write_file(f"{cached_prefix}.png")

    message.reply("当前各模块版本", png2jpg(f"{cached_prefix}.png"))


@command(tokens=['hzys', 'hzls', '活字印刷', '活字乱刷'])
def reply_hzys(message: RobotMessage):
    if len(message.tokens) == 1:
        message.reply("请指定需转换的文字")
        return

    lib_path = Constants.modules_conf.get_lib_path("Huo-Zi-Yin-Shua")

    cached_prefix = get_cached_prefix('Huo-Zi-Yin-Shua')
    audio_output = HuoZiYinShua(lib_path).generate(message.tokens[1], cached_prefix)

    message.reply_audio(audio_output)


@command(tokens=["hitokoto", "来句", "来一句", "来句话", "来一句话"])
def reply_hitokoto(message: RobotMessage):
    data = fetch_url_json("https://v1.hitokoto.cn/", method='GET', accept_codes=[200])
    content = data['hitokoto']
    where = data['from']
    author = data['from_who'] if data['from_who'] else ""
    message.reply(f"[Hitokoto]\n{content}\nBy {author}「{where}」", modal_words=False)


@command(tokens=["arcapk"])
def reply_arcapk(message: RobotMessage):
    """神秘小功能"""
    data = fetch_url_json("https://webapi.lowiro.com/webapi/serve/static/bin/arcaea/apk",
                          method='GET', accept_codes=[200])
    if not data['success']:
        message.reply("[ArcAPK] 获取失败，请稍后重试")
        return
    url = data['value']['url']
    url_sendable = url.replace('.', '. ').replace("https://", "")
    version = data['value']['version']

    cached_prefix = get_cached_prefix('QRCode-Generator')
    qr_img = get_simple_qrcode(url)
    qr_img.save(f"{cached_prefix}.png")

    message.reply(f"[ArcAPK] Arcaea v{version}\n\n"
                  f"可使用双设备配合进行扫码，或者使用下面的链接（需要去掉多余的空格）\n\n"
                  f"{url_sendable}", png2jpg(f"{cached_prefix}.png"), modal_words=False)


@module(
    name="Misc",
    version="v3.1.2"
)
def register_module():
    pass
