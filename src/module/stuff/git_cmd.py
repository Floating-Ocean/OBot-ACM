from src.core.bot.decorator import module, command
from src.core.bot.message import RobotMessage
from src.core.constants import Constants, InvalidGitCommit


@command(tokens=["git"])
def reply_git_commit(message: RobotMessage):
    commit = Constants.git_commit
    if isinstance(commit, InvalidGitCommit):
        message.reply("此 OBot 大概率不是通过 Git Clone 得到的")
    else:
        commit_info = ("[Git] 当前提交信息\n\n"
                       f"commit {commit.hash}{commit.ref}\n"
                       f"Author: {commit.author}\n"
                       f"Date: {commit.date}\n\n"
                       f"{commit.message_title}")
        message.reply(commit_info, modal_words=False)


@module(
    name="Git-Commands",
    version="v1.0.0"
)
def register_module():
    pass
