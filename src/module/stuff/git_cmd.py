import os
import sys
import time

import git

from src.core.bot.decorator import module, command
from src.core.bot.message import RobotMessage, MessageType
from src.core.bot.perm import PermissionLevel
from src.core.bot.transit import clear_message_queue
from src.core.constants import Constants, InvalidGitCommit, HelpStrList
from src.core.util.output_cache import get_cached_prefix

_GIT_HELP = '\n'.join(HelpStrList(Constants.help_contents["git-cmd"]))

_is_git_valid = not isinstance(Constants.git_commit, InvalidGitCommit)
_project_dir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
)
_status_path = os.path.join(_project_dir, ".git_pull_indep_status")

# 重启后回报更新结果所需的信息，靠环境变量传递给重启后的进程
_PENDING_ENV = "OBOT_GIT_PULL_NOTIFY"

# 状态文件中仓库变更指示与实际含义的对应关系
_REPO_CHANGED_TIP = {
    "Yes": "是",
    "No": "否",
    "Yes (with stashes)": "是（本地更改已搁置）",
}

_PULLED_COMMIT_LIMIT = 8


def reply_git_status(message: RobotMessage):
    commit = Constants.git_commit
    commit_info = ("[Git-Commands] 当前提交信息\n\n"
                   f"commit {commit.hash}{commit.ref}\n"
                   f"Author: {commit.author}\n"
                   f"Date: {commit.date}\n\n"
                   f"{commit.message_title}")
    message.reply(commit_info, modal_words=False)


def reply_git_fetch(message: RobotMessage):
    repo = git.Repo(_project_dir)

    try:
        current_branch = repo.active_branch
        branch_name = str(current_branch)
    except TypeError:
        # 当前处于 detached HEAD 状态
        message.reply("[Git-Commands] 当前 HEAD 不在任何分支上，无法对比远程分支")
        return

    tracking_branch = current_branch.tracking_branch()
    if tracking_branch is None:
        message.reply(f"[Git-Commands] 分支 {branch_name} 没有设置远程跟踪分支")
        return

    try:
        origin = repo.remote('origin')
    except ValueError:
        message.reply("[Git-Commands] 未找到 origin 远程仓库")
        return

    try:
        origin.fetch()
    except git.GitCommandError as e:
        message.reply(f"[Git-Commands] 拉取远程更新失败: {str(e)}")
        return

    local_commit = repo.commit(branch_name)
    remote_commit = tracking_branch.commit

    if local_commit.hexsha == remote_commit.hexsha:
        msg = "本地分支已是最新"
    else:
        # 检查是领先、落后还是有分歧
        base = repo.merge_base(local_commit, remote_commit)
        if local_commit in base:
            behind_count = sum(1 for c in repo.iter_commits(f'{local_commit}..{remote_commit}'))
            msg = f"本地分支落后远程分支 {behind_count} 个提交"
        elif remote_commit in base:
            ahead_count = sum(1 for c in repo.iter_commits(f'{remote_commit}..{local_commit}'))
            msg = f"本地分支领先远程分支 {ahead_count} 个提交"
        else:
            msg = "本地分支与远程分支存在冲突"

    message.reply(f"[Git-Commands] {msg}")


def _remember_pull(message: RobotMessage, checkout: str | None):
    """记录发起更新的对话场景与更新前提交，供 Bot 重启后回报更新结果"""
    try:
        raw_message = message.message

        # 主动消息所需的目标与 uuid 并不一致：频道要子频道 ID，频道私信要 guild_id
        if message.message_type == MessageType.GUILD:
            target = f"guild|{raw_message.channel_id}"
        elif message.message_type == MessageType.DIRECT:
            target = f"direct|{raw_message.guild_id}"
        elif message.message_type == MessageType.GROUP:
            target = f"group|{raw_message.group_openid}"
        elif message.message_type == MessageType.C2C:
            target = f"c2c|{message.author_id}"
        else:
            raise ValueError(f"暂不支持的对话场景: {message.message_type}")

        os.environ[_PENDING_ENV] = f"{target}|{Constants.git_commit.hash}|{checkout or ''}"
        Constants.log.info(f"[git] 已记录更新回报场景: {message.uuid}")
    except Exception as e:
        Constants.log.warning("[git] 无法解析当前对话场景，重启后将不回报更新结果")
        Constants.log.exception(f"[git] {e}")


def _list_pulled_commits(commit_before: str, commit_after: str) -> str:
    """列出本次更新实际拉取的提交标题，无法获取时返回空串"""
    if not commit_before or not commit_after or commit_before == commit_after:
        return ""

    try:
        repo = git.Repo(_project_dir)
        commits = list(repo.iter_commits(f"{commit_before}..{commit_after}"))
    except Exception as e:
        Constants.log.warning("[git] 获取本次拉取的提交列表失败")
        Constants.log.exception(f"[git] {e}")
        return ""

    if not commits:
        return ""

    titles = []
    for commit in commits[:_PULLED_COMMIT_LIMIT]:
        title = commit.message.strip().split('\n')[0] or "(无提交信息)"
        titles.append(f"- {title}")
    if len(commits) > _PULLED_COMMIT_LIMIT:
        titles.append(f"- ... 其余 {len(commits) - _PULLED_COMMIT_LIMIT} 个提交已省略")

    return (f"{commit_before[:7]}..{commit_after[:7]}，共 {len(commits)} 个提交\n"
            + '\n'.join(titles))


def _format_pull_result(commit_before: str, checkout: str) -> str:
    """根据更新状态文件与更新前提交，组织更新结果的回报文本"""
    if not os.path.exists(_status_path):
        return ("[Git-Commands] 更新结果回报\n\n"
                "未找到更新状态文件，无法确认本次更新结果，"
                "可稍后使用 /git plog 查看")

    try:
        with open(_status_path, 'r', encoding='utf-8') as f:
            content = f.read().strip('\n')
    except Exception as e:
        Constants.log.warning("[git] 读取更新状态文件失败")
        Constants.log.exception(f"[git] {e}")
        return "[Git-Commands] 更新结果回报\n\n更新状态文件读取失败"

    fields = {}
    commit_lines = []
    lines = content.split('\n')
    for index, line in enumerate(lines):
        if line.startswith("Current Commit:"):
            commit_lines = [item for item in lines[index + 1:index + 3] if item.strip()]
            break
        key, sep, value = line.partition(': ')
        if sep:
            fields[key.strip()] = value.strip()

    success = fields.get("Status", "").upper() == "SUCCESS"
    parts = ["[Git-Commands] 更新结果回报", "",
             f"状态：{'成功' if success else '失败'}"]

    if success:
        changed = fields.get("Repository Changed", "")
        parts.append(f"仓库变更：{_REPO_CHANGED_TIP.get(changed, changed or '未知')}")
        parts.append(f"子模块更新：{fields.get('Submodule Updates', '未知')}")
    else:
        parts.append("更新流程出现异常，完整日志可使用 /git plog 查看")

    if checkout:
        parts.append(f"目标分支：{checkout}")

    commit_after = Constants.git_commit.hash if _is_git_valid else ""
    if commit_before and commit_after:
        parts.append(f"提交变更：{commit_before[:7]} -> {commit_after[:7]}")

    if commit_lines:
        parts.extend(["", "当前提交：", *commit_lines])

    pulled = _list_pulled_commits(commit_before, commit_after)
    if pulled:
        parts.extend(["", "本次拉取的提交：", pulled])

    return '\n'.join(parts)


def notify_git_pull_result(api, loop):
    """Bot 重启后回报上一次 /git pull 的更新结果，无待回报信息时静默返回"""
    pending = os.environ.pop(_PENDING_ENV, None)
    if not pending:
        return

    try:
        message_type, target, commit_before, checkout = pending.split('|', 3)

        message = RobotMessage(api)
        setup_map = {
            MessageType.GUILD: message.setup_active_guild_message,
            MessageType.DIRECT: message.setup_active_direct_message,
            MessageType.GROUP: message.setup_active_group_message,
            MessageType.C2C: message.setup_active_c2c_message,
        }
        setup_map[MessageType(message_type)](loop, target)

        Constants.log.info(f"[git] 向 {message.uuid} 回报更新结果")
        message.reply(_format_pull_result(commit_before, checkout), modal_words=False)
    except Exception as e:
        Constants.log.warning("[git] 回报更新结果失败")
        Constants.log.exception(f"[git] {e}")


def reply_git_pull(message: RobotMessage):
    content = message.tokens
    checkout = None
    if len(content) >= 3:
        checkout = content[2]

    checkout_tip = f"，切换到分支 {checkout}" if checkout else ""
    message.reply(f"[Git-Commands] 正在拉取并应用更新{checkout_tip}")
    clear_message_queue()
    time.sleep(2)  # 等待 message 通知消息线程发送回复
    Constants.log.info(f"[git] 拉取并应用更新{checkout_tip}")

    lib_path = Constants.modules_conf.get_lib_path("Git-Pull-Indep")
    script_path = os.path.join(lib_path, "git_pull_indep.py")
    entry_path = os.path.join(_project_dir, "entry.py")

    cached_prefix = get_cached_prefix('Git-Pull-Indep')
    cache_path = f"{cached_prefix}.cache"
    script_args = [
        script_path,
        _project_dir,
        "--cache_path", cache_path,
        "--initiator", entry_path
    ]
    if checkout:
        # 验证分支名仅包含字母、数字、下划线、横杠和斜杠
        if not all(c.isalnum() or c in '_-/' for c in checkout):
            message.reply("[Git-Commands] 无效的分支名")
            return
        script_args.extend(["--checkout", checkout])
    payload = ' '.join(script_args)

    # 记录本次更新的对话场景，Bot 重启后由 notify_git_pull_result 回报更新结果
    _remember_pull(message, checkout)

    Constants.log.info("[git] 切换到更新脚本")
    Constants.log.info(f'[git] os.execl -> python -X utf8 {payload}')
    os.execl(sys.executable, sys.executable, '-X', 'utf8', *script_args)


def reply_git_plog(message: RobotMessage):
    if not os.path.exists(_status_path):
        message.reply("[Git-Commands] 更新日志不存在")
        return

    with open(_status_path, 'r', encoding='utf-8') as f:
        content = f.read().strip('\n')
        message.reply("[Git-Commands] 上次更新的简略日志\n\n"
                      f"{content}", modal_words=False)


def reply_git_submodule(message: RobotMessage):
    repo = git.Repo(_project_dir)
    status = repo.git.submodule('status').strip('\n')
    message.reply("[Git-Commands] 本项目的所有子模块信息\n\n"
                  f"{status}", modal_words=False)


def reply_git_stash(message: RobotMessage):
    content = message.tokens
    action = 'push'
    if len(content) >= 3:
        action = content[2]

    repo = git.Repo(_project_dir)
    if action == 'push':
        if not repo.is_dirty(untracked_files=True):
            message.reply("[Git-Commands] 暂无更改需要搁置")
            return
        repo.git.stash('push', '-u', '-m', 'obot_module_git_cmd stash')
        message.reply("[Git-Commands] 已搁置更改")
    else:
        stash_list = repo.git.stash('list')
        if action == 'pop':
            if not stash_list:
                message.reply("[Git-Commands] 未找到搁置的更改")
                return
            repo.git.stash('pop')
            message.reply("[Git-Commands] 已弹出上一个搁置更改")
        elif action == 'list':
            if not stash_list:
                message.reply("[Git-Commands] 未找到搁置的更改")
                return
            message.reply("[Git-Commands] 所有搁置更改\n\n"
                          f"{stash_list}", modal_words=False)
        else:
            message.reply("[Git-Commands] 只支持 push, pop 和 list 操作")


@command(tokens=["git"], permission_level=PermissionLevel.ADMIN)
def reply_git(message: RobotMessage):
    try:
        content = message.tokens
        if len(content) < 2:
            message.reply(f'[Git-Commands]\n\n{_GIT_HELP}', modal_words=False)
            return

        if not _is_git_valid:
            message.reply("[Git-Commands] 此 OBot 大概率不是通过 Git Clone 得到的，无法继续操作")
            return

        func = content[1]

        if func == 'status' or func == 'commit' or func == 'log':
            reply_git_status(message)

        elif func == 'fetch' or func == 'check' or func == 'chk':
            reply_git_fetch(message)

        elif func == 'pull' or func == 'update' or func == 'upd':
            reply_git_pull(message)

        elif func == 'plog' or func == 'pull_log' or func == 'last_log':
            reply_git_plog(message)

        elif func == 'submodule' or func == 'plugin' or func == 'module':
            reply_git_submodule(message)

        elif func == 'stash' or func == 'put' or func == 'lay':
            reply_git_stash(message)

        else:
            message.reply(f'[Git-Commands]\n\n{_GIT_HELP}', modal_words=False)

    except Exception as e:
        message.report_exception('Git-Commands', e)


@module(
    name="Git-Commands",
    version="v1.3.0"
)
def register_module():
    pass
