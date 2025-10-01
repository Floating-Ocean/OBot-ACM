#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
OIerDB查询模块
提供OI选手数据库查询功能
"""

import re
from src.core.bot.decorator import command, module
from src.core.bot.message import RobotMessage
from src.data.data_oierdb import oierdb_instance

__oierdb_version__ = "v1.0.0"

@module(
    name="OIerDB查询器",
    version=__oierdb_version__
)
def register_module():
    pass

@command(tokens=["oier", "OI选手", "信息学奥赛"])
def query_oier(message: RobotMessage):
    """查询OI选手信息"""
    try:
        # 移除@标签并解析命令
        content = re.sub(r'<@!\d+>', '', message.content).strip().split()
        
        if len(content) < 1:
            return message.reply("请输入命令，如: oier 张三")
        
        # 获取姓名参数
        names = content[1:] if len(content) > 1 else []
        
        if not names:
            return message.reply("""OIerDB查询帮助:

📝 选手查询:
  oier 张三              - 查询单个选手详细信息
  oier 张三 李四 王五     - 批量查询多个选手

💡 提示: 
  - 支持空格分隔多个姓名
  - 单个查询显示详细信息，批量查询显示简要信息""")
        
        # 限制查询数量
        if len(names) > 10:
            return message.reply("单次查询最多支持10个选手")
        
        # 执行查询
        if len(names) == 1:
            # 单个选手详细查询
            response = query_single_player(names[0])
        else:
            # 批量选手查询
            response = query_batch_players(names)
        
        return message.reply(response)
        
    except Exception as e:
        return message.reply(f"查询过程中出现错误: {str(e)}")

def format_grade_display(grade_str: str) -> str:
    """
    将年级字符串格式化为标准显示格式
    
    Args:
        grade_str: 原始年级字符串
    
    Returns:
        格式化后的年级字符串
    """
    if not grade_str or not grade_str.strip():
        return ""
    
    grade = grade_str.strip()
    
    # 数字年级到标准年级的映射
    number_to_standard = {
        '1': '初一', '2': '初二', '3': '初三',
        '4': '高一', '5': '高二', '6': '高三'
    }
    
    # 如果是数字年级，转换为标准格式
    if grade in number_to_standard:
        return number_to_standard[grade]
    
    # 其他格式直接返回
    return grade


def calculate_current_status(first_award_year: int, first_award_grade: str, current_year: int = 2025) -> str:
    """
    根据第一个奖项的年份和年级，推算选手在当前年份的状态
    
    Args:
        first_award_year: 第一个奖项的年份
        first_award_grade: 第一个奖项时的年级
        current_year: 当前年份，默认2025
    
    Returns:
        选手当前状态的描述字符串
    """
    if not first_award_year or not first_award_grade:
        return "无法推算"
    
    # 年级映射到标准年级数字 (1-12)
    grade_mapping = {
        # 小学
        '小学': 6, '小学/无': 6, '六年级': 6, '五年级': 5, '四年级': 4, '三年级': 3, '二年级': 2, '一年级': 1,
        # 初中
        '初一': 7, '初二': 8, '初三': 9, '1': 7, '2': 8, '3': 9,
        '七年级': 7, '八年级': 8, '九年级': 9,
        '初中一年级': 7, '初中二年级': 8, '初中三年级': 9,
        # 高中
        '高一': 10, '高二': 11, '高三': 12, '4': 10, '5': 11, '6': 12,
        '高中一年级': 10, '高中二年级': 11, '高中三年级': 12,
        # 其他格式
        '预初': 6, '初中': 8, '中四': 10, '中五': 11, '中六': 12,
        '初四': 9, '高四': 12,  # 一些特殊情况
        # 空值处理
        '': None, ' ': None, '无': None, '未知': None
    }
    
    # 获取当时的年级数字
    grade_str = first_award_grade.strip() if first_award_grade else ""
    first_grade_num = grade_mapping.get(grade_str)
    
    # 处理映射失败的情况
    if first_grade_num is None:
        if not grade_str:  # 空年级
            return "无法推算"
        else:  # 无法识别的年级格式
            return f"年级格式不识别: {grade_str}"
    
    # 计算年份差
    year_diff = current_year - first_award_year
    
    # 推算当前年级
    current_grade_num = first_grade_num + year_diff
    
    # 判断当前状态
    if current_grade_num <= 6:
        return f"小学{current_grade_num}年级"
    elif current_grade_num <= 9:
        grade_names = {7: "初一", 8: "初二", 9: "初三"}
        return grade_names.get(current_grade_num, f"初中{current_grade_num-6}年级")
    elif current_grade_num <= 12:
        grade_names = {10: "高一", 11: "高二", 12: "高三"}
        return grade_names.get(current_grade_num, f"高中{current_grade_num-9}年级")
    else:
        # 已经毕业
        years_after_graduation = current_grade_num - 12
        return f"高中毕业{years_after_graduation}年"


def query_single_player(name: str) -> str:
    """查询单个选手详细信息"""
    results = oierdb_instance.query_by_name(name)
    
    if not results:
        return f"[OIerDb] 未找到选手 '{name}'"
    
    if len(results) > 1:
        # 多个同名选手
        response = f"警告：找到多个同名选手，如果你看到这一条返回，说明出现了异常，请联系管理员进行处理\n\n"
    else:
        # 单个选手详细信息
        result = results[0]
        uid_info = f"(UID: {result.get('uid', '未知')})" if result.get('uid') else ""
        response = f"[OIerDb] 选手查询\n\n"
        response += f"{result['name']}{uid_info} \n"

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
                # 计算该学校本学生的CCF评级
                oier_obj = result.get('oier_obj')
                if oier_obj:
                    school_ccf_score, school_ccf_level = oier_obj.calculate_school_ccf_level(school)
                    ccf_info = f"CCF等级: {school_ccf_level}"
                else:
                    ccf_info = ""
                
                # 找到该学校最高奖项的获奖记录来推算当前状态
                def get_award_priority(record):
                    """计算奖项优先级，值越高代表奖项越高"""
                    contest_type = record.get('contest_type', '')
                    level = record.get('level', '')
                    
                    # 比赛类型权重
                    contest_weight = {
                        'IOI': 1000, 'NOI': 900, 'WC': 800, 'CTSC': 700, 'APIO': 600,
                        'CSP提高': 500, 'NOIP提高': 400, 'CSP入门': 300, 'NOIP普及': 200
                    }.get(contest_type, 100)
                    
                    # 奖项等级权重
                    level_weight = 0
                    if '金牌' in level or 'Au' in level:
                        level_weight = 100
                    elif '银牌' in level or 'Ag' in level:
                        level_weight = 80
                    elif '铜牌' in level or 'Cu' in level:
                        level_weight = 60
                    elif '一等奖' in level:
                        level_weight = 50
                    elif '二等奖' in level:
                        level_weight = 30
                    elif '三等奖' in level:
                        level_weight = 10
                    
                    return contest_weight + level_weight
                
                highest_record = max(school_record_list, key=get_award_priority)
                
                # 尝试多个记录来推算状态，优先使用有年级信息的记录
                records_with_grade = [r for r in school_record_list if r.get('grade', '').strip()]
                if records_with_grade:
                    # 如果最高奖项没有年级信息，使用有年级信息的最高奖项
                    if not highest_record.get('grade', '').strip():
                        highest_with_grade = max(records_with_grade, key=get_award_priority)
                        status_record = highest_with_grade
                    else:
                        status_record = highest_record
                else:
                    status_record = highest_record
                
                current_status = calculate_current_status(
                    status_record['year'], 
                    status_record.get('grade', ''), 
                    2025
                )
                
                ccf_display = f"{ccf_info}" if ccf_info else ""
                if current_status == "无法推算":
                    status_display = f"状态未知(基于{status_record['year']}年记录)"
                elif "年级格式不识别" in current_status:
                    grade_str = status_record.get('grade', '')
                    status_display = f"年级格式异常: '{grade_str}'"
                else:
                    status_display = current_status
                response += f"\n#{cnt} {school}\n"
                response += f"{ccf_display} / {status_display}\n"
                
                # 在学校内按比赛类型分组
                contest_types = {}
                for record in school_record_list:
                    contest_type = record['contest_type']
                    if contest_type not in contest_types:
                        contest_types[contest_type] = []
                    contest_types[contest_type].append(record)
                
                # 按重要性排序显示比赛类型
                type_order = ['NOI', 'IOI', 'WC', 'CTSC', 'APIO', 'CSP提高', 'CSP入门', 'NOIP提高', 'NOIP普及', 'NOID类']
                for contest_type in type_order:
                    if contest_type in contest_types:
                        records_of_type = contest_types[contest_type]

                        for record in sorted(records_of_type, key=lambda x: x['year'], reverse=True):
                            year = record['year']
                            contest = record['contest_name']
                            grade = record.get('grade', '').strip()
                            level = record.get('level', '').strip()
                            
                            # 格式化年级显示
                            if grade:
                                formatted_grade = format_grade_display(grade)
                                grade_display = f" @{formatted_grade}"
                            else:
                                grade_display = ""
                            
                            level_display = f"[{level}]" if level else "[未知]"
                            response += f"{level_display} {contest}{grade_display}\n"
                
                # 显示其他类型
                for contest_type in contest_types:
                    if contest_type not in type_order:
                        response += f"出现这个说明你的询问对象曾有列表以外的比赛，算是一个警告，请联系管理员\n\n"
                        records_of_type = contest_types[contest_type]

                        for record in sorted(records_of_type, key=lambda x: x['year'], reverse=True):
                            year = record['year']
                            contest = record['contest_name']
                            grade = record.get('grade', '').strip()
                            level = record.get('level', '').strip()
                            
                            # 格式化年级显示
                            if grade:
                                formatted_grade = format_grade_display(grade)
                                grade_info = f" ({formatted_grade})"
                            else:
                                grade_info = ""
                            
                            level_info = f" {level}" if level else ""
                            response += f"{contest}{level_info}{grade_info}\n"
        else:
            response += "暂无获奖记录"
    
    return response


def query_batch_players(names: list) -> str:
    """批量查询选手信息"""
    response = f"[OIerDb] 选手批量查询 ({len(names)}人)\n"
    found_count = 0

    for i, name in enumerate(names, 1):
        results = oierdb_instance.query_by_name(name)
        if results:
            found_count += 1
            
            # 如果有多个同名选手，选择CCF等级最高的（等级相同则按CCF分数）
            if len(results) > 1:
                result = max(results, key=lambda x: (x['ccf_level'], x['ccf_score']))
                multiple_info = f" [共{len(results)}人，显示最高级]"
            else:
                result = results[0]
                multiple_info = ""
            
            response += f"\n#{i} {result['name']}"
            response += multiple_info + "\n"
            
            # 显示关键信息：CCF等级、CCF分数、获奖次数
            response += f"CCF等级: {result['ccf_level']} / "
            response += f"获奖: {len(result['records'])}次\n"
            
            # 显示学校和省份信息（简化）
            if result.get('schools'):
                school_info = result['schools'][0] if len(result['schools']) == 1 else f"{result['schools'][0]}等{len(result['schools'])}校"
                response += f"@{school_info}"
                
            if result.get('provinces'):
                response += f" / {', '.join(result['provinces'][:2])}"
                if len(result['provinces']) > 2:
                    response += "等"
            response += "\n"
            
        else:
            response += f"{i}. {name} 未找到\n"

    return response