"""
增强的通知管理器模块
支持多通道通知、优先级管理、通知模板和批量发送
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
import json


class NotificationPriority(Enum):
    """通知优先级"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(Enum):
    """通知渠道"""

    TELEGRAM = "telegram"
    SERVERCHAN = "serverchan"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CONSOLE = "console"
    DISCORD = "discord"
    SLACK = "slack"


@dataclass
class NotificationMessage:
    """通知消息"""

    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: List[NotificationChannel] = None
    metadata: Dict[str, Any] = None
    template: str = None
    created_at: datetime = None

    def __post_init__(self):
        if self.channels is None:
            self.channels = [NotificationChannel.CONSOLE]
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "channels": [channel.value for channel in self.channels],
            "metadata": self.metadata,
            "template": self.template,
            "created_at": self.created_at.isoformat(),
        }


class NotificationTemplate:
    """通知模板"""

    def __init__(self, name: str, template: str, variables: List[str] = None):
        self.name = name
        self.template = template
        self.variables = variables or []

    def render(self, **kwargs) -> str:
        """渲染模板"""
        rendered = self.template
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            rendered = rendered.replace(placeholder, str(value))
        return rendered


class BaseNotificationChannel:
    """通知渠道基类"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = True
        self.logger = logging.getLogger(f"notification.{name}")

    async def send(self, message: NotificationMessage) -> bool:
        """发送通知"""
        raise NotImplementedError("Subclasses must implement send method")

    def get_status(self) -> Dict[str, Any]:
        """获取渠道状态"""
        return {"name": self.name, "enabled": self.enabled, "config": self.config}


class ConsoleChannel(BaseNotificationChannel):
    """控制台渠道"""

    async def send(self, message: NotificationMessage) -> bool:
        try:
            print(
                f"[{message.priority.value.upper()}] {message.title}: {message.message}"
            )
            if message.metadata:
                print(f"Metadata: {json.dumps(message.metadata, indent=2)}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send console notification: {e}")
            return False


class TelegramChannel(BaseNotificationChannel):
    """Telegram渠道"""

    async def send(self, message: NotificationMessage) -> bool:
        try:
            # 这里实现Telegram发送逻辑
            # 实际实现需要集成Telegram Bot API
            self.logger.info(f"Telegram notification sent: {message.title}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send Telegram notification: {e}")
            return False


class ServerChanChannel(BaseNotificationChannel):
    """Server酱渠道"""

    async def send(self, message: NotificationMessage) -> bool:
        try:
            # 这里实现Server酱发送逻辑
            self.logger.info(f"ServerChan notification sent: {message.title}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send ServerChan notification: {e}")
            return False


class EmailChannel(BaseNotificationChannel):
    """邮件渠道"""

    async def send(self, message: NotificationMessage) -> bool:
        try:
            # 这里实现邮件发送逻辑
            self.logger.info(f"Email notification sent: {message.title}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False


class NotificationManager:
    """增强的通知管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.channels: Dict[str, BaseNotificationChannel] = {}
        self.templates: Dict[str, NotificationTemplate] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger("notification.manager")

        # 初始化渠道
        self._init_channels()
        # 初始化模板
        self._init_templates()

    def _init_channels(self):
        """初始化通知渠道"""
        # 控制台渠道（始终启用）
        self.channels["console"] = ConsoleChannel("console", {})

        # 根据配置启用其他渠道
        if self.config.get("telegram", {}).get("enabled", False):
            self.channels["telegram"] = TelegramChannel(
                "telegram", self.config.get("telegram", {})
            )

        if self.config.get("serverchan", {}).get("enabled", False):
            self.channels["serverchan"] = ServerChanChannel(
                "serverchan", self.config.get("serverchan", {})
            )

        if self.config.get("email", {}).get("enabled", False):
            self.channels["email"] = EmailChannel("email", self.config.get("email", {}))

    def _init_templates(self):
        """初始化通知模板"""
        # 下载完成模板
        self.templates["download_complete"] = NotificationTemplate(
            name="download_complete",
            template="🎉 下载完成！\n📺 标题：{title}\n📁 文件：{filename}\n💾 大小：{size}\n⏰ 耗时：{duration}",
            variables=["title", "filename", "size", "duration"],
        )

        # 订阅更新模板
        self.templates["subscription_update"] = NotificationTemplate(
            name="subscription_update",
            template="📢 订阅更新\n🎬 剧集：{title}\n📅 季数：{season}\n🎯 集数：{episode}\n🔗 链接：{link}",
            variables=["title", "season", "episode", "link"],
        )

        # 系统错误模板
        self.templates["system_error"] = NotificationTemplate(
            name="system_error",
            template="❌ 系统错误\n💥 模块：{module}\n📝 错误：{error}\n⏰ 时间：{time}",
            variables=["module", "error", "time"],
        )

    async def start(self):
        """启动通知管理器"""
        self.logger.info("Starting notification manager")
        self.worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        """停止通知管理器"""
        self.logger.info("Stopping notification manager")
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

    async def _worker(self):
        """工作线程，处理通知队列"""
        while True:
            try:
                message = await self.queue.get()
                await self._process_message(message)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing notification: {e}")

    async def _process_message(self, message: NotificationMessage):
        """处理单个通知消息"""
        try:
            # 根据优先级决定是否延迟发送
            if message.priority == NotificationPriority.LOW:
                await asyncio.sleep(5)  # 低优先级延迟5秒
            elif message.priority == NotificationPriority.URGENT:
                # 紧急通知立即发送
                pass

            # 发送到指定渠道
            success_count = 0
            for channel_name in message.channels:
                channel = self.channels.get(channel_name.value)
                if channel and channel.enabled:
                    success = await channel.send(message)
                    if success:
                        success_count += 1

            self.logger.info(
                f"Notification sent to {success_count}/{len(message.channels)} channels"
            )

        except Exception as e:
            self.logger.error(f"Failed to process notification: {e}")

    async def send_notification(self, message: NotificationMessage) -> bool:
        """发送通知"""
        try:
            await self.queue.put(message)
            return True
        except Exception as e:
            self.logger.error(f"Failed to queue notification: {e}")
            return False

    async def send_template_notification(self, template_name: str, **kwargs) -> bool:
        """发送模板通知"""
        template = self.templates.get(template_name)
        if not template:
            self.logger.error(f"Template not found: {template_name}")
            return False

        try:
            message_content = template.render(**kwargs)
            message = NotificationMessage(
                title=kwargs.get("title", "系统通知"),
                message=message_content,
                priority=NotificationPriority(kwargs.get("priority", "normal")),
                channels=[
                    NotificationChannel(c) for c in kwargs.get("channels", ["console"])
                ],
                metadata=kwargs.get("metadata", {}),
            )

            return await self.send_notification(message)
        except Exception as e:
            self.logger.error(f"Failed to send template notification: {e}")
            return False

    async def send_batch_notifications(
        self, messages: List[NotificationMessage]
    ) -> List[bool]:
        """批量发送通知"""
        results = []
        for message in messages:
            result = await self.send_notification(message)
            results.append(result)
        return results

    def get_status(self) -> Dict[str, Any]:
        """获取通知系统状态"""
        channels_status = {}
        for name, channel in self.channels.items():
            channels_status[name] = channel.get_status()

        return {
            "enabled": True,
            "queue_size": self.queue.qsize(),
            "channels": channels_status,
            "templates": list(self.templates.keys()),
            "worker_running": self.worker_task is not None
            and not self.worker_task.done(),
        }

    def add_channel(self, name: str, channel: BaseNotificationChannel):
        """添加自定义渠道"""
        self.channels[name] = channel

    def remove_channel(self, name: str):
        """移除渠道"""
        if name in self.channels:
            del self.channels[name]

    def add_template(self, template: NotificationTemplate):
        """添加模板"""
        self.templates[template.name] = template


# 便捷函数
async def send_success_notification(
    manager: NotificationManager,
    title: str,
    message: str,
    metadata: Dict[str, Any] = None,
) -> bool:
    """发送成功通知"""
    msg = NotificationMessage(
        title=title,
        message=message,
        priority=NotificationPriority.NORMAL,
        metadata=metadata or {},
    )
    return await manager.send_notification(msg)


async def send_error_notification(
    manager: NotificationManager,
    title: str,
    message: str,
    metadata: Dict[str, Any] = None,
) -> bool:
    """发送错误通知"""
    msg = NotificationMessage(
        title=title,
        message=message,
        priority=NotificationPriority.HIGH,
        metadata=metadata or {},
    )
    return await manager.send_notification(msg)


async def send_warning_notification(
    manager: NotificationManager,
    title: str,
    message: str,
    metadata: Dict[str, Any] = None,
) -> bool:
    """发送警告通知"""
    msg = NotificationMessage(
        title=title,
        message=message,
        priority=NotificationPriority.NORMAL,
        metadata=metadata or {},
    )
    return await manager.send_notification(msg)


async def send_info_notification(
    manager: NotificationManager,
    title: str,
    message: str,
    metadata: Dict[str, Any] = None,
) -> bool:
    """发送信息通知"""
    msg = NotificationMessage(
        title=title,
        message=message,
        priority=NotificationPriority.LOW,
        metadata=metadata or {},
    )
    return await manager.send_notification(msg)
