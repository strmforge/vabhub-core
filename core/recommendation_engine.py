"""
智能推荐引擎
集成MediaMaster的推荐系统精华功能
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class MediaItem:
    """媒体项目数据类"""
    id: str
    title: str
    media_type: str
    genres: List[str]
    languages: List[str]
    rating: float
    popularity: float
    release_year: int


@dataclass
class UserProfile:
    """用户画像数据类"""
    user_id: str
    preferred_genres: List[str]
    preferred_languages: List[str]
    quality_preference: str
    content_rating: str
    watch_history: List[Dict[str, Any]]
    ratings: Dict[str, int]  # media_id -> rating


class RecommendationEngine:
    """智能推荐引擎"""
    
    def __init__(self):
        self.users: Dict[str, UserProfile] = {}
        self.media_items: Dict[str, MediaItem] = {}
        self.watch_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.model_trained = False
        self.last_trained = 0
        
    async def initialize(self):
        """初始化推荐引擎"""
        logger.info("初始化推荐引擎")
        # 加载预训练数据或从数据库加载
        await self._load_initial_data()
        
    async def _load_initial_data(self):
        """加载初始数据"""
        # 这里可以加载预定义的媒体库数据
        # 实际项目中可以从数据库或API加载
        pass
        
    def add_watch_history(self, media_id: str, media_type: str, title: str, 
                         watch_time: int, total_duration: int, 
                         rating: Optional[int] = None, tags: List[str] = None) -> bool:
        """添加观看历史"""
        try:
            history_entry = {
                "media_id": media_id,
                "media_type": media_type,
                "title": title,
                "watch_time": watch_time,
                "total_duration": total_duration,
                "rating": rating,
                "tags": tags or [],
                "timestamp": int(time.time())
            }
            
            # 这里应该关联到具体用户，暂时使用默认用户
            user_id = "default"
            self.watch_history[user_id].append(history_entry)
            
            # 如果提供了评分，更新用户评分
            if rating:
                if user_id not in self.users:
                    self.users[user_id] = UserProfile(
                        user_id=user_id,
                        preferred_genres=[],
                        preferred_languages=[],
                        quality_preference="1080p",
                        content_rating="PG-13",
                        watch_history=[],
                        ratings={}
                    )
                self.users[user_id].ratings[media_id] = rating
                
            logger.info(f"添加观看历史: {title} (ID: {media_id})")
            return True
            
        except Exception as e:
            logger.error(f"添加观看历史失败: {str(e)}")
            return False
            
    def get_watch_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户观看历史"""
        return self.watch_history.get(user_id, [])
        
    def update_user_preferences(self, user_id: str, preferred_genres: List[str],
                              preferred_languages: List[str], quality_preference: str,
                              content_rating: str) -> bool:
        """更新用户偏好设置"""
        try:
            if user_id not in self.users:
                self.users[user_id] = UserProfile(
                    user_id=user_id,
                    preferred_genres=preferred_genres,
                    preferred_languages=preferred_languages,
                    quality_preference=quality_preference,
                    content_rating=content_rating,
                    watch_history=self.watch_history.get(user_id, []),
                    ratings={}
                )
            else:
                self.users[user_id].preferred_genres = preferred_genres
                self.users[user_id].preferred_languages = preferred_languages
                self.users[user_id].quality_preference = quality_preference
                self.users[user_id].content_rating = content_rating
                
            logger.info(f"更新用户偏好: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新用户偏好失败: {str(e)}")
            return False
            
    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户偏好设置"""
        if user_id in self.users:
            user = self.users[user_id]
            return {
                "preferred_genres": user.preferred_genres,
                "preferred_languages": user.preferred_languages,
                "quality_preference": user.quality_preference,
                "content_rating": user.content_rating
            }
        return None
        
    def get_recommendations(self, user_id: str, limit: int = 10, 
                          media_type: Optional[str] = None, 
                          exclude_watched: bool = True) -> List[Dict[str, Any]]:
        """获取个性化推荐"""
        try:
            # 获取用户画像
            user_profile = self.users.get(user_id)
            if not user_profile:
                # 如果没有用户画像，返回热门推荐
                return self._get_popular_recommendations(limit, media_type)
                
            # 基于内容的推荐算法
            recommendations = self._content_based_recommendation(
                user_profile, limit, media_type, exclude_watched
            )
            
            # 如果推荐数量不足，补充热门推荐
            if len(recommendations) < limit:
                popular_recs = self._get_popular_recommendations(
                    limit - len(recommendations), media_type
                )
                recommendations.extend(popular_recs)
                
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"获取推荐失败: {str(e)}")
            return []
            
    def _content_based_recommendation(self, user_profile: UserProfile, limit: int,
                                    media_type: Optional[str], exclude_watched: bool) -> List[Dict[str, Any]]:
        """基于内容的推荐算法"""
        recommendations = []
        
        # 这里实现简单的基于内容的推荐
        # 实际项目中可以使用更复杂的算法如协同过滤、矩阵分解等
        
        # 根据用户偏好生成推荐
        for media_id, media_item in self.media_items.items():
            # 过滤条件
            if media_type and media_item.media_type != media_type:
                continue
                
            if exclude_watched and media_id in [h["media_id"] for h in user_profile.watch_history]:
                continue
                
            # 计算相似度分数
            score = self._calculate_similarity_score(media_item, user_profile)
            
            if score > 0:  # 只返回有相似度的项目
                recommendations.append({
                    "media_id": media_id,
                    "title": media_item.title,
                    "media_type": media_item.media_type,
                    "genres": media_item.genres,
                    "rating": media_item.rating,
                    "release_year": media_item.release_year,
                    "similarity_score": score
                })
                
        # 按相似度排序
        recommendations.sort(key=lambda x: x["similarity_score"], reverse=True)
        return recommendations[:limit]
        
    def _calculate_similarity_score(self, media_item: MediaItem, user_profile: UserProfile) -> float:
        """计算媒体项目与用户偏好的相似度"""
        score = 0.0
        
        # 类型匹配
        genre_match = len(set(media_item.genres) & set(user_profile.preferred_genres))
        score += genre_match * 2.0
        
        # 语言匹配
        language_match = len(set(media_item.languages) & set(user_profile.preferred_languages))
        score += language_match * 1.5
        
        # 评分权重
        score += media_item.rating * 0.1
        
        # 流行度权重
        score += media_item.popularity * 0.05
        
        return score
        
    def _get_popular_recommendations(self, limit: int, media_type: Optional[str]) -> List[Dict[str, Any]]:
        """获取热门推荐"""
        popular_items = []
        
        for media_id, media_item in self.media_items.items():
            if media_type and media_item.media_type != media_type:
                continue
                
            popular_items.append({
                "media_id": media_id,
                "title": media_item.title,
                "media_type": media_item.media_type,
                "genres": media_item.genres,
                "rating": media_item.rating,
                "release_year": media_item.release_year,
                "popularity_score": media_item.popularity
            })
            
        # 按流行度排序
        popular_items.sort(key=lambda x: x["popularity_score"], reverse=True)
        return popular_items[:limit]
        
    def get_trending_recommendations(self) -> List[Dict[str, Any]]:
        """获取热门推荐"""
        # 这里可以实现基于时间的热门推荐算法
        # 暂时返回基于流行度的推荐
        return self._get_popular_recommendations(10, None)
        
    def get_similar_recommendations(self, media_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取相似内容推荐"""
        if media_id not in self.media_items:
            return []
            
        target_item = self.media_items[media_id]
        similar_items = []
        
        for other_id, other_item in self.media_items.items():
            if other_id == media_id:
                continue
                
            # 计算相似度
            similarity = self._calculate_item_similarity(target_item, other_item)
            
            similar_items.append({
                "media_id": other_id,
                "title": other_item.title,
                "media_type": other_item.media_type,
                "genres": other_item.genres,
                "rating": other_item.rating,
                "release_year": other_item.release_year,
                "similarity_score": similarity
            })
            
        # 按相似度排序
        similar_items.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar_items[:limit]
        
    def _calculate_item_similarity(self, item1: MediaItem, item2: MediaItem) -> float:
        """计算两个媒体项目的相似度"""
        similarity = 0.0
        
        # 类型相似度
        genre_similarity = len(set(item1.genres) & set(item2.genres)) / len(set(item1.genres) | set(item2.genres))
        similarity += genre_similarity * 0.4
        
        # 语言相似度
        language_similarity = len(set(item1.languages) & set(item2.languages)) / len(set(item1.languages) | set(item2.languages))
        similarity += language_similarity * 0.3
        
        # 评分相似度
        rating_similarity = 1.0 - abs(item1.rating - item2.rating) / 10.0
        similarity += rating_similarity * 0.2
        
        # 年份相似度（相近年份有更高相似度）
        year_diff = abs(item1.release_year - item2.release_year)
        year_similarity = max(0, 1.0 - year_diff / 20.0)
        similarity += year_similarity * 0.1
        
        return similarity
        
    def train_model(self) -> bool:
        """训练推荐模型"""
        try:
            # 这里可以实现模型训练逻辑
            # 实际项目中可以使用机器学习库如scikit-learn、TensorFlow等
            
            logger.info("开始训练推荐模型")
            
            # 模拟训练过程
            time.sleep(2)  # 模拟训练时间
            
            self.model_trained = True
            self.last_trained = int(time.time())
            
            logger.info("推荐模型训练完成")
            return True
            
        except Exception as e:
            logger.error(f"训练推荐模型失败: {str(e)}")
            return False
            
    def get_model_info(self) -> Dict[str, Any]:
        """获取推荐模型信息"""
        return {
            "model_trained": self.model_trained,
            "last_trained": self.last_trained,
            "user_count": len(self.users),
            "media_count": len(self.media_items),
            "algorithm": "content_based + popularity"
        }
        
    def add_feedback(self, user_id: str, media_id: str, feedback_type: str, rating: Optional[int] = None) -> bool:
        """添加推荐反馈"""
        try:
            # 记录用户对推荐的反馈
            # 可以用于改进推荐算法
            
            logger.info(f"添加推荐反馈: 用户 {user_id} 对媒体 {media_id} 的 {feedback_type} 反馈")
            
            if rating:
                self.update_user_preferences(user_id, [], [], "", "")
                self.users[user_id].ratings[media_id] = rating
                
            return True
            
        except Exception as e:
            logger.error(f"添加推荐反馈失败: {str(e)}")
            return False
            
    def get_stats(self) -> Dict[str, Any]:
        """获取推荐系统统计信息"""
        total_watch_time = sum(
            sum(h["watch_time"] for h in histories) 
            for histories in self.watch_history.values()
        )
        
        return {
            "total_users": len(self.users),
            "total_media_items": len(self.media_items),
            "total_watch_records": sum(len(histories) for histories in self.watch_history.values()),
            "total_watch_time": total_watch_time,
            "average_rating": self._calculate_average_rating(),
            "model_status": "trained" if self.model_trained else "not_trained"
        }
        
    def _calculate_average_rating(self) -> float:
        """计算平均评分"""
        all_ratings = []
        for user in self.users.values():
            all_ratings.extend(user.ratings.values())
            
        if not all_ratings:
            return 0.0
            
        return sum(all_ratings) / len(all_ratings)
        
    def get_status(self) -> Dict[str, Any]:
        """获取推荐系统状态"""
        return {
            "engine_status": "running",
            "model_status": "trained" if self.model_trained else "not_trained",
            "user_count": len(self.users),
            "media_count": len(self.media_items),
            "last_trained": self.last_trained
        }