import json
import os
import subprocess
from dataclasses import dataclass

from botpy import logging

_project_dir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
)


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


@dataclass()
class GitCommit:
    hash: str
    hash_short: str
    ref: str
    message_title: str
    author: str
    date: str


class InvalidGitCommit(GitCommit):
    def __init__(self, invalid_message: str):
        self.hash_short = invalid_message


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


def _get_git_commit() -> GitCommit:
    """获取当前 Git 仓库的 commit hash"""
    if not os.path.exists(os.path.join(_project_dir, ".git")):
        return InvalidGitCommit("raw_copy_d")

    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=format:%H|||%d|||%s|||%an|||%ai'],
            capture_output=True, text=True, check=True, timeout=5, encoding='utf-8'
        )
        commit_hash, ref, title, author, date = result.stdout.strip().split("|||")
        if len(commit_hash) != 40 or not all(c in "0123456789abcdef" for c in commit_hash.lower()):
            return InvalidGitCommit("raw_copy_i")  # hash 格式错误
        return GitCommit(commit_hash, commit_hash[:12], ref, title, author, date)

    except FileNotFoundError:
        return InvalidGitCommit("raw_copy_g")  # 未安装 git
    except Exception as e:
        Constants.log.warning("[obot-core] 获取 Git 提交信息异常")
        Constants.log.exception(f"[obot-core] {e}")
        return InvalidGitCommit("raw_copy_e")  # 异常


class Constants:
    log = logging.get_logger()
    botpy_conf, role_conf, modules_conf = (_load_conf(os.path.join(_project_dir, "config.json")))

    core_version = "v5.0.0-beta.5"
    git_commit = _get_git_commit()

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
        [["掐楼", "ciallo"], ["Ciallo~", "柚子厨蒸鹅心"]],
        [["ready", "准备"], ["你是准备吗", "我准备好了"]],
        [["在哪"], ["在亚特兰蒂斯", "在海下面", "在你背后", "在哪"]]
    ]

    modal_words = ["喵", "呢", "捏", "qaq"]

    help_contents = {
        'Main': [
            Help("/今日题数 (id)", "查询今天从凌晨到现在的做题数情况，可指定已配置的榜单 id."),
            Help("/昨日总榜 (id)", "查询昨日的完整榜单，可指定已配置的榜单 id."),
            Help("/评测榜单 [verdict]",
                 "查询分类型榜单，其中指定评测结果为第二参数 verdict，需要保证参数中无空格，如 wa, TimeExceeded."),
            Help("/近日比赛 (platform)",
                 "查询 platform 平台近期比赛，可指定 Codeforces, AtCoder, NowCoder，留空则返回三平台近日比赛集合."),
            Help("/今日比赛 (platform)", "查询 platform 平台今日比赛，参数同上."),
            Help("/活着吗", "字面意思，等价于 /ping.")
        ],
        'sub': [
            Help("/user id [uid]", "查询 uid 对应用户的信息."),
            Help("/user name [name]", "查询名为 name 对应用户的信息，支持模糊匹配."),
            Help("/alive", "检查各算竟平台的可连通性."),
            Help("/about", "获取当前各模块的构建信息."),
            Help("/git", "获取当前本项目指向的提交信息.")
        ],
        'contestant': [
            Help("/cpcfinder [name] [school]", "获取名为 name 且学校为 school 的 XCPC 大学生程序设计竞赛选手获奖信息."),
            Help("/oierdb [name]", "获取名为 name 的 OI 信息学奥赛选手获奖信息，支持批量查询."),
        ],
        'codeforces': [
            Help("/cf bind [handle]", "绑定用户名为 handle 的 Codeforces 账号."),
            Help("/cf duel", "Codeforces 对战模块."),
            Help("/cf id [handle]", "获取用户名为 handle 的 Codeforces 基础用户信息卡片."),
            Help("/cf info [handle]", "获取用户名为 handle 的 Codeforces 详细用户信息."),
            Help("/cf recent [handle] (count)",
                 "获取用户名为 handle 的 Codeforces 最近 count 发提交，count 默认为 5."),
            Help("/cf pick [标签|all] (难度) (new)",
                 "从 Codeforces 上随机选题. 标签中间不能有空格，支持模糊匹配. 难度为整数或一个区间，格式为 xxx-xxx. "
                 "末尾加上 new 参数则会忽视 P1000A 以前的题."),
            Help("/cf tags", "用于列出 Codeforces 平台的 tags (辅助 pick)."),
            Help("/cf stand [handle] [id]",
                 "获取 Codeforces 上编号为 id 的比赛中用户名为 handle 的用户的榜单信息，支持预测分数变化.")
        ],
        'atcoder': [
            Help("/atc id [handle]", "获取用户名为 handle 的 AtCoder 基础用户信息卡片."),
            Help("/atc info [handle]", "获取用户名为 handle 的 AtCoder 详细用户信息."),
            Help("/atc pick [比赛类型|all] (难度)",
                 "从 AtCoder 上随机选题，基于 Clist API. 比赛类型可选参数为 [abc, arc, agc, ahc, common, sp, all]，"
                 "其中 common 涵盖前四个类型，而 sp 则是排除前四个类型. 难度为整数或一个区间，格式为xxx-xxx.")
        ],
        'nowcoder': [
            Help("/nk id [handle]", "获取用户名为 handle 的 NowCoder 基础用户信息卡片."),
            Help("/nk info [handle]", "获取用户名为 handle 的 NowCoder 详细用户信息."),
            Help("/nk stand [name] [contest]",
                 "获取 NowCoder 上名称匹配 contest 的比赛中，用户名或学校名匹配 name 的用户的榜单信息.")
        ],
        'pick_one': [
            Help("/来只 [what] ([tag] (index))",
                 "获取一个类别为 what 的随机表情包，可指定关键词 tag，并选择匹配度第 index 的候选."),
            Help("/随便来只", "获取一个随机类别的随机表情包."),
            Help("/添加(来只) [what]", "添加一个类别为 what 的表情包，需要管理员审核.")
        ],
        'random': [
            Help("/rand [num/int] [min] [max]", "在 [min, max] 中选择一个随机数，值域 [-1e9, 1e9]."),
            Help("/rand seq [max]", "获取一个 1, 2, ..., max 的随机排列，值域 [1, 500]."),
            Help("/rand color", "获取一个色卡.")
        ],
        'tetris': [
            Help("/tetris (col)", "开始 24 * col 大小的俄罗斯方块游戏，col 为列数，留空时默认为 24."),
            Help("/tetris [rotate_cnt] [left_col]",
                 "放置方块下落。方块顺时针旋转 rotate_cnt 次，左上角位于 left_col 列，从 1 开始编号."),
            Help("/tetris undo", "回退上一次操作，最多连续被执行一次."),
            Help("/tetris now", "查看当前俄罗斯方块游戏状态."),
            Help("/tetris stop", "结束本轮俄罗斯方块游戏.")
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
        'misc1': [
            Help("/hitokoto", "获取一条一言. 指令别名：/一言，/来(一)句(话)."),
            Help("/qrcode [content]", "生成一个内容为 content 的二维码."),
            Help("/sleep", "进行一种 Minecraft 风格的睡觉."),
            Help("/hzys [content]", "基于文本 content 合成电棍语音，活字乱刷.")
        ],
        'misc2': [
            Help("/来道菜", "获取一道 How-to-Cook 开源项目里的菜谱."),
            Help("/导入比赛", "导入手动配置的比赛，需要管理员权限."),
            Help("/配置重载", "重载配置文件，需要管理员权限."),
            Help("/重启", "重新启动 Bot，需要管理员权限.")
        ],
        'help': [
            Help("/help", "获取本图.")
        ],
    }

    @classmethod
    def reload_conf(cls):
        cls.botpy_conf, cls.role_conf, cls.modules_conf = (
            _load_conf(os.path.join(_project_dir, "config.json")))
