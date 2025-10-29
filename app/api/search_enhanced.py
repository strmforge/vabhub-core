"""
VabHub 增强版搜索API接口
基于MoviePilot搜索架构优化的统一搜索API
支持电影、电视剧、动漫、音乐等多种媒体类型的搜索
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import asyncio

from ...core.enhanced_search_manager import EnhancedSearchManager, SearchMode, SearchPriority
from ...core.optimized_search_manager import OptimizedSearchManager, QueryAnalyzer

router = APIRouter(prefix="/api/search/v2", tags=["search-v2"])

# 依赖注入
async def get_enhanced_search_manager():
    return EnhancedSearchManager()

async def get_optimized_search_manager():
    return OptimizedSearchManager()

# 请求/响应模型
class EnhancedSearchRequest(BaseModel):
    query: str
    mode: Optional[str] = "combined"  # media_info, resource, combined
    type: Optional[str] = "all"  # all, movie, tv, anime, music
    sources: Optional[List[str]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0
    enable_optimization: Optional[bool] = True  # 启用优化搜索

class EnhancedSearchResponse(BaseModel):
    query: str
    mode: str
    type: str
    total: int
    results: List[Dict[str, Any]]
    suggestions: List[str]
    optimization_info: Optional[Dict[str, Any]] = None
    search_strategy: Optional[str] = None

class SearchHistoryRequest(BaseModel):
    query: str
    mode: str
    type: str
    sources: List[str]

class SearchHistoryResponse(BaseModel):
    history: List[Dict[str, Any]]
    total: int
    popular_searches: List[Dict[str, Any]]

class SearchSuggestionResponse(BaseModel):
    suggestions: List[str]
    related_queries: List[str]
    trending_searches: List[str]

# API端点
@router.post("/", response_model=EnhancedSearchResponse)
async def enhanced_search_media(
    request: EnhancedSearchRequest,
    enhanced_manager: EnhancedSearchManager = Depends(get_enhanced_search_manager),
    optimized_manager: OptimizedSearchManager = Depends(get_optimized_search_manager)
):
    """增强版统一搜索接口"""
    try:
        # 查询分析
        query_analysis = QueryAnalyzer.analyze_query(request.query)
        
        # 根据优化设置选择搜索管理器
        if request.enable_optimization and query_analysis.is_old_content:
            # 使用优化搜索管理器处理老电视剧
            results = await optimized_manager.search(
                query_analysis,
                search_mode=SearchMode(request.mode),
                content_type=request.type,
                limit=request.limit,
                offset=request.offset
            )
            search_strategy = "optimized"
        else:
            # 使用增强搜索管理器
            results = await enhanced_manager.search(
                query=request.query,
                search_mode=SearchMode(request.mode),
                content_type=request.type,
                sources=request.sources,
                filters=request.filters,
                limit=request.limit,
                offset=request.offset
            )
            search_strategy = "enhanced"
        
        # 获取搜索建议
        suggestions = await enhanced_manager.get_search_suggestions(request.query)
        
        # 转换为字典格式
        results_dict = [result.to_dict() for result in results]
        
        # 优化信息
        optimization_info = None
        if search_strategy == "optimized":
            optimization_info = {
                "strategy": query_analysis.strategy.value,
                "is_old_content": query_analysis.is_old_content,
                "processed_queries": query_analysis.processed_queries,
                "content_type": query_analysis.content_type,
                "year": query_analysis.year
            }
        
        return EnhancedSearchResponse(
            query=request.query,
            mode=request.mode,
            type=request.type,
            total=len(results_dict),
            results=results_dict,
            suggestions=suggestions,
            optimization_info=optimization_info,
            search_strategy=search_strategy
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.get("/suggestions", response_model=SearchSuggestionResponse)
async def get_search_suggestions(
    query: str = Query(..., description="搜索关键词"),
    enhanced_manager: EnhancedSearchManager = Depends(get_enhanced_search_manager)
):
    """获取搜索建议"""
    try:
        # 获取基础搜索建议
        suggestions = await enhanced_manager.get_search_suggestions(query)
        
        # 获取相关查询
        related_queries = await enhanced_manager.get_related_queries(query)
        
        # 获取热门搜索
        trending_searches = await enhanced_manager.get_trending_searches()
        
        return SearchSuggestionResponse(
            suggestions=suggestions,
            related_queries=related_queries,
            trending_searches=trending_searches
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取搜索建议失败: {str(e)}")

@router.get("/history", response_model=SearchHistoryResponse)
async def get_search_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    enhanced_manager: EnhancedSearchManager = Depends(get_enhanced_search_manager)
):
    """获取搜索历史"""
    try:
        history = await enhanced_manager.get_search_history(limit, offset)
        popular_searches = await enhanced_manager.get_popular_searches()
        
        return SearchHistoryResponse(
            history=history,
            total=len(history),
            popular_searches=popular_searches
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取搜索历史失败: {str(e)}")

@router.delete("/history/{query_id}")
async def delete_search_history(
    query_id: str,
    enhanced_manager: EnhancedSearchManager = Depends(get_enhanced_search_manager)
):
    """删除搜索历史记录"""
    try:
        await enhanced_manager.delete_search_history(query_id)
        return {"message": "搜索历史删除成功"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除搜索历史失败: {str(e)}")

@router.delete("/history")
async def clear_search_history(
    enhanced_manager: EnhancedSearchManager = Depends(get_enhanced_search_manager)
):
    """清空搜索历史"""
    try:
        await enhanced_manager.clear_search_history()
        return {"message": "搜索历史清空成功"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空搜索历史失败: {str(e)}")

@router.get("/trending")
async def get_trending_searches(
    enhanced_manager: EnhancedSearchManager = Depends(get_enhanced_search_manager)
):
    """获取热门搜索"""
    try:
        trending = await enhanced_manager.get_trending_searches()
        return {"trending_searches": trending}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取热门搜索失败: {str(e)}")