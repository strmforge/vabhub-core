#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版搜索管理器
基于MoviePilot搜索功能全景图，支持媒体信息聚合搜索和资源搜索
支持全局过滤规则、优先级规则和搜索链架构
"""

import asyncio
import re
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
import logging

from .site_manager import site_manager, SiteAccessMode
import structlog

logger = structlog.get_logger()


class SearchMode(Enum):
    """搜索模式"""
    MEDIA_INFO = "media_info"  # 媒体信息搜索
    RESOURCE = "resource"      # 资源搜索
    COMBINED = "combined"      # 组合搜索


class SearchPriority(Enum):
    """搜索优先级"""
    HIGH = "high"      # 高优先级
    MEDIUM = "medium"  # 中优先级
    LOW = "low"        # 低优先级


@dataclass
class SearchFilter:
    """搜索过滤器"""
    name: str
    pattern: str
    action: str  # include, exclude
    priority: SearchPriority
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    type: str  # movie, tv, music, etc.
    source: str
    score: float
    metadata: Dict[str, Any]
    download_info: Optional[Dict[str, Any]] = None
    filtered: bool = False
    filter_reason: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class SearchChain:
    """搜索链"""
    
    def __init__(self, name: str, priority: SearchPriority = SearchPriority.MEDIUM):
        self.name = name
        self.priority = priority
        self.searchers: List[Callable] = []
        self.filters: List[SearchFilter] = []
    
    def add_searcher(self, searcher: Callable):
        """添加搜索器"""
        self.searchers.append(searcher)
    
    def add_filter(self, search_filter: SearchFilter):
        """添加过滤器"""
        self.filters.append(search_filter)
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """执行搜索"""
        results = []
        
        # 并行执行所有搜索器
        search_tasks = [searcher(query, **kwargs) for searcher in self.searchers]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 合并结果
        for result in search_results:
            if isinstance(result, list):
                results.extend(result)
        
        # 应用过滤器
        filtered_results = self._apply_filters(results)
        
        # 排序
        sorted_results = self._sort_results(filtered_results)
        
        return sorted_results
    
    def _apply_filters(self, results: List[SearchResult]) -> List[SearchResult]:
        """应用过滤器"""
        filtered_results = []
        
        for result in results:
            filtered = False
            filter_reason = None
            
            for search_filter in self.filters:
                if not search_filter.enabled:
                    continue
                
                # 检查是否匹配过滤器
                if re.search(search_filter.pattern, result.title, re.IGNORECASE):
                    if search_filter.action == "exclude":
                        filtered = True
                        filter_reason = f"被过滤器 '{search_filter.name}' 排除"
                        break
                    elif search_filter.action == "include":
                        # 包含过滤器，继续检查其他过滤器
                        pass
            
            if filtered:
                result.filtered = True
                result.filter_reason = filter_reason
            
            filtered_results.append(result)
        
        return filtered_results
    
    def _sort_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """排序结果"""
        # 按分数降序排序
        return sorted(results, key=lambda x: x.score, reverse=True)


class EnhancedSearchManager:
    """增强版搜索管理器"""
    
    def __init__(self):
        self.search_chains: Dict[str, SearchChain] = {}
        self.global_filters: List[SearchFilter] = []
        self.search_history: List[Dict[str, Any]] = []
        self._initialize_default_chains()
        self._initialize_default_filters()
    
    def _initialize_default_chains(self):
        """初始化默认搜索链"""
        # 媒体信息搜索链
        media_info_chain = SearchChain("media_info", SearchPriority.HIGH)
        media_info_chain.add_searcher(self._search_tmdb)
        media_info_chain.add_searcher(self._search_douban)
        self.search_chains["media_info"] = media_info_chain
        
        # 资源搜索链
        resource_chain = SearchChain("resource", SearchPriority.MEDIUM)
        resource_chain.add_searcher(self._search_pt_sites)
        resource_chain.add_searcher(self._search_torznab)
        self.search_chains["resource"] = resource_chain
        
        # 音乐搜索链
        charts_chain = SearchChain("charts", SearchPriority.MEDIUM)
        charts_chain.add_searcher(self._search_netflix_top10)
        charts_chain.add_searcher(self._search_imdb_datasets)
        self.search_chains["charts"] = charts_chain
    
    def _initialize_default_filters(self):
        """初始化默认过滤器"""
        # 排除DV/HDR等格式
        self.global_filters.append(SearchFilter(
            name="exclude_dv_hdr",
            pattern=r"(DV|HDR|Dolby Vision)",
            action="exclude",
            priority=SearchPriority.MEDIUM
        ))
        
        # 排除低质量版本
        self.global_filters.append(SearchFilter(
            name="exclude_low_quality",
            pattern=r"(CAM|TS|TC|SCR|DVDSCR)",
            action="exclude",
            priority=SearchPriority.HIGH
        ))
        
        # 包含高质量版本
        self.global_filters.append(SearchFilter(
            name="include_high_quality",
            pattern=r"(REMUX|BluRay|WEB-DL|UHD)",
            action="include",
            priority=SearchPriority.HIGH
        ))
    
    async def search(self, 
                     query: str,
                     search_mode: SearchMode = SearchMode.COMBINED,
                     content_type: str = "all",
                     sources: List[str] = None,
                     filters: List[Dict[str, Any]] = None,
                     limit: int = 50,
                     offset: int = 0) -> List[SearchResult]:
        """增强版搜索入口"""
        logger.info(f"增强搜索: {query}, 模式: {search_mode.value}, 类型: {content_type}")
        
        # 记录搜索历史
        self._add_to_history(query, search_mode, content_type, sources)
        
        # 根据搜索模式选择搜索链
        search_chains = self._select_search_chains(search_mode, content_type)
        
        # 执行搜索链
        all_results = []
        for chain_name, chain in search_chains.items():
            try:
                results = await chain.search(query, content_type=content_type, limit=limit)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"搜索链 {chain_name} 执行失败: {e}")
        
        # 应用全局过滤器
        filtered_results = self._apply_global_filters(all_results)
        
        # 合并和排序结果
        sorted_results = self._sort_results(filtered_results, query)
        
        # 分页
        paginated_results = sorted_results[offset:offset + limit]
        
        logger.info(f"增强搜索完成: {query}, 找到 {len(paginated_results)} 个结果")
        return paginated_results
    
    def _select_search_chains(self, search_mode: SearchMode, content_type: str) -> Dict[str, SearchChain]:
        """选择搜索链"""
        chains = {}
        
        if search_mode == SearchMode.MEDIA_INFO:
            if content_type in ["all", "movie", "tv", "anime"]:
                chains["media_info"] = self.search_chains["media_info"]
        elif search_mode == SearchMode.RESOURCE:
            if content_type in ["all", "movie", "tv", "anime"]:
                chains["resource"] = self.search_chains["resource"]
        elif search_mode == SearchMode.COMBINED:
            if content_type in ["all", "movie", "tv", "anime"]:
                chains["media_info"] = self.search_chains["media_info"]
                chains["resource"] = self.search_chains["resource"]
        
        if content_type in ["all", "music"]:
            chains["music"] = self.search_chains["music"]
        
        return chains
    
    def _apply_global_filters(self, results: List[SearchResult]) -> List[SearchResult]:
        """应用全局过滤器"""
        filtered_results = []
        
        for result in results:
            filtered = False
            filter_reason = None
            
            for search_filter in self.global_filters:
                if not search_filter.enabled:
                    continue
                
                # 检查是否匹配过滤器
                if re.search(search_filter.pattern, result.title, re.IGNORECASE):
                    if search_filter.action == "exclude":
                        filtered = True
                        filter_reason = f"被全局过滤器 '{search_filter.name}' 排除"
                        break
                    elif search_filter.action == "include":
                        # 包含过滤器，继续检查其他过滤器
                        pass
            
            if filtered:
                result.filtered = True
                result.filter_reason = filter_reason
            
            filtered_results.append(result)
        
        return filtered_results
    
    def _sort_results(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """排序结果"""
        # 计算相关性分数
        for result in results:
            result.score = self._calculate_relevance_score(result, query)
        
        # 按分数降序排序
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    def _calculate_relevance_score(self, result: SearchResult, query: str) -> float:
        """计算相关性分数"""
        score = 0.0
        
        # 标题匹配度
        if query.lower() in result.title.lower():
            score += 10.0
        
        # 源优先级
        source_priority = {
            "tmdb": 5.0,
            "douban": 4.0,
            "local": 3.0,
            "netflix_top10": 2.5,
            "imdb_datasets": 2.5
        }
        score += source_priority.get(result.source, 1.0)
        
        # 质量分数
        if result.metadata.get("quality"):
            quality_scores = {
                "REMUX": 3.0,
                "BluRay": 2.5,
                "WEB-DL": 2.0,
                "HDTV": 1.5
            }
            score += quality_scores.get(result.metadata["quality"], 1.0)
        
        return score
    
    def _add_to_history(self, query: str, mode: SearchMode, content_type: str, sources: List[str] = None):
        """添加到搜索历史"""
        history_item = {
            "query": query,
            "mode": mode.value,
            "type": content_type,
            "sources": sources or [],
            "timestamp": datetime.now().isoformat(),
            "result_count": 0  # 将在搜索完成后更新
        }
        
        # 限制历史记录数量
        self.search_history.insert(0, history_item)
        if len(self.search_history) > 100:
            self.search_history = self.search_history[:100]
    
    async def get_search_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """获取搜索建议"""
        # 这里应该实现智能搜索建议算法
        # 简化实现：基于历史记录和热门搜索
        suggestions = []
        
        # 基于历史记录的建议
        for history in self.search_history:
            if query.lower() in history["query"].lower():
                suggestions.append(history["query"])
        
        # 去重和限制数量
        suggestions = list(dict.fromkeys(suggestions))[:limit]
        
        return suggestions
    
    async def get_related_queries(self, query: str, limit: int = 5) -> List[str]:
        """获取相关查询"""
        # 这里应该实现相关查询算法
        # 简化实现：基于内容类型的关键词扩展
        related = []
        
        if "电影" in query or "movie" in query.lower():
            related.extend(["热门电影", "最新电影", "高分电影"])
        elif "电视剧" in query or "tv" in query.lower():
            related.extend(["热门电视剧", "最新剧集", "美剧推荐"])
        elif "音乐" in query or "music" in query.lower():
            related.extend(["热门歌曲", "新歌推荐", "排行榜"])
        
        return related[:limit]
    
    async def get_trending_searches(self, limit: int = 10) -> List[str]:
        """获取热门搜索"""
        # 这里应该实现热门搜索算法
        # 简化实现：返回固定热门搜索
        trending = [
            "阿凡达：水之道", "流浪地球2", "封神第一部",
            "漫长的季节", "狂飙", "三体",
            "周杰伦", "Taylor Swift", "林俊杰"
        ]
        
        return trending[:limit]
    
    async def get_search_history(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        return self.search_history[offset:offset + limit]
    
    async def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门搜索统计"""
        # 这里应该实现热门搜索统计
        # 简化实现：返回固定数据
        popular = [
            {"query": "阿凡达：水之道", "count": 150},
            {"query": "流浪地球2", "count": 120},
            {"query": "漫长的季节", "count": 100},
            {"query": "狂飙", "count": 90},
            {"query": "三体", "count": 80}
        ]
        
        return popular[:limit]
    
    async def delete_search_history(self, query_id: str):
        """删除搜索历史记录"""
        # 简化实现：删除指定查询的历史记录
        self.search_history = [h for h in self.search_history if h["query"] != query_id]
    
    async def clear_search_history(self):
        """清空搜索历史"""
        self.search_history = []
    
    # 搜索器实现（简化版）
    async def _search_tmdb(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索TMDB"""
        # 这里应该实现TMDB API调用
        # 简化实现：返回模拟数据
        return [
            SearchResult(
                title="阿凡达：水之道",
                type="movie",
                source="tmdb",
                score=9.5,
                metadata={"year": 2022, "rating": 7.8, "overview": "潘多拉星球的水下冒险故事..."}
            )
        ]
    
    async def _search_douban(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索豆瓣"""
        # 这里应该实现豆瓣API调用
        return [
            SearchResult(
                title="流浪地球2",
                type="movie",
                source="douban",
                score=9.2,
                metadata={"year": 2023, "rating": 8.3, "overview": "人类带着地球逃离太阳系的壮丽史诗..."}
            )
        ]
    
    async def _search_pt_sites(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索PT站点"""
        # 这里应该实现PT站点搜索
        return [
            SearchResult(
                title="阿凡达：水之道.2022.IMAX.1080p.BluRay.x264",
                type="movie",
                source="pt",
                score=8.5,
                metadata={"quality": "BluRay", "size": "15.2GB", "seeds": 150},
                download_info={"magnet": "magnet:?xt=urn:btih:..."}
            )
        ]
    
    async def _search_torznab(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索Torznab"""
        # 这里应该实现Torznab API调用
        return []
    
    async def _search_qq_music(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索QQ音乐"""
        # 这里应该实现QQ音乐API调用
        return [
            SearchResult(
                title="七里香",
                type="music",
                source="qq_music",
                score=9.0,
                metadata={"artist": "周杰伦", "album": "七里香", "duration": "4:59"}
            )
        ]
    
    async def _search_netease(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索网易云音乐"""
        # 这里应该实现网易云音乐API调用
        return [
            SearchResult(
                title="晴天",
                type="music",
                source="netease",
                score=8.8,
                metadata={"artist": "周杰伦", "album": "叶惠美", "duration": "4:29"}
            )
        ]
            action="include",
            priority=SearchPriority.HIGH
        ))
    
    async def global_search(self, 
                           query: str, 
                           search_mode: SearchMode = SearchMode.COMBINED,
                           chains: List[str] = None,
                           limit: int = 50,
                           offset: int = 0) -> Dict[str, Any]:
        """全局搜索入口（MoviePilot Ctrl/⌘+K 功能）"""
        logger.info(f"全局搜索: {query}, 模式: {search_mode.value}")
        
        # 记录搜索历史
        self._add_to_history(query, search_mode, chains)
        
        # 确定要使用的搜索链
        if chains is None:
            chains = self._get_default_chains(search_mode)
        
        # 并行执行搜索链
        search_tasks = []
        for chain_name in chains:
            if chain_name in self.search_chains:
                chain = self.search_chains[chain_name]
                # 添加全局过滤器
                for global_filter in self.global_filters:
                    chain.add_filter(global_filter)
                search_tasks.append(chain.search(query, limit=limit))
        
        chain_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 合并和排序所有结果
        all_results = []
        for result in chain_results:
            if isinstance(result, list):
                all_results.extend(result)
        
        # 按优先级和分数排序
        sorted_results = self._sort_by_priority_and_score(all_results)
        
        # 分页
        paginated_results = sorted_results[offset:offset + limit]
        
        # 统计信息
        total_results = len(all_results)
        filtered_results = len([r for r in all_results if r.filtered])
        
        return {
            "query": query,
            "mode": search_mode.value,
            "chains": chains,
            "results": [r.to_dict() for r in paginated_results],
            "pagination": {
                "total": total_results,
                "filtered": filtered_results,
                "offset": offset,
                "limit": limit,
                "has_more": offset + limit < total_results
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_default_chains(self, search_mode: SearchMode) -> List[str]:
        """获取默认搜索链"""
        if search_mode == SearchMode.MEDIA_INFO:
            return ["media_info"]
        elif search_mode == SearchMode.RESOURCE:
            return ["resource"]
        elif search_mode == SearchMode.COMBINED:
            return ["media_info", "resource", "music"]
        else:
            return list(self.search_chains.keys())
    
    def _sort_by_priority_and_score(self, results: List[SearchResult]) -> List[SearchResult]:
        """按优先级和分数排序"""
        # 首先按优先级排序，然后按分数排序
        priority_order = {SearchPriority.HIGH: 3, SearchPriority.MEDIUM: 2, SearchPriority.LOW: 1}
        
        def sort_key(result):
            # 获取结果的优先级（这里简化处理，实际应该根据来源确定优先级）
            priority_score = priority_order.get(SearchPriority.MEDIUM, 2)
            return (priority_score, result.score)
        
        return sorted(results, key=sort_key, reverse=True)
    
    def _add_to_history(self, query: str, search_mode: SearchMode, chains: List[str]):
        """添加到搜索历史"""
        history_entry = {
            "query": query,
            "mode": search_mode.value,
            "chains": chains,
            "timestamp": datetime.now().isoformat()
        }
        self.search_history.append(history_entry)
        
        # 保持历史记录数量
        if len(self.search_history) > 100:
            self.search_history = self.search_history[-100:]
    
    async def _search_tmdb(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索TMDB"""
        # 这里应该调用实际的TMDB搜索API
        # 简化实现
        return []
    
    async def _search_douban(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索豆瓣"""
        # 这里应该调用实际的豆瓣搜索API
        # 简化实现
        return []
    
    async def _search_pt_sites(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索PT站点"""
        results = []
        
        # 获取启用的站点
        enabled_sites = site_manager.get_enabled_sites()
        
        for site in enabled_sites:
            try:
                # 根据站点访问模式执行搜索
                if site.access_mode == SiteAccessMode.SPIDER:
                    # 爬虫模式搜索
                    site_results = await self._search_pt_spider(site, query)
                else:
                    # RSS模式搜索
                    site_results = await self._search_pt_rss(site, query)
                
                results.extend(site_results)
                
            except Exception as e:
                logger.error(f"PT站点搜索失败: {site.name}, {e}")
        
        return results
    
    async def _search_pt_spider(self, site, query: str) -> List[SearchResult]:
        """爬虫模式搜索"""
        # 这里应该实现具体的爬虫搜索逻辑
        # 简化实现
        return []
    
    async def _search_pt_rss(self, site, query: str) -> List[SearchResult]:
        """RSS模式搜索"""
        # 这里应该实现具体的RSS搜索逻辑
        # 简化实现
        return []
    
    async def _search_torznab(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索Torznab索引器"""
        # 这里应该调用Torznab API
        # 简化实现
        return []
    
    async def _search_netflix_top10(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索Netflix Top 10"""
        # 这里应该调用Netflix Top 10 API
        # 简化实现
        return []
    
    async def _search_imdb_datasets(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索IMDb Datasets"""
        # 这里应该调用IMDb Datasets API
        # 简化实现
        return []
    
    def add_custom_filter(self, search_filter: SearchFilter):
        """添加自定义过滤器"""
        self.global_filters.append(search_filter)
        logger.info(f"添加自定义过滤器: {search_filter.name}")
    
    def get_search_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        return self.search_history[-limit:]
    
    def clear_search_history(self):
        """清空搜索历史"""
        self.search_history.clear()
        logger.info("搜索历史已清空")


# 全局搜索管理器实例
enhanced_search_manager = EnhancedSearchManager()