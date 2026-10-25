"""
OIerDB 数据访问模块
用于查询 OIer 数据库中的选手信息、比赛记录等
数据来源：CPCFinder 提供的 OI 查询接口
"""

from typing import Any, Dict, List

from src.platform.collect.cpcfinder import CPCFinder, CPCOIAward, CPCOIStudent

# 沿用既有的比赛类型命名，保证展示与 CCF 评级逻辑不变
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


class Record:
    """获奖记录类"""

    def __init__(self, contest_name: str, contest_type: str, year: int, level: str,
                 grade: str, school: str, score: float, province: str):
        self.contest_name = contest_name
        self.contest_type = contest_type
        self.year = year
        self.level = level
        self.grade = grade
        self.school = school
        self.score = score
        self.province = province


class OIer:
    """OIer 选手类"""

    def __init__(self, name: str, records: List[Record]):
        self.name = name
        self.records = records
        self.schools = list({r.school for r in records if r.school})
        self.provinces = list({r.province for r in records if r.province})

        # 计算CCF评级
        self.ccf_score, self.ccf_level = self._calculate_ccf_level()

    def _calculate_ccf_level_from_records(self, records: List['Record']) -> tuple[float, int]:
        """
        通用CCF评级计算方法
        参数：records - 要计算的记录列表
        返回：(CCF评分, CCF等级)
        """
        score = 0.0
        level = 0

        # CCF 评级规则 - 统一规则，便于维护
        for record in records:
            if record.contest_type == "NOI":
                if "金牌" in record.level:
                    level = max(level, 10)
                elif "银牌" in record.level:
                    level = max(level, 9)
                elif "铜牌" in record.level:
                    level = max(level, 8)

            elif record.contest_type in ["NOIP提高", "CSP提高"]:
                if "一等奖" in record.level:
                    level = max(level, 6)
                    score += 300
                elif "二等奖" in record.level:
                    level = max(level, 4)
                    score += 200
                elif "三等奖" in record.level:
                    level = max(level, 4)
                    score += 100

            elif record.contest_type in ["NOIP普及", "CSP入门"]:
                if "一等奖" in record.level:
                    level = max(level, 5)
                    score += 150
                elif "二等奖" in record.level:
                    level = max(level, 4)
                    score += 100
                elif "三等奖" in record.level:
                    level = max(level, 3)
                    score += 50

            elif record.contest_type in ["WC", "CTS", "APIO"]:
                # 高级比赛
                if "金牌" in record.level or "Au" == record.level:
                    level = max(level, 10)
                    score += 600
                elif "银牌" in record.level or "Ag" == record.level:
                    level = max(level, 9)
                    score += 500
                elif "铜牌" in record.level or "Cu" == record.level:
                    level = max(level, 8)
                    score += 400

            elif record.contest_type == "IOI":
                # IOI 国际信息学奥林匹克
                if "金牌" in record.level or "Au" == record.level:
                    level = max(level, 10)
                    score += 1000
                elif "银牌" in record.level or "Ag" == record.level:
                    level = max(level, 10)
                    score += 800
                elif "铜牌" in record.level or "Cu" == record.level:
                    level = max(level, 9)
                    score += 600

        return score, level

    def _calculate_ccf_level(self) -> tuple[float, int]:
        """计算该 OIer 的总体 CCF 评分及评级"""
        return self._calculate_ccf_level_from_records(self.records)

    def calculate_school_ccf_level(self, school_name: str) -> tuple[float, int]:
        """计算该 OIer 在特定学校的 CCF 评分及评级"""
        # 只计算该学校的记录
        school_records = [record for record in self.records if record.school == school_name]

        if not school_records:
            return 0.0, 0

        # 使用统一的CCF评级计算方法
        return self._calculate_ccf_level_from_records(school_records)


def _award_year(award: CPCOIAward) -> int:
    """获取获奖年份，缺失时从比赛日期中提取"""
    if award.contest_year:
        return int(award.contest_year)
    if award.event_date:
        return int(award.event_date[:4])
    return 0


def _build_record(student: CPCOIStudent, award: CPCOIAward) -> Record:
    contest_type = _CONTEST_TYPE_ALIAS.get(award.contest_type, award.contest_type)
    level = award.medal
    if contest_type in _HIGH_LEVEL_CONTEST_TYPES:
        level = _MEDAL_ALIAS.get(level, level)

    return Record(
        contest_name=award.contest_name,
        contest_type=contest_type,
        year=_award_year(award),
        level=level,
        grade=award.grade,
        school=award.school,
        score=award.score or 0.0,
        province=student.province,
    )


def _build_result(oier: OIer) -> Dict[str, Any]:
    records_out = []
    for record in oier.records:
        records_out.append({
            "contest_name": record.contest_name,
            "contest_type": record.contest_type,
            "year": record.year,
            "score": record.score,
            "rank": 0,
            "level": record.level,
            "province": record.province,
            "school": record.school,
            "grade": record.grade,
        })

    return {
        "name": oier.name,
        "schools": oier.schools,
        "provinces": oier.provinces,
        "ccf_score": oier.ccf_score,
        "ccf_level": oier.ccf_level,
        "records": records_out,
        "oier_obj": oier,  # 添加原始OIer对象引用
    }


def query_by_name(name: str) -> Dict[str, Any] | None:
    """根据姓名查询选手信息，未找到时返回 None"""
    candidates = CPCFinder.find_oi_students(name)
    if not candidates:
        return None

    # 接口按 OI 评分降序返回同名选手，取评分最高者
    student = candidates[0]
    oier = OIer(student.name,
                [_build_record(student, award)
                 for award in CPCFinder.get_oi_student_awards(student.id)])
    return _build_result(oier)
