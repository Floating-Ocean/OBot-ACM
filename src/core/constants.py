import json
import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import git
    _has_git = True
except ImportError:
    _has_git = False

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


@dataclass
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
    """从 config.json 加载配置"""
    if not os.path.exists(path):
        # 如果配置文件不存在，返回默认配置
        return {}, {}, ModulesConfig(
            general={},
            clist={"apikey": os.getenv("CLIST_APIKEY", "")},
            uptime={"page_id": os.getenv("UPTIME_PAGE_ID", "")},
            game={"exclude": {}},
            peeper={"exclude_id": [], "configs": []}
        )
    
    with open(path, "r", encoding="utf-8") as f:
        conf = json.load(f)
        botpy_conf = conf.get('botpy', {})
        role_conf = conf.get('role', {})
        modules_conf = conf.get('modules', {})
        
        # 从环境变量覆盖敏感配置
        if os.getenv("CLIST_APIKEY"):
            modules_conf.setdefault('clist', {})['apikey'] = os.getenv("CLIST_APIKEY")
        if os.getenv("UPTIME_PAGE_ID"):
            modules_conf.setdefault('uptime', {})['page_id'] = os.getenv("UPTIME_PAGE_ID")
        
        return botpy_conf, role_conf, ModulesConfig(**modules_conf)


def _get_git_commit() -> GitCommit:
    """获取当前 Git 仓库的 commit hash"""
    if not _has_git:
        return InvalidGitCommit("git_not_available")
    
    try:
        repo = git.Repo(_project_dir)
        commit = repo.head.commit

        try:
            ref_description = repo.git.describe("--all", "--exact-match", "HEAD").strip()
            ref_str = f" ({ref_description})" if ref_description else ""
        except git.GitCommandError:
            # HEAD 可能处于分离状态或不在精确匹配的引用上
            ref_str = ""

        return GitCommit(
            commit.hexsha,
            commit.hexsha[:12],
            ref_str,
            commit.message.split('\n')[0],
            commit.author.name,
            commit.authored_datetime.strftime("%Y-%m-%d %H:%M:%S %z")
        )

    except git.InvalidGitRepositoryError:
        return InvalidGitCommit("raw_copy_d")
    except Exception as e:
        try:
            Constants.log.warning("[obot-core] 获取 Git 提交信息异常")
            Constants.log.exception(f"[obot-core] {e}")
        except:
            pass
        return InvalidGitCommit("raw_copy_e")  # 异常


class Constants:
    # 从环境变量读取敏感配置
    bot_owner = int(os.getenv("BOT_OWNER", "123456789"))
    _superusers_str = os.getenv("SUPERUSERS", f"{bot_owner},...")
    SUPERUSERS = [s.strip() for s in _superusers_str.split(',') if s.strip()]
    
    # 加载配置文件
    _config_path = os.path.join(_project_dir, "config.json")
    botpy_conf, role_conf, modules_conf = _load_conf(_config_path)
    
    # 日志（NoneBot 环境下使用 loguru）
    try:
        from loguru import logger as log
    except ImportError:
        import logging
        log = logging.getLogger("obot")
    
    core_version = "v3.1.0"
    git_commit = _get_git_commit()

    CRON_PRIOR = 50
    PLATFORM_PRIOR = 100
    HELP_PRIOR = 1000
    MISC_PRIOR = 200

    # 配置字典（兼容旧代码）
    config = {
        'uptime_apikey': os.getenv("UPTIME_APIKEY", ""),
        'clist_apikey': modules_conf.clist.get('apikey', os.getenv("CLIST_APIKEY", "")),
    }

    help_contents = {
        'Codeforces': '\n'.join([
            "可用 /cf , /codeforces 触发",
            "/cf info [handle]: 获取用户名为 handle 的 Codeforces 基础用户信息.",
            "/cf recent [handle] (count): 获取用户名为 handle 的 Codeforces 最近 count 发提交，count 默认为 5.",
            "/cf pick [标签|all] (难度) (new): 从 Codeforces 上随机选题. 标签中间不能有空格，支持模糊匹配. 难度为整数或一个区间，格式为xxx-xxx"
            ". 末尾加上 new 参数则会忽视 P1000A 以前的题.",
            "/cf contests: 列出最近的 Codeforces 比赛.",
            "/cf tags: 用于列出 codeforces 平台的 tags (辅助 pick)."
        ]),
        'Atcoder': '\n'.join([
            "临时通知：目前 info 和 contests 功能受到 Atcoder 阻拦不可用。仅可以使用 pick 功能，已经向 Atcoder 发工单了。",
            "/atc info [handle]: 获取用户名为 handle 的 AtCoder 基础用户信息.",
            "/atc pick [比赛类型|all] (难度): 从 AtCoder 上随机选题，基于 Clist API"
            ". 比赛类型可选参数为 [abc, arc, agc, ahc, common, sp, all]"
            "，其中 common 涵盖前四个类型，而 sp 则是排除前四个类型. 难度为整数或一个区间，格式为xxx-xxx.",
            "/atc contests: 列出最近的 AtCoder 比赛."
        ]),
        'Nowcoder': '\n'.join([
            "/nk contests: 列出最近的 NowCoder 比赛.",
            "/nk info [uid]: 获取 id 为 uid 的牛客基础用户信息."
        ]),
        'cron / 定时模块': "\n".join([
            "/schedule add [platform] [contestId]: 将比赛 [contestId] 加入调用指令的私聊/群聊提醒列表中。",
        ]),
        'cron / 定时模块 (admin)': "\n".join([
            "/schedule addto [platform] [contestId] [boardcastTo]: 将比赛 [contestId] 加入[boardcastTo]群聊提醒列表中。",
            "/schedule all: 返回当前所有的 shedule 任务",
            "/schedule removeall 删除当前所有的固定时间提醒任务。"
        ]),
    }
    merged_help_content = ("[Functions]\n\n" +
                           "\n\n".join([f"[{module}]\n{helps}" for module, helps in help_contents.items() if not 'admin' in module]))

    @classmethod
    def reload_conf(cls):
        """重新加载配置文件"""
        cls.botpy_conf, cls.role_conf, cls.modules_conf = (
            _load_conf(cls._config_path))
        # 更新 config 字典
        cls.config = {
            'uptime_apikey': os.getenv("UPTIME_APIKEY", ""),
            'clist_apikey': cls.modules_conf.clist.get('apikey', os.getenv("CLIST_APIKEY", "")),
        }
