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
        music_chain = SearchChain("music", SearchPriority.MEDIUM)
        music_chain.add_searcher(self._search_qq_music)
        music_chain.add_searcher(self._search_netease)
        self.search_chains["music"] = music_chain
    
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
    
    async def _search_qq_music(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索QQ音乐"""
        # 这里应该调用QQ音乐API
        # 简化实现
        return []
    
    async def _search_netease(self, query: str, **kwargs) -> List[SearchResult]:
        """搜索网易云音乐"""
        # 这里应该调用网易云音乐API
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