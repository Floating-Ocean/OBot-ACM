import random
import threading
from dataclasses import dataclass
from enum import Enum

from src.core.bot.command import command
from src.core.bot.message import RobotMessage
from src.core.constants import HelpStrList, Constants
from src.core.util.output_cached import get_cached_prefix
from src.core.util.tools import check_is_int, png2jpg
from src.render.pixie.render_tetris_game import TetrisGameRenderer, TetrisNextBlockRenderer

__tetris_version__ = "v1.1.0"

_TETRIS_HELP = '\n'.join(HelpStrList(Constants.help_contents["tetris"]))

BLOCKS = [
    {
        "name": "T字型",
        "perm": [
            [[1, 1, 1], [0, 1, 0]],
            [[0, 1], [1, 1], [0, 1]],
            [[0, 1, 0], [1, 1, 1]],
            [[1, 0], [1, 1], [1, 0]]
        ]
    },
    {
        "name": "L字型",
        "perm": [
            [[2, 0], [2, 0], [2, 2]],
            [[2, 2, 2], [2, 0, 0]],
            [[2, 2], [0, 2], [0, 2]],
            [[0, 0, 2], [2, 2, 2]]
        ]
    },
    {
        "name": "反L字型",
        "perm": [
            [[0, 3], [0, 3], [3, 3]],
            [[3, 0, 0], [3, 3, 3]],
            [[3, 3], [3, 0], [3, 0]],
            [[3, 3, 3], [0, 0, 3]]
        ]
    },
    {
        "name": "Z字型",
        "perm": [
            [[4, 4, 0], [0, 4, 4]],
            [[0, 4], [4, 4], [4, 0]],
            [[4, 4, 0], [0, 4, 4]],
            [[0, 4], [4, 4], [4, 0]]
        ]
    },
    {
        "name": "反Z字型",
        "perm": [
            [[0, 5, 5], [5, 5, 0]],
            [[5, 0], [5, 5], [0, 5]],
            [[0, 5, 5], [5, 5, 0]],
            [[5, 0], [5, 5], [0, 5]]
        ]
    },
    {
        "name": "正方形",
        "perm": [
            [[6, 6], [6, 6]],
            [[6, 6], [6, 6]],
            [[6, 6], [6, 6]],
            [[6, 6], [6, 6]]
        ]
    },
    {
        "name": "长条形",
        "perm": [
            [[7], [7], [7], [7]],
            [[7, 7, 7, 7]],
            [[7], [7], [7], [7]],
            [[7, 7, 7, 7]]
        ]
    }
]


def register_module():
    pass


class GameStatus(Enum):
    """记录当前游戏状态"""
    IDLE = 0
    RUNNING = 1
    ENDED = 2


@dataclass
class GameInfo:
    status: GameStatus
    map: list[list[int]]
    next_block: int
    score: int
    trials: int


_game_info = {}
_game_info_lock = threading.Lock()


def _simulate_block_falling(current_info: GameInfo,
                            block_id: int, rotate_cnt: int, setting_point_col: int) -> int:
    """
    模拟方块下落，找到落脚点，返回方块左上角所在行
    无法下落时返回 -1
    """
    block = BLOCKS[block_id]["perm"][rotate_cnt % len(BLOCKS[block_id]["perm"])]
    block_w, block_h = len(block[0]), len(block)
    map_w, map_h = len(current_info.map[0]), len(current_info.map)
    foot_hold_line = map_h - 1

    for col in range(setting_point_col, setting_point_col + block_w):
        if col >= map_w:
            foot_hold_line = -1
            break

        current_hitbox_b = 0  # 选中方块在当前列的底部碰撞箱
        for row in range(block_h):
            if block[row][col - setting_point_col] != 0:
                current_hitbox_b = row

        current_foothold_line = map_h - 1
        for row in range(map_h - 1, -1, -1):
            if current_info.map[row][col] != 0:
                current_foothold_line = row - 1

        foot_hold_line = max(-1, min(foot_hold_line, current_foothold_line - current_hitbox_b))

    return foot_hold_line


def _get_valid_setting_points(current_info: GameInfo,
                              block_id: int, rotate_cnt: int) -> list[int]:
    """
    获取方块可以下落的位置，返回落脚点对应方块左上角所在行
    """
    map_w = len(current_info.map)
    valid_setting_points = [0] * map_w

    for col in range(map_w):
        valid_setting_points[col] = _simulate_block_falling(current_info,
                                                            block_id, rotate_cnt, col)

    return valid_setting_points


def _eliminate_lines(current_info: GameInfo,
                     block_id: int, rotate_cnt: int, setting_point_row: int) -> int:
    """
    检查方块落下后，能否触发所在行的满行消除，并模拟过程，返回消行数
    """
    block = BLOCKS[block_id]["perm"][rotate_cnt % len(BLOCKS[block_id]["perm"])]
    block_h = len(block)
    map_w = len(current_info.map[0])
    eliminated_lines_cnt = 0

    for row in range(setting_point_row, setting_point_row + block_h):
        if all(x > 0 for x in current_info.map[row]):
            # 触发消行，当前行置零，自底往上交换
            current_info.map[row] = [0] * map_w
            for swap_row in range(row, 0, -1):
                current_info.map[swap_row], current_info.map[swap_row - 1] = \
                    current_info.map[swap_row - 1], current_info.map[swap_row]
            eliminated_lines_cnt += 1

    return eliminated_lines_cnt


def _render_map(current_info: GameInfo) -> str:
    cached_prefix = get_cached_prefix('Tetris-Project')
    img_path = f"{cached_prefix}.png"
    tetris_game_img = TetrisGameRenderer(current_info.map, cached_prefix, current_info.score,
                                         current_info.trials).render()
    tetris_game_img.write_file(img_path)
    return png2jpg(img_path)


def _validate_next_block(current_info: GameInfo, block_id: int) -> bool:
    for rotate_cnt in range(4):
        valid_setting_points = _get_valid_setting_points(current_info, block_id, rotate_cnt)
        if any(x != -1 for x in valid_setting_points):
            return True

    return False


def _end_game(message: RobotMessage, current_info: GameInfo):
    message.reply("游戏结束", img_path=_render_map(current_info), modal_words=False)
    current_uuid = message.uuid
    _game_info[current_uuid] = GameInfo(GameStatus.ENDED,
                                        [[0] * 24 for _ in range(24)], -1, -1, -1)


def _next_block(message: RobotMessage, current_info: GameInfo):
    current_info.next_block = random.randint(0, len(BLOCKS) - 1)
    if not _validate_next_block(current_info, current_info.next_block):
        _end_game(message, current_info)
        return None

    cached_prefix = get_cached_prefix('Tetris-Project')
    img_path = f"{cached_prefix}.png"
    tetris_next_block_img = TetrisNextBlockRenderer(BLOCKS[current_info.next_block],
                                                    cached_prefix).render()
    tetris_next_block_img.write_file(img_path)

    message.reply(f'下一个方块为 {BLOCKS[current_info.next_block]["name"]}\n\n'
                  '使用 "/tetris [旋转次数] [左上角所在列]" 放置方块，不要带上中括号',
                  img_path=png2jpg(img_path))
    return None


def _get_and_validate_map_col(message: RobotMessage) -> int:
    current_uuid = message.uuid
    current_info: GameInfo = _game_info[current_uuid]

    if current_info.status == GameStatus.RUNNING:
        message.reply('游戏已经开始，请使用 "/tetris [旋转次数] [左上角所在列]" 放置方块，不要带上中括号')
        return -1

    if len(message.tokens) > 2:
        message.reply(f'参数有误\n\n{_TETRIS_HELP}', modal_words=False)
        return -1

    map_col = 24
    if len(message.tokens) == 2:
        if (len(message.tokens[1]) != 2 or not check_is_int(message.tokens[1]) or
                not 16 <= int(message.tokens[1]) <= 24):
            message.reply(f'列数 col 应为 [16, 24] 内的整数\n\n{_TETRIS_HELP}', modal_words=False)
            return -1
        map_col = int(message.tokens[1])

    return map_col


def start_game(message: RobotMessage):
    current_uuid = message.uuid
    current_info: GameInfo = _game_info[current_uuid]

    map_col = _get_and_validate_map_col(message)
    if map_col == -1:
        return None

    current_info = GameInfo(GameStatus.RUNNING,
                            [[0] * map_col for _ in range(24)], -1, 0, 0)

    _render_map(current_info)
    message.reply("俄罗斯方块游戏开始！", img_path=_render_map(current_info), modal_words=False)

    _game_info[current_uuid] = current_info
    _next_block(message, current_info)

    return None


def _place_block(current_info: GameInfo,
                 block_id: int, rotate_cnt: int,
                 setting_point_row: int, setting_point_col: int):
    block = BLOCKS[block_id]["perm"][rotate_cnt % len(BLOCKS[block_id]["perm"])]
    block_w, block_h = len(block[0]), len(block)
    for row in range(block_h):
        for col in range(block_w):
            if block[row][col] != 0:
                current_info.map[setting_point_row + row][setting_point_col + col] = \
                    block[row][col]


def _validate_in_game_pre_input(message: RobotMessage) -> bool:
    current_uuid = message.uuid
    current_info: GameInfo = _game_info[current_uuid]

    if _game_info[current_uuid].status == GameStatus.IDLE:
        message.reply(f"游戏还未开始\n\n{_TETRIS_HELP}",
                      modal_words=False)
        return False

    if _game_info[current_uuid].status == GameStatus.ENDED:
        message.reply(f"上一轮游戏已结束\n\n{_TETRIS_HELP}",
                      modal_words=False)
        return False

    if not 2 <= len(message.tokens) <= 3:
        message.reply(f'参数有误\n\n{_TETRIS_HELP}', modal_words=False)
        return False

    if not check_is_int(message.tokens[1]):
        if message.tokens[1] in ['stop', '结束', 'end', 'finish']:
            _end_game(message, current_info)
        else:
            message.reply(f'参数有误\n\n{_TETRIS_HELP}', modal_words=False)
        return False

    if (len(message.tokens) == 2 or not check_is_int(message.tokens[2]) or
            not 0 <= int(message.tokens[1]) < 100 or
            not int(message.tokens[2]) >= 0):
        message.reply(f'参数有误\n\n{_TETRIS_HELP}', modal_words=False)
        return False

    return True


def _get_and_validate_setting_point_row(message: RobotMessage,
                                        setting_point_col: int, rotate_cnt: int) -> int:
    current_uuid = message.uuid
    current_info: GameInfo = _game_info[current_uuid]

    valid_setting_points = _get_valid_setting_points(current_info,
                                                     current_info.next_block, rotate_cnt)

    if setting_point_col == -1:
        message.reply('列从 1 开始编号')
        return -1

    map_w = len(current_info.map[0])

    if setting_point_col >= map_w:
        message.reply('没有这么多列')
        return -1

    setting_point_row = valid_setting_points[setting_point_col]
    if setting_point_row == -1:
        message.reply(f'第 {setting_point_col + 1} 列放不下了')
        return -1

    return setting_point_row


def put_block(message: RobotMessage):
    current_uuid = message.uuid
    current_info: GameInfo = _game_info[current_uuid]

    if not _validate_in_game_pre_input(message):
        return None

    rotate_cnt, setting_point_col = int(message.tokens[1]), int(message.tokens[2]) - 1
    setting_point_row = _get_and_validate_setting_point_row(message, setting_point_col, rotate_cnt)

    current_info.trials += 1
    _place_block(current_info,
                 current_info.next_block, rotate_cnt, setting_point_row, setting_point_col)
    eliminated_lines_count = _eliminate_lines(current_info, current_info.next_block,
                                              rotate_cnt, setting_point_row)

    if eliminated_lines_count > 0:
        obtained_score = eliminated_lines_count ** int(2 * max(1, current_info.score // 150))
        current_info.score += obtained_score
        message.reply(f'成功消除 {eliminated_lines_count} 行，获得 {obtained_score} 分',
                      img_path=_render_map(current_info))
    else:
        message.reply('', img_path=_render_map(current_info), modal_words=False)

    _game_info[current_uuid] = current_info
    _next_block(message, current_info)

    return None


@command(tokens=["tetris", "tetris-project", "俄罗斯方块", "tt"], multi_thread=True)
def reply_tetris(message: RobotMessage):
    with _game_info_lock:
        current_uuid = message.uuid
        if current_uuid not in _game_info:
            _game_info[current_uuid] = GameInfo(GameStatus.IDLE,
                                                [[0] * 24 for _ in range(24)], -1, -1, -1)

        if _game_info[current_uuid].status != GameStatus.RUNNING:
            start_game(message)
        else:
            put_block(message)

        return None
