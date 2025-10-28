#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能搜索引擎
专门解决MoviePilot中老电视剧搜索不到的问题
支持智能关键词扩展、模糊匹配、语义理解
"""

import asyncio
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from enum import Enum
import jieba
import jieba.analyse

import structlog

logger = structlog.get_logger()


class SearchIntelligenceLevel(Enum):
    """搜索智能级别"""
    BASIC = "basic"      # 基础搜索
    ADVANCED = "advanced" # 高级搜索
    EXPERT = "expert"     # 专家级搜索


class ContentCategory(Enum):
    """内容分类"""
    OLD_TV = "old_tv"           # 老电视剧
    MODERN_TV = "modern_tv"     # 现代电视剧
    MOVIE = "movie"             # 电影
    ANIME = "anime"             # 动漫
    DOCUMENTARY = "documentary" # 纪录片


@dataclass
class IntelligentQuery:
    """智能查询对象"""
    original_query: str
    category: ContentCategory
    intelligence_level: SearchIntelligenceLevel
    expanded_queries: List[str]
    alternative_names: List[str]
    search_strategies: List[str]
    confidence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class ContentKnowledgeBase:
    """内容知识库"""
    
    # 老电视剧数据库
    OLD_TV_DATABASE = {
        "天下第一": {
            "year": 2005,
            "episodes": 40,
            "alternative_names": ["天下第一 2005", "天下第一电视剧", "天下第一 全40集"],
            "keywords": ["武侠", "古装", "张卫健", "郭晋安"],
            "search_patterns": ["天下第一", "天下第一 2005", "天下第一电视剧"]
        },
        "武林外传": {
            "year": 2006,
            "episodes": 80,
            "alternative_names": ["武林外传 2006", "武林外传电视剧", "武林外传 80集"],
            "keywords": ["喜剧", "古装", "情景喜剧", "闫妮", "沙溢"],
            "search_patterns": ["武林外传", "武林外传 2006", "武林外传电视剧"]
        },
        "还珠格格": {
            "year": 1998,
            "episodes": 24,
            "alternative_names": ["还珠格格 1998", "还珠格格第一部", "还珠格格电视剧"],
            "keywords": ["琼瑶", "古装", "爱情", "赵薇", "林心如"],
            "search_patterns": ["还珠格格", "还珠格格 1998", "还珠格格第一部"]
        },
        "神雕侠侣": {
            "year": 1995,
            "episodes": 32,
            "alternative_names": ["神雕侠侣 1995", "神雕侠侣古天乐版", "神雕侠侣电视剧"],
            "keywords": ["金庸", "武侠", "古天乐", "李若彤"],
            "search_patterns": ["神雕侠侣", "神雕侠侣 1995", "神雕侠侣古天乐版"]
        }
    }
    
    # 常见搜索问题模式
    SEARCH_PROBLEM_PATTERNS = {
        "no_results": ["没有结果", "搜索结果为空", "找不到资源"],
        "wrong_results": ["搜索结果不对", "搜到其他内容", "匹配错误"],
        "incomplete_results": ["结果不完整", "缺少资源", "部分缺失"]
    }
    
    @classmethod
    def get_content_info(cls, query: str) -> Optional[Dict[str, Any]]:
        """获取内容信息"""
        # 精确匹配
        if query in cls.OLD_TV_DATABASE:
            return cls.OLD_TV_DATABASE[query]
        
        # 模糊匹配
        for title, info in cls.OLD_TV_DATABASE.items():
            if title in query or query in title:
                return info
        
        # 检查替代名称
        for title, info in cls.OLD_TV_DATABASE.items():
            for alt_name in info["alternative_names"]:
                if query in alt_name or alt_name in query:
                    return info
        
        return None
    
    @classmethod
    def detect_content_category(cls, query: str) -> ContentCategory:
        """检测内容分类"""
        # 检查是否为老电视剧
        if cls.get_content_info(query):
            return ContentCategory.OLD_TV
        
        # 检查年份
        year_match = re.search(r'(19\d{2}|20\d{2})', query)
        if year_match:
            year = int(year_match.group(1))
            if year < 2010:
                return ContentCategory.OLD_TV
        
        # 关键词匹配
        tv_keywords = ['电视剧', '剧集', 'TV', 'tv', 'series']
        movie_keywords = ['电影', 'movie', 'film']
        anime_keywords = ['动漫', '动画', 'anime']
        
        if any(keyword in query for keyword in tv_keywords):
            return ContentCategory.MODERN_TV
        elif any(keyword in query for keyword in movie_keywords):
            return ContentCategory.MOVIE
        elif any(keyword in query for keyword in anime_keywords):
            return ContentCategory.ANIME
        
        return ContentCategory.MODERN_TV  # 默认现代电视剧


class QueryExpander:
    """查询扩展器"""
    
    @classmethod
    def expand_query(cls, query: str, category: ContentCategory) -> List[str]:
        """扩展查询"""
        expanded_queries = [query]
        
        # 根据内容分类采用不同的扩展策略
        if category == ContentCategory.OLD_TV:
            expanded_queries.extend(cls._expand_old_tv_query(query))
        elif category == ContentCategory.MODERN_TV:
            expanded_queries.extend(cls._expand_modern_tv_query(query))
        elif category == ContentCategory.MOVIE:
            expanded_queries.extend(cls._expand_movie_query(query))
        
        # 通用扩展
        expanded_queries.extend(cls._general_expansion(query))
        
        # 去重
        return list(dict.fromkeys(expanded_queries))
    
    @classmethod
    def _expand_old_tv_query(cls, query: str) -> List[str]:
        """扩展老电视剧查询"""
        expansions = []
        
        # 1. 添加年份信息
        year_match = re.search(r'(19\d{2}|20\d{2})', query)
        if not year_match:
            # 从知识库获取年份
            content_info = ContentKnowledgeBase.get_content_info(query)
            if content_info:
                expansions.append(f"{query} {content_info['year']}")
        
        # 2. 添加类型后缀
        suffixes = ['电视剧', '剧集', 'TV版', '全集']
        for suffix in suffixes:
            if suffix not in query:
                expansions.append(f"{query} {suffix}")
        
        # 3. 繁体字版本
        traditional_versions = cls._to_traditional_chinese(query)
        expansions.extend(traditional_versions)
        
        # 4. 拼音版本
        pinyin_versions = cls._to_pinyin(query)
        expansions.extend(pinyin_versions)
        
        # 5. 常见错误拼写
        common_misspellings = cls._generate_misspellings(query)
        expansions.extend(common_misspellings)
        
        return expansions
    
    @classmethod
    def _expand_modern_tv_query(cls, query: str) -> List[str]:
        """扩展现代电视剧查询"""
        expansions = []
        
        # 添加季数信息
        season_patterns = ['S\d+', '第[一二三四五六七八九十]+季', 'Season \d+']
        has_season = any(re.search(pattern, query) for pattern in season_patterns)
        
        if not has_season:
            expansions.append(f"{query} S01")
            expansions.append(f"{query} 第一季")
        
        return expansions
    
    @classmethod
    def _expand_movie_query(cls, query: str) -> List[str]:
        """扩展电影查询"""
        expansions = []
        
        # 添加质量信息
        quality_keywords = ['4K', '1080p', '720p', 'BluRay', 'WEB-DL']
        for quality in quality_keywords:
            if quality not in query:
                expansions.append(f"{query} {quality}")
        
        return expansions
    
    @classmethod
    def _general_expansion(cls, query: str) -> List[str]:
        """通用扩展"""
        expansions = []
        
        # 1. 去除标点符号的版本
        clean_query = re.sub(r'[，。！？；：""''《》【】]', ' ', query).strip()
        if clean_query != query:
            expansions.append(clean_query)
        
        # 2. 空格处理的不同版本
        space_variants = [
            query.replace(' ', ''),      # 无空格
            query.replace(' ', '-'),     # 连字符
            query.replace(' ', '_'),     # 下划线
        ]
        expansions.extend(space_variants)
        
        # 3. 大小写变体
        expansions.append(query.lower())
        expansions.append(query.upper())
        
        return expansions
    
    @classmethod
    def _to_traditional_chinese(cls, query: str) -> List[str]:
        """转换为繁体中文"""
        # 简化实现：常见转换
        simplified_to_traditional = {
            '天': '天', '下': '下', '第': '第', '一': '一',
            '武': '武', '林': '林', '外': '外', '传': '傳',
            '还': '還', '珠': '珠', '格': '格', '神': '神',
            '雕': '雕', '侠': '俠', '侣': '侶'
        }
        
        traditional_query = ''.join(simplified_to_traditional.get(char, char) for char in query)
        if traditional_query != query:
            return [traditional_query]
        return []
    
    @classmethod
    def _to_pinyin(cls, query: str) -> List[str]:
        """转换为拼音"""
        # 常见电视剧的拼音映射
        pinyin_map = {
            '天下第一': 'tian xia di yi',
            '武林外传': 'wu lin wai zhuan',
            '还珠格格': 'huan zhu ge ge',
            '神雕侠侣': 'shen diao xia lv'
        }
        
        if query in pinyin_map:
            return [pinyin_map[query]]
        return []
    
    @classmethod
    def _generate_misspellings(cls, query: str) -> List[str]:
        """生成常见错误拼写"""
        misspellings = []
        
        # 常见音近字替换
        sound_alike_map = {
            '第': ['地', '帝'],
            '一': ['衣', '医'],
            '天': ['田', '甜'],
            '下': ['夏', '霞']
        }
        
        # 生成一些可能的错误拼写
        for i, char in enumerate(query):
            if char in sound_alike_map:
                for replacement in sound_alike_map[char]:
                    misspelled = query[:i] + replacement + query[i+1:]
                    misspellings.append(misspelled)
        
        return misspellings


class FuzzyMatcher:
    """模糊匹配器"""
    
    @classmethod
    def calculate_similarity(cls, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 使用多种算法计算相似度
        
        # 1. 编辑距离相似度
        edit_similarity = cls._edit_distance_similarity(text1, text2)
        
        # 2. 序列匹配相似度
        sequence_similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
        # 3. 关键词重叠相似度
        keyword_similarity = cls._keyword_overlap_similarity(text1, text2)
        
        # 综合相似度
        combined_similarity = (edit_similarity + sequence_similarity + keyword_similarity) / 3
        
        return combined_similarity
    
    @classmethod
    def _edit_distance_similarity(cls, text1: str, text2: str) -> float:
        """基于编辑距离的相似度"""
        # 简化实现
        len1, len2 = len(text1), len(text2)
        max_len = max(len1, len2)
        
        if max_len == 0:
            return 1.0
        
        # 计算简单的编辑距离
        distance = abs(len1 - len2)
        for i in range(min(len1, len2)):
            if text1[i] != text2[i]:
                distance += 1
        
        return 1 - (distance / max_len)
    
    @classmethod
    def _keyword_overlap_similarity(cls, text1: str, text2: str) -> float:
        """基于关键词重叠的相似度"""
        # 使用jieba分词
        try:
            words1 = set(jieba.lcut(text1))
            words2 = set(jieba.lcut(text2))
            
            if not words1 and not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union) if union else 0.0
            
        except:
            # 分词失败时使用简单方法
            words1 = set(text1.split())
            words2 = set(text2.split())
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union) if union else 0.0
    
    @classmethod
    def find_best_match(cls, query: str, candidates: List[str], threshold: float = 0.6) -> Optional[Tuple[str, float]]:
        """找到最佳匹配"""
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            score = cls.calculate_similarity(query, candidate)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate
        
        if best_match:
            return best_match, best_score
        return None


class SearchStrategyPlanner:
    """搜索策略规划器"""
    
    @classmethod
    def plan_search_strategies(cls, query: str, category: ContentCategory) -> List[str]:
        """规划搜索策略"""
        strategies = []
        
        # 基础策略
        strategies.append("exact_match")  # 精确匹配
        strategies.append("fuzzy_match")  # 模糊匹配
        
        # 根据内容分类添加特定策略
        if category == ContentCategory.OLD_TV:
            strategies.extend([
                "year_based_search",      # 基于年份的搜索
                "alternative_name_search", # 替代名称搜索
                "keyword_expansion",      # 关键词扩展
                "site_specific_adaptation" # 站点特定适配
            ])
        elif category == ContentCategory.MODERN_TV:
            strategies.extend([
                "season_based_search",    # 基于季数的搜索
                "quality_filtering",      # 质量过滤
                "release_group_search"    # 发布组搜索
            ])
        
        # 高级策略
        strategies.extend([
            "cross_site_search",         # 跨站点搜索
            "fallback_search",           # 备用搜索
            "intelligent_retry"          # 智能重试
        ])
        
        return strategies
    
    @classmethod
    def get_intelligence_level(cls, category: ContentCategory, query_complexity: int) -> SearchIntelligenceLevel:
        """获取智能级别"""
        if category == ContentCategory.OLD_TV:
            return SearchIntelligenceLevel.EXPERT
        elif query_complexity > 3:  # 复杂查询
            return SearchIntelligenceLevel.ADVANCED
        else:
            return SearchIntelligenceLevel.BASIC


class IntelligentSearchEngine:
    """智能搜索引擎"""
    
    def __init__(self):
        self.knowledge_base = ContentKnowledgeBase()
        self.query_expander = QueryExpander()
        self.fuzzy_matcher = FuzzyMatcher()
        self.strategy_planner = SearchStrategyPlanner()
        self.search_history: List[Dict[str, Any]] = []
    
    async def intelligent_search(self, query: str) -> IntelligentQuery:
        """智能搜索分析"""
        logger.info(f"开始智能搜索分析: {query}")
        
        # 1. 内容分类检测
        category = self.knowledge_base.detect_content_category(query)
        
        # 2. 查询复杂度分析
        query_complexity = self._analyze_query_complexity(query)
        
        # 3. 确定智能级别
        intelligence_level = self.strategy_planner.get_intelligence_level(category, query_complexity)
        
        # 4. 查询扩展
        expanded_queries = self.query_expander.expand_query(query, category)
        
        # 5. 获取替代名称
        alternative_names = self._get_alternative_names(query, category)
        
        # 6. 规划搜索策略
        search_strategies = self.strategy_planner.plan_search_strategies(query, category)
        
        # 7. 计算置信度
        confidence_score = self._calculate_confidence(query, category, intelligence_level)
        
        # 创建智能查询对象
        intelligent_query = IntelligentQuery(
            original_query=query,
            category=category,
            intelligence_level=intelligence_level,
            expanded_queries=expanded_queries,
            alternative_names=alternative_names,
            search_strategies=search_strategies,
            confidence_score=confidence_score
        )
        
        # 记录搜索历史
        self._add_to_history(intelligent_query)
        
        logger.info(f"智能搜索分析完成: {query}, 置信度: {confidence_score:.2f}")
        
        return intelligent_query
    
    def _analyze_query_complexity(self, query: str) -> int:
        """分析查询复杂度"""
        complexity = 0
        
        # 长度复杂度
        if len(query) > 10:
            complexity += 1
        
        # 包含年份
        if re.search(r'(19\d{2}|20\d{2})', query):
            complexity += 1
        
        # 包含季数信息
        if re.search(r'(S\d+|第[一二三四五六七八九十]+季)', query):
            complexity += 1
        
        # 包含质量信息
        if re.search(r'(4K|1080p|720p|BluRay|WEB-DL)', query, re.IGNORECASE):
            complexity += 1
        
        # 包含特殊字符
        if re.search(r'[\[\](){}|]', query):
            complexity += 1
        
        return min(complexity, 5)  # 最大复杂度为5
    
    def _get_alternative_names(self, query: str, category: ContentCategory) -> List[str]:
        """获取替代名称"""
        alternative_names = []
        
        # 从知识库获取替代名称
        content_info = self.knowledge_base.get_content_info(query)
        if content_info:
            alternative_names.extend(content_info.get("alternative_names", []))
        
        # 根据分类生成通用替代名称
        if category == ContentCategory.OLD_TV:
            alternative_names.extend([
                f"{query} 电视剧",
                f"{query} 全集",
                f"{query} 国语版"
            ])
        
        return list(dict.fromkeys(alternative_names))
    
    def _calculate_confidence(self, query: str, category: ContentCategory, 
                             intelligence_level: SearchIntelligenceLevel) -> float:
        """计算置信度"""
        confidence = 0.5  # 基础置信度
        
        # 内容分类影响
        if category == ContentCategory.OLD_TV:
            confidence += 0.2  # 老电视剧有专门优化
        
        # 智能级别影响
        if intelligence_level == SearchIntelligenceLevel.EXPERT:
            confidence += 0.2
        elif intelligence_level == SearchIntelligenceLevel.ADVANCED:
            confidence += 0.1
        
        # 查询复杂度影响（适中的复杂度有更高置信度）
        complexity = self._analyze_query_complexity(query)
        if 2 <= complexity <= 4:
            confidence += 0.1
        
        # 知识库匹配影响
        if self.knowledge_base.get_content_info(query):
            confidence += 0.2
        
        return min(confidence, 1.0)  # 最大置信度为1.0
    
    def _add_to_history(self, intelligent_query: IntelligentQuery):
        """添加到搜索历史"""
        history_entry = {
            "original_query": intelligent_query.original_query,
            "category": intelligent_query.category.value,
            "intelligence_level": intelligent_query.intelligence_level.value,
            "expanded_queries_count": len(intelligent_query.expanded_queries),
            "confidence_score": intelligent_query.confidence_score,
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
    
    async def find_similar_content(self, query: str, threshold: float = 0.7) -> List[Tuple[str, float]]:
        """查找相似内容"""
        similar_contents = []
        
        # 从知识库中查找相似内容
        for title, info in self.knowledge_base.OLD_TV_DATABASE.items():
            similarity = self.fuzzy_matcher.calculate_similarity(query, title)
            if similarity >= threshold:
                similar_contents.append((title, similarity))
        
        # 按相似度排序
        similar_contents.sort(key=lambda x: x[1], reverse=True)
        
        return similar_contents


# 全局智能搜索引擎实例
intelligent_search_engine = IntelligentSearchEngine()