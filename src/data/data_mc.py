import json
import os

from src.core.constants import Constants

_lib_path = Constants.modules_conf.get_lib_path("MC-Rand")


def get_mc_resource(resource_name: str) -> dict | list[str]:
    resource_path = os.path.join(_lib_path, f"{resource_name}.json")
    if not os.path.isfile(resource_path):
        raise FileNotFoundError(resource_path)

    try:
        with open(resource_path, "r", encoding="utf-8") as f:
            resource = json.load(f)
            return resource
    except Exception as e:
        raise RuntimeError("Failed to load mc resource json") from e
