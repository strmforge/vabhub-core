"""
VabHub 搜索管理器
基于MoviePilot搜索架构优化的统一搜索系统
支持媒体信息聚合搜索和资源搜索，支持全局过滤规则和优先级规则
"""

import asyncio
from typing import List, Dict, Optional, Any, Union
from enum import Enum
from datetime import datetime
import logging

from .media_scanner import MediaScanner
from .metadata_scraper import MetadataScraper
from .music_manager import MusicManager

logger = logging.getLogger(__name__)


class SearchType(Enum):
    """搜索类型枚举"""
    ALL = "all"
    MOVIE = "movie"
    TV = "tv"
    ANIME = "anime"
    MUSIC = "music"


class SearchSource(Enum):
    """搜索源枚举"""
    TMDB = "tmdb"
    DOUBAN = "douban"
    NETFLIX_TOP10 = "netflix_top10"
    IMDB_DATASETS = "imdb_datasets"
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    LOCAL = "local"


class SearchResult:
    """搜索结果类"""
    
    def __init__(self, 
                 title: str,
                 type: SearchType,
                 source: SearchSource,
                 score: float = 0.0,
                 metadata: Optional[Dict[str, Any]] = None,
                 download_info: Optional[Dict[str, Any]] = None):
        self.title = title
        self.type = type
        self.source = source
        self.score = score
        self.metadata = metadata or {}
        self.download_info = download_info
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "title": self.title,
            "type": self.type.value,
            "source": self.source.value,
            "score": self.score,
            "metadata": self.metadata,
            "download_info": self.download_info,
            "timestamp": self.timestamp.isoformat()
        }


class SearchManager:
    """搜索管理器"""
    
    def __init__(self):
        self.media_scanner = MediaScanner()
        self.metadata_scraper = MetadataScraper()
        self.music_manager = MusicManager()
        self.search_history: List[Dict[str, Any]] = []
    
    async def search(self,
                     query: str,
                     search_type: SearchType = SearchType.ALL,
                     sources: List[SearchSource] = None,
                     limit: int = 50,
                     offset: int = 0) -> List[SearchResult]:
        """统一搜索入口"""
        logger.info(f"开始搜索: {query}, 类型: {search_type.value}, 源: {sources}")
        
        # 记录搜索历史
        self._add_to_history(query, search_type, sources)
        
        # 根据搜索类型和源分发搜索任务
        search_tasks = []
        
        if sources is None:
            sources = self._get_default_sources(search_type)
        
        for source in sources:
            task = self._search_by_source(query, source, search_type, limit)
            search_tasks.append(task)
        
        # 并行执行搜索任务
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 合并和排序结果
        all_results = []
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
        
        # 按相关性排序
        sorted_results = self._sort_results(all_results, query)
        
        # 分页
        paginated_results = sorted_results[offset:offset + limit]
        
        logger.info(f"搜索完成: {query}, 找到 {len(paginated_results)} 个结果")
        return paginated_results
    
    async def search_by_id(self,
                          media_id: str,
                          source: SearchSource = SearchSource.TMDB,
                          search_type: SearchType = SearchType.ALL) -> Optional[SearchResult]:
        """根据ID精确搜索"""
        try:
            if media_id.startswith("tmdb:"):
                tmdb_id = media_id.replace("tmdb:", "")
                metadata = await self.metadata_scraper.scrape_metadata_by_id(tmdb_id, "tmdb")
                if metadata:
                    return SearchResult(
                        title=metadata.get("title", ""),
                        type=SearchType(metadata.get("type", "movie")),
                        source=SearchSource.TMDB,
                        metadata=metadata
                    )
            
            elif media_id.startswith("douban:"):
                douban_id = media_id.replace("douban:", "")
                metadata = await self.metadata_scraper.scrape_metadata_by_id(douban_id, "douban")
                if metadata:
                    return SearchResult(
                        title=metadata.get("title", ""),
                        type=SearchType(metadata.get("type", "movie")),
                        source=SearchSource.DOUBAN,
                        metadata=metadata
                    )
            
            elif media_id.startswith("qq_music:"):
                music_id = media_id.replace("qq_music:", "")
                metadata = await self.music_manager.get_music_metadata(music_id, "qq_music")
                if metadata:
                    return SearchResult(
                        title=metadata.get("title", ""),
                        type=SearchType.MUSIC,
                        source=SearchSource.QQ_MUSIC,
                        metadata=metadata
                    )
            
            elif media_id.startswith("netease:"):
                music_id = media_id.replace("netease:", "")
                metadata = await self.music_manager.get_music_metadata(music_id, "netease")
                if metadata:
                    return SearchResult(
                        title=metadata.get("title", ""),
                        type=SearchType.MUSIC,
                        source=SearchSource.NETEASE,
                        metadata=metadata
                    )
                    
        except Exception as e:
            logger.error(f"根据ID搜索失败: {e}")
        
        return None
    
    async def search_local(self,
                          query: str,
                          search_type: SearchType = SearchType.ALL,
                          limit: int = 50) -> List[SearchResult]:
        """搜索本地媒体库"""
        try:
            media_items = await self.media_scanner.search_media(query, search_type.value, limit)
            
            results = []
            for item in media_items:
                result = SearchResult(
                    title=item.get("title", ""),
                    type=SearchType(item.get("type", "movie")),
                    source=SearchSource.LOCAL,
                    metadata=item
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"搜索本地媒体库失败: {e}")
            return []
    
    async def search_music(self,
                          query: str,
                          sources: List[SearchSource] = None,
                          limit: int = 20) -> List[SearchResult]:
        """专门搜索影视榜单"""
        if sources is None:
            sources = [SearchSource.NETFLIX_TOP10, SearchSource.IMDB_DATASETS, SearchSource.SPOTIFY]
        
        chart_tasks = []
        for source in sources:
            if source in [SearchSource.NETFLIX_TOP10, SearchSource.IMDB_DATASETS, SearchSource.APPLE_MUSIC]:
                task = self._search_charts_by_source(query, source, limit)
                chart_tasks.append(task)
        
        results = await asyncio.gather(*music_tasks, return_exceptions=True)
        
        all_music_results = []
        for result in results:
            if isinstance(result, list):
                all_music_results.extend(result)
        
        sorted_results = self._sort_results(all_music_results, query)
        
        return sorted_results[:limit]
    
    async def get_search_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """获取搜索建议"""
        suggestions = []
        
        # 从搜索历史中获取建议
        for history in self.search_history:
            if history["query"].lower().startswith(query.lower()):
                suggestions.append(history["query"])
        
        # 从本地媒体库获取建议
        local_results = await self.search_local(query, SearchType.ALL, 5)
        for result in local_results:
            suggestions.append(result.title)
        
        # 去重并限制数量
        unique_suggestions = list(set(suggestions))
        return unique_suggestions[:limit]
    
    def get_search_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        return self.search_history[:limit]
    
    def clear_search_history(self):
        """清空搜索历史"""
        self.search_history.clear()
    
    async def _search_by_source(self, 
                               query: str, 
                               source: SearchSource,
                               search_type: SearchType,
                               limit: int) -> List[SearchResult]:
        """根据源进行搜索"""
        try:
            if source == SearchSource.LOCAL:
                return await self.search_local(query, search_type, limit)
            
            elif source in [SearchSource.TMDB, SearchSource.DOUBAN]:
                return await self._search_media_by_source(query, source, search_type, limit)
            
            elif source in [SearchSource.NETFLIX_TOP10, SearchSource.IMDB_DATASETS, SearchSource.APPLE_MUSIC]:
                return await self._search_charts_by_source(query, source, limit)
            
            else:
                return []
                
        except Exception as e:
            logger.error(f"搜索源 {source.value} 失败: {e}")
            return []
    
    async def _search_media_by_source(self,
                                    query: str,
                                    source: SearchSource,
                                    search_type: SearchType,
                                    limit: int) -> List[SearchResult]:
        """搜索影视媒体"""
        try:
            if source == SearchSource.TMDB:
                results = await self.metadata_scraper.search_tmdb(query, search_type.value, limit)
            elif source == SearchSource.DOUBAN:
                results = await self.metadata_scraper.search_douban(query, search_type.value, limit)
            else:
                return []
            
            search_results = []
            for item in results:
                result = SearchResult(
                    title=item.get("title", ""),
                    type=SearchType(item.get("type", "movie")),
                    source=source,
                    metadata=item
                )
                search_results.append(result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"搜索影视媒体失败: {e}")
            return []
    
    async def _search_music_by_source(self,
                                     query: str,
                                     source: SearchSource,
                                     limit: int) -> List[SearchResult]:
        """搜索音乐"""
        try:
            if source == SearchSource.NETFLIX_TOP10:
                results = await self.charts_manager.search_charts(query, "netflix_top10", limit)
            elif source == SearchSource.IMDB_DATASETS:
                results = await self.charts_manager.search_charts(query, "imdb_datasets", limit)
            elif source == SearchSource.APPLE_MUSIC:
                results = await self.charts_manager.search_charts(query, "apple_music", limit)
            else:
                return []
            
            search_results = []
            for item in results:
                result = SearchResult(
                    title=item.get("title", ""),
                    type=SearchType.MUSIC,
                    source=source,
                    metadata=item
                )
                search_results.append(result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"搜索音乐失败: {e}")
            return []
    
    def _sort_results(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """按相关性排序结果"""
        def calculate_score(result: SearchResult) -> float:
            # 基础分数
            score = result.score
            
            # 标题匹配度
            title = result.title.lower()
            query_lower = query.lower()
            
            if title == query_lower:
                score += 10.0
            elif title.startswith(query_lower):
                score += 5.0
            elif query_lower in title:
                score += 3.0
            
            # 源优先级
            if result.source == SearchSource.LOCAL:
                score += 2.0
            elif result.source in [SearchSource.TMDB, SearchSource.DOUBAN]:
                score += 1.5
            
            return score
        
        # 计算每个结果的分数
        for result in results:
            result.score = calculate_score(result)
        
        # 按分数降序排序
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    def _get_default_sources(self, search_type: SearchType) -> List[SearchSource]:
        """获取默认搜索源"""
        if search_type == SearchType.MUSIC:
            return [SearchSource.QQ_MUSIC, SearchSource.NETEASE, SearchSource.LOCAL]
        elif search_type == SearchType.ALL:
            return [SearchSource.LOCAL, SearchSource.TMDB, SearchSource.QQ_MUSIC]
        else:
            return [SearchSource.LOCAL, SearchSource.TMDB, SearchSource.DOUBAN]
    
    def _add_to_history(self, query: str, search_type: SearchType, sources: List[SearchSource]):
        """添加到搜索历史"""
        history_entry = {
            "query": query,
            "type": search_type.value,
            "sources": [source.value for source in sources] if sources else [],
            "timestamp": datetime.now().isoformat()
        }
        
        # 去重
        for i, entry in enumerate(self.search_history):
            if entry["query"] == query and entry["type"] == search_type.value:
                self.search_history.pop(i)
                break
        
        # 添加到历史开头
        self.search_history.insert(0, history_entry)
        
        # 限制历史记录数量
        if len(self.search_history) > 100:
            self.search_history = self.search_history[:100]