"""
TMDB/豆瓣元数据刮削系统
基于现有配置进行增强，支持电影/电视剧/动漫元数据获取
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp
import json

logger = logging.getLogger(__name__)


class MetadataSource(Enum):
    """元数据源枚举"""
    TMDB = "tmdb"
    DOUBAN = "douban"
    IMDB = "imdb"


@dataclass
class MediaMetadata:
    """媒体元数据"""
    title: str
    original_title: Optional[str]
    year: Optional[int]
    type: str  # movie, tv, anime
    genres: List[str]
    overview: Optional[str]
    rating: Optional[float]
    vote_count: Optional[int]
    poster_url: Optional[str]
    backdrop_url: Optional[str]
    duration: Optional[int]  # 分钟
    release_date: Optional[str]
    countries: List[str]
    languages: List[str]
    cast: List[Dict[str, str]]
    directors: List[str]
    writers: List[str]
    source: MetadataSource
    external_ids: Dict[str, str]  # imdb_id, douban_id等


class TMDBScraper:
    """TMDB元数据刮削器"""
    
    def __init__(self, api_key: str, language: str = "zh-CN"):
        self.api_key = api_key
        self.language = language
        self.base_url = "https://api.themoviedb.org/3"
        
    async def search_movie(self, query: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """搜索电影"""
        params = {
            'api_key': self.api_key,
            'language': self.language,
            'query': query,
            'page': 1
        }
        if year:
            params['year'] = year
            
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/search/movie", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('results', [])
                else:
                    logger.error(f"TMDB搜索失败: {response.status}")
                    return []
    
    async def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """获取电影详情"""
        params = {
            'api_key': self.api_key,
            'language': self.language,
            'append_to_response': 'credits,external_ids'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/movie/{movie_id}", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"获取电影详情失败: {response.status}")
                    return None
    
    async def search_tv_show(self, query: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """搜索电视剧"""
        params = {
            'api_key': self.api_key,
            'language': self.language,
            'query': query,
            'page': 1
        }
        if year:
            params['first_air_date_year'] = year
            
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/search/tv", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('results', [])
                else:
                    logger.error(f"TMDB电视剧搜索失败: {response.status}")
                    return []
    
    async def get_tv_show_details(self, tv_id: int) -> Optional[Dict[str, Any]]:
        """获取电视剧详情"""
        params = {
            'api_key': self.api_key,
            'language': self.language,
            'append_to_response': 'credits,external_ids'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/tv/{tv_id}", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"获取电视剧详情失败: {response.status}")
                    return None


class DoubanScraper:
    """豆瓣元数据刮削器"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://api.douban.com/v2"
        
    async def search_movie(self, query: str) -> List[Dict[str, Any]]:
        """搜索电影"""
        params = {
            'q': query,
            'count': 20
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/movie/search", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('subjects', [])
                else:
                    logger.error(f"豆瓣搜索失败: {response.status}")
                    return []
    
    async def get_movie_details(self, douban_id: str) -> Optional[Dict[str, Any]]:
        """获取电影详情"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/movie/subject/{douban_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"获取豆瓣电影详情失败: {response.status}")
                    return None


class MetadataScraper:
    """元数据刮削管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tmdb_scraper = None
        self.douban_scraper = None
        
        # 初始化刮削器
        self._initialize_scrapers()
    
    def _initialize_scrapers(self):
        """初始化刮削器"""
        # TMDB刮削器
        tmdb_api_key = self.config.get('tmdb_api_key')
        if tmdb_api_key and tmdb_api_key != 'your-tmdb-api-key-here':
            self.tmdb_scraper = TMDBScraper(tmdb_api_key)
        
        # 豆瓣刮削器
        douban_api_key = self.config.get('douban_api_key')
        if douban_api_key and douban_api_key != 'your-douban-api-key-here':
            self.douban_scraper = DoubanScraper(douban_api_key)
    
    async def scrape_metadata(self, title: str, year: Optional[int] = None, 
                             media_type: str = "movie") -> Optional[MediaMetadata]:
        """刮削元数据"""
        logger.info(f"开始刮削元数据: {title} ({year})")
        
        # 优先使用TMDB
        if self.tmdb_scraper:
            metadata = await self._scrape_from_tmdb(title, year, media_type)
            if metadata:
                return metadata
        
        # 备用豆瓣
        if self.douban_scraper:
            metadata = await self._scrape_from_douban(title, year, media_type)
            if metadata:
                return metadata
        
        logger.warning(f"无法获取元数据: {title}")
        return None
    
    async def _scrape_from_tmdb(self, title: str, year: Optional[int], 
                              media_type: str) -> Optional[MediaMetadata]:
        """从TMDB刮削元数据"""
        try:
            if media_type == "movie":
                results = await self.tmdb_scraper.search_movie(title, year)
                if results:
                    movie_id = results[0]['id']
                    details = await self.tmdb_scraper.get_movie_details(movie_id)
                    if details:
                        return self._parse_tmdb_movie(details)
            
            elif media_type == "tv_show":
                results = await self.tmdb_scraper.search_tv_show(title, year)
                if results:
                    tv_id = results[0]['id']
                    details = await self.tmdb_scraper.get_tv_show_details(tv_id)
                    if details:
                        return self._parse_tmdb_tv(details)
        
        except Exception as e:
            logger.error(f"TMDB刮削失败: {e}")
        
        return None
    
    async def _scrape_from_douban(self, title: str, year: Optional[int], 
                                 media_type: str) -> Optional[MediaMetadata]:
        """从豆瓣刮削元数据"""
        try:
            if media_type == "movie":
                results = await self.douban_scraper.search_movie(title)
                if results:
                    douban_id = results[0]['id']
                    details = await self.douban_scraper.get_movie_details(douban_id)
                    if details:
                        return self._parse_douban_movie(details)
        
        except Exception as e:
            logger.error(f"豆瓣刮削失败: {e}")
        
        return None
    
    def _parse_tmdb_movie(self, data: Dict[str, Any]) -> MediaMetadata:
        """解析TMDB电影数据"""
        return MediaMetadata(
            title=data.get('title', ''),
            original_title=data.get('original_title', ''),
            year=int(data.get('release_date', '')[:4]) if data.get('release_date') else None,
            type="movie",
            genres=[genre['name'] for genre in data.get('genres', [])],
            overview=data.get('overview', ''),
            rating=data.get('vote_average'),
            vote_count=data.get('vote_count'),
            poster_url=f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}" if data.get('poster_path') else None,
            backdrop_url=f"https://image.tmdb.org/t/p/w1280{data.get('backdrop_path', '')}" if data.get('backdrop_path') else None,
            duration=data.get('runtime'),
            release_date=data.get('release_date'),
            countries=[country['name'] for country in data.get('production_countries', [])],
            languages=[lang['name'] for lang in data.get('spoken_languages', [])],
            cast=[{"name": cast['name'], "character": cast.get('character', '')} 
                  for cast in data.get('credits', {}).get('cast', [])[:10]],
            directors=[crew['name'] for crew in data.get('credits', {}).get('crew', []) 
                      if crew.get('job') == 'Director'],
            writers=[crew['name'] for crew in data.get('credits', {}).get('crew', []) 
                    if crew.get('job') == 'Writer' or crew.get('job') == 'Screenplay'],
            source=MetadataSource.TMDB,
            external_ids={
                'imdb_id': data.get('external_ids', {}).get('imdb_id'),
                'tmdb_id': str(data.get('id'))
            }
        )
    
    def _parse_tmdb_tv(self, data: Dict[str, Any]) -> MediaMetadata:
        """解析TMDB电视剧数据"""
        return MediaMetadata(
            title=data.get('name', ''),
            original_title=data.get('original_name', ''),
            year=int(data.get('first_air_date', '')[:4]) if data.get('first_air_date') else None,
            type="tv_show",
            genres=[genre['name'] for genre in data.get('genres', [])],
            overview=data.get('overview', ''),
            rating=data.get('vote_average'),
            vote_count=data.get('vote_count'),
            poster_url=f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}" if data.get('poster_path') else None,
            backdrop_url=f"https://image.tmdb.org/t/p/w1280{data.get('backdrop_path', '')}" if data.get('backdrop_path') else None,
            duration=data.get('episode_run_time', [0])[0] if data.get('episode_run_time') else None,
            release_date=data.get('first_air_date'),
            countries=[country['name'] for country in data.get('production_countries', [])],
            languages=[lang['name'] for lang in data.get('languages', [])],
            cast=[{"name": cast['name'], "character": cast.get('character', '')} 
                  for cast in data.get('credits', {}).get('cast', [])[:10]],
            directors=[],  # 电视剧通常没有导演
            writers=[],   # 电视剧通常没有编剧
            source=MetadataSource.TMDB,
            external_ids={
                'imdb_id': data.get('external_ids', {}).get('imdb_id'),
                'tmdb_id': str(data.get('id'))
            }
        )
    
    def _parse_douban_movie(self, data: Dict[str, Any]) -> MediaMetadata:
        """解析豆瓣电影数据"""
        return MediaMetadata(
            title=data.get('title', ''),
            original_title=data.get('original_title', ''),
            year=int(data.get('year', 0)) if data.get('year') else None,
            type="movie",
            genres=data.get('genres', []),
            overview=data.get('summary', ''),
            rating=float(data.get('rating', {}).get('average', 0)) if data.get('rating') else None,
            vote_count=data.get('ratings_count', 0),
            poster_url=data.get('images', {}).get('large'),
            backdrop_url=None,  # 豆瓣没有背景图
            duration=None,  # 豆瓣没有时长信息
            release_date=None,  # 豆瓣没有具体发布日期
            countries=[country['name'] for country in data.get('countries', [])],
            languages=[],  # 豆瓣没有语言信息
            cast=[{"name": cast['name'], "character": ''} for cast in data.get('casts', [])[:10]],
            directors=[director['name'] for director in data.get('directors', [])],
            writers=[],  # 豆瓣没有编剧信息
            source=MetadataSource.DOUBAN,
            external_ids={
                'douban_id': str(data.get('id')),
                'imdb_id': data.get('imdb')
            }
        )


# 使用示例
async def main():
    """使用示例"""
    config = {
        'tmdb_api_key': 'your-tmdb-api-key-here',
        'douban_api_key': 'your-douban-api-key-here'
    }
    
    scraper = MetadataScraper(config)
    
    # 刮削电影元数据
    metadata = await scraper.scrape_metadata("复仇者联盟", 2012, "movie")
    if metadata:
        print(f"标题: {metadata.title}")
        print(f"评分: {metadata.rating}")
        print(f"类型: {', '.join(metadata.genres)}")
        print(f"导演: {', '.join(metadata.directors)}")


if __name__ == "__main__":
    asyncio.run(main())