"""
OIerDB查询模块
提供OI选手数据库查询功能
"""

from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.data.data_oierdb import query_by_name


@command(tokens=["oier", "oierdb", "oidb", "oi", "oifinder", "oifind", "oifd",
                 "OI选手", "信息学奥赛"])
def reply_oierdb(message: RobotMessage):
    """查询OI选手信息"""
    try:
        # 解析命令
        content = message.tokens

        # 获取姓名参数
        names = content[1:] if len(content) > 1 else []
        if not names:
            message.reply("请输入选手名，如:\n\n"
                          f"{content[0]} 张三\n"
                          f"{content[0]} 张三 李四 王五", modal_words=False)
            return

        # 限制查询数量
        if len(names) > 3:
            message.reply("单次查询最多支持 3 个选手", modal_words=False)
            return

        # 执行查询
        message.reply('正在查询 OI 选手信息，请稍等')
        if len(names) == 1:
            # 单个选手详细查询
            response = _query_single_player(names[0])
        else:
            # 批量选手查询
            response = _query_batch_players(names)

        message.reply(response, modal_words=False)

    except Exception as e:
        message.report_exception('Contestant-OIerDb', e)


def _query_single_player(name: str) -> str:
    """查询单个选手详细信息"""
    result = query_by_name(name)

    if not result:
        return f"[OIerDb] 未找到选手 '{name}'"

    response = f"[OIerDb] 选手查询\n\n"
    if result.get('same_name_count', 1) > 1:
        response += f"同名选手：共 {result['same_name_count']} 名，仅显示评分最高者\n"
    response += f"{result['name']}"
    if result.get('province'):
        response += f" / {result['province']}"
    if result.get('graduation_year'):
        response += f" / {result['graduation_year']}届"
    response += f"\nCCF等级: {result['ccf_level']} / 评分: {result.get('rating') or 0:.2f}"
    if result.get('rank'):
        response += f" / 全站排名: #{result['rank']}"

    # 按学校分类显示获奖记录
    records = result['records']
    if records:
        # 按学校分组
        school_records = {}
        for record in records:
            school = record['school'] or '未知学校'
            if school not in school_records:
                school_records[school] = []
            school_records[school].append(record)

        # 按学校显示获奖记录
        cnt = 0
        for school, school_record_list in school_records.items():
            cnt += 1
            response += f"\n\n#{cnt} {school}"

            # 在学校内按比赛类型分组
            contest_types = {}
            for record in school_record_list:
                contest_type = record['contest_type']
                if contest_type not in contest_types:
                    contest_types[contest_type] = []
                contest_types[contest_type].append(record)

            # 按重要性排序显示比赛类型
            type_order = ['NOI', 'IOI', 'WC', 'CTS', 'APIO', 'CSP提高', 'CSP入门', 'NOIP提高', 'NOIST', 'NOIP普及', 'NOID类']

            for contest_type in type_order:
                if contest_type in contest_types:
                    records_of_type = contest_types[contest_type]

                    for record in sorted(records_of_type, key=lambda x: x['year'], reverse=True):
                        contest = record['contest_name']
                        grade = record.get('grade', '').strip()
                        level = record.get('level', '').strip()

                        # 年级使用接口返回的写法
                        grade_display = f" @{grade}" if grade else ""

                        level_display = f"[{level}]" if level else "[未知]"
                        response += f"\n{level_display} {contest}{grade_display}"

            # 显示其他类型
            for contest_type in contest_types:
                if contest_type not in type_order:
                    response += "出现这个说明你的询问对象曾有列表以外的比赛，算是一个警告，请联系管理员\n"

                    records_of_type = contest_types[contest_type]

                    for record in sorted(records_of_type, key=lambda x: x['year'], reverse=True):
                        contest = record['contest_name']
                        response += f"未定义比赛名称: {contest}\n"
    else:
        response += "\n\n暂无获奖记录"

    return response


def _query_batch_players(names: list) -> str:
    """批量查询选手信息"""
    blocks = []

    for i, name in enumerate(names, 1):
        result = query_by_name(name)
        if not result:
            blocks.append(f"#{i} {name}  未找到")
            continue

        block = f"#{i} {result['name']}\n"
        if result.get('same_name_count', 1) > 1:
            block += f"同名选手：共 {result['same_name_count']} 名，仅显示评分最高者\n"
        # 显示关键信息：CCF等级、获奖次数
        block += f"CCF等级: {result['ccf_level']} / 获奖: {len(result['records'])}次\n"

        # 显示学校和省份信息（简化）
        if result.get('schools'):
            school_info = result['schools'][0] if len(
                result['schools']) == 1 else f"{result['schools'][0]}等{len(result['schools'])}校"
            block += f"@{school_info}"

        if result.get('provinces'):
            block += f" / {', '.join(result['provinces'][:2])}"
            if len(result['provinces']) > 2:
                block += "等"

        blocks.append(block)

    return f"[OIerDb] 选手批量查询 ({len(names)}人)\n\n" + "\n\n".join(blocks)


@module(
    name="Contestant-OIerDb",
    version="v1.1.1"
)
def register_module():
    pass
