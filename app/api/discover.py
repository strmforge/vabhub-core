"""
VabHub 发现推荐API接口
基于MoviePilot推荐架构优化的发现推荐API
支持影视榜单、音乐榜单、个性化推荐等功能
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import asyncio

from ...core.discover_manager import DiscoverManager, DiscoverCategory, DiscoverSource, DiscoverItem
discover_manager = DiscoverManager()

router = APIRouter(prefix="/api/discover", tags=["discover"])

# 请求/响应模型
class DiscoverRequest(BaseModel):
    category: Optional[str] = "all"  # all, movie, tv, anime, music
    source: Optional[str] = None     # tmdb, douban, bangumi, qq_music, netease, spotify, apple_music
    page: Optional[int] = 1
    limit: Optional[int] = 20

class DiscoverResponse(BaseModel):
    category: str
    source: Optional[str]
    total: int
    page: int
    limit: int
    items: List[Dict[str, Any]]

class PersonalizedRecommendationRequest(BaseModel):
    user_id: Optional[str] = None
    limit: Optional[int] = 10

class TrendingRequest(BaseModel):
    category: Optional[str] = "all"
    limit: Optional[int] = 10

class CategoryInfo(BaseModel):
    name: str
    display_name: str
    count: int

class SourceInfo(BaseModel):
    name: str
    display_name: str
    categories: List[str]

class DiscoverInfoResponse(BaseModel):
    categories: List[CategoryInfo]
    sources: List[SourceInfo]

# API端点
@router.post("/", response_model=DiscoverResponse)
async def discover_items(
    request: DiscoverRequest,
    discover_manager: DiscoverManager = Depends(lambda: discover_manager)
):
    """发现推荐接口"""
    try:
        # 转换分类
        category = DiscoverCategory(request.category)
        
        # 转换来源
        source = None
        if request.source:
            source = DiscoverSource(request.source)
        
        # 获取发现项目
        items = await discover_manager.get_discover_items(
            category=category,
            source=source,
            page=request.page,
            limit=request.limit
        )
        
        # 转换为字典格式
        items_dict = [item.to_dict() for item in items]
        
        return DiscoverResponse(
            category=request.category,
            source=request.source,
            total=len(items_dict),
            page=request.page,
            limit=request.limit,
            items=items_dict
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发现推荐失败: {str(e)}")

@router.post("/personalized", response_model=DiscoverResponse)
async def personalized_recommendations(
    request: PersonalizedRecommendationRequest,
    discover_manager: DiscoverManager = Depends(lambda: discover_manager)
):
    """个性化推荐接口"""
    try:
        # 获取个性化推荐
        items = await discover_manager.get_personalized_recommendations(
            user_id=request.user_id,
            limit=request.limit
        )
        
        # 转换为字典格式
        items_dict = [item.to_dict() for item in items]
        
        return DiscoverResponse(
            category="personalized",
            source=None,
            total=len(items_dict),
            page=1,
            limit=request.limit,
            items=items_dict
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"个性化推荐失败: {str(e)}")

@router.post("/trending", response_model=DiscoverResponse)
async def trending_items(
    request: TrendingRequest,
    discover_manager: DiscoverManager = Depends(lambda: discover_manager)
):
    """趋势推荐接口"""
    try:
        # 转换分类
        category = DiscoverCategory(request.category)
        
        # 获取趋势项目
        items = await discover_manager.get_trending_items(
            category=category
        )
        
        # 转换为字典格式
        items_dict = [item.to_dict() for item in items[:request.limit]]
        
        return DiscoverResponse(
            category=request.category,
            source=None,
            total=len(items_dict),
            page=1,
            limit=request.limit,
            items=items_dict
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"趋势推荐失败: {str(e)}")

@router.get("/info", response_model=DiscoverInfoResponse)
async def discover_info(
    discover_manager: DiscoverManager = Depends(lambda: discover_manager)
):
    """获取发现推荐系统信息"""
    try:
        # 分类信息
        categories = [
            CategoryInfo(name="all", display_name="全部", count=0),
            CategoryInfo(name="movie", display_name="电影", count=0),
            CategoryInfo(name="tv", display_name="电视剧", count=0),
            CategoryInfo(name="anime", display_name="动漫", count=0),
            CategoryInfo(name="music", display_name="音乐", count=0)
        ]
        
        # 来源信息
        sources = [
            SourceInfo(
                name="tmdb", 
                display_name="TMDB", 
                categories=["movie", "tv", "anime"]
            ),
            SourceInfo(
                name="douban", 
                display_name="豆瓣", 
                categories=["movie", "tv", "anime"]
            ),
            SourceInfo(
                name="bangumi", 
                display_name="Bangumi", 
                categories=["anime"]
            ),
            SourceInfo(
                name="qq_music", 
                display_name="QQ音乐", 
                categories=["music"]
            ),
            SourceInfo(
                name="netease", 
                display_name="网易云音乐", 
                categories=["music"]
            ),
            SourceInfo(
                name="spotify", 
                display_name="Spotify", 
                categories=["music"]
            ),
            SourceInfo(
                name="apple_music", 
                display_name="Apple Music", 
                categories=["music"]
            ),
            SourceInfo(
                name="tme_uni_chart", 
                display_name="TME由你榜", 
                categories=["music"]
            ),
            SourceInfo(
                name="billboard_china_tme", 
                display_name="Billboard China TME", 
                categories=["music"]
            )
        ]
        
        return DiscoverInfoResponse(
            categories=categories,
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取发现信息失败: {str(e)}")

@router.get("/categories")
async def get_categories():
    """获取可用的分类"""
    return {
        "categories": [
            {"name": "all", "display_name": "全部"},
            {"name": "movie", "display_name": "电影"},
            {"name": "tv", "display_name": "电视剧"},
            {"name": "anime", "display_name": "动漫"},
            {"name": "music", "display_name": "音乐"}
        ]
    }

@router.get("/sources")
async def get_sources():
    """获取可用的数据源"""
    return {
        "sources": [
            {"name": "tmdb", "display_name": "TMDB", "categories": ["movie", "tv", "anime"]},
            {"name": "douban", "display_name": "豆瓣", "categories": ["movie", "tv", "anime"]},
            {"name": "bangumi", "display_name": "Bangumi", "categories": ["anime"]},
            {"name": "qq_music", "display_name": "QQ音乐", "categories": ["music"]},
            {"name": "netease", "display_name": "网易云音乐", "categories": ["music"]},
            {"name": "spotify", "display_name": "Spotify", "categories": ["music"]},
            {"name": "apple_music", "display_name": "Apple Music", "categories": ["music"]},
            {"name": "tme_uni_chart", "display_name": "TME由你榜", "categories": ["music"]},
            {"name": "billboard_china_tme", "display_name": "Billboard China TME", "categories": ["music"]}
        ]
    }

@router.post("/refresh")
async def refresh_discover_data(
    discover_manager: DiscoverManager = Depends(lambda: discover_manager)
):
    """手动刷新发现数据"""
    try:
        await discover_manager.refresh_discover_data()
        return {"success": True, "message": "发现数据刷新成功"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新发现数据失败: {str(e)}")

# 特定分类的发现接口
@router.get("/movies", response_model=DiscoverResponse)
async def discover_movies(
    source: Optional[str] = Query(None, description="数据源"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    discover_manager: DiscoverManager = Depends(lambda: discover_manager)
):
    """发现电影"""
    try:
        # 转换来源
        source_enum = None
        if source:
            source_enum = DiscoverSource(source)
        
        # 获取电影发现项目
        items = await discover_manager.get_discover_items(
            category=DiscoverCategory.MOVIE,
            source=source_enum,
            page=page,
            limit=limit
        )
        
        # 转换为字典格式
        items_dict = [item.to_dict() for item in items]
        
        return DiscoverResponse(
            category="movie",
            source=source,
            total=len(items_dict),
            page=page,
            limit=limit,
            items=items_dict
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发现电影失败: {str(e)}")

@router.get("/tvs", response_model=DiscoverResponse)
async def discover_tvs(
    source: Optional[str] = Query(None, description="数据源"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    discover_manager: DiscoverManager = Depends(lambda: discover_manager)
):
    """发现电视剧"""
    try:
        # 转换来源
        source_enum = None
        if source:
            source_enum = DiscoverSource(source)
        
        # 获取电视剧发现项目
        items = await discover_manager.get_discover_items(
            category=DiscoverCategory.TV,
            source=source_enum,
            page=page,
            limit=limit
        )
        
        # 转换为字典格式
        items_dict = [item.to_dict() for item in items]
        
        return DiscoverResponse(
            category="tv",
            source=source,
            total=len(items_dict),
            page=page,
            limit=limit,
            items=items_dict
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发现电视剧失败: {str(e)}")

@router.get("/music", response_model=DiscoverResponse)
async def discover_music(
    source: Optional[str] = Query(None, description="数据源"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    discover_manager: DiscoverManager = Depends(lambda: discover_manager)
):
    """发现音乐"""
    try:
        # 转换来源
        source_enum = None
        if source:
            source_enum = DiscoverSource(source)
        
        # 获取音乐发现项目
        items = await discover_manager.get_discover_items(
            category=DiscoverCategory.MUSIC,
            source=source_enum,
            page=page,
            limit=limit
        )
        
        # 转换为字典格式
        items_dict = [item.to_dict() for item in items]
        
        return DiscoverResponse(
            category="music",
            source=source,
            total=len(items_dict),
            page=page,
            limit=limit,
            items=items_dict
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发现音乐失败: {str(e)}")

# 健康检查端点
@router.get("/health")
async def health_check():
    """发现推荐服务健康检查"""
    return {
        "status": "healthy",
        "service": "discover",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0"
    }