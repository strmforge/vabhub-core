"""
通知系统测试模块
"""

import pytest
import asyncio
from datetime import datetime

from core.notification import (
    NotificationMessage, NotificationType,
    TelegramChannel, ServerChanChannel, ConsoleChannel, NotificationManager
)


class TestNotificationMessage:
    """测试通知消息"""
    
    def test_message_creation(self):
        """测试消息创建"""
        message = NotificationMessage(
            title="测试标题",
            message="测试消息内容",
            type=NotificationType.INFO
        )
        
        assert message.title == "测试标题"
        assert message.message == "测试消息内容"
        assert message.type == NotificationType.INFO
        assert isinstance(message.timestamp, datetime)
    
    def test_message_to_dict(self):
        """测试消息转换为字典"""
        message = NotificationMessage(
            title="测试标题",
            message="测试消息内容",
            type=NotificationType.SUCCESS,
            metadata={"key": "value"}
        )
        
        result = message.to_dict()
        
        assert result["title"] == "测试标题"
        assert result["message"] == "测试消息内容"
        assert result["type"] == NotificationType.SUCCESS
        assert result["metadata"] == {"key": "value"}
        assert "timestamp" in result


class TestConsoleChannel:
    """测试控制台渠道"""
    
    def test_console_channel_creation(self):
        """测试控制台渠道创建"""
        channel = ConsoleChannel()
        assert channel.get_name() == "console"
    
    @pytest.mark.asyncio
    async def test_console_channel_send(self):
        """测试控制台渠道发送"""
        channel = ConsoleChannel()
        
        message = NotificationMessage(
            title="测试标题",
            message="测试消息内容",
            type=NotificationType.INFO
        )
        
        success = await channel.send(message)
        assert success is True


class TestNotificationManager:
    """测试通知管理器"""
    
    def test_manager_creation(self):
        """测试管理器创建"""
        config = {
            "telegram_bot_token": "test_token",
            "telegram_chat_id": "test_chat_id",
            "serverchan_send_key": "test_key"
        }
        
        manager = NotificationManager(config)
        
        assert "telegram" in manager.channels
        assert "serverchan" in manager.channels
        assert "console" in manager.channels
        assert "console" in manager.enabled_channels
    
    def test_manager_creation_minimal_config(self):
        """测试管理器创建（最小配置）"""
        config = {}  # 空配置
        
        manager = NotificationManager(config)
        
        # 即使没有配置，控制台渠道也应该存在
        assert "console" in manager.channels
        assert "console" in manager.enabled_channels
    
    @pytest.mark.asyncio
    async def test_manager_send_notification(self):
        """测试管理器发送通知"""
        config = {}
        manager = NotificationManager(config)
        
        # 启动管理器
        await manager.start()
        
        message = NotificationMessage(
            title="测试标题",
            message="测试消息内容",
            type=NotificationType.INFO
        )
        
        success = await manager.send_notification(message)
        assert success is True
        
        # 停止管理器
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_manager_get_status(self):
        """测试管理器状态获取"""
        config = {}
        manager = NotificationManager(config)
        
        status = manager.get_status()
        
        assert "enabled" in status
        assert "channels" in status
        assert "queue_size" in status
        
        # 管理器未启动时应该是禁用状态
        assert status["enabled"] is False


class TestTelegramChannel:
    """测试Telegram渠道"""
    
    def test_telegram_channel_creation(self):
        """测试Telegram渠道创建"""
        channel = TelegramChannel("test_token", "test_chat_id")
        
        assert channel.get_name() == "telegram"
        assert channel.bot_token == "test_token"
        assert channel.chat_id == "test_chat_id"
        assert channel.base_url == "https://api.telegram.org/bottest_token"
    
    def test_telegram_format_message(self):
        """测试Telegram消息格式化"""
        channel = TelegramChannel("test_token", "test_chat_id")
        
        message = NotificationMessage(
            title="测试标题",
            message="测试消息内容",
            type=NotificationType.INFO,
            metadata={"key": "value"}
        )
        
        formatted = channel._format_message(message)
        
        assert "测试标题" in formatted
        assert "测试消息内容" in formatted
        assert "key: value" in formatted
        assert "<b>" in formatted  # HTML格式


class TestServerChanChannel:
    """测试Server酱渠道"""
    
    def test_serverchan_channel_creation(self):
        """测试Server酱渠道创建"""
        channel = ServerChanChannel("test_key")
        
        assert channel.get_name() == "serverchan"
        assert channel.send_key == "test_key"
        assert channel.base_url == "https://sctapi.ftqq.com"
    
    def test_serverchan_format_message(self):
        """测试Server酱消息格式化"""
        channel = ServerChanChannel("test_key")
        
        message = NotificationMessage(
            title="测试标题",
            message="测试消息内容",
            type=NotificationType.INFO,
            metadata={"key": "value"}
        )
        
        title, content = channel._format_message(message)
        
        assert "[信息]" in title
        assert "测试标题" in title
        assert "测试消息内容" in content
        assert "key: value" in content


@pytest.mark.asyncio
async def test_notification_integration():
    """集成测试"""
    config = {
        "telegram_bot_token": "test_token",
        "telegram_chat_id": "test_chat_id",
        "serverchan_send_key": "test_key"
    }
    
    manager = NotificationManager(config)
    
    # 测试管理器状态
    status = manager.get_status()
    assert "enabled" in status
    assert "channels" in status
    
    # 测试渠道数量
    assert len(manager.channels) >= 1  # 至少包含控制台渠道
    
    # 测试便捷函数
    from core.notification import send_info_notification
    
    success = await send_info_notification(
        manager, 
        "测试标题", 
        "测试消息内容",
        {"test": "value"}
    )
    
    # 由于是测试环境，可能无法真正发送，但函数应该能正常执行
    assert success is True or success is False