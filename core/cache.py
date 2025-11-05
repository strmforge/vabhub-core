"""
Cache module for VabHub Core - Redis缓存系统
"""

import json
import redis
from typing import Any, Optional, List
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

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.is_connected():
            return False

        try:
            if self.client:
                return self.client.exists(key) > 0
        except redis.RedisError as e:
            print(f"Redis检查键存在失败: {e}")
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
                keys_count = self.client.dbsize()
                return {
                    "connected": True,
                    "used_memory": info.get("used_memory_human", "0"),
                    "connected_clients": info.get("connected_clients", 0),
                    "keys_count": keys_count,
                    "uptime": info.get("uptime_in_seconds", 0),
                }
        except redis.RedisError as e:
            return {"connected": False, "error": str(e)}
        return {"connected": False}

    def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键列表"""
        if not self.is_connected():
            return []

        try:
            if self.client:
                keys = self.client.keys(pattern)
                return [
                    key.decode("utf-8") if isinstance(key, bytes) else key
                    for key in keys
                ]
        except redis.RedisError as e:
            print(f"Redis获取键列表失败: {e}")
        return []

    def expire(self, key: str, ttl: int) -> bool:
        """设置键的过期时间"""
        if not self.is_connected():
            return False

        try:
            if self.client:
                result = self.client.expire(key, ttl)
                return bool(result)
        except redis.RedisError as e:
            print(f"Redis设置过期时间失败: {e}")
        return False

    def ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        if not self.is_connected():
            return -1

        try:
            if self.client:
                return self.client.ttl(key)
        except redis.RedisError as e:
            print(f"Redis获取TTL失败: {e}")
        return -1

    def increment(self, key: str) -> int:
        """递增键的值"""
        if not self.is_connected():
            return 0

        try:
            if self.client:
                return self.client.incr(key)
        except redis.RedisError as e:
            print(f"Redis递增值失败: {e}")
        return 0

    def decrement(self, key: str) -> int:
        """递减键的值"""
        if not self.is_connected():
            return 0

        try:
            if self.client:
                return self.client.decr(key)
        except redis.RedisError as e:
            print(f"Redis递减值失败: {e}")
        return 0

    def bulk_set(self, items: dict, ttl: Optional[int] = None) -> bool:
        """批量设置键值对"""
        if not self.is_connected():
            return False

        try:
            if self.client:
                ttl = ttl or self.default_ttl
                pipe = self.client.pipeline()
                for key, value in items.items():
                    data = json.dumps(value, default=str)
                    pipe.setex(key, ttl, data)
                pipe.execute()
                return True
        except (redis.RedisError, TypeError) as e:
            print(f"Redis批量设置失败: {e}")
        return False

    def bulk_get(self, keys: List[str]) -> List[Optional[Any]]:
        """批量获取键值"""
        if not self.is_connected():
            return [None] * len(keys)

        try:
            if self.client:
                results = self.client.mget(keys)
                return [json.loads(result) if result else None for result in results]
        except (redis.RedisError, json.JSONDecodeError) as e:
            print(f"Redis批量获取失败: {e}")
        return [None] * len(keys)

    def ping(self) -> bool:
        """测试Redis连接"""
        if not self.is_connected():
            return False

        try:
            if self.client:
                return self.client.ping()
        except redis.RedisError as e:
            print(f"Redis ping失败: {e}")
        return False

    def close(self):
        """关闭Redis连接"""
        if self.client:
            try:
                self.client.close()
            except redis.RedisError as e:
                print(f"Redis关闭连接失败: {e}")


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
