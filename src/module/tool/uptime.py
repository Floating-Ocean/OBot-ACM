from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.core.constants import Constants
from src.core.util.tools import fetch_url_json, png2jpg
from src.data.data_cache import get_cached_prefix
from src.render.pixie.render_uptime import UptimeRenderer

_page_id = Constants.modules_conf.uptime["page_id"]


@command(tokens=['alive', 'uptime'])
def reply_alive(message: RobotMessage):
    message.reply("正在查询服务状态，请稍等")
    status = fetch_url_json(f"https://stats.uptimerobot.com/api/getMonitorList/{_page_id}",
                            method='GET')

    cached_prefix = get_cached_prefix('Uptime')
    uptime_img = UptimeRenderer(status, cached_prefix).render()
    uptime_img.write_file(f"{cached_prefix}.png")
    message.reply("当前服务状态", png2jpg(f"{cached_prefix}.png"))


@module(
    name="Uptime-Robot",
    version="v2.0.0"
)
def register_module():
    pass
