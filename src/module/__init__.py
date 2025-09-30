def register_all_modules():
    """用于加载各模块，函数register_module本身无意义"""
    from .cp.atc import register_module
    from .cp.cf import register_module
    from .cp.contest_manual import register_module
    from .cp.contestant import register_module
    from .cp.nk import register_module
    from .cp.peeper import register_module
    from .game.guess_interval import register_module
    from .game.guess_1a2b import register_module
    from .game.tetris import register_module
    from .tool.how_to_cook import register_module
    from .tool.pick_one import register_module
    from .tool.rand import register_module
    from .tool.uptime import register_module


register_all_modules()
