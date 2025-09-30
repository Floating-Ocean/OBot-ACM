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
        print(f"[oierdb-debug] 原始消息: {message.content}")
        print(f"[oierdb-debug] 解析后内容: {content}")
        
        if len(content) < 1:
            return message.reply("❓ 请输入命令，如: oier 张三")
        
        # 检查是否是oier命令（不需要严格匹配，因为已经通过tokens匹配了）
        print(f"[oierdb-debug] 第一个词: {content[0].lower()}")
        
        # 获取姓名参数
        names = content[1:] if len(content) > 1 else []
        
        if not names:
            return message.reply("""🤖 OIerDB查询帮助:

📝 选手查询:
  oier 张三              - 查询单个选手详细信息
  oier 张三 李四 王五     - 批量查询多个选手

💡 提示: 
  - 支持空格分隔多个姓名
  - 单个查询显示详细信息，批量查询显示简要信息""")
        
        # 限制查询数量
        if len(names) > 10:
            return message.reply("❌ 单次查询最多支持10个选手")
        
        # 执行查询
        if len(names) == 1:
            # 单个选手详细查询
            response = query_single_player(names[0])
        else:
            # 批量选手查询
            response = query_batch_players(names)
        
        return message.reply(response)
        
    except Exception as e:
        return message.reply(f"❌ 查询过程中出现错误: {str(e)}")


@command(tokens=["oier搜索", "OI搜索"])
def search_oier(message: RobotMessage):
    """搜索OI选手"""
    try:
        # 移除@标签并解析命令
        content = re.sub(r'<@!\d+>', '', message.content).strip().split()
        if len(content) < 3:
            return message.reply("❓ 请指定搜索类型和关键词，如: oier搜索 学校 清华")
        
        # 解析搜索类型和关键词
        search_type = content[1]
        query = ' '.join(content[2:]) if len(content) > 2 else ''
        print(f"[oierdb-debug] 搜索类型: {search_type}, 关键词: {query}")
        
        if not query:
            return message.reply("""🔍 OIer搜索帮助:

📝 搜索命令:
  oier搜索 学校 清华      - 按学校搜索
  oier搜索 姓名 张        - 按姓名搜索

💡 提示: 支持模糊搜索""")
        
        # 映射搜索类型
        type_mapping = {
            "学校": "school",
            "姓名": "name",
            "名字": "name"
        }
        
        if search_type not in type_mapping:
            return message.reply("❌ 不支持的搜索类型，请使用: 学校、姓名")
        
        # 执行搜索
        results = oierdb_instance.search(query, type_mapping[search_type], limit=15)
        
        if not results:
            return message.reply(f"❌ 未找到包含 '{query}' 的{search_type}相关选手")
        
        response = f"🔍 {search_type}搜索结果 (关键词: {query}):\n\n"
        
        for i, result in enumerate(results[:10], 1):  # 最多显示10个
            response += f"{i}. {result['name']}\n"
            response += f"   🏅 CCF等级: {result['ccf_level']}\n"
            response += f"   🏆 获奖次数: {len(result['records'])}\n"
            if result['records']:
                latest = result['records'][-1]
                response += f"   🎯 最近获奖: {latest['contest_name']} {latest['level']}\n"
            response += "\n"
        
        if len(results) > 10:
            response += f"... 还有 {len(results) - 10} 个选手未显示"
        
        return message.reply(response)
        
    except Exception as e:
        return message.reply(f"❌ 搜索过程中出现错误: {str(e)}")


@command(tokens=["oier排行", "OI排行榜"])
def oier_ranking(message: RobotMessage):
    """查看OI选手排行榜"""
    try:
        # 移除@标签并解析命令
        content = re.sub(r'<@!\d+>', '', message.content).strip().split()
        if len(content) < 1:
            return message.reply("❓ 请输入命令，如: oier排行")
        
        # 解析数量参数
        limit_str = content[1] if len(content) > 1 else ''
        print(f"[oierdb-debug] 排行榜数量: {limit_str}")
        
        # 解析数量参数
        limit = 10  # 默认显示10名
        if limit_str:
            try:
                limit = int(limit_str)
                if limit < 1:
                    limit = 10
                elif limit > 50:
                    limit = 50  # 最多显示50名
            except ValueError:
                return message.reply("❌ 请输入有效的数量，如: /oier排行 20")
        
        # 获取排行榜
        rankings = oierdb_instance.get_ranking(limit)
        
        if not rankings:
            return message.reply("❌ 无法获取排行榜数据")
        
        response = f"🏆 CCF等级排行榜 (前{len(rankings)}名):\n\n"
        
        for i, result in enumerate(rankings, 1):
            response += f"{i:2d}. {result['name']}\n"
            response += f"🏅 CCF等级: {result['ccf_level']}\n"
            response += f"🎖️ 获奖次数: {len(result['records'])}\n"
            
            # 显示最高荣誉
            if result['records']:
                # 按比赛重要性和奖项等级排序
                best_record = max(result['records'], key=lambda r: (
                    3 if r['contest_type'] == 'NOI' else 2 if 'NOIP' in r['contest_type'] else 1,
                    5 if '金牌' in r['level'] else 4 if '银牌' in r['level'] else 3 if '铜牌' in r['level'] else 1
                ))
                response += f"🎯 最佳成绩: {best_record['contest_name']}\n"
            
            response += "\n"
        
        return message.reply(response)
        
    except Exception as e:
        return message.reply(f"❌ 获取排行榜时出现错误: {str(e)}")


def query_single_player(name: str) -> str:
    """查询单个选手详细信息"""
    results = oierdb_instance.query_by_name(name)
    
    print(f"[oierdb-debug] 查询 '{name}' 返回 {len(results)} 个结果")
    
    if not results:
        return f"❌ 未找到选手 '{name}'"
    
    if len(results) > 1:
        # 多个同名选手
        response = f"🔍 找到 {len(results)} 个名为 '{name}' 的选手:\n\n"
        for i, result in enumerate(results[:5], 1):  # 最多显示5个
            uid_info = f" (UID: {result.get('uid', '未知')})" if result.get('uid') else ""
            response += f"{i}. {result['name']}{uid_info}\n"
            response += f"🏅 CCF等级: {result['ccf_level']}\n"
            response += f"🏆 获奖次数: {len(result['records'])}\n"
            if result['records']:
                latest = result['records'][-1]
                response += f"🎯 最近获奖: {latest['contest_name']}\n"
            response += "\n"
        
        if len(results) > 5:
            response += f"... 还有 {len(results) - 5} 个选手未显示"
    else:
        # 单个选手详细信息
        result = results[0]
        uid_info = f" (UID: {result.get('uid', '未知')})" if result.get('uid') else ""
        response = f"👤 选手信息: {result['name']}{uid_info}\n\n"
        
        # 按学校分类显示获奖记录
        records = result['records']
        if records:
            response += f"🏆 获奖记录 (共{len(records)}次):\n"
            
            # 按学校分组
            school_records = {}
            for record in records:
                school = record['school'] or '未知学校'
                if school not in school_records:
                    school_records[school] = []
                school_records[school].append(record)
            
            # 按学校显示获奖记录
            for school, school_record_list in school_records.items():
                # 计算该学校的CCF评级
                oier_obj = result.get('oier_obj')
                if oier_obj:
                    school_ccf_score, school_ccf_level = oier_obj.calculate_school_ccf_level(school)
                    ccf_info = f" | 🏅 CCF等级: {school_ccf_level}"
                else:
                    ccf_info = ""
                
                response += f"\n  🏫 {school} ({len(school_record_list)}次){ccf_info}:\n"
                
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
                            grade = record.get('grade', '')
                            grade_info = f" ({grade})" if grade else ""
                            response += f"{year} {contest} {grade_info}\n"
                
                # 显示其他类型
                for contest_type in contest_types:
                    if contest_type not in type_order:
                        records_of_type = contest_types[contest_type]

                        for record in sorted(records_of_type, key=lambda x: x['year'], reverse=True):
                            year = record['year']
                            contest = record['contest_name']
                            grade = record.get('grade', '')
                            grade_info = f" ({grade})" if grade else ""
                            response += f"{year} {contest} {grade_info}\n"
        else:
            response += "📝 暂无获奖记录"
    
    return response


def query_batch_players(names: list) -> str:
    """批量查询选手信息"""
    response = f"📋 批量查询结果 (共{len(names)}个选手):\n\n"
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
            
            response += f"{i}. {result['name']}"
            
            # 显示性别（如果有）
            if result.get('gender'):
                response += f" ({result['gender']})"
            
            response += multiple_info + "\n"
            
            # 显示关键信息：CCF等级、CCF分数、获奖次数
            response += f"🏅 CCF等级: {result['ccf_level']} | "
            response += f"🏆 获奖: {len(result['records'])}次\n"
            
            # 显示学校和省份信息（简化）
            if result.get('schools'):
                school_info = result['schools'][0] if len(result['schools']) == 1 else f"{result['schools'][0]}等{len(result['schools'])}校"
                response += f"{school_info}"
                
            if result.get('provinces'):
                response += f" | 📍 {', '.join(result['provinces'][:2])}"
                if len(result['provinces']) > 2:
                    response += "等"
            response += "\n"
            
        else:
            response += f"{i}. {name} ❌ 未找到\n"
        response += "\n"
    
    response += f"✅ 成功找到 {found_count}/{len(names)} 个选手"
    return response