import json
import os
from dataclasses import dataclass
from typing import Optional
from src.core.help_registry import HelpRegistry

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

    def __post_init__(self):
        """初始化后处理，用于存储私有/非开源模块配置"""
        # 用于存储动态添加的模块配置
        self._private_modules = {}

    def __getattr__(self, name: str):
        """动态获取模块配置，用于支持私有/非开源模块"""
        # 如果访问不存在的属性，从私有模块中获取
        if hasattr(self, '_private_modules') and name in self._private_modules:
            return self._private_modules[name]
        # 如果不存在，返回空字典（避免报错）
        if name.startswith('_'):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'")
        return {}

    def _set_private_module(self, name: str, value: dict):
        """设置私有模块配置"""
        if not hasattr(self, '_private_modules'):
            self._private_modules = {}
        self._private_modules[name] = value

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


class _HelpContentsDescriptor:
    """描述符：动态获取帮助文本字典"""

    def __get__(self, obj, objtype=None):
        if objtype is None:
            objtype = type(obj)
        return objtype._get_help_contents()


class _MergedHelpContentDescriptor:
    """描述符：动态获取合并后的帮助内容"""

    def __get__(self, obj, objtype=None):
        if objtype is None:
            objtype = type(obj)
        return objtype._get_merged_help_content()


def _load_conf(path: str) -> tuple[dict, dict, ModulesConfig]:
    """从 config.json 加载配置"""
    # 默认配置（仅包含开源模块）
    default_modules = {
        'general': {},
        'clist': {"apikey": os.getenv("CLIST_APIKEY", "")},
        'uptime': {"page_id": os.getenv("UPTIME_PAGE_ID", "")},
        'game': {"exclude": {}},
        'peeper': {"exclude_id": [], "configs": []},
    }

    if not os.path.exists(path):
        # 如果配置文件不存在，返回默认配置
        return {}, {}, ModulesConfig(**default_modules)

    with open(path, "r", encoding="utf-8") as f:
        conf = json.load(f)
        botpy_conf = conf.get('botpy', {})
        role_conf = conf.get('role', {})
        modules_conf = conf.get('modules', {})

        # 合并默认配置和实际配置
        # 只使用已定义的字段，其他私有模块配置会被 __getattr__ 处理
        merged_modules = default_modules.copy()
        for key in default_modules.keys():
            if key in modules_conf:
                merged_modules[key] = modules_conf[key]

        # 从环境变量覆盖敏感配置
        if os.getenv("CLIST_APIKEY"):
            merged_modules.setdefault('clist', {})[
                'apikey'] = os.getenv("CLIST_APIKEY")
        if os.getenv("UPTIME_PAGE_ID"):
            merged_modules.setdefault('uptime', {})[
                'page_id'] = os.getenv("UPTIME_PAGE_ID")

        # 创建 ModulesConfig 实例
        config_instance = ModulesConfig(**merged_modules)

        # 动态添加其他模块配置（包括私有模块）
        # 这些配置可以通过 __getattr__ 访问
        for key, value in modules_conf.items():
            if key not in merged_modules:
                config_instance._set_private_module(key, value)

        return botpy_conf, role_conf, config_instance


def _get_git_commit() -> GitCommit:
    """获取当前 Git 仓库的 commit hash"""
    if not _has_git:
        return InvalidGitCommit("git_not_available")

    try:
        repo = git.Repo(_project_dir)
        commit = repo.head.commit

        try:
            ref_description = repo.git.describe(
                "--all", "--exact-match", "HEAD").strip()
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

    @classmethod
    def _get_help_contents(cls):
        """
        获取帮助文本字典
        从注册表获取所有帮助文本
        """
        # 从注册表获取所有帮助文本
        registry_helps = HelpRegistry.get_all_helps()
        registry_admin_helps = HelpRegistry.get_all_admin_helps()

        result = registry_helps.copy()

        # 添加管理员帮助文本
        for module_name, help_text in registry_admin_helps.items():
            result[f"{module_name} (admin)"] = help_text

        return result

    @classmethod
    def _get_merged_help_content(cls):
        """
        获取合并后的帮助内容
        从注册表获取所有非管理员帮助文本
        """
        # 从注册表获取所有非管理员帮助文本
        registry_helps = HelpRegistry.get_all_helps()

        return ("[Functions]\n\n" +
                "\n\n".join([f"[{module}]\n{helps}" for module, helps in registry_helps.items()]))

    # 使用描述符实现动态类属性
    help_contents = _HelpContentsDescriptor()
    merged_help_content = _MergedHelpContentDescriptor()

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
