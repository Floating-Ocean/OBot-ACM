import os.path
from dataclasses import dataclass, asdict

from src.core.constants import Constants
from src.data.model.json_storage import JsonSerializer, load_data

_lib_path = Constants.modules_conf.get_lib_path("Color-Rand")


@dataclass
class Colors:
    id: str
    name: str
    color: str


class ColorsJson(JsonSerializer):

    @classmethod
    def serialize(cls, target: list[Colors]) -> list[dict]:
        return [asdict(val) for val in target]

    @classmethod
    def deserialize(cls, target: list[dict]) -> list[Colors]:
        return [Colors(**val) for val in target]


def get_colors(color_scheme: str) -> list[Colors]:
    color_path = os.path.join(_lib_path, f'{color_scheme}.json')
    return load_data([], color_path, ColorsJson)
