from dataclasses import dataclass
from urllib.parse import quote_plus

from src.core.util.tools import fetch_url_json


@dataclass
class CPCStudent:
    id: str
    name: str
    school: str
    champion: int
    sec: int
    thi: int
    gold: int
    silver: int
    bronze: int


@dataclass
class CPCAward:
    id: int
    contest_id: int
    contest_name: str
    team_id: int
    team_name: str
    date: str
    place: str
    rank: int
    official: bool
    official_rank: int
    medal: str


@dataclass
class CPCOIStudent:
    id: int
    name: str
    province: str
    graduation_year: int | None
    rating: float
    rank: int | None  # 全站排名，仅详情接口提供；搜索结果中为 None


@dataclass
class CPCOIAward:
    id: int
    contest_id: int
    contest_name: str
    contest_type: str
    contest_year: int | None
    event_date: str
    grade: str
    school: str
    score: float | None
    rank: int | None
    total_contestants: int | None
    medal: str


_MEDAL_TYPE = {
    'NONE': '铁牌',
    'BRONZE': '铜牌',
    'SILVER': '银牌',
    'GOLD': '金牌',
}

# OI 姓名搜索为模糊匹配，按评分降序返回；单页取较大值，未命中时继续翻页
_OI_SEARCH_PAGE_SIZE = 2000
_OI_SEARCH_MAX_PAGES = 5


class CPCFinder:

    @classmethod
    def find_student_id(cls, name: str, school: str) -> str | int | list:
        name = quote_plus(str(name).strip())
        school = quote_plus(str(school).strip())
        json_data = fetch_url_json(f"https://cpcfinder.com/api/student?"
                                   f"name={name}&school={school}", method='get')
        if 'data' not in json_data:
            raise ValueError("Invalid response for cpcfinder api")

        if len(json_data['data']) == 0:
            return 0
        if len(json_data['data']) > 1:
            # 返回候选列表
            return json_data['data']

        stu = json_data['data'][0]
        return stu['studentId']

    @classmethod
    def get_student_general(cls, student_id: str) -> CPCStudent:
        json_data = fetch_url_json(f"https://cpcfinder.com/api/student/{student_id}",
                                   method='get')
        if 'data' not in json_data:
            raise ValueError("Invalid response for cpcfinder api")

        stu = json_data['data']
        try:
            return CPCStudent(stu['studentId'], stu['name'], stu['schoolName'],
                              stu['championCount'], stu['secCount'], stu['thiCount'],
                              stu['goldCount'], stu['silverCount'], stu['bronzeCount'])
        except KeyError as e:
            raise ValueError("Invalid response for cpcfinder api") from e

    @classmethod
    def get_student_awards(cls, student_id: str) -> list[CPCAward]:
        json_data = fetch_url_json(f"https://cpcfinder.com/api/student/{student_id}/awards",
                                   method='get')
        if 'data' not in json_data:
            raise ValueError("Invalid response for cpcfinder api")

        awards = json_data['data']
        try:
            return [
                CPCAward(award['awardId'], award['contestId'], award['contestName'],
                         award['teamId'], award['teamName'],
                         award['date'], award['place'], award['rank'],
                         award['official'], award['officialRank'] if award['official'] else -1,
                         _MEDAL_TYPE[award['medalType']] if award['official'] else '打星')
                for award in awards
            ]
        except KeyError as e:
            raise ValueError("Invalid response for cpcfinder api") from e

    @classmethod
    def find_oi_students(cls, name: str) -> list[CPCOIStudent]:
        """按姓名查找 OI 选手，仅保留姓名完全一致者，按 OI 评分降序返回"""
        name = str(name).strip()
        if not name:  # 空姓名会让接口返回全库数据
            return []

        students = []
        for page in range(1, _OI_SEARCH_MAX_PAGES + 1):
            json_data = fetch_url_json(
                f"https://cpcfinder.com/api/oi/student?name={quote_plus(name)}"
                f"&current={page}&pageSize={_OI_SEARCH_PAGE_SIZE}", method='get')
            if 'data' not in json_data:
                raise ValueError("Invalid response for cpcfinder oi api")

            try:
                # 接口为模糊搜索，需自行过滤出完全同名的选手
                students = [
                    CPCOIStudent(stu['oiStudentId'], stu['name'],
                                 stu.get('province') or '',
                                 stu.get('graduationYear'),
                                 stu.get('rating') or 0.0,
                                 None)
                    for stu in json_data['data']
                    if (stu.get('name') or '').casefold() == name.casefold()
                ]
            except KeyError as e:
                raise ValueError("Invalid response for cpcfinder oi api") from e

            if students:  # 结果按评分降序，已命中同名选手则无需继续翻页
                break
            if page >= (json_data.get('pagination') or {}).get('pages', 0):
                break

        students.sort(key=lambda stu: stu.rating, reverse=True)
        return students

    @classmethod
    def get_oi_student(cls, student_id: int) -> CPCOIStudent:
        """按 ID 获取 OI 选手详情，包含全站排名"""
        json_data = fetch_url_json(f"https://cpcfinder.com/api/oi/student/{student_id}",
                                   method='get')
        if 'data' not in json_data:
            raise ValueError("Invalid response for cpcfinder oi api")

        stu = json_data['data']
        try:
            return CPCOIStudent(stu['oiStudentId'], stu['name'],
                                stu.get('province') or '',
                                stu.get('graduationYear'),
                                stu.get('rating') or 0.0,
                                stu.get('rank'))
        except KeyError as e:
            raise ValueError("Invalid response for cpcfinder oi api") from e

    @classmethod
    def get_oi_student_awards(cls, student_id: int) -> list[CPCOIAward]:
        json_data = fetch_url_json(
            f"https://cpcfinder.com/api/oi/student/{student_id}/participations",
            method='get')
        if 'data' not in json_data:
            raise ValueError("Invalid response for cpcfinder oi api")

        awards = json_data['data']
        try:
            return [
                CPCOIAward(award['oiAwardId'], award['oiContestId'], award['contestName'],
                           award['contestType'], award.get('contestYear'),
                           award.get('eventDate') or '', award.get('grade') or '',
                           award.get('schoolName') or '', award.get('score'),
                           award.get('rank'), award.get('totalContestants'),
                           award.get('medal') or '')
                for award in awards
            ]
        except KeyError as e:
            raise ValueError("Invalid response for cpcfinder oi api") from e
