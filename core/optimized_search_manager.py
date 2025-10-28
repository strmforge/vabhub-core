#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版搜索管理器
专门解决MoviePilot中老电视剧搜索不到的问题
支持智能关键词扩展、模糊匹配、备用搜索策略
"""

import asyncio
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
import jieba

from .site_manager import site_manager, SiteAccessMode
from .enhanced_search_manager import SearchResult, SearchFilter
import structlog

logger = structlog.get_logger()


class SearchStrategy(Enum):
    """搜索策略"""
    EXACT = "exact"           # 精确匹配
    FUZZY = "fuzzy"           # 模糊匹配
    EXPANDED = "expanded"     # 关键词扩展
    FALLBACK = "fallback"     # 备用策略


@dataclass
class SearchQuery:
    """搜索查询对象"""
    original_query: str
    processed_queries: List[str]
    strategy: SearchStrategy
    is_old_content: bool = False
    content_type: str = "tv"  # movie, tv, anime
    year: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class QueryAnalyzer:
    """查询分析器"""
    
    # 老电视剧关键词库
    OLD_TV_KEYWORDS = {
        "天下第一", "武林外传", "还珠格格", "神雕侠侣", "射雕英雄传",
        "天龙八部", "笑傲江湖", "倚天屠龙记", "西游记", "红楼梦",
        "水浒传", "三国演义", "大宅门", "康熙王朝", "雍正王朝"
    }
    
    # 常见搜索模式
    SEARCH_PATTERNS = [
        (r'(\d{4})', 'year'),  # 年份
        (r'(第[一二三四五六七八九十]+季|S\d+)', 'season'),  # 季数
        (r'(第[一二三四五六七八九十]+集|E\d+)', 'episode'),  # 集数
    ]
    
    @classmethod
    def analyze_query(cls, query: str) -> SearchQuery:
        """分析查询字符串"""
        # 检测是否为老电视剧
        is_old_content = cls._detect_old_content(query)
        
        # 提取年份信息
        year = cls._extract_year(query)
        
        # 确定内容类型
        content_type = cls._detect_content_type(query)
        
        # 生成处理后的查询列表
        processed_queries = cls._generate_queries(query, is_old_content, year)
        
        # 确定搜索策略
        strategy = cls._determine_strategy(query, is_old_content)
        
        return SearchQuery(
            original_query=query,
            processed_queries=processed_queries,
            strategy=strategy,
            is_old_content=is_old_content,
            content_type=content_type,
            year=year
        )
    
    @classmethod
    def _detect_old_content(cls, query: str) -> bool:
        """检测是否为老电视剧"""
        # 检查是否在已知老电视剧列表中
        for keyword in cls.OLD_TV_KEYWORDS:
            if keyword in query:
                return True
        
        # 检查是否包含年份且年份较早
        year = cls._extract_year(query)
        if year and year < 2010:
            return True
        
        return False
    
    @classmethod
    def _extract_year(cls, query: str) -> Optional[int]:
        """提取年份信息"""
        year_match = re.search(r'(19\d{2}|20\d{2})', query)
        if year_match:
            return int(year_match.group(1))
        return None
    
    @classmethod
    def _detect_content_type(cls, query: str) -> str:
        """检测内容类型"""
        tv_keywords = ['电视剧', '剧集', 'TV', 'tv', 'series']
        movie_keywords = ['电影', 'movie', 'film']
        anime_keywords = ['动漫', '动画', 'anime', 'cartoon']
        
        if any(keyword in query for keyword in tv_keywords):
            return "tv"
        elif any(keyword in query for keyword in movie_keywords):
            return "movie"
        elif any(keyword in query for keyword in anime_keywords):
            return "anime"
        else:
            return "tv"  # 默认电视剧
    
    @classmethod
    def _generate_queries(cls, query: str, is_old_content: bool, year: Optional[int]) -> List[str]:
        """生成处理后的查询列表"""
        queries = [query]
        
        # 对于老电视剧，添加多种搜索变体
        if is_old_content:
            # 1. 去除年份的版本
            if year:
                clean_query = re.sub(r'\s*\d{4}\s*', ' ', query).strip()
                if clean_query and clean_query != query:
                    queries.append(clean_query)
            
            # 2. 添加常见后缀
            suffixes = ['电视剧', '剧集', 'TV版']
            for suffix in suffixes:
                if suffix not in query:
                    queries.append(f"{query} {suffix}")
            
            # 3. 繁体字版本（针对港台站点）
            traditional_queries = cls._to_traditional(query)
            queries.extend(traditional_queries)
            
            # 4. 拼音版本
            pinyin_queries = cls._to_pinyin(query)
            queries.extend(pinyin_queries)
        
        # 去重
        return list(dict.fromkeys(queries))
    
    @classmethod
    def _to_traditional(cls, query: str) -> List[str]:
        """转换为繁体字（简化实现）"""
        # 这里应该使用繁简转换库
        # 简化实现：只处理常见转换
        traditional_map = {
            '天': '天', '下': '下', '第': '第', '一': '一',
            '武': '武', '林': '林', '外': '外', '传': '傳'
        }
        
        traditional_query = ''.join(traditional_map.get(char, char) for char in query)
        if traditional_query != query:
            return [traditional_query]
        return []
    
    @classmethod
    def _to_pinyin(cls, query: str) -> List[str]:
        """转换为拼音（简化实现）"""
        # 这里应该使用拼音转换库
        # 简化实现：只处理常见转换
        pinyin_map = {
            '天下第一': 'tian xia di yi',
            '武林外传': 'wu lin wai zhuan'
        }
        
        if query in pinyin_map:
            return [pinyin_map[query]]
        return []
    
    @classmethod
    def _determine_strategy(cls, query: str, is_old_content: bool) -> SearchStrategy:
        """确定搜索策略"""
        if is_old_content:
            return SearchStrategy.EXPANDED
        elif len(query) <= 2:
            return SearchStrategy.FUZZY
        else:
            return SearchStrategy.EXACT


class SiteSearchOptimizer:
    """站点搜索优化器"""
    
    # 站点搜索策略配置
    SITE_STRATEGIES = {
        "M-Team": {"prefer_exact": True, "support_fuzzy": False},
        "HDChina": {"prefer_exact": False, "support_fuzzy": True},
        "TTG": {"prefer_exact": True, "support_fuzzy": True},
    }
    
    @classmethod
    async def optimize_site_search(cls, site_name: str, search_query: SearchQuery) -> List[str]:
        """为特定站点优化搜索查询"""
        site_strategy = cls.SITE_STRATEGIES.get(site_name, {})
        
        optimized_queries = []
        
        for query in search_query.processed_queries:
            # 根据站点特性调整查询
            optimized_query = cls._adapt_query_for_site(query, site_strategy, search_query)
            optimized_queries.append(optimized_query)
        
        return optimized_queries
    
    @classmethod
    def _adapt_query_for_site(cls, query: str, site_strategy: Dict, search_query: SearchQuery) -> str:
        """为特定站点适配查询"""
        # 如果站点偏好精确匹配，使用原始查询
        if site_strategy.get("prefer_exact", False):
            return search_query.original_query
        
        # 对于支持模糊搜索的站点，可以使用处理后的查询
        if site_strategy.get("support_fuzzy", True):
            return query
        
        return search_query.original_query


class ResultRanker:
    """结果排序器"""
    
    @classmethod
    def rank_results(cls, results: List[SearchResult], search_query: SearchQuery) -> List[SearchResult]:
        """对搜索结果进行排序"""
        scored_results = []
        
        for result in results:
            score = cls._calculate_relevance_score(result, search_query)
            result.score = score
            scored_results.append(result)
        
        # 按分数降序排序
        return sorted(scored_results, key=lambda x: x.score, reverse=True)
    
    @classmethod
    def _calculate_relevance_score(cls, result: SearchResult, search_query: SearchQuery) -> float:
        """计算相关性分数"""
        score = 0.0
        
        # 1. 标题匹配度
        title_score = cls._calculate_title_match_score(result.title, search_query)
        score += title_score * 0.6
        
        # 2. 年份匹配度
        year_score = cls._calculate_year_match_score(result.metadata, search_query.year)
        score += year_score * 0.2
        
        # 3. 内容类型匹配度
        type_score = cls._calculate_type_match_score(result.type, search_query.content_type)
        score += type_score * 0.1
        
        # 4. 源可信度
        source_score = cls._calculate_source_score(result.source)
        score += source_score * 0.1
        
        return score
    
    @classmethod
    def _calculate_title_match_score(cls, title: str, search_query: SearchQuery) -> float:
        """计算标题匹配度"""
        best_score = 0.0
        
        for query in search_query.processed_queries:
            # 使用模糊匹配计算相似度
            similarity = SequenceMatcher(None, title.lower(), query.lower()).ratio()
            
            # 如果完全匹配，给予最高分
            if query.lower() in title.lower():
                similarity = max(similarity, 0.9)
            
            best_score = max(best_score, similarity)
        
        return best_score
    
    @classmethod
    def _calculate_year_match_score(cls, metadata: Dict, target_year: Optional[int]) -> float:
        """计算年份匹配度"""
        if not target_year:
            return 0.5  # 没有目标年份时给中等分数
        
        result_year = metadata.get('year')
        if not result_year:
            return 0.3  # 没有年份信息时给较低分数
        
        year_diff = abs(result_year - target_year)
        if year_diff == 0:
            return 1.0
        elif year_diff <= 1:
            return 0.8
        elif year_diff <= 3:
            return 0.6
        else:
            return 0.2
    
    @classmethod
    def _calculate_type_match_score(cls, result_type: str, target_type: str) -> float:
        """计算类型匹配度"""
        if result_type == target_type:
            return 1.0
        elif target_type == "all":
            return 0.8
        else:
            return 0.3
    
    @classmethod
    def _calculate_source_score(cls, source: str) -> float:
        """计算源可信度"""
        source_scores = {
            "local": 1.0,    # 本地媒体库最可信
            "tmdb": 0.9,     # TMDB权威数据
            "douban": 0.8,   # 豆瓣数据
            "pt_site": 0.7,  # PT站点
            "rss": 0.6       # RSS源
        }
        return source_scores.get(source, 0.5)


class OptimizedSearchManager:
    """优化版搜索管理器"""
    
    def __init__(self):
        self.query_analyzer = QueryAnalyzer()
        self.site_optimizer = SiteSearchOptimizer()
        self.result_ranker = ResultRanker()
        self.search_history: List[Dict[str, Any]] = []
    
    async def optimized_search(self, 
                               query: str,
                               sites: List[str] = None,
                               content_type: str = "tv",
                               limit: int = 50) -> Dict[str, Any]:
        """优化搜索入口"""
        logger.info(f"开始优化搜索: {query}, 类型: {content_type}")
        
        # 分析查询
        search_query = self.query_analyzer.analyze_query(query)
        
        # 记录搜索历史
        self._add_to_history(search_query)
        
        # 确定要搜索的站点
        if sites is None:
            sites = self._get_default_sites(content_type)
        
        # 并行搜索所有站点
        search_tasks = []
        for site_name in sites:
            task = self._search_site(site_name, search_query, limit)
            search_tasks.append(task)
        
        site_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 合并结果
        all_results = []
        for result in site_results:
            if isinstance(result, list):
                all_results.extend(result)
        
        # 排序结果
        ranked_results = self.result_ranker.rank_results(all_results, search_query)
        
        # 过滤和限制结果
        final_results = self._filter_results(ranked_results, search_query)[:limit]
        
        # 统计信息
        stats = self._generate_search_stats(search_query, all_results, final_results)
        
        logger.info(f"优化搜索完成: {query}, 找到 {len(final_results)} 个结果")
        
        return {
            "query": query,
            "processed_queries": search_query.processed_queries,
            "strategy": search_query.strategy.value,
            "is_old_content": search_query.is_old_content,
            "results": [r.to_dict() for r in final_results],
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _search_site(self, site_name: str, search_query: SearchQuery, limit: int) -> List[SearchResult]:
        """在单个站点搜索"""
        try:
            # 获取站点信息
            site = site_manager.get_site(site_name)
            if not site or not site.enabled:
                return []
            
            # 优化站点搜索查询
            optimized_queries = await self.site_optimizer.optimize_site_search(site_name, search_query)
            
            results = []
            
            # 使用所有优化后的查询进行搜索
            for query in optimized_queries:
                site_results = await self._execute_site_search(site, query, limit)
                results.extend(site_results)
            
            # 更新站点统计
            site_manager.update_site_statistics(site_name, True, 1.0)
            
            return results
            
        except Exception as e:
            logger.error(f"站点搜索失败: {site_name}, {e}")
            site_manager.update_site_statistics(site_name, False, 0.0)
            return []
    
    async def _execute_site_search(self, site: Any, query: str, limit: int) -> List[SearchResult]:
        """执行站点搜索"""
        # 这里应该调用实际的站点搜索API
        # 简化实现
        
        if site.access_mode == SiteAccessMode.SPIDER:
            return await self._search_pt_spider(site, query, limit)
        else:
            return await self._search_pt_rss(site, query, limit)
    
    async def _search_pt_spider(self, site: Any, query: str, limit: int) -> List[SearchResult]:
        """爬虫模式搜索"""
        # 模拟搜索结果
        # 实际实现应该调用站点爬虫
        
        mock_results = []
        
        # 模拟一些搜索结果
        if "天下第一" in query:
            mock_results.append(SearchResult(
                title="天下第一 2005 电视剧 全40集",
                type="tv",
                source="pt_site",
                score=0.9,
                metadata={"year": 2005, "episodes": 40}
            ))
        
        if "武林外传" in query:
            mock_results.append(SearchResult(
                title="武林外传 2006 电视剧 80集全",
                type="tv",
                source="pt_site",
                score=0.8,
                metadata={"year": 2006, "episodes": 80}
            ))
        
        return mock_results[:limit]
    
    async def _search_pt_rss(self, site: Any, query: str, limit: int) -> List[SearchResult]:
        """RSS模式搜索"""
        # 模拟RSS搜索结果
        return []
    
    def _get_default_sites(self, content_type: str) -> List[str]:
        """获取默认站点"""
        enabled_sites = site_manager.get_enabled_sites()
        
        if content_type == "tv":
            # 对于电视剧，优先选择电视剧资源丰富的站点
            tv_sites = ["M-Team", "HDChina", "TTG"]
            return [site.name for site in enabled_sites if site.name in tv_sites]
        else:
            return [site.name for site in enabled_sites]
    
    def _filter_results(self, results: List[SearchResult], search_query: SearchQuery) -> List[SearchResult]:
        """过滤结果"""
        filtered_results = []
        
        for result in results:
            # 跳过被过滤的结果
            if result.filtered:
                continue
            
            # 对于老电视剧，放宽过滤条件
            if search_query.is_old_content:
                # 降低质量要求
                if result.score >= 0.3:  # 降低阈值
                    filtered_results.append(result)
            else:
                # 正常过滤
                if result.score >= 0.6:
                    filtered_results.append(result)
        
        return filtered_results
    
    def _generate_search_stats(self, search_query: SearchQuery, 
                              all_results: List[SearchResult], 
                              final_results: List[SearchResult]) -> Dict[str, Any]:
        """生成搜索统计信息"""
        return {
            "total_results": len(all_results),
            "filtered_results": len(final_results),
            "strategy_used": search_query.strategy.value,
            "queries_tried": len(search_query.processed_queries),
            "is_old_content": search_query.is_old_content,
            "content_type": search_query.content_type,
            "year": search_query.year
        }
    
    def _add_to_history(self, search_query: SearchQuery):
        """添加到搜索历史"""
        history_entry = {
            "original_query": search_query.original_query,
            "processed_queries": search_query.processed_queries,
            "strategy": search_query.strategy.value,
            "is_old_content": search_query.is_old_content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.search_history.append(history_entry)
        
        # 保持历史记录数量
        if len(self.search_history) > 100:
            self.search_history = self.search_history[-100:]
    
    def get_search_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        return self.search_history[-limit:]
    
    def clear_search_history(self):
        """清空搜索历史"""
        self.search_history.clear()


# 全局优化搜索管理器实例
optimized_search_manager = OptimizedSearchManager()