"""
VabHub 缓存管理器

提供多级缓存、缓存策略、过期管理和性能监控功能
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis.asyncio as redis
else:
    try:
        import redis.asyncio as redis
    except ImportError:
        redis = None


class CacheLevel(Enum):
    """缓存级别"""

    MEMORY = "memory"
    DISK = "disk"
    REDIS = "redis"


class CachePolicy(Enum):
    """缓存策略"""

    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最不经常使用
    FIFO = "fifo"  # 先进先出


@dataclass
class CacheStats:
    """缓存统计信息"""

    hits: int = 0
    misses: int = 0
    size: int = 0
    max_size: int = 0
    hit_rate: float = 0.0


class CacheBackend(ABC):
    """缓存后端抽象基类"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键"""
        pass

    async def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存值"""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def batch_set(self, items: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存值"""
        results = []
        for key, value in items.items():
            success = await self.set(key, value, ttl)
            results.append(success)
        return all(results)

    async def batch_delete(self, keys: List[str]) -> bool:
        """批量删除缓存值"""
        results = []
        for key in keys:
            success = await self.delete(key)
            results.append(success)
        return all(results)

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {"status": "unknown"}

    async def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        return {}

    async def close(self) -> None:
        """关闭连接"""
        pass


class MemoryCacheBackend(CacheBackend):
    """内存缓存后端"""

    def __init__(self, max_size: int = 1000, policy: CachePolicy = CachePolicy.LRU):
        self.max_size = max_size
        self.policy = policy
        self._cache: Dict[str, Any] = {}
        self._access_times: Dict[str, float] = {}
        self._access_counts: Dict[str, int] = {}
        self._creation_times: Dict[str, float] = {}

        if policy == CachePolicy.LRU:
            self._order: OrderedDict[str, float] = OrderedDict()

    async def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None

        # 更新访问信息
        current_time = time.time()
        self._access_times[key] = current_time
        self._access_counts[key] = self._access_counts.get(key, 0) + 1

        if self.policy == CachePolicy.LRU:
            self._order.move_to_end(key)

        return self._cache[key]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        # 检查是否需要淘汰
        if len(self._cache) >= self.max_size:
            await self._evict()

        current_time = time.time()
        self._cache[key] = value
        self._access_times[key] = current_time
        self._access_counts[key] = 0
        self._creation_times[key] = current_time

        if self.policy == CachePolicy.LRU:
            self._order[key] = current_time

        # 设置TTL
        if ttl:
            asyncio.create_task(self._set_ttl(key, ttl))

        return True

    async def _set_ttl(self, key: str, ttl: int):
        """设置TTL过期"""
        await asyncio.sleep(ttl)
        if key in self._cache:
            await self.delete(key)

    async def _evict(self):
        """淘汰缓存"""
        if not self._cache:
            return

        if self.policy == CachePolicy.LRU:
            # LRU策略：淘汰最久未使用的
            oldest_key = next(iter(self._order))
            await self.delete(oldest_key)
        elif self.policy == CachePolicy.LFU:
            # LFU策略：淘汰使用频率最低的
            min_count = min(self._access_counts.values())
            candidates = [k for k, v in self._access_counts.items() if v == min_count]
            if candidates:
                await self.delete(candidates[0])
        else:  # FIFO
            # FIFO策略：淘汰最早创建的
            oldest_time = min(self._creation_times.values())
            candidates = [
                k for k, v in self._creation_times.items() if v == oldest_time
            ]
            if candidates:
                await self.delete(candidates[0])

    async def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            del self._access_times[key]
            del self._access_counts[key]
            del self._creation_times[key]

            if self.policy == CachePolicy.LRU and key in self._order:
                del self._order[key]

            return True
        return False

    async def clear(self) -> bool:
        self._cache.clear()
        self._access_times.clear()
        self._access_counts.clear()
        self._creation_times.clear()
        self._order.clear()
        return True

    async def exists(self, key: str) -> bool:
        return key in self._cache

    async def keys(self, pattern: str = "*") -> List[str]:
        if pattern == "*":
            return list(self._cache.keys())

        # 简单的模式匹配（支持*通配符）
        import fnmatch

        return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]


class RedisCacheBackend(CacheBackend):
    """Redis缓存后端"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "vabhub:",
        max_connections: int = 10,
        health_check_interval: int = 30,
    ):
        if redis is None:
            raise ImportError("redis package is required for RedisCacheBackend")

        # 创建连接池
        self.redis_pool: redis.ConnectionPool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            health_check_interval=health_check_interval,
            retry_on_timeout=True,
        )
        self.redis = redis.Redis(connection_pool=self.redis_pool)
        self.prefix = prefix
        self.logger = logging.getLogger(__name__)
        self._last_health_check = 0
        self._is_healthy = True

    async def get(self, key: str) -> Optional[Any]:
        full_key = f"{self.prefix}{key}"
        try:
            value = await self.redis.get(full_key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get Redis cache {full_key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        full_key = f"{self.prefix}{key}"
        try:
            value_str = json.dumps(value, ensure_ascii=False)
            await self.redis.set(full_key, value_str, ex=ttl)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set Redis cache {full_key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        full_key = f"{self.prefix}{key}"
        try:
            result = await self.redis.delete(full_key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Failed to delete Redis cache {full_key}: {e}")
            return False

    async def clear(self) -> bool:
        try:
            keys = await self.redis.keys(f"{self.prefix}*")
            if keys:
                await self.redis.delete(*keys)
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear Redis cache: {e}")
            return False

    async def exists(self, key: str) -> bool:
        full_key = f"{self.prefix}{key}"
        try:
            return await self.redis.exists(full_key) > 0
        except Exception as e:
            self.logger.error(f"Failed to check Redis cache {full_key}: {e}")
            return False

    async def keys(self, pattern: str = "*") -> List[str]:
        try:
            full_pattern = f"{self.prefix}{pattern}"
            keys = await self.redis.keys(full_pattern)
            # 移除前缀
            return [key.decode().replace(self.prefix, "") for key in keys]
        except Exception as e:
            self.logger.error(f"Failed to get Redis keys {pattern}: {e}")
            return []

    async def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存值"""
        if not keys:
            return {}

        try:
            full_keys = [f"{self.prefix}{key}" for key in keys]
            values = await self.redis.mget(full_keys)

            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value.decode()

            return result
        except Exception as e:
            self.logger.error(f"Failed to batch get Redis cache: {e}")
            return {}

    async def batch_set(self, items: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存值"""
        if not items:
            return True

        try:
            pipeline = self.redis.pipeline()

            for key, value in items.items():
                full_key = f"{self.prefix}{key}"
                value_str = json.dumps(value, ensure_ascii=False)
                pipeline.set(full_key, value_str, ex=ttl)

            await pipeline.execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to batch set Redis cache: {e}")
            return False

    async def batch_delete(self, keys: List[str]) -> bool:
        """批量删除缓存值"""
        if not keys:
            return True

        try:
            full_keys = [f"{self.prefix}{key}" for key in keys]
            result = await self.redis.delete(*full_keys)
            return result > 0
        except Exception as e:
            self.logger.error(f"Failed to batch delete Redis cache: {e}")
            return False

    async def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            info = await self.redis.info("memory")
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                "used_memory_rss": info.get("used_memory_rss", 0),
                "used_memory_rss_human": info.get("used_memory_rss_human", "0B"),
            }
        except Exception as e:
            self.logger.error(f"Failed to get Redis memory usage: {e}")
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查连接状态
            ping_result = await self.redis.ping()  # type: ignore

            # 获取Redis信息
            info = await self.redis.info()  # type: ignore

            # 检查连接池状态
            pool_info = {
                "status": "connected",
                # 不再直接访问内部属性
            }

            return {
                "status": "healthy" if ping_result else "unhealthy",
                "ping": ping_result,
                "memory_used": info.get("used_memory", 0),
                "connected_clients": info.get("connected_clients", 0),
                "pool": pool_info,
                "last_check": time.time(),
            }
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e), "last_check": time.time()}

    async def close(self):
        """关闭Redis连接"""
        try:
            await self.redis.close()  # type: ignore
            self.redis_pool.disconnect()  # type: ignore
        except Exception as e:
            self.logger.error(f"Failed to close Redis connection: {e}")


class DiskCacheBackend(CacheBackend):
    """磁盘缓存后端"""

    def __init__(self, cache_dir: Path = Path(".cache"), max_size: int = 10000):
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.logger = logging.getLogger(__name__)

        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def get(self, key: str) -> Optional[Any]:
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查过期时间
            if "expires" in data and data["expires"] < time.time():
                await self.delete(key)
                return None

            return data.get("value")

        except Exception as e:
            self.logger.error(f"Failed to read cache file {cache_file}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        cache_file = self.cache_dir / f"{key}.json"

        try:
            data = {"value": value, "created": time.time()}

            if ttl:
                data["expires"] = time.time() + ttl

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            return True

        except Exception as e:
            self.logger.error(f"Failed to write cache file {cache_file}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        cache_file = self.cache_dir / f"{key}.json"

        try:
            if cache_file.exists():
                cache_file.unlink()
                return True
            return False

        except Exception as e:
            self.logger.error(f"Failed to delete cache file {cache_file}: {e}")
            return False

    async def clear(self) -> bool:
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            return True

        except Exception as e:
            self.logger.error(f"Failed to clear cache directory: {e}")
            return False

    async def exists(self, key: str) -> bool:
        cache_file = self.cache_dir / f"{key}.json"
        return cache_file.exists()

    async def keys(self, pattern: str = "*") -> List[str]:
        import fnmatch

        keys = []
        for cache_file in self.cache_dir.glob("*.json"):
            key = cache_file.stem
            if fnmatch.fnmatch(key, pattern):
                keys.append(key)

        return keys


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self.backends: Dict[CacheLevel, CacheBackend] = {}
        self.stats: Dict[CacheLevel, CacheStats] = {}
        self.logger = logging.getLogger(__name__)

        # 默认配置
        self.default_ttl = 3600  # 1小时
        self.enabled_levels = [CacheLevel.MEMORY, CacheLevel.DISK]

        # 检查Redis可用性
        if redis is not None:
            self.enabled_levels.append(CacheLevel.REDIS)

    def add_backend(self, level: CacheLevel, backend: CacheBackend):
        """添加缓存后端"""
        self.backends[level] = backend
        self.stats[level] = CacheStats(max_size=getattr(backend, "max_size", 0))

    async def get(self, key: str, level: Optional[CacheLevel] = None) -> Optional[Any]:
        """获取缓存值"""
        levels_to_check = [level] if level else self.enabled_levels

        for cache_level in levels_to_check:
            if cache_level not in self.backends:
                continue

            backend = self.backends[cache_level]
            value = await backend.get(key)

            if value is not None:
                # 缓存命中
                self.stats[cache_level].hits += 1
                self._update_hit_rate(cache_level)

                # 更新其他级别的缓存（写回策略）
                await self._update_other_levels(key, value, cache_level)

                return value
            else:
                # 缓存未命中
                self.stats[cache_level].misses += 1
                self._update_hit_rate(cache_level)

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        level: Optional[CacheLevel] = None,
    ) -> bool:
        """设置缓存值"""
        if ttl is None:
            ttl = self.default_ttl

        levels_to_set = [level] if level else self.enabled_levels
        results = []

        for cache_level in levels_to_set:
            if cache_level not in self.backends:
                continue

            backend = self.backends[cache_level]
            success = await backend.set(key, value, ttl)
            results.append(success)

            if success:
                self.stats[cache_level].size += 1

        return any(results)

    async def delete(self, key: str, level: Optional[CacheLevel] = None) -> bool:
        """删除缓存值"""
        levels_to_delete = [level] if level else self.enabled_levels
        results = []

        for cache_level in levels_to_delete:
            if cache_level not in self.backends:
                continue

            backend = self.backends[cache_level]
            success = await backend.delete(key)
            results.append(success)

            if success:
                self.stats[cache_level].size = max(0, self.stats[cache_level].size - 1)

        return any(results)

    async def clear(self, level: Optional[CacheLevel] = None) -> bool:
        """清空缓存"""
        levels_to_clear = [level] if level else self.enabled_levels
        results = []

        for cache_level in levels_to_clear:
            if cache_level not in self.backends:
                continue

            backend = self.backends[cache_level]
            success = await backend.clear()
            results.append(success)

            if success:
                self.stats[cache_level].size = 0

        return any(results)

    async def exists(self, key: str, level: Optional[CacheLevel] = None) -> bool:
        """检查缓存是否存在"""
        levels_to_check = [level] if level else self.enabled_levels

        for cache_level in levels_to_check:
            if cache_level not in self.backends:
                continue

            backend = self.backends[cache_level]
            if await backend.exists(key):
                return True

        return False

    async def get_stats(
        self, level: Optional[CacheLevel] = None
    ) -> Dict[CacheLevel, CacheStats]:
        """获取缓存统计信息"""
        if level:
            return {level: self.stats.get(level, CacheStats())}
        else:
            return self.stats.copy()

    async def batch_get(
        self, keys: List[str], level: Optional[CacheLevel] = None
    ) -> Dict[str, Any]:
        """批量获取缓存值"""
        levels_to_check = [level] if level else self.enabled_levels

        for cache_level in levels_to_check:
            if cache_level not in self.backends:
                continue

            backend = self.backends[cache_level]
            if hasattr(backend, "batch_get"):
                result = await backend.batch_get(keys)
                if result:
                    # 更新统计信息
                    for key in keys:
                        if key in result:
                            self.stats[cache_level].hits += 1
                        else:
                            self.stats[cache_level].misses += 1
                    self._update_hit_rate(cache_level)
                    return result

        # 如果没有批量操作支持，回退到单个获取
        result = {}
        for key in keys:
            value = await self.get(key, level)
            if value is not None:
                result[key] = value

        return result

    async def batch_set(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        level: Optional[CacheLevel] = None,
    ) -> bool:
        """批量设置缓存值"""
        if ttl is None:
            ttl = self.default_ttl

        levels_to_set = [level] if level else self.enabled_levels
        results = []

        for cache_level in levels_to_set:
            if cache_level not in self.backends:
                continue

            backend = self.backends[cache_level]
            if hasattr(backend, "batch_set"):
                success = await backend.batch_set(items, ttl)
                results.append(success)

                if success:
                    self.stats[cache_level].size += len(items)
            else:
                # 如果没有批量操作支持，回退到单个设置
                for key, value in items.items():
                    success = await backend.set(key, value, ttl)
                    if success:
                        self.stats[cache_level].size += 1
                results.append(True)

        return any(results)

    async def batch_delete(
        self, keys: List[str], level: Optional[CacheLevel] = None
    ) -> bool:
        """批量删除缓存值"""
        levels_to_delete = [level] if level else self.enabled_levels
        results = []

        for cache_level in levels_to_delete:
            if cache_level not in self.backends:
                continue

            backend = self.backends[cache_level]
            if hasattr(backend, "batch_delete"):
                success = await backend.batch_delete(keys)
                results.append(success)

                if success:
                    self.stats[cache_level].size = max(
                        0, self.stats[cache_level].size - len(keys)
                    )
            else:
                # 如果没有批量操作支持，回退到单个删除
                for key in keys:
                    success = await backend.delete(key)
                    if success:
                        self.stats[cache_level].size = max(
                            0, self.stats[cache_level].size - 1
                        )
                results.append(True)

        return any(results)

    async def health_check(self, level: Optional[CacheLevel] = None) -> Dict[str, Any]:
        """健康检查"""
        levels_to_check = [level] if level else self.enabled_levels

        health_status = {}

        for cache_level in levels_to_check:
            if cache_level not in self.backends:
                health_status[cache_level.value] = {
                    "status": "not_configured",
                    "error": f"Backend for {cache_level.value} not configured",
                }
                continue

            backend = self.backends[cache_level]

            if hasattr(backend, "health_check"):
                health_status[cache_level.value] = await backend.health_check()
            else:
                # 基本健康检查
                try:
                    # 尝试简单的操作来检查健康状态
                    test_key = f"health_check_{int(time.time())}"
                    await backend.set(test_key, "test", 10)
                    value = await backend.get(test_key)
                    await backend.delete(test_key)

                    health_status[cache_level.value] = {
                        "status": "healthy" if value == "test" else "unhealthy",
                        "last_check": str(time.time()),
                    }
                except Exception as e:
                    health_status[cache_level.value] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "last_check": str(time.time()),
                    }

        return health_status

    async def get_memory_usage(
        self, level: Optional[CacheLevel] = None
    ) -> Dict[str, Any]:
        """获取内存使用情况"""
        levels_to_check = [level] if level else self.enabled_levels

        memory_usage = {}

        for cache_level in levels_to_check:
            if cache_level not in self.backends:
                continue

            backend = self.backends[cache_level]

            if hasattr(backend, "get_memory_usage"):
                memory_usage[cache_level.value] = await backend.get_memory_usage()
            else:
                # 基本内存使用统计
                stats = self.stats.get(cache_level, CacheStats())
                memory_usage[cache_level.value] = {
                    "size": stats.size,
                    "max_size": stats.max_size,
                    "hit_rate": stats.hit_rate,
                }

        return memory_usage

    async def close(self):
        """关闭所有缓存后端"""
        for backend in self.backends.values():
            if hasattr(backend, "close"):
                await backend.close()

    def _update_hit_rate(self, level: CacheLevel):
        """更新命中率"""
        stats = self.stats[level]
        total = stats.hits + stats.misses
        if total > 0:
            stats.hit_rate = stats.hits / total

    async def _update_other_levels(
        self, key: str, value: Any, source_level: CacheLevel
    ):
        """更新其他级别的缓存"""
        for cache_level in self.enabled_levels:
            if cache_level == source_level:
                continue

            if cache_level in self.backends:
                backend = self.backends[cache_level]
                if not await backend.exists(key):
                    await backend.set(key, value, self.default_ttl)


# 全局缓存管理器实例
cache_manager = CacheManager()


def cached(
    ttl: int = 3600,
    key_func: Optional[Callable] = None,
    level: CacheLevel = CacheLevel.MEMORY,
):
    """
    缓存装饰器

    Args:
        ttl: 缓存时间（秒）
        key_func: 缓存键生成函数
        level: 缓存级别
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认键生成：函数名 + 参数哈希
                import hashlib

                param_str = str(args) + str(kwargs)
                param_hash = hashlib.md5(param_str.encode()).hexdigest()
                cache_key = f"{func.__name__}:{param_hash}"

            # 尝试从缓存获取
            cached_value = await cache_manager.get(cache_key, level)
            if cached_value is not None:
                return cached_value

            # 执行函数并缓存结果
            result = (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )
            await cache_manager.set(cache_key, result, ttl, level)

            return result

        return wrapper

    return decorator
