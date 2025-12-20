from src.core.bot.decorator import module, command
from src.core.bot.message import RobotMessage
from src.platform.collect.cpcfinder import CPCFinder


def _format_cpc_rank(official: bool, rank: int, official_rank: int) -> str:
    if official:
        return f"#{official_rank}({rank})"
    else:
        return f"*{rank}"


@command(tokens=['cpcfinder', 'xcpcfinder', 'cpcfind', 'xcpcfind', 'cpcfd', 'xcpcfd',
                 'acm', 'icpc', 'ccpc', '大学生程序设计竞赛'])
def reply_cpcfinder(message: RobotMessage):
    try:
        content = message.tokens
        if len(content) != 3:
            message.reply('请输入两个参数，分别代表选手姓名和学校，如：\n\n'
                          f'{content[0]} 蒋凌宇 北京大学', modal_words=False)
            return

        stu_name, stu_school = content[1], content[2]

        message.reply('正在查询 XCPC 选手信息，请稍等')
        stu_id = CPCFinder.find_student_id(stu_name, stu_school)

        if isinstance(stu_id, int):
            if stu_id == 0:
                message.reply('未找到该选手信息')
                return
            else:
                message.reply('查询出现意外错误，请稍后重试')
                return
        
        if isinstance(stu_id, list):
            # 显示前5个候选结果
            candidates = stu_id[:5]
            reply_text = f"[CPCFinder] 找到{len(stu_id)}个候选结果\n\n"
            
            for i, stu in enumerate(candidates, 1):
                reply_text += (
                    f"#{i} {stu.get('name', '未知姓名')} / {stu.get('schoolName', '未知学校')}\n"
                    f"金牌: {stu.get('goldCount', 0)} / "
                    f"银牌: {stu.get('silverCount', 0)} / "
                    f"铜牌: {stu.get('bronzeCount', 0)}\n\n"
                )
            
            reply_text += "建议缩小查询范围以精确匹配"
            message.reply(reply_text, modal_words=False)
            return

        stu_general = CPCFinder.get_student_general(stu_id)
        stu_awards = CPCFinder.get_student_awards(stu_id)

        stu_info = ("[CPCFinder] 选手查询\n\n"
                    f"{stu_general.name} / {stu_general.school}\n\n"
                    f"冠军: {stu_general.champion} / 亚军: {stu_general.sec} / 季军: {stu_general.thi}\n"
                    f"金牌: {stu_general.gold} / 银牌: {stu_general.silver} / 铜牌: {stu_general.bronze}\n\n"
                    "获奖信息: \n")

        awards = [
            (
                f"[{stu_award.medal}] {stu_award.contest_name}\n"
                f"{_format_cpc_rank(stu_award.official, stu_award.rank, stu_award.official_rank)} "
                f"{stu_award.team_name}\n"
                f"@{stu_award.place} {stu_award.date}"
            )
            for stu_award in stu_awards
        ]

        stu_info += '\n'.join(awards)
        message.reply(stu_info, modal_words=False)

    except Exception as e:
        message.report_exception('Contestant-CPCFinder', e)


@module(
    name="Contestant-CPCFinder",
    version="v1.0.1"
)
def register_module():
    pass
