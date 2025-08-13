import random

from nonebot.adapters.qq import MessageEvent as QQMessageEvent
from nonebot.adapters import Event
from nonebot_plugin_saa import Image, Text, AggregatedMessageFactory, MessageFactory

from src.core.constants import Constants
from src.core.util.exception import handle_exception


async def reply(contents:list[str | bytes], event:Event, modal_words: bool = True, finish: bool = True):
    msg_builder = None
    if isinstance(event,QQMessageEvent):
        for content in contents:
            if isinstance(content, bytes):
                msg_builder = Image(content) if msg_builder is None else msg_builder + Image(content)
            else:
                msg_builder = Text(content) if msg_builder is None else msg_builder + Text(content)
        if modal_words:
            msg_builder = msg_builder + Text(random.choice(Constants.modal_words))
    else:
        images:list[Image] = []
        texts = Text("")
        for content in contents:
            if isinstance(content, bytes):
                images.append(Image(content))
            else:
                texts = texts + Text(content)
        if modal_words:
            texts = texts + Text(random.choice(Constants.modal_words))
        msg_builder = MessageFactory(texts)
        if len(images):
            msg_builder = AggregatedMessageFactory([msg_builder, *images])
    if finish:
        await msg_builder.finish()
    else:
        await msg_builder.send()


def report_exception(event:Event,module_name: str, e: Exception):
    Constants.log.warning(f"[obot-module] 操作失败，模块 {module_name} 出现异常")
    Constants.log.exception(f"[obot-module] {e}")
    reply([handle_exception(e)], event, modal_words=False, finish=True)
