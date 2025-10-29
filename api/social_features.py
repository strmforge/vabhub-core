"""
社交功能模块
提供用户评分、评论、收藏、分享等社交功能
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import json
import hashlib
from enum import Enum


class SocialAction(Enum):
    """社交行为类型"""
    RATE = "rate"
    COMMENT = "comment"
    FAVORITE = "favorite"
    SHARE = "share"
    VIEW = "view"
    WATCHLIST = "watchlist"


class SocialFeatures:
    """社交功能管理器"""
    
    def __init__(self, redis_client=None):
        self.logger = logging.getLogger(__name__)
        self.redis_client = redis_client
        
        # 用户数据存储
        self.user_ratings = defaultdict(dict)  # {user_id: {content_id: rating}}
        self.user_comments = defaultdict(list)  # {user_id: [comments]}
        self.user_favorites = defaultdict(set)  # {user_id: {content_ids}}
        self.user_watchlist = defaultdict(set)  # {user_id: {content_ids}}
        
        # 内容统计数据
        self.content_stats = defaultdict(dict)  # {content_id: {ratings_count, avg_rating, comments_count}}
        
        # 社交关系
        self.user_follows = defaultdict(set)  # {user_id: {followed_user_ids}}
        
        # 缓存配置
        self.cache_ttl = {
            'content_stats': 3600,  # 1小时
            'user_activity': 1800,  # 30分钟
            'social_feed': 900,  # 15分钟
        }

    async def rate_content(self, user_id: str, content_id: str, rating: float, 
                          content_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """用户评分内容"""
        try:
            # 验证评分范围
            if not (0 <= rating <= 10):
                raise ValueError("评分必须在0-10之间")
            
            # 记录评分
            previous_rating = self.user_ratings[user_id].get(content_id)
            self.user_ratings[user_id][content_id] = rating
            
            # 更新内容统计
            await self._update_content_stats(content_id, rating, previous_rating)
            
            # 记录用户行为
            await self._record_user_activity(
                user_id, SocialAction.RATE, content_id, content_data, 
                metadata={'rating': rating, 'previous_rating': previous_rating}
            )
            
            return {
                'success': True,
                'message': '评分成功',
                'rating': rating,
                'previous_rating': previous_rating,
                'content_stats': await self.get_content_stats(content_id)
            }
            
        except Exception as e:
            self.logger.error(f"评分失败: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def add_comment(self, user_id: str, content_id: str, comment_text: str,
                         content_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """添加评论"""
        try:
            # 验证评论内容
            if not comment_text.strip():
                raise ValueError("评论内容不能为空")
            
            if len(comment_text) > 1000:
                raise ValueError("评论内容不能超过1000字符")
            
            # 创建评论
            comment = {
                'id': self._generate_comment_id(user_id, content_id),
                'user_id': user_id,
                'content_id': content_id,
                'text': comment_text.strip(),
                'timestamp': datetime.now().isoformat(),
                'likes': 0,
                'replies': [],
                'user_display_name': f"用户{user_id[-4:]}"  # 简化显示名
            }
            
            # 存储评论
            self.user_comments[user_id].append(comment)
            
            # 更新内容统计
            await self._update_content_comments_count(content_id)
            
            # 记录用户行为
            await self._record_user_activity(
                user_id, SocialAction.COMMENT, content_id, content_data,
                metadata={'comment_id': comment['id'], 'text_preview': comment_text[:50]}
            )
            
            return {
                'success': True,
                'message': '评论成功',
                'comment': comment,
                'content_stats': await self.get_content_stats(content_id)
            }
            
        except Exception as e:
            self.logger.error(f"评论失败: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def favorite_content(self, user_id: str, content_id: str, 
                             content_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """收藏内容"""
        try:
            if content_id in self.user_favorites[user_id]:
                # 取消收藏
                self.user_favorites[user_id].remove(content_id)
                action = 'unfavorite'
            else:
                # 添加收藏
                self.user_favorites[user_id].add(content_id)
                action = 'favorite'
            
            # 记录用户行为
            await self._record_user_activity(
                user_id, SocialAction.FAVORITE, content_id, content_data,
                metadata={'action': action}
            )
            
            return {
                'success': True,
                'message': f"{'收藏' if action == 'favorite' else '取消收藏'}成功",
                'action': action,
                'favorites_count': len(self.user_favorites[user_id])
            }
            
        except Exception as e:
            self.logger.error(f"收藏操作失败: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def add_to_watchlist(self, user_id: str, content_id: str,
                              content_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """添加到观看列表"""
        try:
            if content_id in self.user_watchlist[user_id]:
                # 从观看列表移除
                self.user_watchlist[user_id].remove(content_id)
                action = 'remove'
            else:
                # 添加到观看列表
                self.user_watchlist[user_id].add(content_id)
                action = 'add'
            
            # 记录用户行为
            await self._record_user_activity(
                user_id, SocialAction.WATCHLIST, content_id, content_data,
                metadata={'action': action}
            )
            
            return {
                'success': True,
                'message': f"{'添加到' if action == 'add' else '从'}观看列表{'' if action == 'add' else '移除'}成功",
                'action': action,
                'watchlist_count': len(self.user_watchlist[user_id])
            }
            
        except Exception as e:
            self.logger.error(f"观看列表操作失败: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def share_content(self, user_id: str, content_id: str, 
                           platform: str, content_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """分享内容"""
        try:
            # 生成分享链接
            share_url = self._generate_share_url(content_id, platform)
            
            # 记录用户行为
            await self._record_user_activity(
                user_id, SocialAction.SHARE, content_id, content_data,
                metadata={'platform': platform, 'share_url': share_url}
            )
            
            return {
                'success': True,
                'message': '分享成功',
                'share_url': share_url,
                'platform': platform
            }
            
        except Exception as e:
            self.logger.error(f"分享失败: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def get_content_stats(self, content_id: str) -> Dict[str, Any]:
        """获取内容统计信息"""
        cache_key = self._generate_cache_key('content_stats', content_id)
        
        # 尝试从缓存获取
        cached_stats = await self._get_cached_data(cache_key)
        if cached_stats:
            return cached_stats
        
        stats = self.content_stats.get(content_id, {})
        
        # 计算默认值
        if 'ratings_count' not in stats:
            stats['ratings_count'] = 0
        if 'avg_rating' not in stats:
            stats['avg_rating'] = 0.0
        if 'comments_count' not in stats:
            stats['comments_count'] = 0
        if 'favorites_count' not in stats:
            stats['favorites_count'] = self._count_favorites(content_id)
        
        # 缓存结果
        await self._cache_data(cache_key, stats, self.cache_ttl['content_stats'])
        
        return stats

    async def get_user_activity(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取用户活动记录"""
        cache_key = self._generate_cache_key('user_activity', user_id, limit)
        
        # 尝试从缓存获取
        cached_activity = await self._get_cached_data(cache_key)
        if cached_activity:
            return cached_activity
        
        # 获取用户活动（简化实现）
        activities = []
        
        # 添加评分活动
        for content_id, rating in self.user_ratings[user_id].items():
            activities.append({
                'type': 'rate',
                'user_id': user_id,
                'content_id': content_id,
                'rating': rating,
                'timestamp': datetime.now().isoformat(),
                'action_text': f"评分为 {rating} 分"
            })
        
        # 添加评论活动
        for comment in self.user_comments[user_id][-10:]:  # 最近10条评论
            activities.append({
                'type': 'comment',
                'user_id': user_id,
                'content_id': comment['content_id'],
                'comment_preview': comment['text'][:50],
                'timestamp': comment['timestamp'],
                'action_text': "发表了评论"
            })
        
        # 按时间排序
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 缓存结果
        await self._cache_data(cache_key, activities[:limit], self.cache_ttl['user_activity'])
        
        return activities[:limit]

    async def get_social_feed(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取社交动态"""
        cache_key = self._generate_cache_key('social_feed', user_id, limit)
        
        # 尝试从缓存获取
        cached_feed = await self._get_cached_data(cache_key)
        if cached_feed:
            return cached_feed
        
        # 获取关注用户的动态
        followed_users = self.user_follows[user_id]
        feed_items = []
        
        for followed_user in followed_users:
            # 获取关注用户的活动
            user_activities = await self.get_user_activity(followed_user, limit=10)
            
            for activity in user_activities:
                feed_items.append({
                    **activity,
                    'is_followed': True,
                    'followed_user_id': followed_user
                })
        
        # 添加热门内容
        popular_content = await self._get_popular_content(limit=5)
        for content in popular_content:
            feed_items.append({
                'type': 'popular',
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'action_text': '热门内容推荐'
            })
        
        # 按时间排序
        feed_items.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 缓存结果
        await self._cache_data(cache_key, feed_items[:limit], self.cache_ttl['social_feed'])
        
        return feed_items[:limit]

    async def follow_user(self, user_id: str, target_user_id: str) -> Dict[str, Any]:
        """关注用户"""
        try:
            if user_id == target_user_id:
                raise ValueError("不能关注自己")
            
            if target_user_id in self.user_follows[user_id]:
                # 取消关注
                self.user_follows[user_id].remove(target_user_id)
                action = 'unfollow'
            else:
                # 关注
                self.user_follows[user_id].add(target_user_id)
                action = 'follow'
            
            return {
                'success': True,
                'message': f"{'关注' if action == 'follow' else '取消关注'}成功",
                'action': action,
                'following_count': len(self.user_follows[user_id])
            }
            
        except Exception as e:
            self.logger.error(f"关注操作失败: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户个人资料"""
        return {
            'user_id': user_id,
            'display_name': f"用户{user_id[-4:]}",
            'ratings_count': len(self.user_ratings[user_id]),
            'comments_count': len(self.user_comments[user_id]),
            'favorites_count': len(self.user_favorites[user_id]),
            'watchlist_count': len(self.user_watchlist[user_id]),
            'following_count': len(self.user_follows[user_id]),
            'joined_date': datetime.now().isoformat()  # 简化实现
        }

    async def _update_content_stats(self, content_id: str, new_rating: float, 
                                  previous_rating: Optional[float] = None):
        """更新内容统计"""
        if content_id not in self.content_stats:
            self.content_stats[content_id] = {
                'ratings_count': 0,
                'total_rating': 0.0,
                'avg_rating': 0.0
            }
        
        stats = self.content_stats[content_id]
        
        if previous_rating is not None:
            # 更新现有评分
            stats['total_rating'] = stats['total_rating'] - previous_rating + new_rating
        else:
            # 新增评分
            stats['ratings_count'] += 1
            stats['total_rating'] += new_rating
        
        # 计算平均分
        if stats['ratings_count'] > 0:
            stats['avg_rating'] = round(stats['total_rating'] / stats['ratings_count'], 1)
        
        # 清除缓存
        cache_key = self._generate_cache_key('content_stats', content_id)
        await self._clear_cache(cache_key)

    async def _update_content_comments_count(self, content_id: str):
        """更新内容评论计数"""
        if content_id not in self.content_stats:
            self.content_stats[content_id] = {}
        
        # 计算该内容的评论总数
        count = sum(1 for user_comments in self.user_comments.values() 
                   for comment in user_comments if comment['content_id'] == content_id)
        
        self.content_stats[content_id]['comments_count'] = count
        
        # 清除缓存
        cache_key = self._generate_cache_key('content_stats', content_id)
        await self._clear_cache(cache_key)

    def _count_favorites(self, content_id: str) -> int:
        """统计内容的收藏数"""
        return sum(1 for favorites in self.user_favorites.values() 
                  if content_id in favorites)

    async def _get_popular_content(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取热门内容（简化实现）"""
        # 按评分和评论数排序
        popular_items = []
        
        for content_id, stats in self.content_stats.items():
            if stats.get('ratings_count', 0) > 0:
                score = stats.get('avg_rating', 0) * stats.get('ratings_count', 1)
                popular_items.append({
                    'content_id': content_id,
                    'score': score,
                    'stats': stats
                })
        
        popular_items.sort(key=lambda x: x['score'], reverse=True)
        
        return [
            {
                'id': item['content_id'],
                'title': f"内容{item['content_id'][-6:]}",  # 简化标题
                'rating': item['stats'].get('avg_rating', 0),
                'ratings_count': item['stats'].get('ratings_count', 0)
            }
            for item in popular_items[:limit]
        ]

    async def _record_user_activity(self, user_id: str, action: SocialAction, 
                                  content_id: str, content_data: Dict[str, Any] = None,
                                  metadata: Dict[str, Any] = None):
        """记录用户行为"""
        # 这里可以集成到数据聚合服务的用户行为追踪
        activity = {
            'user_id': user_id,
            'action': action.value,
            'content_id': content_id,
            'content_data': content_data or {},
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }
        
        # 在实际项目中，这里应该存储到数据库或消息队列
        self.logger.info(f"用户行为记录: {activity}")

    def _generate_comment_id(self, user_id: str, content_id: str) -> str:
        """生成评论ID"""
        timestamp = int(datetime.now().timestamp() * 1000)
        return f"comment_{user_id}_{content_id}_{timestamp}"

    def _generate_share_url(self, content_id: str, platform: str) -> str:
        """生成分享链接"""
        base_url = "https://vabhub.example.com"
        
        if platform == 'wechat':
            return f"{base_url}/share/wechat/{content_id}"
        elif platform == 'weibo':
            return f"{base_url}/share/weibo/{content_id}"
        elif platform == 'qq':
            return f"{base_url}/share/qq/{content_id}"
        else:
            return f"{base_url}/content/{content_id}"

    def _generate_cache_key(self, prefix: str, *args) -> str:
        """生成缓存键"""
        key_string = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_string.encode()).hexdigest()

    async def _get_cached_data(self, cache_key: str) -> Optional[Any]:
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

    async def _cache_data(self, cache_key: str, data: Any, ttl: int):
        """缓存数据"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(cache_key, ttl, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            self.logger.warning(f"缓存写入失败: {e}")

    async def _clear_cache(self, cache_key: str):
        """清除缓存"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.delete(cache_key)
        except Exception as e:
            self.logger.warning(f"缓存清除失败: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'healthy',
            'users_count': len(self.user_ratings),
            'content_count': len(self.content_stats),
            'total_ratings': sum(len(ratings) for ratings in self.user_ratings.values()),
            'total_comments': sum(len(comments) for comments in self.user_comments.values()),
            'cache_enabled': self.redis_client is not None
        }