import os
from dataclasses import dataclass, asdict

from src.core.constants import Constants
from src.core.util.tools import rand_str_len32, download_img, get_md5
from src.data.model.json_storage import JsonSerializer, load_data, NoSerialize, save_data

_lib_path = Constants.modules_conf.get_lib_path("Pick-One")
_conf_data_path = os.path.join(_lib_path, "config.json")


@dataclass
class PickOneConf:
    id: str
    key: list[str]


@dataclass
class PickOne:
    conf: dict[str, PickOneConf]
    ids: list[tuple[str, int]]
    match_dict: dict[str, str]


class PickOneConfJson(JsonSerializer):

    @classmethod
    def serialize(cls, target: dict[str, PickOneConf]) -> dict:
        return {key: asdict(val) for key, val in target.items()}

    @classmethod
    def deserialize(cls, target: dict) -> dict[str, PickOneConf]:
        return {key: PickOneConf(**val) for key, val in target.items()}


def get_pick_one_data() -> PickOne:
    ids, match_dict = [], {}
    pick_one_conf = load_data({}, _conf_data_path, PickOneConfJson)
    for key, value in pick_one_conf.items():  # 方便匹配
        key_path = str(os.path.join(_lib_path, key))
        if os.path.exists(key_path):
            ids.append([value.id, len(os.listdir(key_path))])
        else:
            ids.append([value.id, 0])
        for keys in value.key:
            match_dict[keys] = key
    ids.sort(key=lambda s: s[1], reverse=True)  # 按图片数量降序排序

    return PickOne(pick_one_conf, ids, match_dict)


def _get_img_dir_path(img_key: str, audit: bool = False) -> str:
    dir_path = (os.path.join(_lib_path, "__AUDIT__", img_key) if audit else
                os.path.join(_lib_path, img_key))
    if not os.path.exists(dir_path):  # 保证目录存在
        os.makedirs(dir_path)
    return dir_path


def get_img_parser(img_key: str) -> dict:
    dir_path = _get_img_dir_path(img_key)
    parser_path = os.path.join(dir_path, "parser.json")
    return load_data({}, parser_path, NoSerialize)


def save_img_parser(img_key: str, data: dict[str, PickOneConf]):
    dir_path = _get_img_dir_path(img_key)
    parser_path = os.path.join(dir_path, "parser.json")
    save_data(data, parser_path, NoSerialize)


def get_img_full_path(img_key: str, name: str) -> str:
    dir_path = _get_img_dir_path(img_key)
    return os.path.join(dir_path, name)


def list_img(img_key: str) -> list[tuple[str, str]]:
    dir_path = _get_img_dir_path(img_key)
    return [(img, get_img_full_path(img_key, img))
            for img in os.listdir(dir_path) if img.endswith(".gif")]


def list_auditable() -> list[str]:
    audit_dir_path = _get_img_dir_path("__AUDIT__")
    return [key for key in os.listdir(audit_dir_path)
            if (os.path.isdir(os.path.join(audit_dir_path, key)) and
                os.path.exists(os.path.join(_lib_path, key)))]


def accept_audit(img_key: str, ok_status: dict[str, int]) -> int:
    dir_path = _get_img_dir_path(img_key, audit=True)
    real_dir_path = _get_img_dir_path(img_key, audit=False)
    img_list = [img for img in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, img))]

    cnt = 0
    for img in img_list:
        cnt += 1
        if os.path.exists(os.path.join(real_dir_path, img)):
            continue  # 图片重复
        os.rename(os.path.join(dir_path, img), os.path.join(real_dir_path, img))
        ok_status[img_key] = ok_status.get(img_key, 0) + 1

    return cnt


def accept_attachment(img_key: str, need_audit: bool, attachments: list[str]) -> tuple[int, int, int]:
    dir_path = _get_img_dir_path(img_key, need_audit)
    real_dir_path = _get_img_dir_path(img_key, audit=False)
    cnt, ok, duplicate = len(attachments), 0, 0

    for attach in attachments:
        if not getattr(attach, 'content_type', '').startswith('image'):
            continue  # 不是图片

        # 全都保存为 *.gif，客户端会自动解析，且这样便于判重
        file_path = os.path.join(dir_path, f"{rand_str_len32()}.gif")
        response = download_img(getattr(attach, 'url'), file_path)

        if response:
            md5 = get_md5(file_path)

            if (os.path.exists(os.path.join(real_dir_path, f"{md5}.gif")) or
                    os.path.exists(os.path.join(dir_path, f"{md5}.gif"))):
                os.remove(file_path)
                duplicate += 1  # 图片重复
                continue

            os.rename(file_path, os.path.join(dir_path, f"{md5}.gif"))
            ok += 1

    return cnt, ok, duplicate
