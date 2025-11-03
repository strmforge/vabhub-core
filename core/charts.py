"""
Charts module for VabHub Core - 图表数据服务
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import HTTPException
import httpx
import asyncio
from datetime import datetime, timedelta
from .cache import init_cache_manager, get_cache_manager


class ChartItem(BaseModel):
    """图表数据项"""

    id: str
    title: str
    type: str  # movie, tv, music, anime
    rank: int
    score: Optional[float] = None
    popularity: Optional[int] = None
    release_date: Optional[str] = None
    poster_url: Optional[str] = None
    provider: str  # tmdb, spotify, apple_music, bangumi
    region: str
    time_range: str


class ChartsService:
    """图表数据服务"""

    def __init__(self, config):
        self.config = config
        self.cache_ttl = config.CACHE_TTL

        # 初始化缓存
        self.cache = {}

    async def fetch_charts(
        self,
        source: str,
        region: str = "US",
        time_range: str = "week",
        media_type: str = "all",
        limit: int = 20,
    ) -> List[ChartItem]:
        """获取图表数据"""

        cache_key = f"{source}:{region}:{time_range}:{media_type}:{limit}"

        # 检查缓存
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return cached_data

        # 根据数据源调用不同的provider
        if source == "tmdb":
            charts = await self._fetch_tmdb_charts(
                region, time_range, media_type, limit
            )
        elif source == "spotify":
            charts = await self._fetch_spotify_charts(region, time_range, limit)
        elif source == "apple_music":
            charts = await self._fetch_apple_music_charts(region, time_range, limit)
        elif source == "bangumi":
            charts = await self._fetch_bangumi_charts(time_range, limit)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")

        # 缓存结果
        self.cache[cache_key] = (charts, datetime.now())

        return charts

    async def _fetch_tmdb_charts(
        self, region: str, time_range: str, media_type: str, limit: int
    ) -> List[ChartItem]:
        """获取TMDB图表数据"""
        try:
            if not self.config.TMDB_API_KEY:
                # 如果没有API密钥，返回模拟数据
                return await self._fetch_tmdb_mock_data(
                    region, time_range, media_type, limit
                )

            # 构建TMDB API URL
            base_url = "https://api.themoviedb.org/3"

            # 根据媒体类型和时间范围选择不同的端点
            if media_type == "movie":
                if time_range == "day":
                    endpoint = f"/trending/movie/day"
                elif time_range == "week":
                    endpoint = f"/trending/movie/week"
                else:
                    endpoint = f"/movie/popular"
            elif media_type == "tv":
                if time_range == "day":
                    endpoint = f"/trending/tv/day"
                elif time_range == "week":
                    endpoint = f"/trending/tv/week"
                else:
                    endpoint = f"/tv/popular"
            else:
                # 默认使用电影数据
                endpoint = f"/trending/movie/week"

            url = f"{base_url}{endpoint}?api_key={self.config.TMDB_API_KEY}&language=zh-CN&region={region}&page=1"

            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            # 解析TMDB响应数据
            charts = []
            for i, item in enumerate(data.get("results", [])[:limit]):
                chart_item = ChartItem(
                    id=f"tmdb_{item.get('id', i)}",
                    title=item.get("title") or item.get("name", f"Unknown {i}"),
                    type=media_type,
                    rank=i + 1,
                    score=item.get("vote_average", 0.0),
                    popularity=item.get("popularity", 0),
                    release_date=item.get("release_date")
                    or item.get("first_air_date", ""),
                    poster_url=(
                        f"https://image.tmdb.org/t/p/w500{item.get('poster_path', '')}"
                        if item.get("poster_path")
                        else ""
                    ),
                    provider="tmdb",
                    region=region,
                    time_range=time_range,
                )
                charts.append(chart_item)

            return charts
        except httpx.HTTPError as e:
            # 如果API调用失败，返回模拟数据
            return await self._fetch_tmdb_mock_data(
                region, time_range, media_type, limit
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TMDB API error: {str(e)}")

    async def _fetch_tmdb_mock_data(
        self, region: str, time_range: str, media_type: str, limit: int
    ) -> List[ChartItem]:
        """获取TMDB模拟数据"""
        await asyncio.sleep(0.1)  # 模拟网络延迟

        charts = []
        for i in range(1, limit + 1):
            chart_item = ChartItem(
                id=f"tmdb_{i}",
                title=f"Movie {i}",
                type="movie",
                rank=i,
                score=8.5 - (i * 0.1),
                popularity=1000 - (i * 50),
                release_date="2024-01-01",
                poster_url=f"https://image.tmdb.org/t/p/w500/poster_{i}.jpg",
                provider="tmdb",
                region=region,
                time_range=time_range,
            )
            charts.append(chart_item)

        return charts

    async def _fetch_spotify_charts(
        self, region: str, time_range: str, limit: int
    ) -> List[ChartItem]:
        """获取Spotify图表数据"""
        try:
            # 模拟Spotify API调用
            await asyncio.sleep(0.1)

            charts = []
            for i in range(1, limit + 1):
                chart_item = ChartItem(
                    id=f"spotify_{i}",
                    title=f"Song {i}",
                    type="music",
                    rank=i,
                    score=None,
                    popularity=1000 - (i * 50),
                    release_date="2024-01-01",
                    poster_url=f"https://i.scdn.co/image/album_{i}",
                    provider="spotify",
                    region=region,
                    time_range=time_range,
                )
                charts.append(chart_item)

            return charts
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Spotify API error: {str(e)}")

    async def _fetch_apple_music_charts(
        self, region: str, time_range: str, limit: int
    ) -> List[ChartItem]:
        """获取Apple Music图表数据"""
        try:
            # 模拟Apple Music API调用
            await asyncio.sleep(0.1)

            charts = []
            for i in range(1, limit + 1):
                chart_item = ChartItem(
                    id=f"apple_{i}",
                    title=f"Apple Song {i}",
                    type="music",
                    rank=i,
                    score=None,
                    popularity=800 - (i * 40),
                    release_date="2024-01-01",
                    poster_url=f"https://is1-ssl.mzstatic.com/image/album_{i}",
                    provider="apple_music",
                    region=region,
                    time_range=time_range,
                )
                charts.append(chart_item)

            return charts
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Apple Music API error: {str(e)}"
            )

    async def _fetch_bangumi_charts(
        self, time_range: str, limit: int
    ) -> List[ChartItem]:
        """获取Bangumi图表数据"""
        try:
            # 模拟Bangumi API调用
            await asyncio.sleep(0.1)

            charts = []
            for i in range(1, limit + 1):
                chart_item = ChartItem(
                    id=f"bangumi_{i}",
                    title=f"Anime {i}",
                    type="anime",
                    rank=i,
                    score=8.0 - (i * 0.1),
                    popularity=500 - (i * 25),
                    release_date="2024-01-01",
                    poster_url=f"https://bangumi.tv/img/cover/{i}.jpg",
                    provider="bangumi",
                    region="JP",
                    time_range=time_range,
                )
                charts.append(chart_item)

            return charts
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Bangumi API error: {str(e)}")


# 全局服务实例（需要配置初始化）
# charts_service = ChartsService(config)
