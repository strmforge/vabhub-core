"""
音乐平台适配器模块
定义音乐平台适配器的抽象基类和各平台的具体实现
"""

import abc
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional

from .config import Config
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


# 自定义异常类
class MusicPlatformAPIError(Exception):
    """音乐平台API错误"""

    pass


class MusicPlatformAuthError(Exception):
    """音乐平台认证错误"""

    pass


class MusicPlatformRateLimitError(Exception):
    """音乐平台限流错误"""

    pass


class MusicNotFoundError(Exception):
    """音乐资源未找到错误"""

    pass


# 重试装饰器
import functools
from typing import Callable


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    指数退避重试装饰器
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"重试 {attempt + 1}/{max_retries}: {e}, 等待 {delay} 秒"
                    )
                    await asyncio.sleep(delay)
            return None

        return wrapper

    return decorator


# 限流器
class Throttler:
    """API调用限流器"""

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    async def acquire(self):
        """获取调用许可"""
        now = time.time()
        # 清理过期调用记录
        self.calls = [
            call_time for call_time in self.calls if now - call_time < self.period
        ]

        if len(self.calls) >= self.max_calls:
            # 需要等待
            wait_time = self.period - (now - self.calls[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # 重新清理并检查
                self.calls = [
                    call_time
                    for call_time in self.calls
                    if now + wait_time - call_time < self.period
                ]

        self.calls.append(time.time())


class MusicPlatformAdapter(abc.ABC):
    """音乐平台适配器抽象基类，实现缓存策略和通用接口"""

    # 资源类型对应的TTL配置（秒）
    CACHE_TTL_CONFIG = {
        "artist": 86400,  # 艺术家信息缓存1天
        "album": 43200,  # 专辑信息缓存12小时
        "track": 1800,  # 单曲信息缓存30分钟
        "playlist": 3600,  # 播放列表缓存1小时
        "search": 900,  # 搜索结果缓存15分钟
        "artist_tracks": 7200,  # 艺术家歌曲列表缓存2小时
    }

    # 预热优先级配置
    PRECACHE_PRIORITY = {
        "artist": 1,  # 最高优先级
        "track": 2,  # 高优先级
        "album": 3,  # 中优先级
        "playlist": 4,  # 低优先级
    }

    def __init__(self, config: Config, cache_manager: Optional[CacheManager] = None):
        self.config = config
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache_hits = 0
        self._cache_misses = 0
        self._last_stats_reset = time.time()

    @property
    @abc.abstractmethod
    def platform_name(self) -> str:
        """获取平台名称"""
        pass

    @abc.abstractmethod
    async def search_track(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        pass

    @abc.abstractmethod
    async def search_artist(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索艺术家"""
        pass

    @abc.abstractmethod
    async def search_album(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索专辑"""
        pass

    @abc.abstractmethod
    async def search_playlist(
        self, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索歌单"""
        pass

    async def search(
        self, query: str, query_type: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """通用搜索方法"""
        if query_type == "track":
            return await self.search_track(query, limit)
        elif query_type == "artist":
            return await self.search_artist(query, limit)
        elif query_type == "album":
            return await self.search_album(query, limit)
        elif query_type == "playlist":
            return await self.search_playlist(query, limit)
        else:
            logger.warning(f"不支持的搜索类型: {query_type}")
            return []

    @abc.abstractmethod
    async def get_artist_tracks(
        self, artist_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取艺术家的热门歌曲"""
        pass

    async def get_album_tracks(self, album_id: str) -> List[Dict[str, Any]]:
        """获取专辑中的歌曲"""
        pass

    @abc.abstractmethod
    async def get_track_details(self, track_id: str) -> Dict[str, Any]:
        """获取歌曲详细信息"""
        pass

    @abc.abstractmethod
    async def get_artist_details(self, artist_id: str) -> Dict[str, Any]:
        """获取艺术家详细信息"""
        pass

    @abc.abstractmethod
    async def get_album_details(self, album_id: str) -> Dict[str, Any]:
        """获取专辑详细信息"""
        pass

    @abc.abstractmethod
    async def get_playlist_details(self, playlist_id: str) -> Dict[str, Any]:
        """获取播放列表详细信息"""
        pass

    def _get_cache_key(self, resource_type: str, resource_id: str) -> str:
        """生成缓存键"""
        return f"music:{self.platform_name}:{resource_type}:{resource_id}"

    async def _get_cached_data(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.cache_manager:
            return None

        try:
            data = await self.cache_manager.get(cache_key)
            if data:
                self._cache_hits += 1
                return data
            else:
                self._cache_misses += 1
        except Exception as e:
            self.logger.warning(f"缓存读取失败: {e}")

        return None

    async def _set_cached_data(self, cache_key: str, data: Any, ttl: int) -> bool:
        """设置缓存数据"""
        if not self.cache_manager:
            return False

        try:
            await self.cache_manager.set(cache_key, data, ttl)
            return True
        except Exception as e:
            self.logger.warning(f"缓存写入失败: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": (
                self._cache_hits / (self._cache_hits + self._cache_misses)
                if (self._cache_hits + self._cache_misses) > 0
                else 0
            ),
        }

    def reset_cache_stats(self):
        """重置缓存统计"""
        self._cache_hits = 0
        self._cache_misses = 0
        self._last_stats_reset = time.time()


# 具体平台适配器实现
class SpotifyAdapter(MusicPlatformAdapter):
    """Spotify平台适配器"""

    @property
    def platform_name(self) -> str:
        return "spotify"

    async def search_track(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索Spotify歌曲"""
        # 实现Spotify搜索逻辑
        return []

    async def search_artist(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索Spotify艺术家"""
        return []

    async def search_album(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索Spotify专辑"""
        return []

    async def search_playlist(
        self, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索Spotify播放列表"""
        return []

    async def get_artist_tracks(
        self, artist_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取Spotify艺术家的热门歌曲"""
        return []

    async def get_track_details(self, track_id: str) -> Dict[str, Any]:
        """获取Spotify歌曲详细信息"""
        return {}

    async def get_artist_details(self, artist_id: str) -> Dict[str, Any]:
        """获取Spotify艺术家详细信息"""
        return {}

    async def get_album_details(self, album_id: str) -> Dict[str, Any]:
        """获取Spotify专辑详细信息"""
        return {}

    async def get_playlist_details(self, playlist_id: str) -> Dict[str, Any]:
        """获取Spotify播放列表详细信息"""
        return {}


class QQMusicAdapter(MusicPlatformAdapter):
    """QQ音乐平台适配器"""

    @property
    def platform_name(self) -> str:
        return "qqmusic"

    async def search_track(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索QQ音乐歌曲"""
        return []

    async def search_artist(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索QQ音乐艺术家"""
        return []

    async def search_album(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索QQ音乐专辑"""
        return []

    async def search_playlist(
        self, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索QQ音乐播放列表"""
        return []

    async def get_artist_tracks(
        self, artist_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取QQ音乐艺术家的热门歌曲"""
        return []

    async def get_track_details(self, track_id: str) -> Dict[str, Any]:
        """获取QQ音乐歌曲详细信息"""
        return {}

    async def get_artist_details(self, artist_id: str) -> Dict[str, Any]:
        """获取QQ音乐艺术家详细信息"""
        return {}

    async def get_album_details(self, album_id: str) -> Dict[str, Any]:
        """获取QQ音乐专辑详细信息"""
        return {}

    async def get_playlist_details(self, playlist_id: str) -> Dict[str, Any]:
        """获取QQ音乐播放列表详细信息"""
        return {}


class NeteaseMusicAdapter(MusicPlatformAdapter):
    """网易云音乐平台适配器"""

    @property
    def platform_name(self) -> str:
        return "netease"

    async def search_track(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索网易云音乐歌曲"""
        return []

    async def search_artist(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索网易云音乐艺术家"""
        return []

    async def search_album(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索网易云音乐专辑"""
        return []

    async def search_playlist(
        self, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索网易云音乐播放列表"""
        return []

    async def get_artist_tracks(
        self, artist_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取网易云音乐艺术家的热门歌曲"""
        return []

    async def get_track_details(self, track_id: str) -> Dict[str, Any]:
        """获取网易云音乐歌曲详细信息"""
        return {}

    async def get_artist_details(self, artist_id: str) -> Dict[str, Any]:
        """获取网易云音乐艺术家详细信息"""
        return {}

    async def get_album_details(self, album_id: str) -> Dict[str, Any]:
        """获取网易云音乐专辑详细信息"""
        return {}

    async def get_playlist_details(self, playlist_id: str) -> Dict[str, Any]:
        """获取网易云音乐播放列表详细信息"""
        return {}


# 音乐平台适配器工厂
class MusicPlatformFactory:
    """音乐平台适配器工厂"""

    @staticmethod
    def create_adapter(
        platform_name: str, config: Config, cache_manager: Optional[CacheManager] = None
    ) -> MusicPlatformAdapter:
        """创建音乐平台适配器"""
        adapters = {
            "spotify": SpotifyAdapter,
            "qqmusic": QQMusicAdapter,
            "netease": NeteaseMusicAdapter,
        }

        if platform_name not in adapters:
            raise ValueError(f"不支持的平台: {platform_name}")

        return adapters[platform_name](config, cache_manager)
