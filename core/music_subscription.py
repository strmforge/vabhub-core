"""
音乐订阅管理器
管理多平台音乐订阅、下载和同步
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict

from .music_platform_adapter import MusicPlatformAdapter, MusicPlatformFactory
from .cache_manager import CacheManager
from .config import Config

logger = logging.getLogger(__name__)


class MusicSubscriptionManager:
    """音乐订阅管理器"""

    def __init__(self, config: Config, cache_manager: Optional[CacheManager] = None):
        self.config = config
        self.cache_manager = cache_manager

        # 平台适配器
        self.adapters: Dict[str, MusicPlatformAdapter] = {}

        # 订阅数据
        self.subscriptions: Dict[str, Dict] = {}
        self.user_preferences: Dict[str, Dict] = {}
        self.download_queue: List[Dict] = []
        self.sync_status: Dict[str, Any] = {}

        # 性能统计
        self.stats = {
            "total_searches": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "last_sync_time": None,
        }

        # 初始化平台适配器
        self._init_adapters()

    def _init_adapters(self):
        """初始化平台适配器"""
        try:
            # 支持的平台列表
            supported_platforms = ["spotify", "qqmusic", "netease"]

            for platform in supported_platforms:
                adapter = MusicPlatformFactory.create_adapter(
                    platform, self.config, self.cache_manager
                )
                self.adapters[platform] = adapter
                logger.info(f"初始化音乐平台适配器: {platform}")

            logger.info(f"成功初始化 {len(self.adapters)} 个音乐平台适配器")

        except Exception as e:
            logger.error(f"初始化音乐平台适配器失败: {e}")
            raise

    async def search_music(
        self,
        query: str,
        platform: str = "all",
        query_type: str = "track",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        搜索音乐

        Args:
            query: 搜索关键词
            platform: 平台名称 ('all' 表示所有平台)
            query_type: 搜索类型 ('track', 'artist', 'album', 'playlist')
            limit: 返回结果数量

        Returns:
            搜索结果列表
        """
        # 确保stats字典中有total_searches键且不为None
        if "total_searches" not in self.stats:
            self.stats["total_searches"] = 0
        elif self.stats["total_searches"] is None:
            self.stats["total_searches"] = 0
        self.stats["total_searches"] += 1

        try:
            if platform == "all":
                # 在所有平台搜索
                tasks = []
                for adapter in self.adapters.values():
                    task = adapter.search(query, query_type, limit)
                    tasks.append(task)

                # 并发搜索
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 合并结果
                merged_results: List[Dict[str, Any]] = []
                for result in results:
                    if isinstance(result, Exception):
                        logger.warning(f"平台搜索失败: {result}")
                        continue
                    if result and isinstance(result, list):
                        merged_results.extend(result)

                # 去重和排序
                merged_results = self._deduplicate_results(merged_results)
                return merged_results[:limit]

            else:
                # 在指定平台搜索
                if platform not in self.adapters:
                    raise ValueError(f"不支持的平台: {platform}")

                adapter = self.adapters[platform]
                return await adapter.search(query, query_type, limit)

        except Exception as e:
            logger.error(f"音乐搜索失败: {e}")
            raise

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """去重搜索结果"""
        seen = set()
        deduplicated = []

        for result in results:
            # 基于标题和艺术家去重
            key = (result.get("title", ""), result.get("artist", ""))
            if key not in seen:
                seen.add(key)
                deduplicated.append(result)

        return deduplicated

    async def add_subscription(self, user_id: str, subscription_data: Dict) -> bool:
        """添加音乐订阅"""
        try:
            subscription_id = f"{user_id}_{int(time.time())}"

            subscription = {
                "id": subscription_id,
                "user_id": user_id,
                "type": subscription_data.get("type", "track"),
                "target": subscription_data.get("target"),
                "platform": subscription_data.get("platform", "all"),
                "filters": subscription_data.get("filters", {}),
                "schedule": subscription_data.get("schedule", "daily"),
                "enabled": True,
                "created_at": datetime.now(),
                "last_sync": None,
                "next_sync": (
                    datetime.now() + timedelta(hours=24)
                    if subscription_data.get("schedule", "daily") == "daily"
                    else datetime.now() + timedelta(days=7)
                ),
            }

            self.subscriptions[subscription_id] = subscription

            logger.info(f"用户 {user_id} 添加订阅: {subscription_id}")
            return True

        except Exception as e:
            logger.error(f"添加订阅失败: {e}")
            return False

    async def remove_subscription(self, subscription_id: str) -> bool:
        """移除订阅"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            logger.info(f"移除订阅: {subscription_id}")
            return True
        return False

    async def sync_subscriptions(self) -> Dict[str, Any]:
        """同步所有订阅"""
        sync_results = {
            "total": len(self.subscriptions),
            "successful": 0,
            "failed": 0,
            "new_content": [],
            "errors": [],
        }

        current_time = datetime.now()

        for subscription_id, subscription in self.subscriptions.items():
            if not subscription["enabled"]:
                continue

            if subscription["next_sync"] and subscription["next_sync"] > current_time:
                continue

            try:
                # 执行订阅同步
                new_content = await self._sync_single_subscription(subscription)

                if new_content and isinstance(new_content, list):
                    sync_results["new_content"].extend(new_content)
                    sync_results["successful"] = sync_results.get("successful", 0) + 1
                else:
                    sync_results["successful"] = sync_results.get("successful", 0) + 1

                # 更新同步时间
                subscription["last_sync"] = current_time
                subscription["next_sync"] = current_time + self._get_sync_interval(
                    subscription["schedule"]
                )

            except Exception as e:
                sync_results["failed"] = sync_results.get("failed", 0) + 1
                sync_results["errors"].append(
                    {"subscription_id": subscription_id, "error": str(e)}
                )
                logger.error(f"订阅同步失败 {subscription_id}: {e}")

        self.stats["last_sync_time"] = current_time
        logger.info(f"订阅同步完成: {sync_results}")

        return sync_results

    async def _sync_single_subscription(self, subscription: Dict) -> List[Dict]:
        """同步单个订阅"""
        new_content = []

        if subscription["type"] == "track":
            # 同步歌曲
            results = await self.search_music(
                subscription["target"], subscription["platform"], "track", 10
            )

            # 应用过滤器
            filtered_results = self._apply_filters(results, subscription["filters"])
            new_content.extend(filtered_results)

        elif subscription["type"] == "artist":
            # 同步艺术家
            pass

        elif subscription["type"] == "playlist":
            # 同步播放列表
            pass

        return new_content

    def _apply_filters(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """应用过滤器"""
        filtered = []

        for result in results:
            # 应用各种过滤器
            if self._matches_filters(result, filters):
                filtered.append(result)

        return filtered

    def _matches_filters(self, result: Dict, filters: Dict) -> bool:
        """检查结果是否匹配过滤器"""
        # 实现各种过滤逻辑
        return True

    def _get_sync_interval(self, schedule: str) -> timedelta:
        """获取同步间隔"""
        intervals = {
            "hourly": timedelta(hours=1),
            "daily": timedelta(hours=24),
            "weekly": timedelta(days=7),
            "monthly": timedelta(days=30),
        }
        return intervals.get(schedule, timedelta(hours=24))

    async def get_user_subscriptions(self, user_id: str) -> List[Dict]:
        """获取用户订阅列表"""
        user_subs = []
        for sub in self.subscriptions.values():
            if sub["user_id"] == user_id:
                user_subs.append(sub)
        return user_subs

    async def update_user_preferences(self, user_id: str, preferences: Dict):
        """更新用户偏好"""
        self.user_preferences[user_id] = preferences
        logger.info(f"更新用户 {user_id} 偏好设置")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "subscriptions": len(self.subscriptions),
            "active_platforms": len(self.adapters),
            "performance": self.stats,
            "cache_stats": self._get_cache_stats(),
        }

    def _get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        cache_stats = {}
        for platform, adapter in self.adapters.items():
            cache_stats[platform] = adapter.get_cache_stats()
        return cache_stats

    async def cleanup(self):
        """清理资源"""
        # 清理过期的订阅数据
        current_time = datetime.now()
        expired_subs = []

        for sub_id, sub in self.subscriptions.items():
            # 如果订阅超过30天未同步且未启用，则清理
            if (
                sub["last_sync"]
                and (current_time - sub["last_sync"]).days > 30
                and not sub["enabled"]
            ):
                expired_subs.append(sub_id)

        for sub_id in expired_subs:
            await self.remove_subscription(sub_id)

        logger.info(f"清理了 {len(expired_subs)} 个过期订阅")


# 音乐订阅管理器工厂
class MusicSubscriptionManagerFactory:
    """音乐订阅管理器工厂"""

    _instance = None

    @classmethod
    def get_instance(
        cls, config: Config, cache_manager: Optional[CacheManager] = None
    ) -> MusicSubscriptionManager:
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = MusicSubscriptionManager(config, cache_manager)
        return cls._instance

    @classmethod
    def create_manager(
        cls, config: Config, cache_manager: Optional[CacheManager] = None
    ) -> MusicSubscriptionManager:
        """创建新的管理器实例"""
        return MusicSubscriptionManager(config, cache_manager)
