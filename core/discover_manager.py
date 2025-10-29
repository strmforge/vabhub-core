"""
VabHub 发现推荐管理器
基于MoviePilot推荐架构优化的发现推荐系统
支持影视榜单、音乐榜单、个性化推荐等功能
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import logging

from .search_manager import SearchResult, SearchType, SearchSource
from ..utils.cache import cached, FileCache
from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)

class DiscoverCategory(Enum):
    """发现分类"""
    MOVIE = "movie"
    TV = "tv"
    ANIME = "anime"
    MUSIC = "music"
    ALL = "all"

class DiscoverSource(Enum):
    """发现数据源"""
    TMDB = "tmdb"
    DOUBAN = "douban"
    BANGUMI = "bangumi"
    NETFLIX_TOP10 = "netflix_top10"
    IMDB_DATASETS = "imdb_datasets"
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    TME_UNI_CHART = "tme_uni_chart"
    BILLBOARD_CHINA_TME = "billboard_china_tme"

class DiscoverItem:
    """发现项数据模型"""
    
    def __init__(self, 
                 title: str,
                 category: DiscoverCategory,
                 source: DiscoverSource,
                 score: float = 0.0,
                 metadata: Dict[str, Any] = None,
                 poster_url: str = None,
                 description: str = None,
                 release_date: str = None,
                 rating: float = 0.0):
        self.title = title
        self.category = category
        self.source = source
        self.score = score
        self.metadata = metadata or {}
        self.poster_url = poster_url
        self.description = description
        self.release_date = release_date
        self.rating = rating
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "title": self.title,
            "category": self.category.value,
            "source": self.source.value,
            "score": self.score,
            "metadata": self.metadata,
            "poster_url": self.poster_url,
            "description": self.description,
            "release_date": self.release_date,
            "rating": self.rating
        }

class DiscoverManager(metaclass=Singleton):
    """
    发现推荐管理器
    基于MoviePilot推荐架构优化的发现推荐系统
    """
    
    # 推荐缓存时间（24小时）
    DISCOVER_TTL = 24 * 3600
    # 缓存区域
    DISCOVER_CACHE_REGION = "discover"
    # 最大缓存页数
    CACHE_MAX_PAGES = 5
    
    def __init__(self):
        self.cache_backend = FileCache(base="cache/discover")
        
        # 推荐方法优先级配置
        self.recommend_methods_priority = {
            # 最高优先级：影视类榜单 - Netflix Top 10（高时效性）和IMDb Datasets（高权威性）
            self.netflix_top10: 2.0,  # 最高优先级
            self.imdb_datasets: 1.8,  # 高优先级
            
            # 高优先级：TMDB和豆瓣热门数据
            self.tmdb_popular_movies: 1.6,  # TMDB热门电影
            self.tmdb_popular_tvs: 1.6,     # TMDB热门电视剧
            self.douban_hot_movies: 1.6,    # 豆瓣热门电影
            self.douban_hot_tvs: 1.6,      # 豆瓣热门电视剧
            
            # 中高优先级：TMDB趋势和豆瓣TOP250
            self.tmdb_trending: 1.5,        # TMDB趋势
            self.douban_movie_top250: 1.5,  # 豆瓣电影TOP250
            
            # 中等优先级：音乐数据源
            self.tme_uni_chart: 1.2,       # TME由你榜具有高时效性
            self.billboard_china_tme: 1.1, # Billboard China TME具有权威性
            self.spotify_top_tracks: 1.0,
            self.apple_music_top_songs: 1.0,
            
            # 较低优先级：其他数据源
            self.douban_chinese_tv_weekly: 0.9,
            self.douban_global_tv_weekly: 0.9,
            self.douban_animation: 0.9,
            self.bangumi_calendar: 0.9
        }
        
        # 按优先级排序的推荐方法列表
        self.recommend_methods = sorted(
            self.recommend_methods_priority.keys(),
            key=lambda x: self.recommend_methods_priority[x],
            reverse=True
        )
    
    async def refresh_discover_data(self):
        """刷新发现数据"""
        logger.info("开始刷新发现推荐数据")
        
        all_discover_items = []
        completed_methods = set()
        
        # 分页获取所有推荐数据
        for page in range(1, self.CACHE_MAX_PAGES + 1):
            for method in self.recommend_methods:
                if method in completed_methods:
                    continue
                
                try:
                    logger.debug(f"获取 {method.__name__} 第 {page} 页数据")
                    items = await method(page=page)
                    
                    if not items:
                        logger.debug(f"{method.__name__} 数据获取完成")
                        completed_methods.add(method)
                        continue
                    
                    all_discover_items.extend(items)
                    
                except Exception as e:
                    logger.error(f"获取 {method.__name__} 数据失败: {e}")
            
            # 如果所有方法都已完成，提前结束
            if len(completed_methods) == len(self.recommend_methods):
                break
        
        # 缓存海报图片
        await self._cache_posters(all_discover_items)
        
        logger.info(f"发现数据刷新完成，共获取 {len(all_discover_items)} 个项目")
        return all_discover_items
    
    async def _cache_posters(self, items: List[DiscoverItem]):
        """缓存海报图片"""
        # 这里可以实现图片缓存逻辑
        # 简化实现：记录需要缓存的图片URL
        poster_urls = [item.poster_url for item in items if item.poster_url]
        logger.debug(f"需要缓存的图片数量: {len(poster_urls)}")
    
    # TMDB相关推荐方法
    async def tmdb_popular_movies(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """TMDB热门电影"""
        # 这里应该调用TMDB API
        # 简化实现：返回模拟数据
        return [
            DiscoverItem(
                title="阿凡达：水之道",
                category=DiscoverCategory.MOVIE,
                source=DiscoverSource.TMDB,
                score=9.5,
                poster_url="https://image.tmdb.org/t/p/w500/...",
                description="潘多拉星球的水下冒险故事",
                release_date="2022-12-16",
                rating=7.8
            ),
            DiscoverItem(
                title="流浪地球2",
                category=DiscoverCategory.MOVIE,
                source=DiscoverSource.TMDB,
                score=9.2,
                poster_url="https://image.tmdb.org/t/p/w500/...",
                description="人类带着地球逃离太阳系的壮丽史诗",
                release_date="2023-01-22",
                rating=8.3
            )
        ]
    
    async def tmdb_popular_tvs(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """TMDB热门电视剧"""
        return [
            DiscoverItem(
                title="漫长的季节",
                category=DiscoverCategory.TV,
                source=DiscoverSource.TMDB,
                score=9.3,
                poster_url="https://image.tmdb.org/t/p/w500/...",
                description="东北小城桦林的故事",
                release_date="2023-04-22",
                rating=9.4
            )
        ]
    
    async def tmdb_trending(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """TMDB流行趋势"""
        return [
            DiscoverItem(
                title="封神第一部",
                category=DiscoverCategory.MOVIE,
                source=DiscoverSource.TMDB,
                score=8.9,
                poster_url="https://image.tmdb.org/t/p/w500/...",
                description="中国神话史诗电影",
                release_date="2023-07-20",
                rating=7.9
            )
        ]
    
    # 豆瓣相关推荐方法
    async def douban_movie_top250(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """豆瓣电影TOP250"""
        return [
            DiscoverItem(
                title="肖申克的救赎",
                category=DiscoverCategory.MOVIE,
                source=DiscoverSource.DOUBAN,
                score=9.7,
                poster_url="https://img9.doubanio.com/view/photo/s_ratio_poster/public/...",
                description="希望让人自由",
                release_date="1994-09-10",
                rating=9.7
            )
        ]
    
    async def douban_hot_movies(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """豆瓣热门电影"""
        return [
            DiscoverItem(
                title="热辣滚烫",
                category=DiscoverCategory.MOVIE,
                source=DiscoverSource.DOUBAN,
                score=8.5,
                poster_url="https://img9.doubanio.com/view/photo/s_ratio_poster/public/...",
                description="贾玲导演的励志喜剧",
                release_date="2024-02-10",
                rating=7.8
            )
        ]
    
    async def douban_hot_tvs(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """豆瓣热门电视剧"""
        return [
            DiscoverItem(
                title="狂飙",
                category=DiscoverCategory.TV,
                source=DiscoverSource.DOUBAN,
                score=9.1,
                poster_url="https://img9.doubanio.com/view/photo/s_ratio_poster/public/...",
                description="扫黑除恶题材电视剧",
                release_date="2023-01-14",
                rating=8.5
            )
        ]
    
    async def douban_chinese_tv_weekly(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """豆瓣国产剧集榜"""
        return [
            DiscoverItem(
                title="三体",
                category=DiscoverCategory.TV,
                source=DiscoverSource.DOUBAN,
                score=8.7,
                poster_url="https://img9.doubanio.com/view/photo/s_ratio_poster/public/...",
                description="科幻小说改编电视剧",
                release_date="2023-01-15",
                rating=8.7
            )
        ]
    
    async def douban_global_tv_weekly(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """豆瓣全球剧集榜"""
        return [
            DiscoverItem(
                title="最后生还者",
                category=DiscoverCategory.TV,
                source=DiscoverSource.DOUBAN,
                score=9.1,
                poster_url="https://img9.doubanio.com/view/photo/s_ratio_poster/public/...",
                description="游戏改编的末日生存剧",
                release_date="2023-01-15",
                rating=9.1
            )
        ]
    
    async def douban_animation(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """豆瓣热门动漫"""
        return [
            DiscoverItem(
                title="咒术回战",
                category=DiscoverCategory.ANIME,
                source=DiscoverSource.DOUBAN,
                score=8.9,
                poster_url="https://img9.doubanio.com/view/photo/s_ratio_poster/public/...",
                description="现代咒术战斗题材",
                release_date="2020-10-03",
                rating=8.9
            )
        ]
    
    # Bangumi相关推荐方法
    async def bangumi_calendar(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """Bangumi每日放送"""
        return [
            DiscoverItem(
                title="葬送的芙莉莲",
                category=DiscoverCategory.ANIME,
                source=DiscoverSource.BANGUMI,
                score=9.5,
                poster_url="https://lain.bgm.tv/pic/cover/...",
                description="精灵魔法使的千年之旅",
                release_date="2023-09-29",
                rating=9.5
            )
        ]
    
    # 影视榜单相关推荐方法
    async def netflix_top10(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """Netflix Top 10热门影视"""
        return [
            DiscoverItem(
                title="怪奇物语",
                category=DiscoverCategory.TV,
                source=DiscoverSource.NETFLIX_TOP10,
                score=8.7,
                poster_url="https://image.tmdb.org/t/p/w500/49WJfeN0moxb9IPfGn8AIqMGskD.jpg",
                description="Netflix热门科幻剧集",
                release_date="2022-05-27",
                rating=8.7
            )
        ]
    
    async def imdb_datasets(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """IMDb高评分电影"""
        return [
            DiscoverItem(
                title="肖申克的救赎",
                category=DiscoverCategory.MOVIE,
                source=DiscoverSource.IMDB_DATASETS,
                score=9.3,
                poster_url="https://image.tmdb.org/t/p/w500/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg",
                description="IMDb评分最高的电影",
                release_date="1994-09-23",
                rating=9.3
            )
        ]
    
    async def spotify_top_tracks(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """Spotify热门歌曲"""
        return [
            DiscoverItem(
                title="Blinding Lights",
                category=DiscoverCategory.MUSIC,
                source=DiscoverSource.SPOTIFY,
                score=9.5,
                poster_url="https://i.scdn.co/image/...",
                description="The Weeknd热门单曲",
                release_date="2019-11-29",
                rating=9.5
            )
        ]
    
    async def apple_music_top_songs(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """Apple Music热门歌曲"""
        return [
            DiscoverItem(
                title="Anti-Hero",
                category=DiscoverCategory.MUSIC,
                source=DiscoverSource.APPLE_MUSIC,
                score=9.3,
                poster_url="https://is1-ssl.mzstatic.com/...",
                description="Taylor Swift热门单曲",
                release_date="2022-10-21",
                rating=9.3
            )
        ]
    
    # 新增音乐榜单数据源方法
    async def tme_uni_chart(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """TME由你榜 - 腾讯音乐娱乐热门歌曲榜单"""
        import requests
        import time
        
        try:
            # 基于 youni-collector 的 TME UNI Chart 抓取逻辑
            url = "https://yobang.tencentmusic.com/chart/uni-chart/api/rankList"
            params = {"issue": f"2025W{page}"}  # 使用page参数作为周数
            
            headers = {
                "User-Agent": "VabHub/1.0 (+https://vabhub.local)",
                "Referer": "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            items = []
            
            # 解析数据，基于 youni-collector 的 _normalize 函数逻辑
            for path in [("data", "list"), ("result", "records"), ("list",), ("records",)]:
                cur = data
                ok = True
                for p in path:
                    if isinstance(cur, dict) and p in cur:
                        cur = cur[p]
                    else:
                        ok = False
                        break
                if ok and isinstance(cur, list):
                    for item in cur:
                        title = (item.get("songName") or item.get("title") or "").strip()
                        artist = (item.get("singerName") or item.get("artist") or "").strip()
                        rank = item.get("rank") or item.get("sort") or item.get("index") or item.get("rankNum")
                        
                        if title and artist and rank:
                            try:
                                rank = int(rank)
                                # 计算评分（基于排名，排名越靠前评分越高）
                                score = max(10.0 - (rank - 1) * 0.2, 5.0)
                                
                                items.append(DiscoverItem(
                                    title=title,
                                    category=DiscoverCategory.MUSIC,
                                    source=DiscoverSource.TME_UNI_CHART,
                                    score=score,
                                    poster_url=item.get("coverUrl") or item.get("poster") or "",
                                    description=f"TME由你榜第{rank}名 - {artist}",
                                    release_date=item.get("releaseDate") or "",
                                    rating=score
                                ))
                            except (ValueError, TypeError):
                                continue
                    break
            
            # 如果API调用失败，返回模拟数据
            if not items:
                items = [
                    DiscoverItem(
                        title="光的方向",
                        category=DiscoverCategory.MUSIC,
                        source=DiscoverSource.TME_UNI_CHART,
                        score=9.8,
                        poster_url="https://y.qq.com/music/photo_new/T002R300x300M000004MkXyZ0qLr6c_1.jpg",
                        description="TME由你榜第1名 - 张碧晨",
                        release_date="2024-01-01",
                        rating=9.8
                    ),
                    DiscoverItem(
                        title="星辰大海",
                        category=DiscoverCategory.MUSIC,
                        source=DiscoverSource.TME_UNI_CHART,
                        score=9.6,
                        poster_url="https://y.qq.com/music/photo_new/T002R300x300M000003RMaRI1iFoYd_1.jpg",
                        description="TME由你榜第2名 - 黄霄雲",
                        release_date="2024-01-01",
                        rating=9.6
                    )
                ]
            
            return items[:limit]
            
        except Exception as e:
            logger.error(f"获取TME由你榜数据失败: {e}")
            # 返回模拟数据作为降级方案
            return [
                DiscoverItem(
                    title="光的方向",
                    category=DiscoverCategory.MUSIC,
                    source=DiscoverSource.TME_UNI_CHART,
                    score=9.8,
                    poster_url="https://y.qq.com/music/photo_new/T002R300x300M000004MkXyZ0qLr6c_1.jpg",
                    description="TME由你榜热门歌曲",
                    release_date="2024-01-01",
                    rating=9.8
                )
            ]
    
    async def billboard_china_tme(self, page: int = 1, limit: int = 20) -> List[DiscoverItem]:
        """Billboard China TME UNI Songs - 公告牌中国TME联合榜单"""
        import requests
        import time
        from bs4 import BeautifulSoup
        
        try:
            # 基于 youni-collector 的 Billboard TME 抓取逻辑
            url = "https://www.billboard.com/charts/china-tme-uni-songs/"
            headers = {
                "User-Agent": "VabHub/1.0 (+https://vabhub.local)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            items = []
            rank = 0
            
            # 解析榜单数据
            for li in soup.select("li.o-chart-results-list__item"):
                title_el = li.select_one("h3#title-of-a-story") or li.select_one("h3")
                artist_el = li.select_one("span.c-label") or li.select_one("span")
                
                if not title_el or not artist_el:
                    continue
                
                title = title_el.get_text(strip=True)
                artist = artist_el.get_text(" ", strip=True)
                
                if title and artist:
                    rank += 1
                    # 计算评分（基于排名，排名越靠前评分越高）
                    score = max(10.0 - (rank - 1) * 0.15, 6.0)
                    
                    items.append(DiscoverItem(
                        title=title,
                        category=DiscoverCategory.MUSIC,
                        source=DiscoverSource.BILLBOARD_CHINA_TME,
                        score=score,
                        poster_url="",  # Billboard页面通常不提供封面图URL
                        description=f"Billboard China TME第{rank}名 - {artist}",
                        release_date=time.strftime("%Y-%m-%d"),
                        rating=score
                    ))
                
                if rank >= 10:  # Billboard榜单通常显示前10名
                    break
            
            # 如果网页解析失败，返回模拟数据
            if not items:
                items = [
                    DiscoverItem(
                        title="Flowers",
                        category=DiscoverCategory.MUSIC,
                        source=DiscoverSource.BILLBOARD_CHINA_TME,
                        score=9.7,
                        poster_url="",
                        description="Billboard China TME第1名 - Miley Cyrus",
                        release_date=time.strftime("%Y-%m-%d"),
                        rating=9.7
                    ),
                    DiscoverItem(
                        title="Kill Bill",
                        category=DiscoverCategory.MUSIC,
                        source=DiscoverSource.BILLBOARD_CHINA_TME,
                        score=9.5,
                        poster_url="",
                        description="Billboard China TME第2名 - SZA",
                        release_date=time.strftime("%Y-%m-%d"),
                        rating=9.5
                    )
                ]
            
            return items[:limit]
            
        except Exception as e:
            logger.error(f"获取Billboard China TME数据失败: {e}")
            # 返回模拟数据作为降级方案
            return [
                DiscoverItem(
                    title="Flowers",
                    category=DiscoverCategory.MUSIC,
                    source=DiscoverSource.BILLBOARD_CHINA_TME,
                    score=9.7,
                    poster_url="",
                    description="Billboard China TME热门歌曲",
                    release_date=time.strftime("%Y-%m-%d"),
                    rating=9.7
                )
            ]
    
    # 发现数据获取接口
    async def get_discover_items(self, 
                                category: DiscoverCategory = DiscoverCategory.ALL,
                                source: DiscoverSource = None,
                                page: int = 1,
                                limit: int = 20) -> List[DiscoverItem]:
        """获取发现项目"""
        # 这里应该实现基于分类和来源的过滤逻辑
        # 简化实现：返回所有数据
        all_items = await self.refresh_discover_data()
        
        # 过滤分类
        if category != DiscoverCategory.ALL:
            all_items = [item for item in all_items if item.category == category]
        
        # 过滤来源
        if source:
            all_items = [item for item in all_items if item.source == source]
        
        # 分页
        start_index = (page - 1) * limit
        end_index = start_index + limit
        
        return all_items[start_index:end_index]
    
    async def get_personalized_recommendations(self, 
                                              user_id: str = None,
                                              limit: int = 10) -> List[DiscoverItem]:
        """获取个性化推荐"""
        # 整合所有数据源到推荐算法
        all_items = await self.refresh_discover_data()
        
        # 为不同数据源设置推荐权重（与优先级配置保持一致）
        weighted_items = []
        for item in all_items:
            weight = 1.0
            
            # 最高优先级：影视类榜单
            if item.source == DiscoverSource.NETFLIX_TOP10:
                weight = 2.0  # 最高优先级
            
            elif item.source == DiscoverSource.IMDB_DATASETS:
                weight = 1.8  # 高优先级
            
            # 高优先级：TMDB和豆瓣热门数据
            elif item.source in [DiscoverSource.TMDB, DiscoverSource.DOUBAN]:
                weight = 1.6  # 高优先级
            
            # 中等优先级：音乐数据源
            elif item.source == DiscoverSource.TME_UNI_CHART:
                weight = 1.2  # 中等优先级
            
            elif item.source == DiscoverSource.BILLBOARD_CHINA_TME:
                weight = 1.1  # 中等优先级
            
            # 较低优先级：其他数据源
            elif item.source in [DiscoverSource.SPOTIFY, DiscoverSource.APPLE_MUSIC]:
                weight = 1.0  # 标准优先级
            
            # 基于用户历史（如果有）调整权重
            if user_id:
                # 这里可以添加基于用户偏好的权重调整
                pass
            
            weighted_items.append((item, weight))
        
        # 按权重和评分排序
        sorted_items = sorted(weighted_items, key=lambda x: (x[1], x[0].rating), reverse=True)
        
        # 返回前limit个推荐项
        return [item[0] for item in sorted_items[:limit]]
    
    async def get_trending_items(self, category: DiscoverCategory = DiscoverCategory.ALL) -> List[DiscoverItem]:
        """获取趋势项目"""
        # 整合所有数据源到趋势推荐
        all_items = await self.refresh_discover_data()
        
        if category != DiscoverCategory.ALL:
            all_items = [item for item in all_items if item.category == category]
        
        # 为不同数据源设置趋势权重（与优先级配置保持一致）
        trending_items = []
        for item in all_items:
            trend_score = item.rating  # 基础评分
            
            # 最高优先级：影视类榜单
            if item.source == DiscoverSource.NETFLIX_TOP10:
                trend_score *= 2.0  # 最高优先级
            
            # 高优先级：IMDb Datasets和TMDB/豆瓣热门数据
            elif item.source == DiscoverSource.IMDB_DATASETS:
                trend_score *= 1.8  # 高优先级
            
            elif item.source in [DiscoverSource.TMDB, DiscoverSource.DOUBAN]:
                trend_score *= 1.6  # 高优先级
            
            # 中等优先级：音乐数据源
            elif item.source == DiscoverSource.TME_UNI_CHART:
                trend_score *= 1.2  # 中等优先级
            
            elif item.source == DiscoverSource.BILLBOARD_CHINA_TME:
                trend_score *= 1.1  # 中等优先级
            
            # 较低优先级：其他数据源
            elif item.source in [DiscoverSource.SPOTIFY, DiscoverSource.APPLE_MUSIC]:
                trend_score *= 1.0  # 标准优先级
            
            trending_items.append((item, trend_score))
        
        # 按趋势评分排序
        sorted_items = sorted(trending_items, key=lambda x: x[1], reverse=True)
        
        # 确保热门数据源在趋势推荐中有良好表现
        netflix_items = [item for item in all_items if item.source == DiscoverSource.NETFLIX_TOP10]
        imdb_items = [item for item in all_items if item.source == DiscoverSource.IMDB_DATASETS]
        tme_items = [item for item in all_items if item.source == DiscoverSource.TME_UNI_CHART]
        billboard_items = [item for item in all_items if item.source == DiscoverSource.BILLBOARD_CHINA_TME]
        
        # 如果热门项目不在前10，则替换部分项目
        final_items = [item[0] for item in sorted_items[:6]]  # 取前6个
        
        # 确保至少包含1个Netflix Top 10项目
        if netflix_items and not any(item.source == DiscoverSource.NETFLIX_TOP10 for item in final_items):
            final_items.append(netflix_items[0])
        
        # 确保至少包含1个IMDb Datasets项目
        if imdb_items and not any(item.source == DiscoverSource.IMDB_DATASETS for item in final_items):
            final_items.append(imdb_items[0])
        
        # 确保至少包含1个TME由你榜项目
        if tme_items and not any(item.source == DiscoverSource.TME_UNI_CHART for item in final_items):
            final_items.append(tme_items[0])
        
        # 确保至少包含1个Billboard China TME项目
        if billboard_items and not any(item.source == DiscoverSource.BILLBOARD_CHINA_TME for item in final_items):
            final_items.append(billboard_items[0])
        
        return final_items[:10]  # 返回最多10个项目

# 创建全局实例
discover_manager = DiscoverManager()