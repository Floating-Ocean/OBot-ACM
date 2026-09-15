import os
import random
from dataclasses import dataclass, asdict

from src.core.constants import Constants
from src.core.util.tools import rand_str_len32, download_img, get_md5, md5_to_base62
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
            ids.append([value.id,
                        len([item for item in os.listdir(key_path)
                             if item.endswith(".gif")])])  # 不计入 parser.json
        else:
            ids.append([value.id, 0])
        for keys in value.key:
            match_dict[keys] = key
    ids.sort(key=lambda s: s[1], reverse=True)  # 按图片数量降序排序

    return PickOne(pick_one_conf, ids, match_dict)


def _get_img_dir_path(img_key: str, audit: bool = False) -> str:
    dir_path = (os.path.join(_lib_path, "__AUDIT__", img_key) if audit else
                os.path.join(_lib_path, img_key))
    os.makedirs(dir_path, exist_ok=True)
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


@dataclass
class PickOneImgStat:
    """单张表情包的统计信息"""
    md5: str
    hash_id: str  # 展示用 ID，与 /来只 回复中的 ID 一致
    likes: int
    comments: int
    pickup_times: int
    add_time: float


def _fallback_add_time(full_path: str, parser_data) -> float:
    """parser 里还是旧版字符串（或缺失）时，退回文件的修改时间"""
    if isinstance(parser_data, dict):
        return 0.0
    try:
        return os.stat(full_path).st_mtime
    except OSError:
        return 0.0


def _build_img_stat(name: str, parser_data, add_time: float) -> PickOneImgStat:
    """把 parser 中的一条记录转成统计信息，兼容值仍是字符串（旧版仅存 ocr_text）的情况"""
    md5 = name[:-4] if name.endswith(".gif") else name
    if not isinstance(parser_data, dict):  # 旧版数据或尚未解析
        return PickOneImgStat(md5, md5_to_base62(md5), 0, 0, 0, add_time)

    return PickOneImgStat(
        md5, md5_to_base62(md5),
        int(parser_data.get('likes', 0) or 0),
        len(parser_data.get('comments', []) or []),
        int(parser_data.get('pickup_times', 0) or 0),
        float(parser_data.get('add_time', 0) or 0)
    )


def get_category_stat(img_key: str) -> list[PickOneImgStat]:
    """获取一个类别下所有表情包的统计信息

    只读一次 parser.json：类别下图片可达数千张，逐张读盘会慢到不可用。
    """
    parser = get_img_parser(img_key)

    imgs = []
    for name, full_path in list_img(img_key):
        parser_data = parser.get(name)
        imgs.append(_build_img_stat(name, parser_data,
                                    _fallback_add_time(full_path, parser_data)))

    return imgs


def pick_preview_imgs(imgs: list[PickOneImgStat], count: int) -> list[PickOneImgStat]:
    """挑选若干张表情包作为预览，数量不足时有多少给多少"""
    if len(imgs) <= count:
        picked = list(imgs)
        random.shuffle(picked)
        return picked
    return random.sample(imgs, count)


def match_hash_id_prefix(preview_ids: list[str], category_ids: list[str],
                         prefix: str) -> list[str]:
    """按前缀匹配展示用 ID，优先匹配上一次预览展示过的图片，其次匹配整个类别

    匹配到多张时交由调用方提示前缀过短；大小写没对上时放宽一次。
    """
    if not prefix:
        return []

    for candidates in (preview_ids, category_ids):
        matched = [hash_id for hash_id in candidates if hash_id.startswith(prefix)]
        if not matched:
            lowered = prefix.lower()
            matched = [hash_id for hash_id in candidates if hash_id.lower().startswith(lowered)]
        if matched:
            return matched
    return []


def list_parser_hash_ids(img_parser: dict) -> list[str]:
    """列出 parser 中所有表情包的展示用 ID"""
    return [md5_to_base62(name[:-4]) for name in img_parser if name.endswith(".gif")]


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
