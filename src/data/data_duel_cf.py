import os
import time
from dataclasses import dataclass, asdict

import nonebot_plugin_localstore as store
from src.data.model.binding import Binding, BindStatus
from src.data.model.json_storage import JsonSerializer, load_data, save_data
from src.data.model.ptt_system import DuelUser, PttSystem

_data_dir = store.get_data_dir("duel")
_data_path = os.path.join(_data_dir, "codeforces.json")

_MAX_BINDING_DURATION = 10 * 60


@dataclass
class CFUser(DuelUser, Binding):
    handle: str


class CFUserJson(JsonSerializer):

    @classmethod
    def serialize(cls, target: dict[str, CFUser]) -> dict:
        return {key: asdict(val) for key, val in target.items()}

    @classmethod
    def deserialize(cls, target: dict) -> dict[str, CFUser]:
        return {key: CFUser(**val) for key, val in target.items()}


def _update_user(user_id: str, target: CFUser, no_save: bool = False):
    current_data = load_data({}, _data_path, CFUserJson)
    current_data[user_id] = target
    if not no_save:  # 避免频繁写
        save_data(current_data, _data_path, CFUserJson)


def _refresh_bind_status(target: CFUser):
    if (target.bind_status == BindStatus.BINDING and
            time.time() - target.establish_binding_time > _MAX_BINDING_DURATION):
        target.bind_status = BindStatus.UNBOUNDED


def get_binding(user_id: str) -> CFUser:
    current_data = load_data({}, _data_path, CFUserJson)
    if user_id in current_data:
        return current_data[user_id]
    return CFUser(0, BindStatus.UNBOUNDED, 0, [], "")


def establish_binding(user_id: str, target: CFUser, handle: str) -> int:
    _refresh_bind_status(target)
    if target.bind_status == BindStatus.BINDING:
        return -1
    if target.bind_status == BindStatus.BOUND:
        return -2

    target.establish_binding_time = int(time.time())
    target.bind_status = BindStatus.BINDING
    target.handle = handle

    _update_user(user_id, target)
    return 0


def accept_binding(user_id: str, target: CFUser) -> int:
    _refresh_bind_status(target)
    if target.bind_status != BindStatus.BINDING:
        return -1

    target.bind_status = BindStatus.BOUND

    _update_user(user_id, target)
    return 0


def unbind(user_id: str, target: CFUser) -> int:
    if target.bind_status != BindStatus.BOUND:
        return -1

    target.bind_status = BindStatus.UNBOUNDED

    _update_user(user_id, target)
    return 0


def settle_duel(user_a_id: str, target_a: CFUser, user_b_id: str, target_b: CFUser,
                outcome: int, difficulty: int) -> int:
    if target_a.bind_status != BindStatus.BOUND or target_b.bind_status != BindStatus.BOUND:
        return -1

    PttSystem.process_duel(target_a, target_b, outcome, difficulty)

    _update_user(user_a_id, target_a, no_save=True)
    _update_user(user_b_id, target_b)
    return 0
