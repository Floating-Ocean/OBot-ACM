import os
import sys
import time

import git

from src.core.bot.decorator import module, command
from src.core.bot.message import RobotMessage
from src.core.bot.perm import PermissionLevel
from src.core.bot.transit import clear_message_queue
from src.core.constants import Constants, InvalidGitCommit, HelpStrList
from src.data.data_cache import get_cached_prefix

_GIT_HELP = '\n'.join(HelpStrList(Constants.help_contents["git-cmd"]))

_is_git_valid = not isinstance(Constants.git_commit, InvalidGitCommit)
_project_dir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
)


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
        script_args.extend(["--checkout", checkout])
    payload = ' '.join(script_args)

    Constants.log.info("[git] 切换到更新脚本")
    Constants.log.info(f'[git] os.execl -> python -X utf8 {payload}')
    os.execl(sys.executable, sys.executable, '-X', 'utf8', *script_args)


def reply_git_plog(message: RobotMessage):
    plog_path = os.path.join(_project_dir, ".git_pull_indep_status")
    if not os.path.exists(plog_path):
        message.reply("[Git-Commands] 更新日志不存在")
        return

    with open(plog_path, 'r', encoding='utf-8') as f:
        content = f.read()
        message.reply("[Git-Commands] 上次更新的简略日志\n\n"
                      f"{content}", modal_words=False)


def reply_git_submodule(message: RobotMessage):
    repo = git.Repo(_project_dir)
    status = repo.git.submodule('status')
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
    version="v1.2.1"
)
def register_module():
    pass
