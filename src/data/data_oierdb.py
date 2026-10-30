"""
OIerDB 数据访问模块
用于查询 OIer 数据库中的选手信息、比赛记录等
数据来源：CPCFinder 提供的 OI 查询接口
"""

from typing import Any, Dict

from src.platform.collect.cpcfinder import CPCFinder, CPCOIAward, CPCOIStudent

# 沿用既有的比赛类型命名，保证展示逻辑不变
_CONTEST_TYPE_ALIAS = {
    "CTSC": "CTS",
    "NOIP": "NOIP提高",
}

# 部分年份的高级比赛使用一/二/三等奖或国际金/银牌表述，统一为金/银/铜
_HIGH_LEVEL_CONTEST_TYPES = {"IOI", "NOI", "WC", "CTS", "APIO"}
_MEDAL_ALIAS = {
    "一等奖": "金牌",
    "二等奖": "银牌",
    "三等奖": "铜牌",
    "国际金牌": "金牌",
    "国际银牌": "银牌",
}


def _award_year(award: CPCOIAward) -> int:
    """获取获奖年份，缺失时从比赛日期中提取"""
    if award.contest_year:
        return int(award.contest_year)
    if award.event_date:
        return int(award.event_date[:4])
    return 0


def _build_record(student: CPCOIStudent, award: CPCOIAward) -> Dict[str, Any]:
    contest_type = _CONTEST_TYPE_ALIAS.get(award.contest_type, award.contest_type)
    level = award.medal
    if contest_type in _HIGH_LEVEL_CONTEST_TYPES:
        level = _MEDAL_ALIAS.get(level, level)

    return {
        "contest_name": award.contest_name,
        "contest_type": contest_type,
        "year": _award_year(award),
        "score": award.score or 0.0,
        "rank": award.rank or 0,
        "level": level,
        "province": student.province,
        "school": award.school,
        "grade": award.grade,
    }


def _calculate_ccf_level(records: list[Dict[str, Any]]) -> tuple[float, int]:
    """通用CCF评级计算方法"""
    score = 0.0
    level = 0

    # CCF 评级规则 - 统一规则，便于维护
    for record in records:
        contest_type = record['contest_type']
        medal = record['level']

        if contest_type == "NOI":
            if "金牌" in medal:
                level = max(level, 10)
            elif "银牌" in medal:
                level = max(level, 9)
            elif "铜牌" in medal:
                level = max(level, 8)

        elif contest_type in ["NOIP提高", "CSP提高"]:
            if "一等奖" in medal:
                level = max(level, 6)
                score += 300
            elif "二等奖" in medal:
                level = max(level, 4)
                score += 200
            elif "三等奖" in medal:
                level = max(level, 4)
                score += 100

        elif contest_type in ["NOIP普及", "CSP入门"]:
            if "一等奖" in medal:
                level = max(level, 5)
                score += 150
            elif "二等奖" in medal:
                level = max(level, 4)
                score += 100
            elif "三等奖" in medal:
                level = max(level, 3)
                score += 50

        elif contest_type in ["WC", "CTS", "APIO"]:
            if "金牌" in medal or "Au" == medal:
                level = max(level, 10)
                score += 600
            elif "银牌" in medal or "Ag" == medal:
                level = max(level, 9)
                score += 500
            elif "铜牌" in medal or "Cu" == medal:
                level = max(level, 8)
                score += 400

        elif contest_type == "IOI":
            if "金牌" in medal or "Au" == medal:
                level = max(level, 10)
                score += 1000
            elif "银牌" in medal or "Ag" == medal:
                level = max(level, 10)
                score += 800
            elif "铜牌" in medal or "Cu" == medal:
                level = max(level, 9)
                score += 600

    return score, level


def query_by_name(name: str) -> Dict[str, Any] | None:
    """根据姓名查询选手信息，未找到时返回 None"""
    candidates = CPCFinder.find_oi_students(name)
    if not candidates:
        return None

    # 接口按 OI 评分降序返回同名选手，取评分最高者
    student = CPCFinder.get_oi_student(candidates[0].id)
    records = [_build_record(student, award)
               for award in CPCFinder.get_oi_student_awards(student.id)]
    ccf_score, ccf_level = _calculate_ccf_level(records)

    return {
        "name": student.name,
        "same_name_count": len(candidates),
        "province": student.province,
        "graduation_year": student.graduation_year,
        "rating": student.rating,
        "rank": student.rank,
        "ccf_score": ccf_score,
        "ccf_level": ccf_level,
        "schools": list(dict.fromkeys(r['school'] for r in records if r['school'])),
        "provinces": [student.province] if student.province else [],
        "records": records,
    }
