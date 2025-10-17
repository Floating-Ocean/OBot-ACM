"""
OIerDB 数据访问模块
用于查询 OIer 数据库中的选手信息、比赛记录等
直接解析 raw.txt 原始数据文件
"""

import json
import os
import re
from collections import defaultdict
from typing import List, Dict, Any

from src.core.constants import Constants


class Record:
    """获奖记录类"""

    def __init__(self, name: str, contest_name: str, contest_type: str, year: int,
                 level: str, grade: str, school: str, score: float, province: str, gender: str):
        self.name = name
        self.contest_name = contest_name
        self.contest_type = contest_type
        self.year = year
        self.level = level
        self.grade = grade
        self.school = school
        self.score = score
        self.province = province
        self.gender = gender


class OIer:
    """OIer 选手类"""

    def __init__(self, name: str, records: List[Record]):
        self.name = name
        self.records = records
        self.gender = records[0].gender if records else ""
        self.schools = list(set([r.school for r in records if r.school]))
        self.provinces = list(set([r.province for r in records if r.province]))

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


class OIerDB:
    """OIer 数据库查询系统"""

    def __init__(self):
        self.oiers: List[OIer] = []
        self.contests: Dict[str, Dict] = {}
        self.data_loaded = False

        # 索引映射
        self.oier_name_map: Dict[str, List[OIer]] = defaultdict(list)

    def _get_data_path(self, filename: str) -> str:
        """获取数据文件路径"""
        # 从src/data目录向上两级到项目根目录，然后进入lib/OIerDb
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))  # 向上两级到项目根目录

        # 根据文件类型确定子目录
        # raw.txt 和 school.txt 在 data/ 文件夹
        # contests.json 等配置文件在 static/ 文件夹
        if filename in ["raw.txt", "school.txt"]:
            return os.path.join(project_root, "lib", "OIerDb", "data", filename)
        else:
            return os.path.join(project_root, "lib", "OIerDb", "static", filename)

    def _parse_contest_info(self, contest_name: str) -> Dict[str, Any]:
        """解析比赛名称，提取比赛类型和年份"""
        # 常见比赛类型映射
        contest_types = {
            "NOIP": "NOIP提高",
            "CSP": "CSP提高",
            "NOI": "NOI",
            "IOI": "IOI",
            "WC": "WC",
            "CTSC": "CTS",
            "CTS": "CTS",
            "APIO": "APIO",
            "NGOI": "NGOI",
            "NOIST": "NOIST",
            "春季测试": "NOIST"
        }

        contest_type = "其他"
        year = 2024  # 默认年份

        # 提取年份
        year_match = re.search(r'(\d{4})', contest_name)
        if year_match:
            year = int(year_match.group(1))

        # 提取比赛类型
        for key, value in contest_types.items():
            if key in contest_name:
                contest_type = value
                break

        # 特殊处理
        if "提高" in contest_name:
            if "NOIP" in contest_name:
                contest_type = "NOIP提高"
            elif "CSP" in contest_name:
                contest_type = "CSP提高"
        elif "入门" in contest_name or "普及" in contest_name:
            if "NOIP" in contest_name:
                contest_type = "NOIP普及"
            elif "CSP" in contest_name:
                contest_type = "CSP入门"

        return {
            "name": contest_name,
            "type": contest_type,
            "year": year
        }

    def load_contests(self):
        """加载比赛数据（从contests.json读取用于参考）"""
        contests_file = self._get_data_path("contests.json")
        try:
            with open(contests_file, "r", encoding="utf-8") as f:
                contests_data = json.load(f)

            # 新格式的 contests.json 是一个字典
            if isinstance(contests_data, dict):
                self.contests = contests_data
            # 旧格式是列表
            elif isinstance(contests_data, list):
                for contest_data in contests_data:
                    self.contests[contest_data["name"]] = contest_data
        except FileNotFoundError:
            Constants.log.warning("[OIerDb] 比赛数据文件不存在")
            raise
        except json.JSONDecodeError as e:
            Constants.log.warning("[OIerDb] 比赛数据JSON格式错误")
            Constants.log.exception(f"[OIerDb] {e}")
            raise
        except Exception as e:
            Constants.log.warning("[OIerDb] 加载比赛数据时发生未知错误")
            Constants.log.exception(f"[OIerDb] {e}")
            raise

    def load_raw_data(self):
        """加载原始数据文件 raw.txt"""
        raw_file = self._get_data_path("raw.txt")
        records_by_name = defaultdict(list)

        try:
            with open(raw_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # 解析每行数据
                    # 格式：比赛名称,奖项等级,姓名,年级,学校,分数,省份,性别,其他信息
                    parts = line.split(",")
                    if len(parts) < 8:
                        continue

                    try:
                        contest_name = parts[0].strip()
                        level = parts[1].strip()
                        name = parts[2].strip()
                        grade = parts[3].strip()
                        school = parts[4].strip()
                        score_str = parts[5].strip()
                        province = parts[6].strip()
                        gender = parts[7].strip()

                        # 处理分数
                        score = 0.0
                        if score_str and score_str.replace(".", "").isdigit():
                            score = float(score_str)

                        # 解析比赛信息
                        contest_info = self._parse_contest_info(contest_name)

                        # 创建记录
                        record = Record(
                            name=name,
                            contest_name=contest_name,
                            contest_type=contest_info["type"],
                            year=contest_info["year"],
                            level=level,
                            grade=grade,
                            school=school,
                            score=score,
                            province=province,
                            gender=gender
                        )

                        records_by_name[name].append(record)

                    except Exception as e:
                        Constants.log.warning(f"[OIerDb] 解析第 {line_num} 行数据失败: {line}")
                        Constants.log.exception(f"[OIerDb] {e}")
                        continue

            # 创建 OIer 对象
            for name, records in records_by_name.items():
                oier = OIer(name, records)
                self.oiers.append(oier)
                self.oier_name_map[name].append(oier)

            # 按CCF等级和分数排序
            self.oiers.sort(key=lambda x: (x.ccf_level, x.ccf_score), reverse=True)
        except Exception as e:
            Constants.log.warning("[OIerDb] 加载原始数据失败")
            Constants.log.exception(f"[OIerDb] {e}")
            raise

    def load_data(self):
        """加载所有数据"""
        if not self.data_loaded:
            try:
                self.load_contests()
                self.load_raw_data()

                self.data_loaded = True
            except Exception as e:
                Constants.log.warning("[OIerDb] 数据加载失败")
                Constants.log.exception(f"[OIerDb] {e}")
                raise

    def query_by_name(self, name: str) -> List[Dict[str, Any]]:
        """根据姓名查询选手信息"""
        if not self.data_loaded:
            self.load_data()

        results = []
        oiers = self.oier_name_map.get(name, [])

        for oier in oiers:
            records_out = []
            for record in oier.records:
                records_out.append({
                    "contest_name": record.contest_name,
                    "contest_type": record.contest_type,
                    "year": record.year,
                    "score": record.score,
                    "rank": 0,  # raw.txt 中没有排名信息
                    "level": record.level,
                    "province": record.province,
                    "school": record.school,
                    "grade": record.grade,
                })

            results.append({
                "name": oier.name,
                "gender": oier.gender,
                "schools": oier.schools,
                "provinces": oier.provinces,
                "ccf_score": oier.ccf_score,
                "ccf_level": oier.ccf_level,
                "records": records_out,
                "oier_obj": oier,  # 添加原始OIer对象引用
            })

        return results

    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """智能搜索选手"""
        if not self.data_loaded:
            self.load_data()

        results = []
        query = query.lower().strip()

        for oier in self.oiers:
            found = False

            # 按姓名搜索
            if query in oier.name.lower():
                found = True

            # 按学校搜索
            if not found:
                for school in oier.schools:
                    if query in school.lower():
                        found = True
                        break

            # 按省份搜索
            if not found:
                for province in oier.provinces:
                    if query in province.lower():
                        found = True
                        break

            if found:
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

                results.append({
                    "name": oier.name,
                    "gender": oier.gender,
                    "schools": oier.schools,
                    "provinces": oier.provinces,
                    "ccf_score": oier.ccf_score,
                    "ccf_level": oier.ccf_level,
                    "records": records_out,
                    "oier_obj": oier,  # 添加原始OIer对象引用
                })

                if len(results) >= limit:
                    break

        return results

    def get_ranking(self, start: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        """获取排行榜"""
        if not self.data_loaded:
            self.load_data()

        results = []
        end = min(start + limit - 1, len(self.oiers))

        for i in range(start - 1, end):
            oier = self.oiers[i]
            results.append({
                "rank": i + 1,
                "name": oier.name,
                "gender": oier.gender,
                "schools": oier.schools,
                "provinces": oier.provinces,
                "ccf_score": oier.ccf_score,
                "ccf_level": oier.ccf_level,
                "record_count": len(oier.records),
            })

        return results


# 全局实例
oierdb_instance = OIerDB()
