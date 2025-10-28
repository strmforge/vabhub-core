"""
VabHub 搜索API接口
基于MoviePilot搜索架构优化的统一搜索API
支持电影、电视剧、动漫、音乐等多种媒体类型的搜索
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import asyncio

from ...core.search_manager import SearchManager, SearchType, SearchSource, SearchResult

router = APIRouter(prefix="/api/search", tags=["search"])

# 依赖注入
async def get_search_manager():
    return SearchManager()

# 请求/响应模型
class SearchRequest(BaseModel):
    query: str
    type: Optional[str] = "all"  # all, movie, tv, anime, music
    sources: Optional[List[str]] = None  # tmdb, douban, qq_music, netease, spotify, apple_music, local
    limit: Optional[int] = 50
    offset: Optional[int] = 0

class SearchResponse(BaseModel):
    query: str
    type: str
    total: int
    results: List[Dict[str, Any]]
    suggestions: List[str]

class SearchByIdRequest(BaseModel):
    media_id: str
    source: Optional[str] = "tmdb"
    type: Optional[str] = "all"

class SearchHistoryItem(BaseModel):
    query: str
    type: str
    sources: List[str]
    timestamp: str

class SearchHistoryResponse(BaseModel):
    history: List[SearchHistoryItem]
    total: int

# API端点
@router.post("/", response_model=SearchResponse)
async def search_media(
    request: SearchRequest,
    search_manager: SearchManager = Depends(get_search_manager)
):
    """统一搜索接口"""
    try:
        # 转换搜索类型
        search_type = SearchType(request.type)
        
        # 转换搜索源
        sources = None
        if request.sources:
            sources = [SearchSource(source) for source in request.sources]
        
        # 执行搜索
        results = await search_manager.search(
            query=request.query,
            search_type=search_type,
            sources=sources,
            limit=request.limit,
            offset=request.offset
        )
        
        # 获取搜索建议
        suggestions = await search_manager.get_search_suggestions(request.query)
        
        # 转换为字典格式
        results_dict = [result.to_dict() for result in results]
        
        return SearchResponse(
            query=request.query,
            type=request.type,
            total=len(results_dict),
            results=results_dict,
            suggestions=suggestions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.post("/by-id", response_model=Dict[str, Any])
async def search_by_id(
    request: SearchByIdRequest,
    search_manager: SearchManager = Depends(get_search_manager)
):
    """根据ID精确搜索"""
    try:
        # 转换搜索源
        source = SearchSource(request.source)
        search_type = SearchType(request.type)
        
        # 执行搜索
        result = await search_manager.search_by_id(
            media_id=request.media_id,
            source=source,
            search_type=search_type
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="未找到匹配的媒体")
        
        return {
            "success": True,
            "data": result.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"根据ID搜索失败: {str(e)}")

@router.get("/music", response_model=SearchResponse)
async def search_music(
    query: str = Query(..., description="搜索关键词"),
    sources: Optional[str] = Query(None, description="搜索源，逗号分隔: qq_music,netease,spotify,apple_music"),
    limit: int = Query(20, ge=1, le=100),
    search_manager: SearchManager = Depends(get_search_manager)
):
    """专门搜索音乐"""
    try:
        # 转换搜索源
        music_sources = None
        if sources:
            source_list = [s.strip() for s in sources.split(",")]
            music_sources = [SearchSource(source) for source in source_list]
        
        # 执行音乐搜索
        results = await search_manager.search_music(
            query=query,
            sources=music_sources,
            limit=limit
        )
        
        # 获取搜索建议
        suggestions = await search_manager.get_search_suggestions(query)
        
        # 转换为字典格式
        results_dict = [result.to_dict() for result in results]
        
        return SearchResponse(
            query=query,
            type="music",
            total=len(results_dict),
            results=results_dict,
            suggestions=suggestions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音乐搜索失败: {str(e)}")

@router.get("/local", response_model=SearchResponse)
async def search_local(
    query: str = Query(..., description="搜索关键词"),
    type: str = Query("all", description="搜索类型: all, movie, tv, anime, music"),
    limit: int = Query(50, ge=1, le=100),
    search_manager: SearchManager = Depends(get_search_manager)
):
    """搜索本地媒体库"""
    try:
        # 转换搜索类型
        search_type = SearchType(type)
        
        # 执行本地搜索
        results = await search_manager.search_local(
            query=query,
            search_type=search_type,
            limit=limit
        )
        
        # 获取搜索建议
        suggestions = await search_manager.get_search_suggestions(query)
        
        # 转换为字典格式
        results_dict = [result.to_dict() for result in results]
        
        return SearchResponse(
            query=query,
            type=type,
            total=len(results_dict),
            results=results_dict,
            suggestions=suggestions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"本地搜索失败: {str(e)}")

@router.get("/suggestions", response_model=List[str])
async def get_search_suggestions(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=20),
    search_manager: SearchManager = Depends(get_search_manager)
):
    """获取搜索建议"""
    try:
        suggestions = await search_manager.get_search_suggestions(query, limit)
        return suggestions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取搜索建议失败: {str(e)}")

@router.get("/history", response_model=SearchHistoryResponse)
async def get_search_history(
    limit: int = Query(20, ge=1, le=100),
    search_manager: SearchManager = Depends(get_search_manager)
):
    """获取搜索历史"""
    try:
        history_data = search_manager.get_search_history(limit)
        
        history_items = []
        for item in history_data:
            history_items.append(SearchHistoryItem(
                query=item["query"],
                type=item["type"],
                sources=item["sources"],
                timestamp=item["timestamp"]
            ))
        
        return SearchHistoryResponse(
            history=history_items,
            total=len(history_items)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取搜索历史失败: {str(e)}")

@router.delete("/history")
async def clear_search_history(
    search_manager: SearchManager = Depends(get_search_manager)
):
    """清空搜索历史"""
    try:
        search_manager.clear_search_history()
        return {"success": True, "message": "搜索历史已清空"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空搜索历史失败: {str(e)}")

@router.get("/sources")
async def get_search_sources():
    """获取可用的搜索源"""
    return {
        "sources": {
            "media": ["tmdb", "douban", "local"],
            "music": ["qq_music", "netease", "spotify", "apple_music", "local"],
            "all": ["tmdb", "douban", "qq_music", "netease", "spotify", "apple_music", "local"]
        }
    }

@router.get("/types")
async def get_search_types():
    """获取可用的搜索类型"""
    return {
        "types": ["all", "movie", "tv", "anime", "music"]
    }

# 健康检查端点
@router.get("/health")
async def health_check():
    """搜索服务健康检查"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0"
    }