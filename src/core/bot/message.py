from src.core.util.exception import handle_exception
from nonebot.exception import MatcherException
from nonebot_plugin_saa import Image, Text, AggregatedMessageFactory, MessageFactory, SaaTarget
from urllib.parse import urlparse
from nonebot import get_bot
from nonebot.adapters import Event



def _is_image_url(content: str) -> bool:
    """
    判断字符串是否是图片 URL

    Args:
        content: 待判断的字符串

    Returns:
        如果是图片 URL 则返回 True，否则返回 False
    """
    # 检查是否是 URL
    try:
        parsed = urlparse(content)
        if not parsed.scheme or parsed.scheme not in ('http', 'https'):
            return False
    except Exception:
        return False

    # 检查 URL 路径是否包含图片扩展名
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif',
                        '.bmp', '.webp', '.svg', '.ico')
    path_lower = parsed.path.lower()

    # 检查路径是否以图片扩展名结尾，或者 URL 中包含图片相关的关键词
    if any(path_lower.endswith(ext) for ext in image_extensions):
        return True

    # 有些图片 URL 可能没有扩展名，但包含图片相关的路径
    image_keywords = ('/avatar', '/image', '/img',
                      '/picture', '/photo', '/pic')
    if any(keyword in path_lower for keyword in image_keywords):
        return True

    return False


async def reply(contents: list[str | bytes], event: Event, modal_words: bool = False, finish: bool = True):
    """
    统一的回复函数，用于简化消息发送

    Args:
        contents: 消息内容列表，可以是字符串（文本或图片URL）或字节（图片数据）
        event: 事件对象
        modal_words: 是否添加语气词（当前项目未使用，保留参数以兼容）
        finish: 是否结束处理（调用 finish 或 send）
    """
    try:
        images: list[Image] = []
        text_parts: list[str] = []

        for content in contents:
            if isinstance(content, bytes):
                images.append(Image(content))
            elif _is_image_url(content):
                # 如果是图片 URL，使用 Image 类处理
                images.append(Image(content))
            else:
                text_parts.append(content)

        texts = Text("".join(text_parts)) if text_parts else None
        msg_builder = MessageFactory(texts) if texts else None

        if len(images):
            if msg_builder:
                msg_builder = AggregatedMessageFactory([msg_builder, *images])
            else:
                msg_builder = AggregatedMessageFactory(images)

        if msg_builder:
            if finish:
                await msg_builder.finish()
            else:
                await msg_builder.send()
    except MatcherException:
        # 忽略 MatcherException，这是 NoneBot 的正常终止行为
        pass


async def send(contents: list[str | bytes], target: SaaTarget):
    """
    统一的发送函数，用于主动发送消息到指定目标
    当有多条消息时，会自动聚合为合并消息

    Args:
        contents: 消息内容列表，可以是字符串（文本或图片URL）或字节（图片数据）
        target: 目标对象（如 TargetQQGroup, TargetQQPrivate）
    """
    try:
        message_factories = []

        for content in contents:
            if isinstance(content, bytes):
                message_factories.append(Image(content))
            elif _is_image_url(content):
                # 如果是图片 URL，使用 Image 类处理
                message_factories.append(Image(content))
            else:
                # 文本消息，每条消息创建一个 MessageFactory
                message_factories.append(MessageFactory(Text(content)))

        if not message_factories:
            return

        # 如果只有一条消息，直接发送；否则使用 AggregatedMessageFactory 聚合
        if len(message_factories) == 1:
            msg_builder = message_factories[0]
        else:
            msg_builder = AggregatedMessageFactory(message_factories)

        bot = get_bot()
        await msg_builder.send_to(target=target, bot=bot)
    except MatcherException:
        # 忽略 MatcherException，这是 NoneBot 的正常终止行为
        pass


async def report_exception(event: Event, module_name: str, e: Exception):
    """报告异常，自动忽略 MatcherException（NoneBot 的正常终止行为）"""
    from src.core.constants import Constants

    # 忽略 MatcherException，这是 NoneBot 的正常终止行为
    if isinstance(e, MatcherException):
        return

    Constants.log.warning(f"[obot-module] 操作失败，模块 {module_name} 出现异常")
    Constants.log.exception(f"[obot-module] {e}")
    await reply([handle_exception(e)], event, modal_words=False, finish=True)
