import json
import os
from dataclasses import dataclass

from botpy import logging

_project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


@dataclass
class ModulesConfig:
    general: dict
    clist: dict
    uptime: dict
    game: dict
    peeper: dict

    @classmethod
    def get_lib_path(cls, lib_name: str) -> str:
        return os.path.join(_project_dir, 'lib', lib_name)

    @classmethod
    def get_cache_path(cls) -> str:
        cache_path = os.path.join(_project_dir, 'cache')
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        return cache_path


@dataclass(frozen=True)
class Help:
    command: str
    help: str

    def __str__(self):
        return f"{self.command}: {self.help}"


class HelpStrList(list):
    def __iter__(self):
        # 每次迭代时返回每个元素的字符串表示
        return (str(item) for item in super().__iter__())


def _load_conf(path: str) -> tuple[dict, dict, ModulesConfig]:
    with open(path, "r", encoding="utf-8") as f:
        conf = json.load(f)
        botpy_conf = conf.get('botpy', {})
        role_conf = conf.get('role', {})
        modules_conf = conf.get('modules', {})
        return botpy_conf, role_conf, ModulesConfig(**modules_conf)


class Constants:
    log = logging.get_logger()
    botpy_conf, role_conf, modules_conf = (_load_conf(os.path.join(_project_dir, "config.json")))

    core_version = "v3.9.4.beta1_07101400"

    key_words = [
        [["沙壁", "纸张", "挠蚕", "sb", "老缠", "nt", "矛兵"], [
            "谢谢夸奖", "反弹", "可能还真被你说对了", "嗯", "好的", "哼，你才是", "哈哈", "你可能说对了，你可能没说对",
            "干什么", "你干嘛害哎呦", "那我问你"
        ]],
        [["性别"], ["盲猜我的性别是武装直升机", "我也不知道我的性别是啥", "那我问你"]],
        [["干嘛", "干什么"], ["how", "what", "which", "why", "whether", "when"]],
        [["谢谢", "thank"], ["qaq", "不用谢qaq", "qwq"]],
        [["qaq", "qwq"], ["qwq"]],
        [["你是谁", "你谁"], ["猜猜我是谁", "我也不知道", "你是谁", "那我问你"]],
        [["省"], ["妈妈生的", "一眼丁真"]],
        [["似"], ["看上去我还活着", "似了"]],
        [["go"], ["哎你们这些go批", "还在go还在go"]],
        [["春日影"], ["为什么要演奏春日影"]],
        [["乌蒙"],
         ["哎你们这些wmc", "awmc", "我们乌蒙怎么你了", "要开始了哟", "游戏结束，还有剩余哟", "完美挑战曲，后面忘了"]],
        [["creeper", "creeper?"], ["ohh, man."]],
        [["你爱我"], ["我爱你"]],
        [["我爱你"], ["你爱我"]],
        [["你喜欢我"], ["我喜欢你"]],
        [["我喜欢你"], ["你喜欢我"]],
        [["学我说话"], ["可惜我不是复读机", "人类的本质...哎我不是人来着", "学我说话"]],
        [["猫"], ["喵"]],
        [["好"], ["好"]],
        [["掐楼", "ciallo"], ["Ciallo~", "柚子厨蒸鹅心"]]
    ]

    modal_words = ["喵", "呢", "捏", "qaq"]

    help_contents = {
        'Main': [
            Help("/今日题数", "查询今天从凌晨到现在的做题数情况."),
            Help("/昨日总榜", "查询昨日的完整榜单."),
            Help("/评测榜单 [verdict]",
                 "查询分类型榜单，其中指定评测结果为第二参数 verdict，需要保证参数中无空格，如 wa, TimeExceeded.")
        ],
        'sub': [
            Help("/user id [uid]", "查询 uid 对应用户的信息."),
            Help("/user name [name]", "查询名为 name 对应用户的信息，支持模糊匹配."),
            Help("/contests (platform)",
                 "查询 platform 平台近期比赛，可指定 Codeforces, AtCoder, NowCoder，留空则返回三平台近日比赛集合."),
            Help("/contests today (platform)", "查询 platform 平台今日比赛，参数同上."),
            Help("/alive", "检查各算竟平台的可连通性."),
            Help("/api", "获取当前各模块的构建信息.")
        ],
        'pick_one': [
            Help("/来只 [what]", "获取一个类别为 what 的随机表情包."),
            Help("/随便来只", "获取一个随机类别的随机表情包."),
            Help("/添加(来只) [what]", "添加一个类别为 what 的表情包，需要管理员审核.")
        ],
        'codeforces': [
            Help("/cf bind [handle]", "绑定用户名为 handle 的 Codeforces 账号."),
            Help("/cf duel", "Codeforces 对战模块."),
            Help("/cf id [handle]", "获取用户名为 handle 的 Codeforces 基础用户信息卡片."),
            Help("/cf info [handle]", "获取用户名为 handle 的 Codeforces 详细用户信息."),
            Help("/cf recent [handle] (count)", "获取用户名为 handle 的 Codeforces 最近 count 发提交，count 默认为 5."),
            Help("/cf pick [标签|all] (难度) (new)",
                 "从 Codeforces 上随机选题. 标签中间不能有空格，支持模糊匹配. 难度为整数或一个区间，格式为 xxx-xxx. "
                 "末尾加上 new 参数则会忽视 P1000A 以前的题."),
            Help("/cf contests", "列出最近的 Codeforces 比赛."),
            Help("/cf tags", "用于列出 codeforces 平台的 tags (辅助 pick).")
        ],
        'atcoder': [
            Help("/atc id [handle]", "获取用户名为 handle 的 AtCoder 基础用户信息卡片."),
            Help("/atc info [handle]", "获取用户名为 handle 的 AtCoder 详细用户信息."),
            Help("/atc pick [比赛类型|all] (难度)",
                 "从 AtCoder 上随机选题，基于 Clist API. 比赛类型可选参数为 [abc, arc, agc, ahc, common, sp, all]，"
                 "其中 common 涵盖前四个类型，而 sp 则是排除前四个类型. 难度为整数或一个区间，格式为xxx-xxx."),
            Help("/atc contests", "列出最近的 AtCoder 比赛.")
        ],
        'nowcoder': [
            Help("/nk id [handle]", "获取用户名为 handle 的 NowCoder 基础用户信息卡片."),
            Help("/nk info [handle]", "获取用户名为 handle 的 NowCoder 详细用户信息."),
            Help("/nk contests", "列出最近的 NowCoder 比赛.")
        ],
        'random': [
            Help("/rand [num/int] [min] [max]", "在 [min, max] 中选择一个随机数，值域 [-1e9, 1e9]."),
            Help("/rand seq [max]", "获取一个 1, 2, ..., max 的随机排列，值域 [1, 500]."),
            Help("/rand color", "获取一个色卡.")
        ],
        'guess-interval': [
            Help("/guess", "开始区间猜数字."),
            Help("/guess [num]", "猜测数字为 num."),
            Help("/guess stop", "结束本轮区间猜数字游戏.")
        ],
        'guess-1a2b': [
            Help("/1a2b", "开始 1a2b 游戏."),
            Help("/1a2b [num]", "猜测数字为 num."),
            Help("/1a2b stop", "结束本轮 1a2b 游戏.")
        ],
        'tetris': [
            Help("/tetris (col)", "开始 24 * col 大小的俄罗斯方块游戏，col 为列数，留空时默认为 24."),
            Help("/tetris [rotate_cnt] [left_col]",
                 "放置方块下落。方块顺时针旋转 rotate_cnt 次，左上角位于 left_col 列，从 1 开始编号."),
            Help("/tetris undo", "回退上一次操作，最多连续被执行一次."),
            Help("/tetris now", "查看当前俄罗斯方块游戏状态."),
            Help("/tetris stop", "结束本轮俄罗斯方块游戏.")
        ],
        'misc': [
            Help("/hitokoto", "获取一条一言. 指令别名：/一言，/来(一)句(话)."),
            Help("/qrcode [content]", "生成一个内容为 content 的二维码."),
            Help("/sleep", "进行一种 Minecraft 风格的睡觉."),
            Help("/help", "获取本图.")
        ],
    }

    def reload_conf(self):
        self.botpy_conf, self.role_conf, self.modules_conf = (
            _load_conf(os.path.join(_project_dir, "config.json")))
