import json
import os
import time
from dataclasses import dataclass, asdict

from src.core.constants import Constants
from src.data.model.binding import Binding, BindStatus
from src.data.model.ptt_system import DuelUser, PttSystem

_lib_path = os.path.join(Constants.config["lib_path"], "Duel")
_data_path = os.path.join(_lib_path, "codeforces.json")

_MAX_BINDING_DURATION = 10 * 60


@dataclass
class CFUser(DuelUser, Binding):
    establish_binding_time: int
    bind_status: int
    ptt: int
    contest_history: list[int]
    handle: str


def _save_data(current_data: dict[str, CFUser]):
    raw_data = {key: asdict(val) for key, val in current_data.items()}
    with open(_data_path, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=4)


def _fetch_data() -> dict[str, CFUser]:
    if not os.path.exists(_data_path):
        _save_data({})

    with open(_data_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        return {key: CFUser(**val) for key, val in raw_data.items()}


def _update_user(user_id: str, target: CFUser):
    current_data = _fetch_data()
    current_data[user_id] = target
    _save_data(current_data)


def _refresh_bind_status(target: CFUser):
    if target.bind_status == BindStatus.BINDING:
        if time.time() - target.establish_binding_time > _MAX_BINDING_DURATION:
            target.bind_status = BindStatus.UNBOUNDED


def get_binding(user_id: str) -> CFUser:
    current_data = _fetch_data()
    if user_id in current_data:
        return current_data[user_id]
    else:
        return CFUser(-1, BindStatus.UNBOUNDED, 0, [], "")


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


def unbound(user_id: str, target: CFUser) -> int:
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

    _update_user(user_a_id, target_a)
    _update_user(user_b_id, target_b)
    return 0
