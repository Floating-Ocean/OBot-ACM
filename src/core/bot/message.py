import asyncio
import base64
import random
import re
import threading
import uuid
from enum import Enum
from typing import Optional, Union, Literal

from botpy import BotAPI
from botpy.message import Message, GroupMessage, C2CMessage, DirectMessage

from src.core.bot.perm import PermissionLevel
from src.core.constants import Constants
from src.core.util.exception import handle_exception
from src.core.util.img_transform import patch_img_transform
from src.core.util.tools import reverse_text_on_41


class MessageType(Enum):
    GUILD = "guild"
    DIRECT = "direct"
    GROUP = "group"
    C2C = "c2c"


class RobotMessage:
    """合并多种消息类型的操作"""

    def __init__(self, api: BotAPI):
        self.api = api
        self.message_type: Optional[MessageType] = None
        self.message: Optional[Union[Message, GroupMessage, C2CMessage, DirectMessage]] = None
        self.loop = None

        self.content = ""
        self.tokens = []
        self.author_id = ""
        self.attachments = []
        self.msg_seq = 0
        self.seq_lock = threading.Lock()
        self.user_permission_level: PermissionLevel = PermissionLevel.USER
        self.uuid = str(uuid.uuid4())  # 默认值，正常来说会被覆盖
        self._guild_public = False  # Guild only
        self._group_public = False  # Group only，非 @bot 的群公屏消息
        self._active = False  # 主动消息标记
        # 主动消息所需的标识符
        self._channel_id: Optional[str] = None
        self._guild_id: Optional[str] = None
        self._group_openid: Optional[str] = None

    def is_guild_public(self):
        return self._guild_public

    def is_group_public(self):
        return self._group_public

    def is_active(self):
        return self._active

    def _initial_setup(self, message: Message | GroupMessage | C2CMessage | DirectMessage,
                       author_id_path: str):
        self.content = message.content
        self.tokens = re.sub(r'<@!\d+>', '', message.content).strip().split()
        self.author_id = getattr(message.author, author_id_path, "")
        self.attachments = message.attachments
        self.user_permission_level = PermissionLevel.distribute_permission(self.author_id)

    def setup_guild_message(self, loop: asyncio.AbstractEventLoop,
                            message: Message, is_public: bool = False):
        self.loop = loop
        self.message_type = MessageType.GUILD
        self.message = message
        self._guild_public = is_public
        self._initial_setup(message, 'id')
        self.uuid = f"guild_{self.message.guild_id}"

    def setup_direct_message(self, loop: asyncio.AbstractEventLoop, message: DirectMessage):
        self.loop = loop
        self.message_type = MessageType.DIRECT
        self.message = message
        self._initial_setup(message, 'id')
        self.uuid = f"direct_{self.author_id}"

    def setup_group_message(self, loop: asyncio.AbstractEventLoop, message: GroupMessage,
                            is_public: bool = False):
        self.loop = loop
        self.message_type = MessageType.GROUP
        self.message = message
        self._group_public = is_public
        self._initial_setup(message, 'member_openid')
        self.uuid = f"group_{self.message.group_openid}"

    def setup_c2c_message(self, loop: asyncio.AbstractEventLoop, message: C2CMessage):
        self.loop = loop
        self.message_type = MessageType.C2C
        self.message = message
        self._initial_setup(message, 'user_openid')
        self.uuid = f"c2c_{self.author_id}"

    def setup_active_guild_message(self, loop: asyncio.AbstractEventLoop,
                                    channel_id: str):
        """设置主动频道消息（无需 incoming message）"""
        self.loop = loop
        self.message_type = MessageType.GUILD
        self.message = None
        self._active = True
        self._channel_id = channel_id
        self.uuid = f"guild_{channel_id}"

    def setup_active_direct_message(self, loop: asyncio.AbstractEventLoop,
                                     guild_id: str):
        """设置主动私信消息（无需 incoming message）"""
        self.loop = loop
        self.message_type = MessageType.DIRECT
        self.message = None
        self._active = True
        self._guild_id = guild_id
        self.uuid = f"direct_{guild_id}"

    def setup_active_group_message(self, loop: asyncio.AbstractEventLoop,
                                    group_openid: str):
        """设置主动群聊消息（无需 incoming message）"""
        self.loop = loop
        self.message_type = MessageType.GROUP
        self.message = None
        self._active = True
        self._group_openid = group_openid
        self.uuid = f"group_{group_openid}"

    def setup_active_c2c_message(self, loop: asyncio.AbstractEventLoop,
                                  openid: str):
        """设置主动私聊消息（无需 incoming message）"""
        self.loop = loop
        self.message_type = MessageType.C2C
        self.message = None
        self._active = True
        self.author_id = openid  # C2C 使用 author_id 存储 openid
        self.uuid = f"c2c_{openid}"

    def reply(self, content: str, img_path: str = None, img_url: str = None, modal_words: bool = True):
        """异步发送回复的入口方法"""
        if not self.loop:
            raise RuntimeError("Event loop not initialized")

        friendly_content = content + random.choice(Constants.modal_words) if modal_words else content
        friendly_content = reverse_text_on_41(friendly_content)

        with self.seq_lock:
            self.msg_seq += 1
            asyncio.run_coroutine_threadsafe(  # 不能使用 loop.create_task，会造成资源竞争
                self._send_message(friendly_content, self.msg_seq, img_path, img_url),
                self.loop
            )

    def reply_audio(self, audio_path: str = None, audio_url: str = None):
        """异步发送语音的入口方法"""
        if not self.loop:
            raise RuntimeError("Event loop not initialized")

        with self.seq_lock:
            self.msg_seq += 1
            asyncio.run_coroutine_threadsafe(  # 不能使用 loop.create_task，会造成资源竞争
                self._send_audio(self.msg_seq, audio_path, audio_url),
                self.loop
            )

    async def _send_message(self, content: str, msg_seq: int,
                            img_path: str = None, img_url: str = None):
        """统一消息发送入口"""
        if self._active:
            Constants.log.info(f"[obot-act] 向 {self.uuid} 发起主动回复: {content}")
        else:
            Constants.log.info(f"[obot-act] 发起回复: {content}")

        try:
            if img_path:
                img_path = patch_img_transform(self.author_id, img_path)

            # 处理媒体文件上传
            media = (await self._upload_media(img_path, img_url, media_type="Image")
                     if (img_path or img_url) and
                        self.message_type not in [MessageType.GUILD, MessageType.DIRECT] else None)

            base_params = await self._pack_message_params(content, msg_seq, media)
            if not base_params:
                return
            params = base_params

            # 频道api只需传递参数
            if self.message_type in [MessageType.GUILD, MessageType.DIRECT]:
                params = {**base_params, 'file_image': img_path, 'image': img_url}

            await self._handle_send_request(params)

        except Exception as e:
            Constants.log.warning("[obot-act] 发起回复失败.")
            Constants.log.exception(f"[obot-act] {e}")

    async def _send_audio(self, msg_seq: int, audio_path: str = None, audio_url: str = None):
        """语音发送入口"""
        if self.message_type in [MessageType.GUILD, MessageType.DIRECT]:
            await self._send_message("频道不支持发送语音消息", msg_seq)
            return

        Constants.log.info("[obot-act] 发起语音回复")

        try:
            if not audio_path and not audio_url:
                raise ValueError("Missing audio path or url")

            # 处理媒体文件上传
            media = await self._upload_media(audio_path, audio_url, media_type="Audio")

            params = await self._pack_message_params("", msg_seq, media)
            if not params:
                return

            await self._handle_send_request(params)

        except Exception as e:
            Constants.log.warning("[obot-act] 发起语音回复失败.")
            Constants.log.exception(f"[obot-act] {e}")

    async def _upload_media(self, path: str, url: str,
                            media_type: Literal["Image", "Audio"]) -> dict:
        """带重试机制的媒体上传"""
        type_id = {
            "Image": 1,
            "Audio": 3
        }
        for _ in range(3):  # 最多重试3次
            try:
                if path:
                    with open(path, "rb") as f:
                        file_data = base64.b64encode(f.read()).decode()
                    received_media = await self._call_upload_api(file_type=type_id[media_type],
                                                                 file_data=file_data)
                else:
                    received_media = await self._call_upload_api(file_type=type_id[media_type],
                                                                 url=url)
                if received_media['status'] == 'ok':
                    return received_media
            except Exception as e:
                Constants.log.warning("[obot-act] 上传媒体文件失败.")
                Constants.log.exception(f"[obot-act] {e}")
        return {'status': 'error', 'data': None}

    async def _call_upload_api(self, **kwargs) -> dict:
        """调用对应的文件上传API"""
        if self.message_type in [MessageType.GUILD, MessageType.DIRECT]:
            raise PermissionError("Not allowed to upload files for guild and direct messages.")

        method_map: dict = {
            MessageType.GROUP: self.api.post_group_file,
            MessageType.C2C: self.api.post_c2c_file
        }
        common_args: dict = {
            **kwargs
        }

        if self.message_type == MessageType.GROUP:
            common_args["group_openid"] = (self._group_openid if self._active
                                           else self.message.group_openid)
        elif self.message_type == MessageType.C2C:
            common_args["openid"] = self.author_id

        received_media = await method_map[self.message_type](**common_args)
        if received_media:
            return {'status': 'ok', 'data': received_media}
        else:
            return {'status': 'error', 'data': None}

    async def _pack_message_params(self, content: str, msg_seq: int,
                                   media: Optional[dict]) -> Optional[dict]:
        """构造消息发送参数"""
        base_params = {
            "content": content,
            "msg_id": None if self._active else self.message.id,
            "msg_seq": msg_seq
        }

        # 媒体消息
        if media:
            if media['status'] != 'ok':
                await self._send_fallback_message("发送媒体文件失败，请稍后重试", msg_seq)
                return None
            return {**base_params, "msg_type": 7, "media": media['data']}

        # 文本消息
        return {**base_params, "msg_type": 0}

    async def _handle_send_request(self, params: dict):
        """分发到具体的发送方法"""
        intended_params_name = ['content', 'embed', 'ark', 'message_reference',
                                'msg_id', 'event_id', 'markdown', 'keyboard']
        if self.message_type == MessageType.GUILD:
            if not self._active:
                params['content'] = f"<@{self.message.author.id}>{params['content']}"
            params['channel_id'] = (self._channel_id if self._active
                                    else self.message.channel_id)
            intended_params_name.extend(['channel_id', 'image', 'file_image'])
            api_method = self.api.post_message
        elif self.message_type == MessageType.DIRECT:
            if not self._active:
                params['content'] = f"<@{self.message.author.id}>{params['content']}"
            params['guild_id'] = (self._guild_id if self._active
                                  else self.message.guild_id)
            intended_params_name.extend(['guild_id', 'image', 'file_image'])
            api_method = self.api.post_dms
        elif self.message_type == MessageType.GROUP:
            params['group_openid'] = (self._group_openid if self._active
                                      else self.message.group_openid)
            intended_params_name.extend(['group_openid', 'msg_type', 'media', 'msg_seq'])
            api_method = self.api.post_group_message
        else:
            params['openid'] = self.author_id
            intended_params_name.extend(['openid', 'msg_type', 'media', 'msg_seq'])
            api_method = self.api.post_c2c_message

        intended_params = {name: params[name] for name in intended_params_name if name in params}
        await api_method(**intended_params)

    async def _send_fallback_message(self, text: str, msg_seq: int):
        """发送失败回退消息"""
        fallback_params = {
            "msg_type": 0,
            "content": text,
            "msg_id": None if self._active else self.message.id,
            "msg_seq": msg_seq
        }
        await self._handle_send_request(fallback_params)

    def report_exception(self, module_name: str, e: Exception):
        Constants.log.warning(f"[obot-module] 操作失败，模块 {module_name} 出现异常")
        Constants.log.exception(f"[obot-module] {e}")
        self.reply(handle_exception(e), modal_words=False)
