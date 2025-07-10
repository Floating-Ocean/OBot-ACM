import os

from src.core.constants import Constants

_lib_path = Constants.modules_conf.get_lib_path("How-To-Cook")
_dishes_path = os.path.join(_lib_path, "lib", "dishes")


def load_dishes():
    dishes: dict[str, str] = {}
    for root, _, files in os.walk(_dishes_path):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)
                dish_name = os.path.splitext(file)[0]
                dishes[dish_name] = full_path
    return dishes
