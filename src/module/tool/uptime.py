from src.core.bot.command import command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.tools import fetch_url_json

_api_key = Constants.modules_conf.uptime["apikey"]


def register_module():
    pass


@command(tokens=['alive'])
def alive(message: RobotMessage):
    message.reply("正在查询服务状态，请稍等")
    data = fetch_url_json("https://api.uptimerobot.com/v2/getMonitors",
                          payload={"api_key": _api_key})

    checker_urls = [
        "https://fjnuacm.top",
        "https://codeforces.com",
        "https://atcoder.jp",
        "https://www.luogu.com.cn",
        "https://nowcoder.com",
        "https://vjudge.net"
    ]
    checker_names = ["FjnuOJ", "Codeforces", "AtCoder", "Luogu", "NowCoder", "VJudge"]
    checker_results = [-1] * len(checker_urls)

    if data["stat"] == "ok":
        monitors = data["monitors"]
        for monitor in monitors:
            url = monitor["url"]
            if url in checker_urls:
                checker_results[checker_urls.index(url)] = 1 if monitor["status"] == 2 else 0  # 1 活着, 0 似了

    if min(checker_results) == -1:
        message.reply("[UptimeRobot Api] Api 异常")
        return

    info = "[UptimeRobot Api] "
    if min(checker_results) == 1:
        info += "所有服务均正常\n"
    else:
        info += "部分服务存在异常\n"

    for i in range(len(checker_results)):
        status_text = "正常" if checker_results[i] == 1 else "异常"
        info += f"\n[{checker_names[i]}] {status_text}"

    message.reply(info, modal_words=False)
