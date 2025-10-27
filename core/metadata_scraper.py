"""
元数据刮削器
集成NASTool的元数据获取精华功能
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MediaMetadata:
    """媒体元数据数据类"""
    title: str
    original_title: Optional[str]
    year: Optional[int]
    media_type: str  # movie, tv, anime
    genres: List[str]
    countries: List[str]
    languages: List[str]
    rating: Optional[float]
    duration: Optional[int]
    description: Optional[str]
    poster_url: Optional[str]
    backdrop_url: Optional[str]
    cast: List[Dict[str, str]]
    directors: List[str]
    writers: List[str]
    release_date: Optional[str]
    imdb_id: Optional[str]
    tmdb_id: Optional[str]
    douban_id: Optional[str]


class MetadataScraper:
    """元数据刮削器"""
    
    def __init__(self):
        self.sources = {
            "tmdb": {
                "name": "The Movie Database",
                "api_key": None,
                "base_url": "https://api.themoviedb.org/3",
                "enabled": True
            },
            "douban": {
                "name": "豆瓣",
                "api_key": None,
                "base_url": "https://api.douban.com/v2",
                "enabled": True
            },
            "omdb": {
                "name": "OMDb API",
                "api_key": None,
                "base_url": "http://www.omdbapi.com",
                "enabled": True
            }
        }
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """初始化刮削器"""
        logger.info("初始化元数据刮削器")
        self.session = aiohttp.ClientSession()
        
    async def close(self):
        """关闭刮削器"""
        if self.session:
            await self.session.close()
            
    def set_api_key(self, source: str, api_key: str):
        """设置API密钥"""
        if source in self.sources:
            self.sources[source]["api_key"] = api_key
            logger.info(f"设置 {source} API密钥")
            
    def enable_source(self, source: str, enabled: bool = True):
        """启用/禁用数据源"""
        if source in self.sources:
            self.sources[source]["enabled"] = enabled
            status = "启用" if enabled else "禁用"
            logger.info(f"{status} {source} 数据源")
            
    async def search_media(self, query: str, media_type: str = "movie", 
                          year: Optional[int] = None) -> List[Dict[str, Any]]:
        """搜索媒体"""
        results = []
        
        # 并行搜索多个数据源
        tasks = []
        for source_name, source_config in self.sources.items():
            if source_config["enabled"] and source_config["api_key"]:
                if source_name == "tmdb":
                    tasks.append(self._search_tmdb(query, media_type, year))
                elif source_name == "douban":
                    tasks.append(self._search_douban(query, media_type, year))
                elif source_name == "omdb":
                    tasks.append(self._search_omdb(query, media_type, year))
                    
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in search_results:
                if isinstance(result, Exception):
                    logger.error(f"搜索失败: {str(result)}")
                    continue
                if result:
                    results.extend(result)
                    
        # 去重和排序
        results = self._deduplicate_and_sort_results(results)
        
        return results
        
    async def get_media_details(self, source: str, media_id: str, 
                               media_type: str = "movie") -> Optional[MediaMetadata]:
        """获取媒体详细信息"""
        try:
            if source == "tmdb":
                return await self._get_tmdb_details(media_id, media_type)
            elif source == "douban":
                return await self._get_douban_details(media_id, media_type)
            elif source == "omdb":
                return await self._get_omdb_details(media_id)
            else:
                logger.error(f"不支持的数据源: {source}")
                return None
                
        except Exception as e:
            logger.error(f"获取媒体详情失败: {str(e)}")
            return None
            
    async def _search_tmdb(self, query: str, media_type: str, year: Optional[int]) -> List[Dict[str, Any]]:
        """搜索TMDB"""
        if not self.session:
            return []
            
        try:
            params = {
                "api_key": self.sources["tmdb"]["api_key"],
                "query": query,
                "language": "zh-CN"
            }
            
            if year:
                params["year"] = year
                
            if media_type == "movie":
                url = f"{self.sources['tmdb']['base_url']}/search/movie"
            elif media_type == "tv":
                url = f"{self.sources['tmdb']['base_url']}/search/tv"
            else:
                url = f"{self.sources['tmdb']['base_url']}/search/multi"
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    
                    formatted_results = []
                    for item in results:
                        formatted_item = {
                            "source": "tmdb",
                            "id": str(item.get("id", "")),
                            "title": item.get("title") or item.get("name", ""),
                            "original_title": item.get("original_title") or item.get("original_name", ""),
                            "year": self._extract_year(item.get("release_date") or item.get("first_air_date")),
                            "media_type": media_type,
                            "poster_url": f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else None,
                            "rating": item.get("vote_average"),
                            "overview": item.get("overview", "")
                        }
                        formatted_results.append(formatted_item)
                        
                    return formatted_results
                else:
                    logger.error(f"TMDB搜索失败: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"TMDB搜索异常: {str(e)}")
            return []
            
    async def _search_douban(self, query: str, media_type: str, year: Optional[int]) -> List[Dict[str, Any]]:
        """搜索豆瓣"""
        if not self.session:
            return []
            
        try:
            # 豆瓣API需要特定的搜索格式
            search_type = "movie" if media_type == "movie" else "tv"
            url = f"{self.sources['douban']['base_url']}/{search_type}/search"
            
            params = {
                "q": query,
                "apikey": self.sources["douban"]["api_key"]
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("subjects", [])
                    
                    formatted_results = []
                    for item in results:
                        formatted_item = {
                            "source": "douban",
                            "id": item.get("id", ""),
                            "title": item.get("title", ""),
                            "original_title": item.get("original_title", ""),
                            "year": item.get("year"),
                            "media_type": media_type,
                            "poster_url": item.get("images", {}).get("medium"),
                            "rating": item.get("rating", {}).get("average"),
                            "genres": item.get("genres", []),
                            "casts": [cast["name"] for cast in item.get("casts", [])[:3]]
                        }
                        formatted_results.append(formatted_item)
                        
                    return formatted_results
                else:
                    logger.error(f"豆瓣搜索失败: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"豆瓣搜索异常: {str(e)}")
            return []
            
    async def _search_omdb(self, query: str, media_type: str, year: Optional[int]) -> List[Dict[str, Any]]:
        """搜索OMDb"""
        if not self.session:
            return []
            
        try:
            params = {
                "apikey": self.sources["omdb"]["api_key"],
                "s": query,
                "type": "movie" if media_type == "movie" else "series"
            }
            
            if year:
                params["y"] = year
                
            url = self.sources["omdb"]["base_url"]
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("Search", [])
                    
                    formatted_results = []
                    for item in results:
                        formatted_item = {
                            "source": "omdb",
                            "id": item.get("imdbID", ""),
                            "title": item.get("Title", ""),
                            "year": int(item.get("Year", "0").split("-")[0]) if item.get("Year") else None,
                            "media_type": media_type,
                            "poster_url": item.get("Poster"),
                            "type": item.get("Type", "")
                        }
                        formatted_results.append(formatted_item)
                        
                    return formatted_results
                else:
                    logger.error(f"OMDb搜索失败: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"OMDb搜索异常: {str(e)}")
            return []
            
    async def _get_tmdb_details(self, media_id: str, media_type: str) -> Optional[MediaMetadata]:
        """获取TMDB详细信息"""
        if not self.session:
            return None
            
        try:
            url = f"{self.sources['tmdb']['base_url']}/{media_type}/{media_id}"
            params = {
                "api_key": self.sources["tmdb"]["api_key"],
                "language": "zh-CN",
                "append_to_response": "credits"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 提取演员信息
                    cast = []
                    credits = data.get("credits", {})
                    for person in credits.get("cast", [])[:10]:  # 前10个演员
                        cast.append({
                            "name": person.get("name", ""),
                            "character": person.get("character", ""),
                            "profile_path": f"https://image.tmdb.org/t/p/w185{person['profile_path']}" if person.get("profile_path") else None
                        })
                    
                    return MediaMetadata(
                        title=data.get("title") or data.get("name", ""),
                        original_title=data.get("original_title") or data.get("original_name", ""),
                        year=self._extract_year(data.get("release_date") or data.get("first_air_date")),
                        media_type=media_type,
                        genres=[genre["name"] for genre in data.get("genres", [])],
                        countries=[country["name"] for country in data.get("production_countries", [])],
                        languages=[lang["name"] for lang in data.get("spoken_languages", [])],
                        rating=data.get("vote_average"),
                        duration=data.get("runtime") or data.get("episode_run_time", [0])[0] if data.get("episode_run_time") else None,
                        description=data.get("overview", ""),
                        poster_url=f"https://image.tmdb.org/t/p/w500{data['poster_path']}" if data.get("poster_path") else None,
                        backdrop_url=f"https://image.tmdb.org/t/p/w1280{data['backdrop_path']}" if data.get("backdrop_path") else None,
                        cast=cast,
                        directors=[person["name"] for person in credits.get("crew", []) if person.get("job") == "Director"],
                        writers=[person["name"] for person in credits.get("crew", []) if person.get("department") == "Writing"],
                        release_date=data.get("release_date") or data.get("first_air_date"),
                        imdb_id=data.get("imdb_id"),
                        tmdb_id=str(data.get("id", "")),
                        douban_id=None
                    )
                else:
                    logger.error(f"获取TMDB详情失败: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"获取TMDB详情异常: {str(e)}")
            return None
            
    async def _get_douban_details(self, media_id: str, media_type: str) -> Optional[MediaMetadata]:
        """获取豆瓣详细信息"""
        if not self.session:
            return None
            
        try:
            search_type = "movie" if media_type == "movie" else "tv"
            url = f"{self.sources['douban']['base_url']}/{search_type}/subject/{media_id}"
            
            params = {
                "apikey": self.sources["douban"]["api_key"]
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return MediaMetadata(
                        title=data.get("title", ""),
                        original_title=data.get("original_title", ""),
                        year=data.get("year"),
                        media_type=media_type,
                        genres=data.get("genres", []),
                        countries=data.get("countries", []),
                        languages=[],  # 豆瓣API不直接提供语言信息
                        rating=data.get("rating", {}).get("average"),
                        duration=None,  # 需要额外处理
                        description=data.get("summary", ""),
                        poster_url=data.get("images", {}).get("large"),
                        backdrop_url=None,
                        cast=[{"name": cast["name"], "character": ""} for cast in data.get("casts", [])[:10]],
                        directors=[director["name"] for director in data.get("directors", [])],
                        writers=[writer["name"] for writer in data.get("writers", [])],
                        release_date=None,  # 需要额外处理
                        imdb_id=data.get("imdb_id"),
                        tmdb_id=None,
                        douban_id=data.get("id", "")
                    )
                else:
                    logger.error(f"获取豆瓣详情失败: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"获取豆瓣详情异常: {str(e)}")
            return None
            
    async def _get_omdb_details(self, media_id: str) -> Optional[MediaMetadata]:
        """获取OMDb详细信息"""
        if not self.session:
            return None
            
        try:
            params = {
                "apikey": self.sources["omdb"]["api_key"],
                "i": media_id,
                "plot": "full"
            }
            
            url = self.sources["omdb"]["base_url"]
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 解析演员列表
                    cast_list = []
                    if data.get("Actors"):
                        actors = data["Actors"].split(", ")
                        for actor in actors:
                            cast_list.append({"name": actor, "character": ""})
                    
                    return MediaMetadata(
                        title=data.get("Title", ""),
                        original_title=data.get("Title", ""),
                        year=int(data.get("Year", "0").split("-")[0]) if data.get("Year") else None,
                        media_type="movie" if data.get("Type") == "movie" else "tv",
                        genres=data.get("Genre", "").split(", ") if data.get("Genre") else [],
                        countries=data.get("Country", "").split(", ") if data.get("Country") else [],
                        languages=data.get("Language", "").split(", ") if data.get("Language") else [],
                        rating=float(data["imdbRating"]) if data.get("imdbRating") and data["imdbRating"] != "N/A" else None,
                        duration=int(data["Runtime"].split(" ")[0]) if data.get("Runtime") and data["Runtime"] != "N/A" else None,
                        description=data.get("Plot", ""),
                        poster_url=data.get("Poster"),
                        backdrop_url=None,
                        cast=cast_list,
                        directors=data.get("Director", "").split(", ") if data.get("Director") else [],
                        writers=data.get("Writer", "").split(", ") if data.get("Writer") else [],
                        release_date=data.get("Released"),
                        imdb_id=data.get("imdbID"),
                        tmdb_id=None,
                        douban_id=None
                    )
                else:
                    logger.error(f"获取OMDb详情失败: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"获取OMDb详情异常: {str(e)}")
            return None
            
    def _extract_year(self, date_str: Optional[str]) -> Optional[int]:
        """从日期字符串中提取年份"""
        if not date_str:
            return None
            
        try:
            # 假设日期格式为 YYYY-MM-DD
            return int(date_str.split("-")[0])
        except (ValueError, IndexError):
            return None
            
    def _deduplicate_and_sort_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重和排序搜索结果"""
        # 简单的基于标题和年份的去重
        seen = set()
        unique_results = []
        
        for result in results:
            key = (result["title"], result.get("year"))
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
                
        # 按评分排序（评分高的在前）
        unique_results.sort(key=lambda x: x.get("rating", 0) or 0, reverse=True)
        
        return unique_results
        
    def get_status(self) -> Dict[str, Any]:
        """获取刮削器状态"""
        enabled_sources = [name for name, config in self.sources.items() if config["enabled"]]
        configured_sources = [name for name, config in self.sources.items() if config["api_key"]]
        
        return {
            "status": "running" if self.session else "stopped",
            "enabled_sources": enabled_sources,
            "configured_sources": configured_sources,
            "total_sources": len(self.sources)
        }