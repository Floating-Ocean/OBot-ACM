import json
import os

from src.core.constants import Constants

_lib_path = Constants.modules_conf.get_lib_path("Dazs")


def get_dazs_resource() -> list[str]:
    resource_path = os.path.join(_lib_path, f"dazs_ans.json")
    if not os.path.isfile(resource_path):
        raise FileNotFoundError(resource_path)

    try:
        with open(resource_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(
            f"Failed to load Dazs resource: {e}"
        ) from e
