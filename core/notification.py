"""
通知系统 - 基于MoviePilot参考实现
支持Telegram、Server酱等多种通知渠道
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

import aiohttp
from pydantic import BaseModel


class NotificationType:
    """通知类型枚举"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationMessage(BaseModel):
    """通知消息模型"""

    title: str
    message: str
    type: str = NotificationType.INFO
    timestamp: datetime = None
    metadata: Dict[str, Any] = {}

    def __init__(self, **data):
        if "timestamp" not in data or data["timestamp"] is None:
            data["timestamp"] = datetime.now()
        super().__init__(**data)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class NotificationChannel(ABC):
    """通知渠道抽象类"""

    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """发送通知"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """获取渠道名称"""
        pass


class TelegramChannel(NotificationChannel):
    """Telegram通知渠道"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None

    def get_name(self) -> str:
        return "telegram"

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def send(self, message: NotificationMessage) -> bool:
        """发送Telegram通知"""
        try:
            # 格式化消息内容
            text = self._format_message(message)

            # 发送消息
            session = await self._get_session()
            url = f"{self.base_url}/sendMessage"

            params = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }

            async with session.post(url, data=params) as response:
                if response.status == 200:
                    logging.info(f"Telegram notification sent: {message.title}")
                    return True
                else:
                    error_text = await response.text()
                    logging.error(
                        f"Telegram API error: {response.status} - {error_text}"
                    )
                    return False

        except Exception as e:
            logging.error(f"Failed to send Telegram notification: {e}")
            return False

    def _format_message(self, message: NotificationMessage) -> str:
        """格式化消息内容"""
        # 根据消息类型设置表情符号
        emoji_map = {
            NotificationType.INFO: "ℹ️",
            NotificationType.SUCCESS: "✅",
            NotificationType.WARNING: "⚠️",
            NotificationType.ERROR: "❌",
        }

        emoji = emoji_map.get(message.type, "ℹ️")

        # 构建HTML格式的消息
        lines = [f"<b>{emoji} {message.title}</b>", "", message.message]

        # 添加元数据
        if message.metadata:
            lines.append("")
            lines.append("<i>详细信息:</i>")
            for key, value in message.metadata.items():
                lines.append(f"• {key}: {value}")

        # 添加时间戳
        lines.append("")
        lines.append(f"<i>时间: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</i>")

        return "\n".join(lines)

    async def close(self):
        """关闭资源"""
        if self.session:
            await self.session.close()


class ServerChanChannel(NotificationChannel):
    """Server酱通知渠道"""

    def __init__(self, send_key: str):
        self.send_key = send_key
        self.base_url = "https://sctapi.ftqq.com"
        self.session: Optional[aiohttp.ClientSession] = None

    def get_name(self) -> str:
        return "serverchan"

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def send(self, message: NotificationMessage) -> bool:
        """发送Server酱通知"""
        try:
            # 格式化消息内容
            title, content = self._format_message(message)

            # 发送消息
            session = await self._get_session()
            url = f"{self.base_url}/{self.send_key}.send"

            data = {"title": title, "desp": content}

            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("code") == 0:
                        logging.info(f"ServerChan notification sent: {message.title}")
                        return True
                    else:
                        logging.error(f"ServerChan API error: {result}")
                        return False
                else:
                    error_text = await response.text()
                    logging.error(
                        f"ServerChan HTTP error: {response.status} - {error_text}"
                    )
                    return False

        except Exception as e:
            logging.error(f"Failed to send ServerChan notification: {e}")
            return False

    def _format_message(self, message: NotificationMessage) -> Tuple[str, str]:
        """格式化消息内容"""
        # 根据消息类型设置标题前缀
        prefix_map = {
            NotificationType.INFO: "[信息]",
            NotificationType.SUCCESS: "[成功]",
            NotificationType.WARNING: "[警告]",
            NotificationType.ERROR: "[错误]",
        }

        prefix = prefix_map.get(message.type, "[信息]")
        title = f"{prefix} {message.title}"

        # 构建Markdown格式的内容
        lines = [message.message]

        # 添加元数据
        if message.metadata:
            lines.append("")
            lines.append("**详细信息:**")
            for key, value in message.metadata.items():
                lines.append(f"- {key}: {value}")

        # 添加时间戳
        lines.append("")
        lines.append(f"*时间: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*")

        content = "\n".join(lines)

        return title, content

    async def close(self):
        """关闭资源"""
        if self.session:
            await self.session.close()


class ConsoleChannel(NotificationChannel):
    """控制台通知渠道（用于调试）"""

    def get_name(self) -> str:
        return "console"

    async def send(self, message: NotificationMessage) -> bool:
        """发送控制台通知"""
        try:
            # 格式化消息
            formatted = self._format_message(message)

            # 输出到控制台
            print(formatted)
            logging.info(f"Console notification: {message.title}")

            return True

        except Exception as e:
            logging.error(f"Failed to send console notification: {e}")
            return False

    def _format_message(self, message: NotificationMessage) -> str:
        """格式化消息内容"""
        # 根据消息类型设置颜色前缀
        color_map = {
            NotificationType.INFO: "[INFO]",
            NotificationType.SUCCESS: "[SUCCESS]",
            NotificationType.WARNING: "[WARNING]",
            NotificationType.ERROR: "[ERROR]",
        }

        prefix = color_map.get(message.type, "[INFO]")

        lines = [
            f"{prefix} {message.title}",
            f"Message: {message.message}",
            f"Time: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        # 添加元数据
        if message.metadata:
            lines.append("Metadata:")
            for key, value in message.metadata.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)


class NotificationManager:
    """通知管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.channels: Dict[str, NotificationChannel] = {}
        self.enabled_channels: List[str] = []
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False

        # 初始化渠道
        self._init_channels(config)

    def _init_channels(self, config: Dict[str, Any]):
        """初始化通知渠道"""
        # Telegram渠道
        if config.get("telegram_bot_token") and config.get("telegram_chat_id"):
            telegram_channel = TelegramChannel(
                config["telegram_bot_token"], config["telegram_chat_id"]
            )
            self.channels["telegram"] = telegram_channel
            self.enabled_channels.append("telegram")

        # Server酱渠道
        if config.get("serverchan_send_key"):
            serverchan_channel = ServerChanChannel(config["serverchan_send_key"])
            self.channels["serverchan"] = serverchan_channel
            self.enabled_channels.append("serverchan")

        # 控制台渠道（始终启用）
        console_channel = ConsoleChannel()
        self.channels["console"] = console_channel
        self.enabled_channels.append("console")

    async def start(self):
        """启动通知管理器"""
        if self.is_running:
            return

        self.is_running = True

        # 启动消息处理循环
        asyncio.create_task(self._message_loop())

        logging.info("Notification manager started")

    async def stop(self):
        """停止通知管理器"""
        self.is_running = False

        # 关闭所有渠道
        for channel in self.channels.values():
            if hasattr(channel, "close"):
                await channel.close()

        logging.info("Notification manager stopped")

    async def send_notification(self, message: NotificationMessage) -> bool:
        """发送通知"""
        try:
            # 将消息加入队列
            await self.message_queue.put(message)
            return True

        except Exception as e:
            logging.error(f"Failed to queue notification: {e}")
            return False

    async def send_immediate(self, message: NotificationMessage) -> bool:
        """立即发送通知（绕过队列）"""
        return await self._send_to_channels(message)

    async def _message_loop(self):
        """消息处理循环"""
        while self.is_running:
            try:
                # 从队列获取消息
                message = await self.message_queue.get()

                # 发送到所有渠道
                await self._send_to_channels(message)

                # 标记任务完成
                self.message_queue.task_done()

            except Exception as e:
                logging.error(f"Error in notification message loop: {e}")

    async def _send_to_channels(self, message: NotificationMessage) -> bool:
        """发送消息到所有渠道"""
        results = []

        for channel_name in self.enabled_channels:
            if channel_name in self.channels:
                try:
                    channel = self.channels[channel_name]
                    success = await channel.send(message)
                    results.append((channel_name, success))
                except Exception as e:
                    logging.error(f"Error sending to {channel_name}: {e}")
                    results.append((channel_name, False))

        # 检查是否至少有一个渠道发送成功
        successful_sends = [result for _, result in results if result]
        return len(successful_sends) > 0

    def get_status(self) -> Dict[str, Any]:
        """获取通知管理器状态"""
        return {
            "enabled": self.is_running,
            "channels": {
                name: {"enabled": name in self.enabled_channels}
                for name in self.channels.keys()
            },
            "queue_size": self.message_queue.qsize(),
        }


# 便捷函数
async def send_success_notification(
    manager: NotificationManager,
    title: str,
    message: str,
    metadata: Dict[str, Any] = None,
):
    """发送成功通知"""
    msg = NotificationMessage(
        title=title,
        message=message,
        type=NotificationType.SUCCESS,
        metadata=metadata or {},
    )
    return await manager.send_notification(msg)


async def send_error_notification(
    manager: NotificationManager,
    title: str,
    message: str,
    metadata: Dict[str, Any] = None,
):
    """发送错误通知"""
    msg = NotificationMessage(
        title=title,
        message=message,
        type=NotificationType.ERROR,
        metadata=metadata or {},
    )
    return await manager.send_notification(msg)


async def send_warning_notification(
    manager: NotificationManager,
    title: str,
    message: str,
    metadata: Dict[str, Any] = None,
):
    """发送警告通知"""
    msg = NotificationMessage(
        title=title,
        message=message,
        type=NotificationType.WARNING,
        metadata=metadata or {},
    )
    return await manager.send_notification(msg)


async def send_info_notification(
    manager: NotificationManager,
    title: str,
    message: str,
    metadata: Dict[str, Any] = None,
):
    """发送信息通知"""
    msg = NotificationMessage(
        title=title,
        message=message,
        type=NotificationType.INFO,
        metadata=metadata or {},
    )
    return await manager.send_notification(msg)
