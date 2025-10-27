"""
分类API路由 - 基于MoviePilot分类策略
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from enum import Enum

from core.enhanced_classifier import classifier, MediaType

router = APIRouter(prefix="/api/category", tags=["分类管理"])


class MediaTypeEnum(str, Enum):
    """媒体类型枚举"""
    MOVIE = "movie"
    TV = "tv"


class CategoryRequest(BaseModel):
    """分类请求模型"""
    media_type: MediaTypeEnum
    media_info: Dict[str, Any]


class CategoryResponse(BaseModel):
    """分类响应模型"""
    category_name: str
    category_path: str
    available_categories: List[str]


class CategoryListRequest(BaseModel):
    """分类列表请求模型"""
    media_type: MediaTypeEnum


class CategoryListResponse(BaseModel):
    """分类列表响应模型"""
    categories: List[str]


@router.post("/classify", response_model=CategoryResponse)
async def classify_media(request: CategoryRequest):
    """
    对媒体进行分类
    
    Args:
        request: 分类请求
        
    Returns:
        分类结果
    """
    try:
        # 转换媒体类型
        if request.media_type == MediaTypeEnum.MOVIE:
            media_type = MediaType.MOVIE
        else:
            media_type = MediaType.TV
        
        # 进行分类
        category_name = classifier.classify_media(media_type, request.media_info)
        
        # 获取标题和年份
        title = request.media_info.get('title', 'Unknown')
        year = request.media_info.get('year')
        
        # 获取分类路径
        category_path = classifier.get_category_path(media_type, category_name, title, year)
        
        # 获取可用分类列表
        available_categories = classifier.get_available_categories(media_type)
        
        return CategoryResponse(
            category_name=category_name,
            category_path=category_path,
            available_categories=available_categories
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分类失败: {str(e)}")


@router.post("/list", response_model=CategoryListResponse)
async def get_category_list(request: CategoryListRequest):
    """
    获取分类列表
    
    Args:
        request: 分类列表请求
        
    Returns:
        分类列表
    """
    try:
        # 转换媒体类型
        if request.media_type == MediaTypeEnum.MOVIE:
            media_type = MediaType.MOVIE
        else:
            media_type = MediaType.TV
        
        # 获取分类列表
        categories = classifier.get_available_categories(media_type)
        
        return CategoryListResponse(categories=categories)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类列表失败: {str(e)}")


@router.post("/reload")
async def reload_category_config():
    """
    重新加载分类配置
    
    Returns:
        操作结果
    """
    try:
        classifier.reload_config()
        return {"message": "分类配置已重新加载"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新加载配置失败: {str(e)}")


# 示例媒体信息
SAMPLE_MOVIE_INFO = {
    "title": "流浪地球",
    "year": "2019",
    "original_language": "zh",
    "genre_ids": ["878", "28"],
    "origin_country": ["CN"]
}

SAMPLE_TV_INFO = {
    "title": "三体",
    "year": "2023",
    "original_language": "zh",
    "genre_ids": ["878", "18"],
    "origin_country": ["CN"]
}


@router.get("/test/movie")
async def test_movie_classification():
    """测试电影分类"""
    return await classify_media(CategoryRequest(
        media_type=MediaTypeEnum.MOVIE,
        media_info=SAMPLE_MOVIE_INFO
    ))


@router.get("/test/tv")
async def test_tv_classification():
    """测试电视剧分类"""
    return await classify_media(CategoryRequest(
        media_type=MediaTypeEnum.TV,
        media_info=SAMPLE_TV_INFO
    ))