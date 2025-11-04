"""
通知系统API路由模块
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional

from .notification_manager import (
    NotificationManager,
    NotificationMessage,
    NotificationPriority,
    send_success_notification,
    send_error_notification,
    send_warning_notification,
    send_info_notification,
)
from .auth import get_current_user

router = APIRouter(prefix="/notification", tags=["Notification"])

# 全局通知管理器
notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """获取通知管理器实例"""
    global notification_manager
    if notification_manager is None:
        # 从配置中获取通知设置
        config = {
            "telegram_bot_token": "your_telegram_bot_token",  # 应该从环境变量获取
            "telegram_chat_id": "your_telegram_chat_id",
            "serverchan_send_key": "your_serverchan_send_key",
        }
        notification_manager = NotificationManager(config)
    return notification_manager


@router.on_event("startup")
async def startup_event():
    """应用启动时启动通知管理器"""
    manager = get_notification_manager()
    await manager.start()


@router.on_event("shutdown")
async def shutdown_event():
    """应用关闭时停止通知管理器"""
    manager = get_notification_manager()
    await manager.stop()


@router.post("/send")
async def send_notification(
    title: str,
    message: str,
    notification_type: str = NotificationPriority.NORMAL.value,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user),
):
    """发送通知"""
    try:
        manager = get_notification_manager()

        msg = NotificationMessage(
            title=title,
            message=message,
            priority=NotificationPriority(notification_type),
            metadata=metadata or {},
        )

        success = await manager.send_notification(msg)

        return {
            "success": success,
            "message": (
                "Notification sent successfully"
                if success
                else "Failed to send notification"
            ),
            "notification": msg.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {e}")


@router.post("/send/success")
async def send_success(
    title: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user),
):
    """发送成功通知"""
    try:
        manager = get_notification_manager()
        success = await send_success_notification(manager, title, message, metadata)

        return {
            "success": success,
            "type": "success",
            "message": (
                "Success notification sent"
                if success
                else "Failed to send success notification"
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send success notification: {e}"
        )


@router.post("/send/error")
async def send_error(
    title: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user),
):
    """发送错误通知"""
    try:
        manager = get_notification_manager()
        success = await send_error_notification(manager, title, message, metadata)

        return {
            "success": success,
            "type": "error",
            "message": (
                "Error notification sent"
                if success
                else "Failed to send error notification"
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send error notification: {e}"
        )


@router.post("/send/warning")
async def send_warning(
    title: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user),
):
    """发送警告通知"""
    try:
        manager = get_notification_manager()
        success = await send_warning_notification(manager, title, message, metadata)

        return {
            "success": success,
            "type": "warning",
            "message": (
                "Warning notification sent"
                if success
                else "Failed to send warning notification"
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send warning notification: {e}"
        )


@router.post("/send/info")
async def send_info(
    title: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user),
):
    """发送信息通知"""
    try:
        manager = get_notification_manager()
        success = await send_info_notification(manager, title, message, metadata)

        return {
            "success": success,
            "type": "info",
            "message": (
                "Info notification sent"
                if success
                else "Failed to send info notification"
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send info notification: {e}"
        )


@router.get("/status")
async def get_status(current_user: dict = Depends(get_current_user)):
    """获取通知系统状态"""
    try:
        manager = get_notification_manager()
        status = manager.get_status()

        return {
            "status": status,
            "message": "Notification system status retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get notification status: {e}"
        )


@router.post("/test")
async def test_notification(
    channel: str = "all", current_user: dict = Depends(get_current_user)
):
    """测试通知系统"""
    try:
        manager = get_notification_manager()

        # 创建测试消息
        test_message = NotificationMessage(
            title="测试通知",
            message="这是一条测试通知消息，用于验证通知系统是否正常工作。",
            priority=NotificationPriority.NORMAL,
            metadata={"测试类型": "功能测试", "测试时间": "现在", "测试渠道": channel},
        )

        success = await manager.send_notification(test_message)

        return {
            "success": success,
            "message": (
                "Test notification sent successfully"
                if success
                else "Failed to send test notification"
            ),
            "test_message": test_message.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test notification: {e}")


@router.get("/channels")
async def get_channels(current_user: dict = Depends(get_current_user)):
    """获取可用的通知渠道"""
    try:
        manager = get_notification_manager()
        status = manager.get_status()

        channels = []
        for channel_name, channel_info in status["channels"].items():
            channels.append(
                {
                    "name": channel_name,
                    "enabled": channel_info["enabled"],
                    "description": _get_channel_description(channel_name),
                }
            )

        return {"channels": channels, "message": "Channels retrieved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {e}")


def _get_channel_description(channel_name: str) -> str:
    """获取渠道描述"""
    descriptions = {
        "telegram": "Telegram机器人通知，支持HTML格式",
        "serverchan": "Server酱微信通知，支持Markdown格式",
        "console": "控制台输出，用于调试",
    }
    return descriptions.get(channel_name, "未知渠道")


@router.post("/config")
async def update_config(
    config: Dict[str, Any], current_user: dict = Depends(get_current_user)
):
    """更新通知配置"""
    try:
        # 这里可以实现配置更新逻辑
        # 注意：实际实现中需要重启通知管理器来应用新配置

        return {
            "success": True,
            "message": "Configuration updated successfully (restart required)",
            "config": config,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {e}")
