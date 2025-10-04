from dataclasses import dataclass
from urllib.parse import quote

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


_MEDAL_TYPE = {
    'NONE': '铁牌',
    'BRONZE': '铜牌',
    'SILVER': '银牌',
    'GOLD': '金牌',
}


class CPCFinder:

    @classmethod
    def find_student_id(cls, name: str, school: str) -> str | int:
        name = quote(name.strip())
        school = quote(school.strip())
        json_data = fetch_url_json(f"https://cpcfinder.com/api/student?"
                                   f"name={name}&school={school}", method='get')
        if 'data' not in json_data:
            raise ValueError("Invalid response for cpcfinder api")

        if len(json_data['data']) == 0:
            return 0
        if len(json_data['data']) > 1:
            return 1

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
