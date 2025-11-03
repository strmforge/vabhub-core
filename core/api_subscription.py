"""
订阅系统API路由模块
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime

from .subscription_manager import (
    SubscriptionManager,
    Subscription,
    SubscriptionRule,
    SubscriptionStatus,
    MediaType,
)
from .auth import get_current_user
from .config import Config
from .download_manager import DownloadManager

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

# 全局订阅管理器
subscription_manager = None


async def get_subscription_manager():
    """获取订阅管理器实例"""
    global subscription_manager
    if subscription_manager is None:
        config = Config()
        download_manager = DownloadManager(config)
        subscription_manager = SubscriptionManager(config, download_manager)
        await subscription_manager.start()
    return subscription_manager


@router.post("/", response_model=Dict[str, Any])
async def create_subscription(
    name: str,
    rules: List[Dict[str, Any]],
    check_interval: int = 3600,
    current_user: dict = Depends(get_current_user),
    manager: SubscriptionManager = Depends(get_subscription_manager),
):
    """创建新订阅"""
    try:
        # 转换规则数据
        subscription_rules = []
        for rule_data in rules:
            rule = SubscriptionRule(
                name=rule_data["name"],
                keywords=rule_data["keywords"],
                exclude_keywords=rule_data.get("exclude_keywords", []),
                quality=rule_data.get("quality", "1080p"),
                media_type=MediaType(rule_data.get("media_type", "movie")),
                enabled=rule_data.get("enabled", True),
                priority=rule_data.get("priority", 1),
            )
            subscription_rules.append(rule)

        subscription = await manager.create_subscription(
            name=name, rules=subscription_rules, check_interval=check_interval
        )

        return {
            "id": subscription.id,
            "name": subscription.name,
            "status": subscription.status.value,
            "rules_count": len(subscription.rules),
            "created_at": subscription.created_at.isoformat(),
            "message": "Subscription created successfully",
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[Dict[str, Any]])
async def list_subscriptions(
    current_user: dict = Depends(get_current_user),
    manager: SubscriptionManager = Depends(get_subscription_manager),
):
    """获取所有订阅"""
    try:
        subscriptions = await manager.list_subscriptions()

        result = []
        for subscription in subscriptions:
            result.append(
                {
                    "id": subscription.id,
                    "name": subscription.name,
                    "status": subscription.status.value,
                    "rules_count": len(subscription.rules),
                    "last_check": (
                        subscription.last_check.isoformat()
                        if subscription.last_check
                        else None
                    ),
                    "next_check": (
                        subscription.next_check.isoformat()
                        if subscription.next_check
                        else None
                    ),
                    "created_at": subscription.created_at.isoformat(),
                    "updated_at": subscription.updated_at.isoformat(),
                }
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{subscription_id}", response_model=Dict[str, Any])
async def get_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    manager: SubscriptionManager = Depends(get_subscription_manager),
):
    """获取订阅详情"""
    try:
        subscription = await manager.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # 转换规则数据
        rules_data = []
        for rule in subscription.rules:
            rules_data.append(
                {
                    "name": rule.name,
                    "keywords": rule.keywords,
                    "exclude_keywords": rule.exclude_keywords,
                    "quality": rule.quality,
                    "media_type": rule.media_type.value,
                    "enabled": rule.enabled,
                    "priority": rule.priority,
                }
            )

        return {
            "id": subscription.id,
            "name": subscription.name,
            "status": subscription.status.value,
            "rules": rules_data,
            "check_interval": subscription.check_interval,
            "last_check": (
                subscription.last_check.isoformat() if subscription.last_check else None
            ),
            "next_check": (
                subscription.next_check.isoformat() if subscription.next_check else None
            ),
            "created_at": subscription.created_at.isoformat(),
            "updated_at": subscription.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{subscription_id}", response_model=Dict[str, Any])
async def update_subscription(
    subscription_id: str,
    update_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    manager: SubscriptionManager = Depends(get_subscription_manager),
):
    """更新订阅"""
    try:
        # 检查订阅是否存在
        subscription = await manager.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # 更新订阅
        updated_subscription = await manager.update_subscription(
            subscription_id, **update_data
        )
        if not updated_subscription:
            raise HTTPException(status_code=500, detail="Failed to update subscription")

        return {
            "id": updated_subscription.id,
            "name": updated_subscription.name,
            "status": updated_subscription.status.value,
            "message": "Subscription updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{subscription_id}", response_model=Dict[str, Any])
async def delete_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    manager: SubscriptionManager = Depends(get_subscription_manager),
):
    """删除订阅"""
    try:
        success = await manager.delete_subscription(subscription_id)
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return {"message": "Subscription deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{subscription_id}/pause", response_model=Dict[str, Any])
async def pause_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    manager: SubscriptionManager = Depends(get_subscription_manager),
):
    """暂停订阅"""
    try:
        success = await manager.pause_subscription(subscription_id)
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return {"message": "Subscription paused successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{subscription_id}/resume", response_model=Dict[str, Any])
async def resume_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    manager: SubscriptionManager = Depends(get_subscription_manager),
):
    """恢复订阅"""
    try:
        success = await manager.resume_subscription(subscription_id)
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return {"message": "Subscription resumed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{subscription_id}/trigger", response_model=Dict[str, Any])
async def trigger_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    manager: SubscriptionManager = Depends(get_subscription_manager),
):
    """手动触发订阅检查"""
    try:
        subscription = await manager.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # 立即处理订阅
        await manager._process_subscription(subscription)

        # 更新检查时间
        now = datetime.now()
        subscription.last_check = now
        subscription.next_check = now + timedelta(seconds=subscription.check_interval)
        subscription.updated_at = now

        return {"message": "Subscription triggered successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{subscription_id}/history", response_model=List[Dict[str, Any]])
async def get_subscription_history(
    subscription_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    manager: SubscriptionManager = Depends(get_subscription_manager),
):
    """获取订阅历史记录"""
    try:
        subscription = await manager.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # TODO: 实现历史记录存储和查询
        # 暂时返回空列表
        return []

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media-types", response_model=List[Dict[str, Any]])
async def get_media_types():
    """获取支持的媒体类型"""
    return [
        {"value": "movie", "label": "电影", "description": "电影类型"},
        {"value": "tv", "label": "电视剧", "description": "电视剧类型"},
        {"value": "music", "label": "音乐", "description": "音乐类型"},
        {"value": "anime", "label": "动漫", "description": "动漫类型"},
    ]


@router.get("/quality-options", response_model=List[Dict[str, Any]])
async def get_quality_options():
    """获取质量选项"""
    return [
        {"value": "4K", "label": "4K", "description": "超高清4K"},
        {"value": "1080p", "label": "1080p", "description": "全高清1080p"},
        {"value": "720p", "label": "720p", "description": "高清720p"},
        {"value": "480p", "label": "480p", "description": "标清480p"},
    ]
