import json
import os

from src.core.constants import Constants

_lib_path = Constants.modules_conf.get_lib_path("MC-Rand")


def _merge_all_lists(nested_dict: dict) -> list:
    """将字典嵌套的列表扁平化，但不处理列表内部嵌套"""
    result = []

    def _extract_lists(obj):
        if isinstance(obj, list):
            result.extend(obj)
        elif isinstance(obj, dict):
            # 如果是字典，递归处理每个值
            for value in obj.values():
                _extract_lists(value)

    _extract_lists(nested_dict)
    return result


def get_mc_resource(resource_name: str) -> list[str]:
    resource_path = os.path.join(_lib_path, f"{resource_name}.json")
    if not os.path.isfile(resource_path):
        raise FileNotFoundError(resource_path)

    try:
        with open(resource_path, "r", encoding="utf-8") as f:
            resource = json.load(f)
            return _merge_all_lists(resource)
    except Exception as e:
        raise RuntimeError(
            f"Failed to load MC resource '{resource_name}' from '{resource_path}': {e}"
        ) from e
