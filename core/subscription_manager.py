"""
自动化订阅系统核心模块
"""

import asyncio
from .logging_config import get_logger
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass
from .config import Config
from .download_manager import DownloadManager
from datetime import timedelta
from datetime import timedelta

logger = get_logger("vabhub.subscription")

class SubscriptionStatus(Enum):
    """订阅状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class MediaType(Enum):
    """媒体类型"""
    MOVIE = "movie"
    TV = "tv"
    MUSIC = "music"
    ANIME = "anime"

@dataclass
class SubscriptionRule:
    """订阅规则"""
    name: str
    keywords: List[str]
    exclude_keywords: List[str] = None
    quality: str = "1080p"
    media_type: MediaType = MediaType.MOVIE
    enabled: bool = True
    priority: int = 1
    
    def __post_init__(self):
        if self.exclude_keywords is None:
            self.exclude_keywords = []

@dataclass
class Subscription:
    """订阅实体"""
    id: str
    name: str
    rules: List[SubscriptionRule]
    status: SubscriptionStatus
    last_check: Optional[datetime] = None
    next_check: Optional[datetime] = None
    check_interval: int = 3600  # 默认1小时
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.next_check is None:
            self.next_check = datetime.now() + timedelta(seconds=self.check_interval)

class SubscriptionManager:
    """订阅管理器"""
    
    def __init__(self, config: Config, download_manager: DownloadManager):
        self.config = config
        self.download_manager = download_manager
        self.subscriptions: Dict[str, Subscription] = {}
        self.running = False
        self.task = None
        
    async def start(self):
        """启动订阅管理器"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("Subscription manager started")
    
    async def stop(self):
        """停止订阅管理器"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Subscription manager stopped")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                await self._check_subscriptions()
                await asyncio.sleep(60)  # 每分钟检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in subscription monitor loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_subscriptions(self):
        """检查所有订阅"""
        now = datetime.now()
        for subscription in self.subscriptions.values():
            if (subscription.status == SubscriptionStatus.ACTIVE and 
                subscription.next_check and subscription.next_check <= now):
                
                try:
                    await self._process_subscription(subscription)
                    subscription.last_check = now
                    subscription.next_check = now + timedelta(seconds=subscription.check_interval)
                    subscription.updated_at = now
                except Exception as e:
                    logger.error(f"Error processing subscription {subscription.name}: {e}")
                    subscription.status = SubscriptionStatus.ERROR
    
    async def _process_subscription(self, subscription: Subscription):
        """处理单个订阅"""
        logger.info(f"Processing subscription: {subscription.name}")
        
        # 这里需要集成RSS引擎来获取新的媒体项
        # 暂时使用模拟数据
        new_items = await self._fetch_new_items(subscription)
        
        for item in new_items:
            if await self._should_download(item, subscription.rules):
                await self._trigger_download(item, subscription)
    
    async def _fetch_new_items(self, subscription: Subscription) -> List[Dict[str, Any]]:
        """获取新的媒体项（模拟实现）"""
        # TODO: 集成RSS引擎
        return [
            {
                "title": "Test Movie 2023",
                "quality": "1080p",
                "size": "2.5GB",
                "download_url": "http://example.com/test.torrent",
                "media_type": MediaType.MOVIE
            }
        ]
    
    async def _should_download(self, item: Dict[str, Any], rules: List[SubscriptionRule]) -> bool:
        """判断是否应该下载"""
        for rule in rules:
            if not rule.enabled:
                continue
                
            # 检查关键词匹配
            title = item.get("title", "").lower()
            
            # 必须包含所有关键词
            if not all(keyword.lower() in title for keyword in rule.keywords):
                continue
                
            # 不能包含排除关键词
            if any(exclude.lower() in title for exclude in rule.exclude_keywords):
                continue
                
            # 检查质量要求
            if rule.quality and item.get("quality") != rule.quality:
                continue
                
            # 检查媒体类型
            if rule.media_type and item.get("media_type") != rule.media_type:
                continue
                
            return True
            
        return False
    
    async def _trigger_download(self, item: Dict[str, Any], subscription: Subscription):
        """触发下载"""
        try:
            download_info = {
                "url": item["download_url"],
                "name": item["title"],
                "category": f"subscription_{subscription.id}",
                "tags": ["auto", "subscription"]
            }
            
            await self.download_manager.add_download(download_info)
            logger.info(f"Triggered download for: {item['title']}")
            
        except Exception as e:
            logger.error(f"Failed to trigger download for {item['title']}: {e}")
    
    # 订阅管理方法
    async def create_subscription(self, name: str, rules: List[SubscriptionRule], 
                                 check_interval: int = 3600) -> Subscription:
        """创建新订阅"""
        subscription_id = f"sub_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        subscription = Subscription(
            id=subscription_id,
            name=name,
            rules=rules,
            status=SubscriptionStatus.ACTIVE,
            check_interval=check_interval
        )
        
        self.subscriptions[subscription_id] = subscription
        logger.info(f"Created subscription: {name} (ID: {subscription_id})")
        return subscription
    
    async def update_subscription(self, subscription_id: str, **kwargs) -> Optional[Subscription]:
        """更新订阅"""
        if subscription_id not in self.subscriptions:
            return None
            
        subscription = self.subscriptions[subscription_id]
        
        for key, value in kwargs.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)
        
        subscription.updated_at = datetime.now()
        return subscription
    
    async def delete_subscription(self, subscription_id: str) -> bool:
        """删除订阅"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            logger.info(f"Deleted subscription: {subscription_id}")
            return True
        return False
    
    async def pause_subscription(self, subscription_id: str) -> bool:
        """暂停订阅"""
        if subscription_id in self.subscriptions:
            subscription = self.subscriptions[subscription_id]
            subscription.status = SubscriptionStatus.PAUSED
            subscription.updated_at = datetime.now()
            return True
        return False
    
    async def resume_subscription(self, subscription_id: str) -> bool:
        """恢复订阅"""
        if subscription_id in self.subscriptions:
            subscription = self.subscriptions[subscription_id]
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.updated_at = datetime.now()
            return True
        return False
    
    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """获取订阅"""
        return self.subscriptions.get(subscription_id)
    
    async def list_subscriptions(self) -> List[Subscription]:
        """获取所有订阅"""
        return list(self.subscriptions.values())