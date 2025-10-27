#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能推荐系统
基于用户行为和AI分析的个性化媒体推荐
"""

import json
import time
import random
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta


class AIRecommender:
    """AI智能推荐系统"""
    
    def __init__(self):
        self.user_profiles = {}
        self.media_database = {}
        self.recommendation_history = {}
        self.user_preferences_file = "user_preferences.json"
        self.media_database_file = "media_database.json"
        
        self._load_user_preferences()
        self._load_media_database()
    
    def _load_user_preferences(self):
        """加载用户偏好数据"""
        try:
            with open(self.user_preferences_file, 'r', encoding='utf-8') as f:
                self.user_profiles = json.load(f)
        except:
            self.user_profiles = {}
    
    def _save_user_preferences(self):
        """保存用户偏好数据"""
        try:
            with open(self.user_preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_profiles, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def _load_media_database(self):
        """加载媒体数据库"""
        try:
            with open(self.media_database_file, 'r', encoding='utf-8') as f:
                self.media_database = json.load(f)
        except:
            # 初始化示例媒体数据库
            self.media_database = self._initialize_sample_database()
            self._save_media_database()
    
    def _save_media_database(self):
        """保存媒体数据库"""
        try:
            with open(self.media_database_file, 'w', encoding='utf-8') as f:
                json.dump(self.media_database, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def _initialize_sample_database(self) -> Dict[str, Any]:
        """初始化示例媒体数据库"""
        return {
            "movies": [
                {
                    "id": "movie_001",
                    "title": "复仇者联盟4：终局之战",
                    "genres": ["动作", "科幻", "冒险"],
                    "year": 2019,
                    "rating": 8.4,
                    "duration": 181,
                    "quality": "4K",
                    "tags": ["漫威", "超级英雄", "史诗"]
                },
                {
                    "id": "movie_002", 
                    "title": "泰坦尼克号",
                    "genres": ["爱情", "剧情", "灾难"],
                    "year": 1997,
                    "rating": 9.1,
                    "duration": 194,
                    "quality": "1080P",
                    "tags": ["经典", "浪漫", "史诗爱情"]
                },
                {
                    "id": "movie_003",
                    "title": "盗梦空间",
                    "genres": ["科幻", "动作", "悬疑"],
                    "year": 2010,
                    "rating": 9.3,
                    "duration": 148,
                    "quality": "1080P", 
                    "tags": ["诺兰", "烧脑", "梦境"]
                }
            ],
            "tv_shows": [
                {
                    "id": "tv_001",
                    "title": "权力的游戏",
                    "genres": ["奇幻", "剧情", "冒险"],
                    "seasons": 8,
                    "rating": 9.3,
                    "tags": ["史诗", "中世纪", "权力斗争"]
                },
                {
                    "id": "tv_002",
                    "title": "老友记",
                    "genres": ["喜剧", "爱情", "情景剧"],
                    "seasons": 10,
                    "rating": 9.0,
                    "tags": ["经典", "友情", "纽约"]
                }
            ]
        }
    
    def record_user_action(self, user_id: str, action_type: str, media_info: Dict[str, Any]):
        """记录用户行为"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                "preferences": {},
                "watch_history": [],
                "search_history": [],
                "ratings": {},
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
        
        user_profile = self.user_profiles[user_id]
        user_profile["last_active"] = datetime.now().isoformat()
        
        if action_type == "watch":
            # 记录观看历史
            watch_record = {
                "media_id": media_info.get("id"),
                "media_title": media_info.get("title"),
                "genres": media_info.get("genres", []),
                "timestamp": datetime.now().isoformat(),
                "duration_watched": media_info.get("duration_watched", 0),
                "completed": media_info.get("completed", False)
            }
            user_profile["watch_history"].append(watch_record)
            
            # 更新用户偏好
            self._update_user_preferences(user_id, media_info)
            
        elif action_type == "search":
            # 记录搜索历史
            search_record = {
                "query": media_info.get("query"),
                "timestamp": datetime.now().isoformat(),
                "results_count": media_info.get("results_count", 0)
            }
            user_profile["search_history"].append(search_record)
            
        elif action_type == "rate":
            # 记录评分
            media_id = media_info.get("id")
            rating = media_info.get("rating")
            if media_id and rating:
                user_profile["ratings"][media_id] = {
                    "rating": rating,
                    "timestamp": datetime.now().isoformat()
                }
        
        self._save_user_preferences()
    
    def _update_user_preferences(self, user_id: str, media_info: Dict[str, Any]):
        """更新用户偏好"""
        user_profile = self.user_profiles[user_id]
        preferences = user_profile.setdefault("preferences", {})
        
        # 更新类型偏好
        genres = media_info.get("genres", [])
        for genre in genres:
            preferences[genre] = preferences.get(genre, 0) + 1
        
        # 更新质量偏好
        quality = media_info.get("quality", "")
        if quality:
            preferences[f"quality_{quality}"] = preferences.get(f"quality_{quality}", 0) + 1
        
        # 更新年代偏好
        year = media_info.get("year")
        if year:
            decade = (year // 10) * 10
            preferences[f"decade_{decade}s"] = preferences.get(f"decade_{decade}s", 0) + 1
    
    def get_recommendations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取个性化推荐"""
        if user_id not in self.user_profiles:
            return self._get_popular_recommendations(limit)
        
        user_profile = self.user_profiles[user_id]
        
        # 基于用户偏好的推荐算法
        recommendations = []
        
        # 1. 基于观看历史的推荐
        watch_based = self._recommend_based_on_watch_history(user_profile)
        recommendations.extend(watch_based)
        
        # 2. 基于搜索历史的推荐
        search_based = self._recommend_based_on_search_history(user_profile)
        recommendations.extend(search_based)
        
        # 3. 基于评分的推荐
        rating_based = self._recommend_based_on_ratings(user_profile)
        recommendations.extend(rating_based)
        
        # 4. 热门推荐（补充）
        if len(recommendations) < limit:
            popular = self._get_popular_recommendations(limit - len(recommendations))
            recommendations.extend(popular)
        
        # 去重和排序
        unique_recommendations = self._deduplicate_recommendations(recommendations)
        sorted_recommendations = sorted(
            unique_recommendations, 
            key=lambda x: x.get("recommendation_score", 0), 
            reverse=True
        )
        
        # 记录推荐历史
        self._record_recommendation_history(user_id, sorted_recommendations[:limit])
        
        return sorted_recommendations[:limit]
    
    def _recommend_based_on_watch_history(self, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于观看历史的推荐"""
        recommendations = []
        watch_history = user_profile.get("watch_history", [])
        
        if not watch_history:
            return recommendations
        
        # 分析最近观看的媒体
        recent_watches = watch_history[-5:]  # 最近5个
        
        for watch in recent_watches:
            media_id = watch.get("media_id")
            if media_id:
                # 查找相似媒体
                similar_media = self._find_similar_media(media_id)
                recommendations.extend(similar_media)
        
        return recommendations
    
    def _recommend_based_on_search_history(self, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于搜索历史的推荐"""
        recommendations = []
        search_history = user_profile.get("search_history", [])
        
        if not search_history:
            return recommendations
        
        # 分析最近的搜索查询
        recent_searches = search_history[-3:]  # 最近3个搜索
        
        for search in recent_searches:
            query = search.get("query", "")
            if query:
                # 基于搜索查询推荐相关媒体
                query_based = self._recommend_based_on_query(query)
                recommendations.extend(query_based)
        
        return recommendations
    
    def _recommend_based_on_ratings(self, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于评分的推荐"""
        recommendations = []
        ratings = user_profile.get("ratings", {})
        
        if not ratings:
            return recommendations
        
        # 找出用户评分高的媒体
        high_rated_media = [
            media_id for media_id, rating_info in ratings.items() 
            if rating_info.get("rating", 0) >= 4
        ]
        
        for media_id in high_rated_media:
            # 推荐相似的高质量媒体
            similar_high_quality = self._find_similar_high_quality_media(media_id)
            recommendations.extend(similar_high_quality)
        
        return recommendations
    
    def _find_similar_media(self, media_id: str) -> List[Dict[str, Any]]:
        """查找相似媒体"""
        # 在实际实现中，这里会使用更复杂的相似度算法
        # 这里使用简单的基于类型和标签的匹配
        
        target_media = self._find_media_by_id(media_id)
        if not target_media:
            return []
        
        similar_media = []
        target_genres = set(target_media.get("genres", []))
        target_tags = set(target_media.get("tags", []))
        
        # 在所有媒体中查找相似项
        for media_type, media_list in self.media_database.items():
            for media in media_list:
                if media.get("id") == media_id:
                    continue
                
                media_genres = set(media.get("genres", []))
                media_tags = set(media.get("tags", []))
                
                # 计算相似度分数
                genre_similarity = len(target_genres & media_genres) / len(target_genres | media_genres) if target_genres else 0
                tag_similarity = len(target_tags & media_tags) / len(target_tags | media_tags) if target_tags else 0
                
                similarity_score = (genre_similarity + tag_similarity) / 2
                
                if similarity_score > 0.3:  # 相似度阈值
                    recommendation = media.copy()
                    recommendation["recommendation_type"] = "similar_content"
                    recommendation["recommendation_score"] = similarity_score
                    recommendation["similarity_reason"] = f"与'{target_media.get('title')}'相似"
                    similar_media.append(recommendation)
        
        return similar_media
    
    def _recommend_based_on_query(self, query: str) -> List[Dict[str, Any]]:
        """基于搜索查询推荐"""
        recommendations = []
        
        # 简单的关键词匹配
        for media_type, media_list in self.media_database.items():
            for media in media_list:
                title = media.get("title", "").lower()
                genres = [g.lower() for g in media.get("genres", [])]
                tags = [t.lower() for t in media.get("tags", [])]
                
                query_lower = query.lower()
                
                # 检查标题、类型、标签是否包含查询关键词
                if (query_lower in title or 
                    any(query_lower in genre for genre in genres) or
                    any(query_lower in tag for tag in tags)):
                    
                    recommendation = media.copy()
                    recommendation["recommendation_type"] = "search_related"
                    recommendation["recommendation_score"] = 0.8
                    recommendation["similarity_reason"] = f"与搜索'{query}'相关"
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _find_similar_high_quality_media(self, media_id: str) -> List[Dict[str, Any]]:
        """查找相似的高质量媒体"""
        similar_media = self._find_similar_media(media_id)
        
        # 过滤高质量媒体（评分>=8）
        high_quality = [
            media for media in similar_media 
            if media.get("rating", 0) >= 8.0
        ]
        
        for media in high_quality:
            media["recommendation_type"] = "high_quality_similar"
            media["recommendation_score"] = media.get("recommendation_score", 0) + 0.2
            media["similarity_reason"] = "高质量相似内容"
        
        return high_quality
    
    def _get_popular_recommendations(self, limit: int) -> List[Dict[str, Any]]:
        """获取热门推荐"""
        recommendations = []
        
        # 合并所有媒体并按评分排序
        all_media = []
        for media_type, media_list in self.media_database.items():
            for media in media_list:
                media_copy = media.copy()
                media_copy["media_type"] = media_type
                all_media.append(media_copy)
        
        # 按评分排序
        popular_media = sorted(all_media, key=lambda x: x.get("rating", 0), reverse=True)
        
        for media in popular_media[:limit]:
            media["recommendation_type"] = "popular"
            media["recommendation_score"] = media.get("rating", 0) / 10
            media["similarity_reason"] = "热门内容"
            recommendations.append(media)
        
        return recommendations
    
    def _deduplicate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重推荐结果"""
        seen_ids = set()
        unique_recommendations = []
        
        for rec in recommendations:
            media_id = rec.get("id")
            if media_id not in seen_ids:
                seen_ids.add(media_id)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _record_recommendation_history(self, user_id: str, recommendations: List[Dict[str, Any]]):
        """记录推荐历史"""
        if user_id not in self.recommendation_history:
            self.recommendation_history[user_id] = []
        
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "recommendations": [
                {
                    "media_id": rec.get("id"),
                    "media_title": rec.get("title"),
                    "recommendation_score": rec.get("recommendation_score", 0),
                    "recommendation_type": rec.get("recommendation_type", "")
                }
                for rec in recommendations
            ]
        }
        
        self.recommendation_history[user_id].append(history_entry)
    
    def _find_media_by_id(self, media_id: str) -> Optional[Dict[str, Any]]:
        """根据ID查找媒体"""
        for media_type, media_list in self.media_database.items():
            for media in media_list:
                if media.get("id") == media_id:
                    return media
        return None
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户画像"""
        if user_id not in self.user_profiles:
            return {"error": "用户不存在"}
        
        profile = self.user_profiles[user_id].copy()
        
        # 计算用户偏好摘要
        preferences = profile.get("preferences", {})
        if preferences:
            top_genres = sorted(preferences.items(), key=lambda x: x[1], reverse=True)[:5]
            profile["preference_summary"] = {
                "top_genres": [genre for genre, count in top_genres],
                "total_watched": len(profile.get("watch_history", [])),
                "average_rating": self._calculate_average_rating(profile)
            }
        
        return profile
    
    def _calculate_average_rating(self, profile: Dict[str, Any]) -> float:
        """计算用户平均评分"""
        ratings = profile.get("ratings", {})
        if not ratings:
            return 0.0
        
        total_rating = sum(rating_info.get("rating", 0) for rating_info in ratings.values())
        return total_rating / len(ratings)
    
    def add_media_to_database(self, media_info: Dict[str, Any]):
        """添加媒体到数据库"""
        media_type = media_info.get("media_type", "movies")
        
        if media_type not in self.media_database:
            self.media_database[media_type] = []
        
        # 生成唯一ID
        if "id" not in media_info:
            media_info["id"] = f"{media_type}_{len(self.media_database[media_type]) + 1:03d}"
        
        self.media_database[media_type].append(media_info)
        self._save_media_database()
    
    def get_recommendation_insights(self, user_id: str) -> Dict[str, Any]:
        """获取推荐洞察"""
        if user_id not in self.user_profiles:
            return {"error": "用户不存在"}
        
        profile = self.user_profiles[user_id]
        recommendations = self.get_recommendations(user_id, 5)
        
        insights = {
            "user_id": user_id,
            "profile_summary": {
                "watch_count": len(profile.get("watch_history", [])),
                "search_count": len(profile.get("search_history", [])),
                "rating_count": len(profile.get("ratings", {})),
                "preference_count": len(profile.get("preferences", {})),
                "last_active": profile.get("last_active")
            },
            "recommendation_analysis": {
                "total_recommendations": len(recommendations),
                "recommendation_types": {},
                "average_score": sum(r.get("recommendation_score", 0) for r in recommendations) / len(recommendations) if recommendations else 0
            }
        }
        
        # 统计推荐类型
        for rec in recommendations:
            rec_type = rec.get("recommendation_type", "unknown")
            insights["recommendation_analysis"]["recommendation_types"][rec_type] = \
                insights["recommendation_analysis"]["recommendation_types"].get(rec_type, 0) + 1
        
        return insights