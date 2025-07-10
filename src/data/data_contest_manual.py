import os
from dataclasses import dataclass, asdict

from src.core.constants import Constants
from src.data.model.json_storage import JsonSerializer, load_data, save_data

_lib_path = Constants.modules_conf.get_lib_path("Contest-List-Renderer")
_data_path = os.path.join(_lib_path, "manual_contests.json")


@dataclass
class ManualContest:
    platform: str
    abbr: str
    name: str
    start_time: int
    duration: int
    supplement: str

    def __eq__(self, other):
        return (self.start_time == other.start_time and
                self.platform == other.platform and
                self.name == other.name)


class ManualContestJson(JsonSerializer):

    @classmethod
    def serialize(cls, target: list[ManualContest]) -> list[dict]:
        return [asdict(val) for val in target]

    @classmethod
    def deserialize(cls, target: list[dict]) -> list[ManualContest]:
        return [ManualContest(**val) for val in target]


def get_contests() -> list[ManualContest]:
    return load_data([], _data_path, ManualContestJson)


def save_contest(contest: ManualContest) -> bool:
    manual_contests = get_contests()

    for existing_contest in manual_contests:
        if existing_contest == contest:
            return False

    manual_contests.append(contest)
    save_data(manual_contests, _data_path, ManualContestJson)
    return True
