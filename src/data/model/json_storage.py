import abc
import json
import os
from typing import Any


class JsonSerializer(abc.ABC):

    @classmethod
    @abc.abstractmethod
    def serialize(cls, target: Any) -> Any:
        pass

    @classmethod
    @abc.abstractmethod
    def deserialize(cls, target: Any) -> Any:
        pass


class NoSerialize(JsonSerializer):

    @classmethod
    def serialize(cls, target: Any) -> Any:
        return target

    @classmethod
    def deserialize(cls, target: Any) -> Any:
        return target


def save_data(current_data: Any, data_path: str, serializer: type[JsonSerializer]):
    try:
        raw_data = serializer.serialize(current_data)

        if not os.path.exists(os.path.dirname(data_path)):
            os.makedirs(os.path.dirname(data_path))

        tmp_path = f"{data_path}.tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=4)

        os.replace(tmp_path, data_path)

    except Exception as e:
        raise RuntimeError(f"Failed to save data: {e}") from e


def load_data(default_data: Any, data_path: str, serializer: type[JsonSerializer]) -> Any:
    try:
        if not os.path.exists(data_path):
            save_data(default_data, data_path, serializer)

        with open(data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            return serializer.deserialize(raw_data)

    except Exception as e:
        raise RuntimeError(f"Failed to load data: {e}") from e
