#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级结果处理器
专门解决MoviePilot中搜索结果排序和过滤不合理的问题
支持智能排序、质量评估、去重优化
"""

import asyncio
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from difflib import SequenceMatcher
import jieba

import structlog

logger = structlog.get_logger()


class ResultQuality(Enum):
    """结果质量等级"""
    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"           # 良好
    FAIR = "fair"           # 一般
    POOR = "poor"           # 较差


class SortingStrategy(Enum):
    """排序策略"""
    RELEVANCE = "relevance"      # 相关性优先
    QUALITY = "quality"          # 质量优先
    POPULARITY = "popularity"    # 流行度优先
    RECENCY = "recency"          # 时效性优先
    COMPREHENSIVE = "comprehensive"  # 综合排序


@dataclass
class QualityMetrics:
    """质量指标"""
    title_match_score: float          # 标题匹配度
    content_completeness: float       # 内容完整性
    source_reliability: float         # 源可信度
    technical_quality: float           # 技术质量
    popularity_score: float           # 流行度
    recency_score: float              # 时效性
    
    def overall_score(self) -> float:
        """计算综合分数"""
        weights = {
            'title_match_score': 0.3,
            'content_completeness': 0.2,
            'source_reliability': 0.15,
            'technical_quality': 0.15,
            'popularity_score': 0.1,
            'recency_score': 0.1
        }
        
        total_score = 0.0
        for metric, weight in weights.items():
            total_score += getattr(self, metric) * weight
        
        return total_score
    
    def get_quality_level(self) -> ResultQuality:
        """获取质量等级"""
        overall_score = self.overall_score()
        
        if overall_score >= 0.8:
            return ResultQuality.EXCELLENT
        elif overall_score >= 0.6:
            return ResultQuality.GOOD
        elif overall_score >= 0.4:
            return ResultQuality.FAIR
        else:
            return ResultQuality.POOR


class QualityAssessor:
    """质量评估器"""
    
    # 质量关键词映射
    QUALITY_KEYWORDS = {
        'excellent': ['4K', 'UHD', 'BluRay', 'REMUX', '无损', '原盘'],
        'good': ['1080p', 'WEB-DL', '高码率', '高清'],
        'fair': ['720p', 'HDTV', '标清'],
        'poor': ['CAM', 'TS', 'TC', '枪版', '录制版']
    }
    
    # 源可信度映射
    SOURCE_RELIABILITY = {
        'local': 1.0,      # 本地媒体库
        'tmdb': 0.9,      # TMDB
        'douban': 0.8,     # 豆瓣
        'mteam': 0.85,    # M-Team
        'hdchina': 0.8,   # HDChina
        'ttg': 0.8,       # TTG
        'rss': 0.6,       # RSS源
        'unknown': 0.5     # 未知源
    }
    
    @classmethod
    def assess_quality(cls, result_title: str, source: str, metadata: Dict) -> QualityMetrics:
        """评估结果质量"""
        # 标题匹配度
        title_match_score = cls._calculate_title_match_quality(result_title, metadata)
        
        # 内容完整性
        content_completeness = cls._assess_content_completeness(result_title, metadata)
        
        # 源可信度
        source_reliability = cls._get_source_reliability(source)
        
        # 技术质量
        technical_quality = cls._assess_technical_quality(result_title)
        
        # 流行度
        popularity_score = cls._estimate_popularity(metadata)
        
        # 时效性
        recency_score = cls._assess_recency(metadata)
        
        return QualityMetrics(
            title_match_score=title_match_score,
            content_completeness=content_completeness,
            source_reliability=source_reliability,
            technical_quality=technical_quality,
            popularity_score=popularity_score,
            recency_score=recency_score
        )
    
    @classmethod
    def _calculate_title_match_quality(cls, result_title: str, metadata: Dict) -> float:
        """计算标题匹配质量"""
        # 这里应该与原始查询进行比较
        # 简化实现
        
        # 检查标题是否包含关键信息
        expected_keywords = metadata.get('expected_keywords', [])
        if expected_keywords:
            match_count = sum(1 for keyword in expected_keywords if keyword in result_title)
            return match_count / len(expected_keywords)
        
        return 0.7  # 默认分数
    
    @classmethod
    def _assess_content_completeness(cls, result_title: str, metadata: Dict) -> float:
        """评估内容完整性"""
        score = 0.5  # 基础分数
        
        # 检查是否完整
        completeness_indicators = ['全集', '全季', '完整版', '未删减']
        for indicator in completeness_indicators:
            if indicator in result_title:
                score += 0.2
        
        # 检查是否分集
        episode_indicators = ['第\d+集', 'E\d+', '集全']
        for pattern in episode_indicators:
            if re.search(pattern, result_title):
                score += 0.1
        
        return min(score, 1.0)
    
    @classmethod
    def _get_source_reliability(cls, source: str) -> float:
        """获取源可信度"""
        return cls.SOURCE_RELIABILITY.get(source, 0.5)
    
    @classmethod
    def _assess_technical_quality(cls, result_title: str) -> float:
        """评估技术质量"""
        score = 0.5  # 基础分数
        
        # 检查质量关键词
        for quality_level, keywords in cls.QUALITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in result_title.lower():
                    if quality_level == 'excellent':
                        score = max(score, 0.9)
                    elif quality_level == 'good':
                        score = max(score, 0.7)
                    elif quality_level == 'fair':
                        score = max(score, 0.5)
                    elif quality_level == 'poor':
                        score = max(score, 0.3)
        
        return score
    
    @classmethod
    def _estimate_popularity(cls, metadata: Dict) -> float:
        """估计流行度"""
        # 从元数据中获取流行度信息
        popularity = metadata.get('popularity', 0)
        
        # 归一化到0-1范围
        if popularity > 1000:
            return 1.0
        elif popularity > 100:
            return 0.8
        elif popularity > 10:
            return 0.6
        else:
            return 0.4
    
    @classmethod
    def _assess_recency(cls, metadata: Dict) -> float:
        """评估时效性"""
        # 获取发布时间
        release_date = metadata.get('release_date')
        if not release_date:
            return 0.5
        
        try:
            # 计算与当前时间的差距
            if isinstance(release_date, str):
                release_time = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
            else:
                release_time = release_date
            
            current_time = datetime.now()
            time_diff = (current_time - release_time).days
            
            # 计算时效性分数（越新分数越高）
            if time_diff <= 7:    # 一周内
                return 1.0
            elif time_diff <= 30:  # 一月内
                return 0.8
            elif time_diff <= 365: # 一年内
                return 0.6
            else:                 # 一年以上
                return 0.4
                
        except:
            return 0.5


class DuplicateDetector:
    """重复检测器"""
    
    @classmethod
    def find_duplicates(cls, results: List[Dict]) -> List[List[int]]:
        """查找重复结果"""
        duplicate_groups = []
        processed_indices = set()
        
        for i in range(len(results)):
            if i in processed_indices:
                continue
            
            duplicates = [i]
            
            for j in range(i + 1, len(results)):
                if j in processed_indices:
                    continue
                
                if cls._are_duplicates(results[i], results[j]):
                    duplicates.append(j)
                    processed_indices.add(j)
            
            if len(duplicates) > 1:
                duplicate_groups.append(duplicates)
            
            processed_indices.add(i)
        
        return duplicate_groups
    
    @classmethod
    def _are_duplicates(cls, result1: Dict, result2: Dict) -> bool:
        """判断两个结果是否为重复"""
        # 1. 标题相似度
        title_similarity = SequenceMatcher(
            None, 
            result1.get('title', '').lower(), 
            result2.get('title', '').lower()
        ).ratio()
        
        if title_similarity < 0.7:
            return False
        
        # 2. 年份匹配
        year1 = cls._extract_year(result1.get('title', ''))
        year2 = cls._extract_year(result2.get('title', ''))
        
        if year1 and year2 and year1 != year2:
            return False
        
        # 3. 内容类型匹配
        type1 = result1.get('type', '')
        type2 = result2.get('type', '')
        
        if type1 != type2:
            return False
        
        return True
    
    @classmethod
    def _extract_year(cls, text: str) -> Optional[int]:
        """从文本中提取年份"""
        year_match = re.search(r'(19\d{2}|20\d{2})', text)
        if year_match:
            return int(year_match.group(1))
        return None


class ResultSorter:
    """结果排序器"""
    
    @classmethod
    def sort_results(cls, results: List[Dict], strategy: SortingStrategy, 
                    query: str = "") -> List[Dict]:
        """排序结果"""
        if not results:
            return results
        
        # 根据策略选择排序方法
        if strategy == SortingStrategy.RELEVANCE:
            return cls._sort_by_relevance(results, query)
        elif strategy == SortingStrategy.QUALITY:
            return cls._sort_by_quality(results)
        elif strategy == SortingStrategy.POPULARITY:
            return cls._sort_by_popularity(results)
        elif strategy == SortingStrategy.RECENCY:
            return cls._sort_by_recency(results)
        elif strategy == SortingStrategy.COMPREHENSIVE:
            return cls._sort_comprehensively(results, query)
        else:
            return results
    
    @classmethod
    def _sort_by_relevance(cls, results: List[Dict], query: str) -> List[Dict]:
        """按相关性排序"""
        def relevance_score(result):
            title = result.get('title', '').lower()
            query_lower = query.lower()
            
            # 计算相关性分数
            if query_lower in title:
                return 1.0
            
            # 使用模糊匹配
            similarity = SequenceMatcher(None, title, query_lower).ratio()
            return similarity
        
        return sorted(results, key=relevance_score, reverse=True)
    
    @classmethod
    def _sort_by_quality(cls, results: List[Dict]) -> List[Dict]:
        """按质量排序"""
        def quality_score(result):
            # 使用质量评估器
            quality_metrics = QualityAssessor.assess_quality(
                result.get('title', ''),
                result.get('source', ''),
                result.get('metadata', {})
            )
            return quality_metrics.overall_score()
        
        return sorted(results, key=quality_score, reverse=True)
    
    @classmethod
    def _sort_by_popularity(cls, results: List[Dict]) -> List[Dict]:
        """按流行度排序"""
        def popularity_score(result):
            metadata = result.get('metadata', {})
            popularity = metadata.get('popularity', 0)
            return popularity
        
        return sorted(results, key=popularity_score, reverse=True)
    
    @classmethod
    def _sort_by_recency(cls, results: List[Dict]) -> List[Dict]:
        """按时效性排序"""
        def recency_score(result):
            metadata = result.get('metadata', {})
            release_date = metadata.get('release_date')
            
            if not release_date:
                return 0
            
            try:
                if isinstance(release_date, str):
                    release_time = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                else:
                    release_time = release_date
                
                # 返回时间戳（越新越大）
                return release_time.timestamp()
            except:
                return 0
        
        return sorted(results, key=recency_score, reverse=True)
    
    @classmethod
    def _sort_comprehensively(cls, results: List[Dict], query: str) -> List[Dict]:
        """综合排序"""
        def comprehensive_score(result):
            # 计算多个维度的分数
            title = result.get('title', '')
            source = result.get('source', '')
            metadata = result.get('metadata', {})
            
            # 1. 相关性分数
            relevance = cls._calculate_relevance(title, query)
            
            # 2. 质量分数
            quality_metrics = QualityAssessor.assess_quality(title, source, metadata)
            quality = quality_metrics.overall_score()
            
            # 3. 流行度分数
            popularity = metadata.get('popularity', 0) / 1000.0  # 归一化
            
            # 4. 时效性分数
            recency = quality_metrics.recency_score
            
            # 综合分数（加权平均）
            weights = {
                'relevance': 0.4,
                'quality': 0.3,
                'popularity': 0.15,
                'recency': 0.15
            }
            
            total_score = (
                relevance * weights['relevance'] +
                quality * weights['quality'] +
                popularity * weights['popularity'] +
                recency * weights['recency']
            )
            
            return total_score
        
        return sorted(results, key=comprehensive_score, reverse=True)
    
    @classmethod
    def _calculate_relevance(cls, title: str, query: str) -> float:
        """计算相关性"""
        if not query:
            return 0.5
        
        title_lower = title.lower()
        query_lower = query.lower()
        
        # 精确匹配
        if query_lower in title_lower:
            return 1.0
        
        # 模糊匹配
        similarity = SequenceMatcher(None, title_lower, query_lower).ratio()
        
        # 关键词匹配
        query_words = set(query_lower.split())
        title_words = set(title_lower.split())
        
        keyword_match = len(query_words.intersection(title_words)) / len(query_words)
        
        # 综合相关性
        return max(similarity, keyword_match)


class ResultFilter:
    """结果过滤器"""
    
    @classmethod
    def filter_results(cls, results: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
        """过滤结果"""
        filtered_results = results.copy()
        
        # 应用质量过滤器
        if 'min_quality' in filters:
            filtered_results = cls._filter_by_quality(filtered_results, filters['min_quality'])
        
        # 应用类型过滤器
        if 'content_type' in filters:
            filtered_results = cls._filter_by_type(filtered_results, filters['content_type'])
        
        # 应用年份过滤器
        if 'year_range' in filters:
            filtered_results = cls._filter_by_year(filtered_results, filters['year_range'])
        
        # 应用源过滤器
        if 'sources' in filters:
            filtered_results = cls._filter_by_source(filtered_results, filters['sources'])
        
        # 应用重复过滤器
        if filters.get('remove_duplicates', True):
            filtered_results = cls._remove_duplicates(filtered_results)
        
        return filtered_results
    
    @classmethod
    def _filter_by_quality(cls, results: List[Dict], min_quality: ResultQuality) -> List[Dict]:
        """按质量过滤"""
        quality_order = {
            ResultQuality.EXCELLENT: 4,
            ResultQuality.GOOD: 3,
            ResultQuality.FAIR: 2,
            ResultQuality.POOR: 1
        }
        
        min_quality_level = quality_order[min_quality]
        
        filtered_results = []
        for result in results:
            quality_metrics = QualityAssessor.assess_quality(
                result.get('title', ''),
                result.get('source', ''),
                result.get('metadata', {})
            )
            
            result_quality_level = quality_order[quality_metrics.get_quality_level()]
            
            if result_quality_level >= min_quality_level:
                filtered_results.append(result)
        
        return filtered_results
    
    @classmethod
    def _filter_by_type(cls, results: List[Dict], content_type: str) -> List[Dict]:
        """按类型过滤"""
        return [result for result in results if result.get('type') == content_type]
    
    @classmethod
    def _filter_by_year(cls, results: List[Dict], year_range: Tuple[int, int]) -> List[Dict]:
        """按年份过滤"""
        min_year, max_year = year_range
        
        filtered_results = []
        for result in results:
            year = cls._extract_year_from_result(result)
            if year and min_year <= year <= max_year:
                filtered_results.append(result)
        
        return filtered_results
    
    @classmethod
    def _filter_by_source(cls, results: List[Dict], allowed_sources: List[str]) -> List[Dict]:
        """按源过滤"""
        return [result for result in results if result.get('source') in allowed_sources]
    
    @classmethod
    def _remove_duplicates(cls, results: List[Dict]) -> List[Dict]:
        """移除重复结果"""
        duplicate_groups = DuplicateDetector.find_duplicates(results)
        
        # 保留每个重复组中质量最高的结果
        kept_indices = set()
        
        for group in duplicate_groups:
            # 找到组中质量最高的结果
            best_result_index = max(group, key=lambda i: 
                QualityAssessor.assess_quality(
                    results[i].get('title', ''),
                    results[i].get('source', ''),
                    results[i].get('metadata', {})
                ).overall_score()
            )
            kept_indices.add(best_result_index)
        
        # 构建去重后的结果列表
        unique_results = []
        for i, result in enumerate(results):
            if i in kept_indices or i not in [idx for group in duplicate_groups for idx in group]:
                unique_results.append(result)
        
        return unique_results
    
    @classmethod
    def _extract_year_from_result(cls, result: Dict) -> Optional[int]:
        """从结果中提取年份"""
        # 从标题中提取
        title = result.get('title', '')
        year_match = re.search(r'(19\d{2}|20\d{2})', title)
        if year_match:
            return int(year_match.group(1))
        
        # 从元数据中提取
        metadata = result.get('metadata', {})
        year = metadata.get('year')
        if year:
            return int(year)
        
        return None


class AdvancedResultProcessor:
    """高级结果处理器"""
    
    def __init__(self):
        self.quality_assessor = QualityAssessor()
        self.duplicate_detector = DuplicateDetector()
        self.result_sorter = ResultSorter()
        self.result_filter = ResultFilter()
    
    async def process_results(self, 
                             results: List[Dict], 
                             query: str = "",
                             sorting_strategy: SortingStrategy = SortingStrategy.COMPREHENSIVE,
                             filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理搜索结果"""
        logger.info(f"开始处理 {len(results)} 个搜索结果")
        
        if filters is None:
            filters = {}
        
        # 1. 质量评估
        results_with_quality = await self._assess_results_quality(results)
        
        # 2. 过滤结果
        filtered_results = self.result_filter.filter_results(results_with_quality, filters)
        
        # 3. 排序结果
        sorted_results = self.result_sorter.sort_results(filtered_results, sorting_strategy, query)
        
        # 4. 生成统计信息
        stats = self._generate_statistics(results_with_quality, filtered_results, sorted_results)
        
        logger.info(f"结果处理完成: 原始 {len(results)} -> 过滤后 {len(filtered_results)} -> 排序后 {len(sorted_results)}")
        
        return {
            'original_count': len(results),
            'filtered_count': len(filtered_results),
            'final_count': len(sorted_results),
            'results': sorted_results,
            'statistics': stats,
            'sorting_strategy': sorting_strategy.value,
            'filters_applied': filters
        }
    
    async def _assess_results_quality(self, results: List[Dict]) -> List[Dict]:
        """评估结果质量"""
        results_with_quality = []
        
        for result in results:
            # 评估质量
            quality_metrics = self.quality_assessor.assess_quality(
                result.get('title', ''),
                result.get('source', ''),
                result.get('metadata', {})
            )
            
            # 添加质量信息到结果
            result_with_quality = result.copy()
            result_with_quality['quality_metrics'] = {
                'overall_score': quality_metrics.overall_score(),
                'quality_level': quality_metrics.get_quality_level().value,
                'title_match_score': quality_metrics.title_match_score,
                'content_completeness': quality_metrics.content_completeness,
                'source_reliability': quality_metrics.source_reliability,
                'technical_quality': quality_metrics.technical_quality,
                'popularity_score': quality_metrics.popularity_score,
                'recency_score': quality_metrics.recency_score
            }
            
            results_with_quality.append(result_with_quality)
        
        return results_with_quality
    
    def _generate_statistics(self, 
                            original_results: List[Dict], 
                            filtered_results: List[Dict],
                            final_results: List[Dict]) -> Dict[str, Any]:
        """生成统计信息"""
        # 质量分布统计
        quality_distribution = {}
        for result in original_results:
            quality_level = result.get('quality_metrics', {}).get('quality_level', 'unknown')
            quality_distribution[quality_level] = quality_distribution.get(quality_level, 0) + 1
        
        # 源分布统计
        source_distribution = {}
        for result in original_results:
            source = result.get('source', 'unknown')
            source_distribution[source] = source_distribution.get(source, 0) + 1
        
        return {
            'quality_distribution': quality_distribution,
            'source_distribution': source_distribution,
            'filter_effectiveness': {
                'removed_count': len(original_results) - len(filtered_results),
                'removal_rate': (len(original_results) - len(filtered_results)) / len(original_results) if original_results else 0
            },
            'processing_timestamp': datetime.now().isoformat()
        }


# 全局高级结果处理器实例
advanced_result_processor = AdvancedResultProcessor()