"""
数据聚合服务
统一管理多个数据源，提供智能推荐和缓存优化
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import json
import redis
import hashlib


class DataAggregator:
    """数据聚合服务"""
    
    def __init__(self, redis_client=None):
        self.logger = logging.getLogger(__name__)
        self.redis_client = redis_client
        
        # 数据源管理器
        self.data_sources = {}
        
        # 缓存配置
        self.cache_ttl = {
            'chart_data': 3600,  # 1小时
            'search_results': 1800,  # 30分钟
            'content_details': 7200,  # 2小时
            'recommendations': 1800  # 30分钟
        }
        
        # 用户行为追踪
        self.user_behavior = defaultdict(list)
        
        # 推荐算法配置
        self.recommendation_config = {
            'collaborative_weight': 0.4,
            'content_based_weight': 0.3,
            'popularity_weight': 0.2,
            'recency_weight': 0.1
        }

    def register_data_source(self, name: str, data_source):
        """注册数据源"""
        self.data_sources[name] = data_source
        self.logger.info(f"数据源注册成功: {name}")

    async def get_aggregated_chart_data(self, chart_type: str, limit: int = 50, 
                                      sources: List[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """获取聚合的榜单数据"""
        cache_key = self._generate_cache_key('chart', chart_type, limit, sources, kwargs)
        
        # 尝试从缓存获取
        cached_data = await self._get_cached_data(cache_key)
        if cached_data:
            self.logger.info(f"从缓存获取榜单数据: {chart_type}")
            return cached_data
        
        # 并行获取各数据源数据
        tasks = []
        source_names = sources or list(self.data_sources.keys())
        
        for source_name in source_names:
            if source_name in self.data_sources:
                task = self._get_source_chart_data(source_name, chart_type, limit, **kwargs)
                tasks.append(task)
        
        # 等待所有数据源完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并和去重数据
        aggregated_data = self._merge_and_deduplicate(results)
        
        # 智能排序
        aggregated_data = self._smart_sort(aggregated_data, chart_type)
        
        # 缓存结果
        await self._cache_data(cache_key, aggregated_data, self.cache_ttl['chart_data'])
        
        return aggregated_data[:limit]

    async def _get_source_chart_data(self, source_name: str, chart_type: str, 
                                   limit: int, **kwargs) -> List[Dict[str, Any]]:
        """从单个数据源获取数据"""
        try:
            data_source = self.data_sources[source_name]
            
            # 检查数据源是否支持该榜单类型
            supported_types = data_source.get_supported_chart_types()
            if chart_type not in supported_types:
                self.logger.warning(f"数据源 {source_name} 不支持榜单类型 {chart_type}")
                return []
            
            data = await data_source.get_chart_data(chart_type, limit, **kwargs)
            
            # 添加数据源标记
            for item in data:
                item['data_source'] = source_name
                item['data_source_weight'] = self._calculate_source_weight(source_name, chart_type)
            
            return data
            
        except Exception as e:
            self.logger.error(f"从数据源 {source_name} 获取数据失败: {e}")
            return []

    async def search_aggregated_content(self, query: str, content_type: str = "all",
                                      sources: List[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """聚合搜索内容"""
        cache_key = self._generate_cache_key('search', query, content_type, sources, kwargs)
        
        # 尝试从缓存获取
        cached_data = await self._get_cached_data(cache_key)
        if cached_data:
            self.logger.info(f"从缓存获取搜索结果: {query}")
            return cached_data
        
        # 并行搜索各数据源
        tasks = []
        source_names = sources or list(self.data_sources.keys())
        
        for source_name in source_names:
            if source_name in self.data_sources:
                task = self._search_source_content(source_name, query, content_type, **kwargs)
                tasks.append(task)
        
        # 等待所有搜索完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并和去重
        search_results = self._merge_and_deduplicate(results)
        
        # 相关性排序
        search_results = self._relevance_sort(search_results, query)
        
        # 缓存结果
        await self._cache_data(cache_key, search_results, self.cache_ttl['search_results'])
        
        return search_results

    async def _search_source_content(self, source_name: str, query: str, 
                                   content_type: str, **kwargs) -> List[Dict[str, Any]]:
        """从单个数据源搜索内容"""
        try:
            data_source = self.data_sources[source_name]
            results = await data_source.search_content(query, content_type, **kwargs)
            
            # 添加数据源标记
            for item in results:
                item['data_source'] = source_name
                item['relevance_score'] = self._calculate_relevance_score(item, query)
            
            return results
            
        except Exception as e:
            self.logger.error(f"数据源 {source_name} 搜索失败: {e}")
            return []

    async def get_personalized_recommendations(self, user_id: str, limit: int = 20,
                                             content_types: List[str] = None) -> List[Dict[str, Any]]:
        """获取个性化推荐"""
        cache_key = self._generate_cache_key('recommendations', user_id, limit, content_types)
        
        # 尝试从缓存获取
        cached_data = await self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        # 获取用户行为数据
        user_behavior = self.user_behavior.get(user_id, [])
        
        if not user_behavior:
            # 新用户，返回热门推荐
            recommendations = await self._get_popular_recommendations(limit, content_types)
        else:
            # 个性化推荐算法
            recommendations = await self._generate_personalized_recommendations(
                user_id, user_behavior, limit, content_types
            )
        
        # 缓存推荐结果
        await self._cache_data(cache_key, recommendations, self.cache_ttl['recommendations'])
        
        return recommendations

    async def _generate_personalized_recommendations(self, user_id: str, user_behavior: List,
                                                   limit: int, content_types: List[str]) -> List[Dict[str, Any]]:
        """生成个性化推荐"""
        # 基于内容的推荐
        content_based_recs = await self._content_based_recommendation(user_behavior, limit)
        
        # 协同过滤推荐
        collaborative_recs = await self._collaborative_recommendation(user_id, limit)
        
        # 热门推荐
        popular_recs = await self._get_popular_recommendations(limit, content_types)
        
        # 合并推荐结果
        all_recommendations = content_based_recs + collaborative_recs + popular_recs
        
        # 去重和加权排序
        merged_recs = self._merge_and_weight_recommendations(
            all_recommendations, user_behavior
        )
        
        return merged_recs[:limit]

    async def _content_based_recommendation(self, user_behavior: List, limit: int) -> List[Dict[str, Any]]:
        """基于内容的推荐"""
        # 分析用户偏好
        user_preferences = self._analyze_user_preferences(user_behavior)
        
        # 根据偏好搜索相关内容
        recommendations = []
        
        for preference in user_preferences[:3]:  # 取前3个偏好
            if preference['type'] == 'genre':
                # 按类型推荐
                recs = await self.search_aggregated_content(
                    preference['value'], 
                    content_type='movie',
                    limit=limit//3
                )
                recommendations.extend(recs)
        
        return recommendations

    async def _collaborative_recommendation(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """协同过滤推荐"""
        # 简化实现：基于相似用户行为
        # 实际项目中可以使用更复杂的算法
        
        similar_users = self._find_similar_users(user_id)
        
        recommendations = []
        for similar_user in similar_users[:5]:  # 取前5个相似用户
            user_recs = self.user_behavior.get(similar_user, [])
            recommendations.extend(user_recs)
        
        return recommendations[:limit]

    async def _get_popular_recommendations(self, limit: int, content_types: List[str]) -> List[Dict[str, Any]]:
        """获取热门推荐"""
        try:
            # 获取多个数据源的流行内容
            popular_data = await self.get_aggregated_chart_data(
                'most_popular', 
                limit=limit,
                sources=['tmdb', 'douban', 'imdb']
            )
            
            # 过滤内容类型
            if content_types:
                popular_data = [item for item in popular_data 
                              if item.get('type') in content_types]
            
            return popular_data[:limit]
            
        except Exception as e:
            self.logger.error(f"获取热门推荐失败: {e}")
            return []

    def track_user_behavior(self, user_id: str, action: str, content: Dict[str, Any]):
        """追踪用户行为"""
        behavior_record = {
            'action': action,  # view, rate, favorite, etc.
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'content_type': content.get('type', 'unknown')
        }
        
        self.user_behavior[user_id].append(behavior_record)
        
        # 限制行为记录数量
        if len(self.user_behavior[user_id]) > 100:
            self.user_behavior[user_id] = self.user_behavior[user_id][-50:]

    def _analyze_user_preferences(self, user_behavior: List) -> List[Dict[str, Any]]:
        """分析用户偏好"""
        preferences = defaultdict(int)
        
        for behavior in user_behavior:
            content = behavior['content']
            
            # 分析类型偏好
            if 'genres' in content:
                for genre in content['genres']:
                    preferences[f'genre:{genre}'] += 1
            
            # 分析导演偏好
            if 'directors' in content:
                for director in content['directors']:
                    preferences[f'director:{director}'] += 1
        
        # 转换为排序列表
        sorted_preferences = [
            {'type': k.split(':')[0], 'value': k.split(':')[1], 'count': v}
            for k, v in sorted(preferences.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return sorted_preferences

    def _find_similar_users(self, user_id: str) -> List[str]:
        """寻找相似用户"""
        # 简化实现：基于共同观看内容
        # 实际项目中可以使用更复杂的相似度算法
        
        current_user_behavior = set(
            f"{b['content'].get('id')}-{b['content'].get('title')}" 
            for b in self.user_behavior.get(user_id, [])
        )
        
        similar_users = []
        
        for other_user_id, other_behavior in self.user_behavior.items():
            if other_user_id == user_id:
                continue
            
            other_user_content = set(
                f"{b['content'].get('id')}-{b['content'].get('title')}" 
                for b in other_behavior
            )
            
            similarity = len(current_user_behavior & other_user_content) / len(
                current_user_behavior | other_user_content
            ) if (current_user_behavior | other_user_content) else 0
            
            if similarity > 0.3:  # 相似度阈值
                similar_users.append((other_user_id, similarity))
        
        # 按相似度排序
        similar_users.sort(key=lambda x: x[1], reverse=True)
        
        return [user_id for user_id, _ in similar_users]

    def _merge_and_deduplicate(self, results: List[List[Dict]]) -> List[Dict[str, Any]]:
        """合并和去重数据"""
        seen_ids = set()
        merged_data = []
        
        for result in results:
            if isinstance(result, Exception):
                continue
            
            for item in result:
                # 使用唯一标识符去重
                item_id = self._generate_item_id(item)
                
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    merged_data.append(item)
        
        return merged_data

    def _smart_sort(self, data: List[Dict], chart_type: str) -> List[Dict[str, Any]]:
        """智能排序"""
        if chart_type.endswith('popular') or chart_type == 'trending':
            # 按流行度排序
            return sorted(data, key=lambda x: (
                float(x.get('rating', 0)) * float(x.get('rating_count', 1)),
                x.get('data_source_weight', 1)
            ), reverse=True)
        
        elif chart_type.endswith('rated'):
            # 按评分排序
            return sorted(data, key=lambda x: (
                float(x.get('rating', 0)),
                float(x.get('rating_count', 1))
            ), reverse=True)
        
        elif 'top' in chart_type:
            # 按排名排序
            return sorted(data, key=lambda x: int(x.get('rank', 999)))
        
        else:
            # 默认按数据源权重排序
            return sorted(data, key=lambda x: x.get('data_source_weight', 1), reverse=True)

    def _relevance_sort(self, data: List[Dict], query: str) -> List[Dict[str, Any]]:
        """相关性排序"""
        query_lower = query.lower()
        
        def relevance_score(item):
            score = 0
            title = item.get('title', '').lower()
            
            if query_lower in title:
                score += 10
            elif title.startswith(query_lower):
                score += 8
            elif query_lower in title.split():
                score += 6
            
            # 考虑评分和流行度
            score += float(item.get('rating', 0)) * 0.5
            score += min(float(item.get('rating_count', 0)) / 1000, 5)
            
            return score
        
        return sorted(data, key=relevance_score, reverse=True)

    def _merge_and_weight_recommendations(self, recommendations: List[Dict], 
                                        user_behavior: List) -> List[Dict[str, Any]]:
        """合并和加权推荐结果"""
        scored_items = defaultdict(float)
        
        for item in recommendations:
            item_id = self._generate_item_id(item)
            
            # 基础分数
            base_score = float(item.get('rating', 0)) * 0.1
            base_score += min(float(item.get('rating_count', 0)) / 10000, 1)
            
            # 避免重复推荐用户已经看过的内容
            if any(b['content'].get('id') == item.get('id') for b in user_behavior):
                base_score *= 0.1
            
            scored_items[item_id] = max(scored_items[item_id], base_score)
        
        # 转换为列表并排序
        sorted_items = [
            {'item': item, 'score': score}
            for item, score in sorted(scored_items.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return [item['item'] for item in sorted_items]

    def _calculate_source_weight(self, source_name: str, chart_type: str) -> float:
        """计算数据源权重"""
        weights = {
            'tmdb': 1.0,
            'douban': 0.9,
            'imdb': 0.8,
            'netflix': 0.7
        }
        
        base_weight = weights.get(source_name, 0.5)
        
        # 根据榜单类型调整权重
        type_weights = {
            'top_250': 1.2 if source_name == 'imdb' else 0.8,
            'popular': 1.1 if source_name == 'tmdb' else 0.9,
            'trending': 1.0
        }
        
        for pattern, weight in type_weights.items():
            if pattern in chart_type:
                base_weight *= weight
                break
        
        return base_weight

    def _calculate_relevance_score(self, item: Dict, query: str) -> float:
        """计算相关性分数"""
        score = 0
        query_lower = query.lower()
        
        # 标题匹配
        title = item.get('title', '').lower()
        if query_lower == title:
            score += 10
        elif query_lower in title:
            score += 8
        
        # 类型匹配
        genres = [g.lower() for g in item.get('genres', [])]
        if query_lower in genres:
            score += 5
        
        return score

    def _generate_item_id(self, item: Dict) -> str:
        """生成项目唯一ID"""
        # 使用标题和年份作为唯一标识
        title = item.get('title', '').replace(' ', '_').lower()
        year = item.get('year', 'unknown')
        return f"{title}_{year}"

    def _generate_cache_key(self, prefix: str, *args) -> str:
        """生成缓存键"""
        key_string = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_string.encode()).hexdigest()

    async def _get_cached_data(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """从缓存获取数据"""
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            self.logger.warning(f"缓存读取失败: {e}")
        
        return None

    async def _cache_data(self, cache_key: str, data: List[Dict[str, Any]], ttl: int):
        """缓存数据"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(cache_key, ttl, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            self.logger.warning(f"缓存写入失败: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            'status': 'healthy',
            'data_sources': {},
            'cache_status': 'unknown',
            'recommendation_engine': 'operational'
        }
        
        # 检查数据源
        for name, source in self.data_sources.items():
            try:
                source_health = await source.health_check()
                health_status['data_sources'][name] = source_health
            except Exception as e:
                health_status['data_sources'][name] = {
                    'status': 'error',
                    'message': str(e)
                }
        
        # 检查缓存
        if self.redis_client:
            try:
                self.redis_client.ping()
                health_status['cache_status'] = 'healthy'
            except Exception as e:
                health_status['cache_status'] = 'error'
                health_status['cache_message'] = str(e)
        
        return health_status