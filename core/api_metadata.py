"""
元数据API路由模块
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

from .metadata_manager import (
    MetadataManager,
    MediaType,
    MediaEntity,
    Movie,
    TVShow,
    Season,
    Episode,
)
from .auth import get_current_user

router = APIRouter(prefix="/metadata", tags=["Metadata"])

# 全局元数据管理器
metadata_manager: Optional[MetadataManager] = None


def get_metadata_manager() -> MetadataManager:
    """获取元数据管理器实例"""
    global metadata_manager
    if metadata_manager is None:
        # 从配置中获取API密钥
        config = {
            "tmdb_api_key": "your_tmdb_api_key_here",  # 应该从环境变量获取
            "douban_enabled": False,
            "provider_priority": ["tmdb"],
            "cache_dir": "./cache",
        }
        metadata_manager = MetadataManager(config)
    return metadata_manager


@router.get("/search", response_model=List[MediaEntity])
async def search_media(
    query: str,
    media_type: str = Query("movie", description="媒体类型: movie, tv"),
    language: str = Query("zh-CN", description="语言代码"),
    current_user: dict = Depends(get_current_user),
):
    """搜索媒体"""
    try:
        manager = get_metadata_manager()
        results = await manager.search(query, media_type, language)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.get("/movie/{movie_id}", response_model=Movie)
async def get_movie(
    movie_id: str,
    language: str = Query("zh-CN", description="语言代码"),
    current_user: dict = Depends(get_current_user),
):
    """获取电影详情"""
    try:
        manager = get_metadata_manager()
        movie = await manager.get_media(MediaType.MOVIE, movie_id, language)
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        return movie
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get movie: {e}")


@router.get("/tv/{tv_id}", response_model=TVShow)
async def get_tv_show(
    tv_id: str,
    language: str = Query("zh-CN", description="语言代码"),
    current_user: dict = Depends(get_current_user),
):
    """获取电视剧详情"""
    try:
        manager = get_metadata_manager()
        tv_show = await manager.get_media(MediaType.TV_SHOW, tv_id, language)
        if not tv_show:
            raise HTTPException(status_code=404, detail="TV show not found")
        return tv_show
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get TV show: {e}")


@router.get("/tv/{tv_id}/season/{season_number}", response_model=Season)
async def get_season(
    tv_id: str,
    season_number: int,
    language: str = Query("zh-CN", description="语言代码"),
    current_user: dict = Depends(get_current_user),
):
    """获取季详情"""
    try:
        manager = get_metadata_manager()
        season = await manager.get_season(tv_id, season_number, language)
        if not season:
            raise HTTPException(status_code=404, detail="Season not found")
        return season
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get season: {e}")


@router.get(
    "/tv/{tv_id}/season/{season_number}/episode/{episode_number}",
    response_model=Episode,
)
async def get_episode(
    tv_id: str,
    season_number: int,
    episode_number: int,
    language: str = Query("zh-CN", description="语言代码"),
    current_user: dict = Depends(get_current_user),
):
    """获取剧集详情"""
    try:
        manager = get_metadata_manager()
        episode = await manager.get_episode(
            tv_id, season_number, episode_number, language
        )
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        return episode
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get episode: {e}")


@router.get("/providers")
async def get_providers(current_user: dict = Depends(get_current_user)):
    """获取支持的元数据提供者"""
    manager = get_metadata_manager()
    return {"providers": list(manager.providers.keys()), "priority": manager.priority}


@router.post("/cache/clear")
async def clear_cache(current_user: dict = Depends(get_current_user)):
    """清除元数据缓存"""
    # 这里可以实现缓存清除逻辑
    return {"message": "Cache cleared successfully"}


@router.get("/config")
async def get_config(current_user: dict = Depends(get_current_user)):
    """获取元数据配置"""
    manager = get_metadata_manager()
    return {
        "providers": list(manager.providers.keys()),
        "priority": manager.priority,
        "cache_dir": manager.cache_dir,
    }
