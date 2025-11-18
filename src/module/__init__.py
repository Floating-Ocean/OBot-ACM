import importlib


def register_all_modules():
    """注册所有模块"""
    modules = [
        "cp.atc",
        "cp.cf",
        "cp.contest_manual",
        "cp.cpcfinder",
        "cp.oierdb",
        "cp.nk",
        "cp.peeper",
        "game.guess_interval",
        "game.guess_1a2b",
        "game.tetris",
        "stuff.color",
        "stuff.git_cmd",
        "stuff.how_to_cook",
        "stuff.mc",
        "stuff.misc",
        "stuff.pick_one",
        "stuff.rand",
        "stuff.uptime",
    ]
    for mod in modules:
        importlib.import_module(f"src.module.{mod}")


register_all_modules()
