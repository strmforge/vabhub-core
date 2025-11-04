"""
Cache module for VabHub Core - Redis缓存系统
"""

import json
import redis
from typing import Any, Optional
from datetime import datetime, timedelta


class RedisCacheManager:
    """Redis缓存管理器"""

    def __init__(self, redis_url: str, default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client = None
        self._connect()

    def _connect(self):
        """连接到Redis服务器"""
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            # 测试连接
            self.client.ping()
        except redis.ConnectionError as e:
            print(f"Redis连接失败: {e}")
            self.client = None

    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        return self.client is not None

    def get(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.is_connected():
            return None

        try:
            if self.client:
                data = self.client.get(key)
                if data:
                    return json.loads(data)
        except (redis.RedisError, json.JSONDecodeError) as e:
            print(f"Redis获取数据失败: {e}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存数据"""
        if not self.is_connected():
            return False

        try:
            if self.client:
                ttl = ttl or self.default_ttl
                data = json.dumps(value, default=str)
                self.client.setex(key, ttl, data)
                return True
        except (redis.RedisError, TypeError) as e:
            print(f"Redis设置数据失败: {e}")
        return False

    def delete(self, key: str) -> bool:
        """删除缓存数据"""
        if not self.is_connected():
            return False

        try:
            if self.client:
                self.client.delete(key)
                return True
        except redis.RedisError as e:
            print(f"Redis删除数据失败: {e}")
        return False

    def clear(self) -> bool:
        """清空所有缓存"""
        if not self.is_connected():
            return False

        try:
            if self.client:
                self.client.flushdb()
                return True
        except redis.RedisError as e:
            print(f"Redis清空缓存失败: {e}")
        return False

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        if not self.is_connected():
            return {"connected": False}

        try:
            if self.client:
                info = self.client.info()
                return {
                    "connected": True,
                    "used_memory": info.get("used_memory_human", "0"),
                    "connected_clients": info.get("connected_clients", 0),
                    "keys": self.client.dbsize(),
                    "uptime": info.get("uptime_in_seconds", 0),
                }
        except redis.RedisError as e:
            return {"connected": False, "error": str(e)}
        return {"connected": False}


# 全局缓存管理器实例
cache_manager = None


def init_cache_manager(redis_url: str, default_ttl: int = 3600):
    """初始化全局缓存管理器"""
    global cache_manager
    cache_manager = RedisCacheManager(redis_url, default_ttl)
    return cache_manager


def get_cache_manager() -> Optional[RedisCacheManager]:
    """获取全局缓存管理器"""
    if cache_manager is None:
        print("警告: 缓存管理器尚未初始化，请先调用init_cache_manager")
    return cache_manager
