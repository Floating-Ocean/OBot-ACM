import random
import re
import time
from collections import deque

from src.core.bot.decorator import hook, module
from src.core.bot.message import MessageType, RobotMessage, is_bot_reply, is_own_message
from src.core.constants import Constants

_DEFAULT_CHAIN_THRESHOLD = 3  # 触发打断所需的连续相同消息条数
_MIN_CHAIN_AUTHORS = 2        # 至少需要几个不同的发言人，避免单人刷屏被误判为复读
_MIN_MIMIC_LENGTH = 2         # 至少多长才认为是在学 Bot 说话，避免语气词误伤
_CHAIN_WINDOW = 60            # 秒，连续复读的时间窗口
_BREAK_COOLDOWN = 30          # 秒，同群两次打断之间的冷却
_MIMIC_COOLDOWN = 60          # 秒，同群两次抓学舌之间的冷却
_MAX_CHAIN_HISTORY = 24       # 每个群保留的近期消息数

_MENTION_PATTERN = re.compile(r'<@!?[0-9A-Za-z]+>')

_BREAK_REPLIES = [
    "再复读我就要别复读了",
    "打断",
    "复读机被砸坏了",
    "复读得挺好，下次别复读了",
    "复读机成精了",
    "禁止套娃",
    "打断施法",
    "复读键给你扣了",
    "检测到复读，已自动打断。",
    "Token 很贵的，别烧了",
    "上下文不是这么用的",
    "复读次数已达上限",
    "你再复读，我就当没看见",
    "这句子已经包浆了",
    "别复读了，我快不认识这几个字了",
    "你卡了？要不要重启一下？",
    "复读机已被管理员移出群聊",
    "再复读就截断你的上下文",
]

_MIMIC_REPLIES = [
    "在？为什么学我说话？",
    "干嘛...",
    "别学我，学点好的",
    "你学我，是不是想引起我注意？",
    "干嘛学我，暗恋我就直说",
    "？",
]

# 群 ID -> 近期消息 (时间, 发言人, 归一化内容)
_chain_history: dict[str, deque[tuple[float, str, str]]] = {}
_last_break_time: dict[str, float] = {}
_last_mimic_time: dict[str, float] = {}

_repeat_conf = Constants.modules_conf.repeat or {}
_chain_threshold = max(_MIN_CHAIN_AUTHORS,
                       int(_repeat_conf.get('threshold', _DEFAULT_CHAIN_THRESHOLD)))
_exclude_scenes: dict = _repeat_conf.get('exclude', {})


def _normalize(content: str) -> str:
    """归一化消息内容，忽略 @ 与空白差异"""
    return re.sub(r'\s+', ' ', _MENTION_PATTERN.sub('', content)).strip()


def _is_repeating(uuid: str, content: str, author_id: str, now: float) -> bool:
    """判断这条消息是否构成了必须打断的复读链，命中时清空链并开始冷却"""
    chain = _chain_history.setdefault(uuid, deque(maxlen=_MAX_CHAIN_HISTORY))
    chain.append((now, author_id, content))

    if now - _last_break_time.get(uuid, 0) < _BREAK_COOLDOWN:
        return False

    authors: list[str] = []
    for stamp, author, text in reversed(chain):
        if text != content or now - stamp > _CHAIN_WINDOW:
            break
        authors.append(author)

    if len(authors) < _chain_threshold or len(set(authors)) < _MIN_CHAIN_AUTHORS:
        return False

    chain.clear()
    _last_break_time[uuid] = now
    return True


@hook(tokens=['*'])
def watch_group_messages(message: RobotMessage):
    """群内全量消息钩子：打断复读，并抓学 Bot 说话的群友"""
    uuid = message.uuid
    if message.message_type != MessageType.GROUP or uuid in _exclude_scenes:
        return

    # Bot 自己发出的消息会被推送回来，需要剔除
    if is_own_message(message):
        return

    content = _normalize(message.content)
    if not content or content.startswith('/'):
        # 纯媒体消息与指令不参与复读判定
        return

    now = time.time()

    if is_bot_reply(uuid, content):
        if (len(content) >= _MIN_MIMIC_LENGTH and
                now - _last_mimic_time.get(uuid, 0) >= _MIMIC_COOLDOWN):
            message.reply(random.choice(_MIMIC_REPLIES), modal_words=False)
            _last_mimic_time[uuid] = now
        return

    if _is_repeating(uuid, content, message.author_id, now):
        message.reply(random.choice(_BREAK_REPLIES), modal_words=False)


@module(
    name="Repeat",
    version="v1.0.0"
)
def register_module():
    pass
