"""
元数据管理器 - 基于MoviePilot参考实现
支持TMDb、豆瓣等多数据源，统一实体模型
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urljoin

import aiohttp
from pydantic import BaseModel, Field


class MediaType:
    """媒体类型枚举"""

    MOVIE = "movie"
    TV_SHOW = "tv"
    SEASON = "season"
    EPISODE = "episode"


class MediaEntity(BaseModel):
    """媒体实体基类"""

    id: str
    type: str
    title: str
    original_title: str = ""
    overview: str = ""
    poster: str = ""
    backdrop: str = ""
    release_date: Optional[datetime] = None
    genres: List[str] = []
    rating: float = 0.0
    vote_count: int = 0
    runtime: int = 0

    # 地区化信息
    language: str = "zh-CN"
    region: str = "CN"

    # 来源信息
    source: str = ""  # tmdb, douban, etc.
    source_id: str = ""


class Movie(MediaEntity):
    """电影实体"""

    type: str = MediaType.MOVIE
    tagline: str = ""
    budget: int = 0
    revenue: int = 0

    # 制作信息
    production_companies: List[str] = []
    production_countries: List[str] = []
    spoken_languages: List[str] = []


class TVShow(MediaEntity):
    """电视剧实体"""

    type: str = MediaType.TV_SHOW
    first_air_date: Optional[datetime] = None
    last_air_date: Optional[datetime] = None
    status: str = ""  # Returning Series, Ended, etc.
    number_of_seasons: int = 0
    number_of_episodes: int = 0

    # 网络信息
    networks: List[str] = []

    # 季信息
    seasons: List[Any] = []


class Season(BaseModel):
    """季实体"""

    id: str
    tv_show_id: str
    season_number: int
    title: str
    overview: str = ""
    poster: str = ""
    air_date: Optional[datetime] = None
    episode_count: int = 0

    # 剧集列表
    episodes: List[Any] = []


class Episode(BaseModel):
    """剧集实体"""

    id: str
    season_id: str
    tv_show_id: str
    episode_number: int
    title: str
    overview: str = ""
    still: str = ""
    air_date: Optional[datetime] = None
    runtime: int = 0
    rating: float = 0.0


class MetadataProvider(ABC):
    """元数据提供者抽象类"""

    @abstractmethod
    async def search(
        self, query: str, media_type: str = "movie", language: str = "zh-CN"
    ) -> List[MediaEntity]:
        """搜索媒体"""
        pass

    @abstractmethod
    async def get_movie(
        self, movie_id: str, language: str = "zh-CN"
    ) -> Optional[Movie]:
        """获取电影详情"""
        pass

    @abstractmethod
    async def get_tv_show(
        self, tv_id: str, language: str = "zh-CN"
    ) -> Optional[TVShow]:
        """获取电视剧详情"""
        pass

    @abstractmethod
    async def get_season(
        self, tv_id: str, season_number: int, language: str = "zh-CN"
    ) -> Optional[Season]:
        """获取季详情"""
        pass

    @abstractmethod
    async def get_episode(
        self,
        tv_id: str,
        season_number: int,
        episode_number: int,
        language: str = "zh-CN",
    ) -> Optional[Episode]:
        """获取剧集详情"""
        pass


class TMDBProvider(MetadataProvider):
    """TMDb提供者"""

    def __init__(self, api_key: str, base_url: str = "https://api.themoviedb.org/3"):
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送API请求"""
        if params is None:
            params = {}

        params["api_key"] = self.api_key

        session = await self._get_session()
        url = urljoin(self.base_url, endpoint)

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"TMDB API error: {response.status}")
                    return {}
        except Exception as e:
            logging.error(f"TMDB request failed: {e}")
            return {}

    async def search(
        self, query: str, media_type: str = "movie", language: str = "zh-CN"
    ) -> List[MediaEntity]:
        """搜索媒体"""
        endpoint = f"search/{media_type}"
        params = {"query": query, "language": language, "include_adult": False}

        data = await self._request(endpoint, params)
        results = data.get("results", [])

        entities: List[MediaEntity] = []
        for item in results:
            entity: Optional[MediaEntity] = None
            if media_type == MediaType.MOVIE:
                entity = self._parse_movie(item)
            elif media_type == MediaType.TV_SHOW:
                entity = self._parse_tv_show(item)
            else:
                continue

            if entity:
                entities.append(entity)

        return entities

    async def get_movie(
        self, movie_id: str, language: str = "zh-CN"
    ) -> Optional[Movie]:
        """获取电影详情"""
        endpoint = f"movie/{movie_id}"
        params = {"language": language}

        data = await self._request(endpoint, params)
        if not data:
            return None

        return self._parse_movie(data)

    async def get_tv_show(
        self, tv_id: str, language: str = "zh-CN"
    ) -> Optional[TVShow]:
        """获取电视剧详情"""
        endpoint = f"tv/{tv_id}"
        params = {"language": language}

        data = await self._request(endpoint, params)
        if not data:
            return None

        return self._parse_tv_show(data)

    async def get_season(
        self, tv_id: str, season_number: int, language: str = "zh-CN"
    ) -> Optional[Season]:
        """获取季详情"""
        endpoint = f"tv/{tv_id}/season/{season_number}"
        params = {"language": language}

        data = await self._request(endpoint, params)
        if not data:
            return None

        return self._parse_season(data, tv_id)

    async def get_episode(
        self,
        tv_id: str,
        season_number: int,
        episode_number: int,
        language: str = "zh-CN",
    ) -> Optional[Episode]:
        """获取剧集详情"""
        endpoint = f"tv/{tv_id}/season/{season_number}/episode/{episode_number}"
        params = {"language": language}

        data = await self._request(endpoint, params)
        if not data:
            return None

        return self._parse_episode(data, tv_id, season_number)

    def _parse_movie(self, data: Dict[str, Any]) -> Movie:
        """解析电影数据"""
        return Movie(
            id=str(data.get("id", "")),
            title=data.get("title", ""),
            original_title=data.get("original_title", ""),
            overview=data.get("overview", ""),
            poster=self._get_image_url(data.get("poster_path")),
            backdrop=self._get_image_url(data.get("backdrop_path")),
            release_date=self._parse_date(data.get("release_date")),
            genres=[genre["name"] for genre in data.get("genres", [])],
            rating=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0),
            runtime=data.get("runtime", 0),
            tagline=data.get("tagline", ""),
            budget=data.get("budget", 0),
            revenue=data.get("revenue", 0),
            production_companies=[
                company["name"] for company in data.get("production_companies", [])
            ],
            production_countries=[
                country["name"] for country in data.get("production_countries", [])
            ],
            spoken_languages=[
                lang["name"] for lang in data.get("spoken_languages", [])
            ],
            source="tmdb",
            source_id=str(data.get("id", "")),
        )

    def _parse_tv_show(self, data: Dict[str, Any]) -> TVShow:
        """解析电视剧数据"""
        return TVShow(
            id=str(data.get("id", "")),
            title=data.get("name", ""),
            original_title=data.get("original_name", ""),
            overview=data.get("overview", ""),
            poster=self._get_image_url(data.get("poster_path")),
            backdrop=self._get_image_url(data.get("backdrop_path")),
            release_date=self._parse_date(data.get("first_air_date")),
            first_air_date=self._parse_date(data.get("first_air_date")),
            last_air_date=self._parse_date(data.get("last_air_date")),
            genres=[genre["name"] for genre in data.get("genres", [])],
            rating=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0),
            status=data.get("status", ""),
            number_of_seasons=data.get("number_of_seasons", 0),
            number_of_episodes=data.get("number_of_episodes", 0),
            networks=[network["name"] for network in data.get("networks", [])],
            source="tmdb",
            source_id=str(data.get("id", "")),
        )

    def _parse_season(self, data: Dict[str, Any], tv_id: str) -> Season:
        """解析季数据"""
        return Season(
            id=str(data.get("id", "")),
            tv_show_id=tv_id,
            season_number=data.get("season_number", 0),
            title=data.get("name", ""),
            overview=data.get("overview", ""),
            poster=self._get_image_url(data.get("poster_path")),
            air_date=self._parse_date(data.get("air_date")),
            episode_count=data.get("episode_count", 0),
        )

    def _parse_episode(
        self, data: Dict[str, Any], tv_id: str, season_number: int
    ) -> Episode:
        """解析剧集数据"""
        return Episode(
            id=str(data.get("id", "")),
            season_id=str(data.get("season_id", "")),
            tv_show_id=tv_id,
            episode_number=data.get("episode_number", 0),
            title=data.get("name", ""),
            overview=data.get("overview", ""),
            still=self._get_image_url(data.get("still_path")),
            air_date=self._parse_date(data.get("air_date")),
            runtime=data.get("runtime", 0),
            rating=data.get("vote_average", 0.0),
        )

    def _get_image_url(self, path: Optional[str]) -> str:
        """获取图片URL"""
        if not path:
            return ""
        return f"https://image.tmdb.org/t/p/original{path}"

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None


class DoubanProvider(MetadataProvider):
    """豆瓣提供者（占位实现）"""

    def __init__(self):
        # 豆瓣API需要特殊处理，这里先实现占位
        pass

    async def search(
        self, query: str, media_type: str = "movie", language: str = "zh-CN"
    ) -> List[MediaEntity]:
        """搜索媒体"""
        # 豆瓣搜索实现
        return []

    async def get_movie(
        self, movie_id: str, language: str = "zh-CN"
    ) -> Optional[Movie]:
        """获取电影详情"""
        return None

    async def get_tv_show(
        self, tv_id: str, language: str = "zh-CN"
    ) -> Optional[TVShow]:
        """获取电视剧详情"""
        return None

    async def get_season(
        self, tv_id: str, season_number: int, language: str = "zh-CN"
    ) -> Optional[Season]:
        """获取季详情"""
        return None

    async def get_episode(
        self,
        tv_id: str,
        season_number: int,
        episode_number: int,
        language: str = "zh-CN",
    ) -> Optional[Episode]:
        """获取剧集详情"""
        return None


class MetadataManager:
    """元数据管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.providers: Dict[str, MetadataProvider] = {}
        self.priority: List[str] = []
        self.cache_dir: str = config.get("cache_dir", "./cache")

        # 初始化提供者
        self._init_providers(config)

    def _init_providers(self, config: Dict[str, Any]):
        """初始化提供者"""
        # TMDb提供者
        if config.get("tmdb_api_key"):
            self.providers["tmdb"] = TMDBProvider(config["tmdb_api_key"])

        # 豆瓣提供者
        if config.get("douban_enabled", False):
            self.providers["douban"] = DoubanProvider()

        # 设置优先级
        self.priority = config.get("provider_priority", ["tmdb", "douban"])

    async def search(
        self, query: str, media_type: str = "movie", language: str = "zh-CN"
    ) -> List[MediaEntity]:
        """搜索媒体"""
        all_results = []

        for provider_name in self.priority:
            if provider_name in self.providers:
                try:
                    results = await self.providers[provider_name].search(
                        query, media_type, language
                    )
                    all_results.extend(results)
                except Exception as e:
                    logging.error(f"Search failed for provider {provider_name}: {e}")

        # 去重（基于source_id）
        seen_ids = set()
        unique_results = []

        for result in all_results:
            if result.source_id not in seen_ids:
                seen_ids.add(result.source_id)
                unique_results.append(result)

        return unique_results

    async def get_media(
        self, media_type: str, media_id: str, language: str = "zh-CN"
    ) -> Optional[MediaEntity]:
        """获取媒体详情"""
        for provider_name in self.priority:
            if provider_name in self.providers:
                try:
                    result: Optional[MediaEntity] = None
                    if media_type == MediaType.MOVIE:
                        result = await self.providers[provider_name].get_movie(
                            media_id, language
                        )
                    elif media_type == MediaType.TV_SHOW:
                        result = await self.providers[provider_name].get_tv_show(
                            media_id, language
                        )
                    else:
                        continue

                    if result:
                        return result
                except Exception as e:
                    logging.error(f"Get media failed for provider {provider_name}: {e}")

        return None

    async def get_season(
        self, tv_id: str, season_number: int, language: str = "zh-CN"
    ) -> Optional[Season]:
        """获取季详情"""
        for provider_name in self.priority:
            if provider_name in self.providers:
                try:
                    result = await self.providers[provider_name].get_season(
                        tv_id, season_number, language
                    )
                    if result:
                        return result
                except Exception as e:
                    logging.error(
                        f"Get season failed for provider {provider_name}: {e}"
                    )

        return None

    async def get_episode(
        self,
        tv_id: str,
        season_number: int,
        episode_number: int,
        language: str = "zh-CN",
    ) -> Optional[Episode]:
        """获取剧集详情"""
        for provider_name in self.priority:
            if provider_name in self.providers:
                try:
                    result = await self.providers[provider_name].get_episode(
                        tv_id, season_number, episode_number, language
                    )
                    if result:
                        return result
                except Exception as e:
                    logging.error(
                        f"Get episode failed for provider {provider_name}: {e}"
                    )

        return None

    async def close(self):
        """关闭资源"""
        for provider in self.providers.values():
            if hasattr(provider, "session") and provider.session:
                await provider.session.close()
