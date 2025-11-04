#!/usr/bin/env python3
"""
AI推荐系统API接口
提供RESTful API用于智能内容推荐
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from datetime import datetime
import json

from .ai_recommendation import AIRecommendationSystem

logger = logging.getLogger(__name__)

# API路由
router = APIRouter(prefix="/ai/recommend", tags=["AI推荐"])

# 全局推荐系统实例
recommender = None


def get_recommender():
    """获取推荐系统实例（单例模式）"""
    global recommender
    if recommender is None:
        recommender = AIRecommendationSystem()
    return recommender


# 请求/响应模型
class RecommendationRequest(BaseModel):
    """推荐请求模型"""

    query: Optional[str] = Field(None, description="查询文本")
    media_id: Optional[str] = Field(None, description="媒体ID")
    media_ids: Optional[List[str]] = Field(None, description="批量媒体ID列表")
    top_k: int = Field(10, description="推荐数量", ge=1, le=50)
    similarity_threshold: float = Field(0.5, description="相似度阈值", ge=0.0, le=1.0)


class RecommendationResponse(BaseModel):
    """推荐响应模型"""

    success: bool
    message: str
    recommendations: List[Dict[str, Any]]
    query_info: Dict[str, Any]
    stats: Dict[str, Any]
    timestamp: datetime


class BatchRecommendationResponse(BaseModel):
    """批量推荐响应模型"""

    success: bool
    message: str
    results: Dict[str, List[Dict[str, Any]]]
    stats: Dict[str, Any]
    timestamp: datetime


class UserFeedbackRequest(BaseModel):
    """用户反馈请求模型"""

    recommendation_id: str = Field(..., description="推荐ID")
    media_id: str = Field(..., description="媒体ID")
    feedback_type: str = Field(
        ...,
        description="反馈类型: like/dislike/neutral",
        pattern="^(like|dislike|neutral)$",
    )
    user_id: Optional[str] = Field(None, description="用户ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="反馈时间")


class UserPreferenceRequest(BaseModel):
    """用户偏好设置请求模型"""

    user_id: str = Field(..., description="用户ID")
    preferences: Dict[str, Any] = Field(..., description="用户偏好设置")
    favorite_genres: Optional[List[str]] = Field(None, description="喜欢的类型")
    favorite_directors: Optional[List[str]] = Field(None, description="喜欢的导演")
    favorite_actors: Optional[List[str]] = Field(None, description="喜欢的演员")
    excluded_genres: Optional[List[str]] = Field(None, description="排除的类型")


class SystemStatsResponse(BaseModel):
    """系统统计响应模型"""

    success: bool
    message: str
    stats: Dict[str, Any]
    timestamp: datetime


# API端点
@router.get("/health", summary="健康检查")
async def health_check():
    """推荐系统健康检查"""
    recommender = get_recommender()
    return {
        "status": "healthy",
        "model_loaded": recommender.is_initialized,
        "media_count": len(recommender.media_items),
        "timestamp": datetime.now(),
    }


@router.post("/query", response_model=RecommendationResponse, summary="基于查询推荐")
async def recommend_by_query(request: RecommendationRequest = Body(...)):
    """
    基于文本查询的推荐

    Args:
        request: 推荐请求参数

    Returns:
        推荐结果
    """
    try:
        recommender = get_recommender()

        if not request.query:
            raise HTTPException(status_code=400, detail="查询文本不能为空")

        # 临时调整阈值
        original_threshold = recommender.config["similarity_threshold"]
        recommender.config["similarity_threshold"] = request.similarity_threshold

        # 获取推荐
        recommendations = recommender.get_similar_items(request.query, request.top_k)

        # 恢复阈值
        recommender.config["similarity_threshold"] = original_threshold

        # 构建响应
        response = RecommendationResponse(
            success=True,
            message=f"找到 {len(recommendations)} 个推荐内容",
            recommendations=recommendations,
            query_info={
                "query": request.query,
                "top_k": request.top_k,
                "similarity_threshold": request.similarity_threshold,
            },
            stats=recommender.get_recommendation_stats(),
            timestamp=datetime.now(),
        )

        return response

    except Exception as e:
        logger.error(f"查询推荐失败: {e}")
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")


@router.post(
    "/media/{media_id}", response_model=RecommendationResponse, summary="基于媒体推荐"
)
async def recommend_by_media(media_id: str, request: RecommendationRequest = Body(...)):
    """
    基于特定媒体内容的推荐

    Args:
        media_id: 媒体ID
        request: 推荐请求参数

    Returns:
        推荐结果
    """
    try:
        recommender = get_recommender()

        # 临时调整阈值
        original_threshold = recommender.config["similarity_threshold"]
        recommender.config["similarity_threshold"] = request.similarity_threshold

        # 获取推荐
        recommendations = recommender.get_similar_to_media(media_id, request.top_k)

        # 恢复阈值
        recommender.config["similarity_threshold"] = original_threshold

        # 构建响应
        response = RecommendationResponse(
            success=True,
            message=f"基于媒体 {media_id} 找到 {len(recommendations)} 个推荐内容",
            recommendations=recommendations,
            query_info={
                "media_id": media_id,
                "top_k": request.top_k,
                "similarity_threshold": request.similarity_threshold,
            },
            stats=recommender.get_recommendation_stats(),
            timestamp=datetime.now(),
        )

        return response

    except Exception as e:
        logger.error(f"媒体推荐失败: {e}")
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")


@router.post("/batch", response_model=BatchRecommendationResponse, summary="批量推荐")
async def batch_recommend(request: RecommendationRequest = Body(...)):
    """
    批量推荐

    Args:
        request: 批量推荐请求参数

    Returns:
        批量推荐结果
    """
    try:
        recommender = get_recommender()

        if not request.media_ids:
            raise HTTPException(status_code=400, detail="媒体ID列表不能为空")

        # 临时调整阈值
        original_threshold = recommender.config["similarity_threshold"]
        recommender.config["similarity_threshold"] = request.similarity_threshold

        # 获取批量推荐
        results = recommender.batch_recommend(request.media_ids, request.top_k)

        # 恢复阈值
        recommender.config["similarity_threshold"] = original_threshold

        # 构建响应
        response = BatchRecommendationResponse(
            success=True,
            message=f"批量推荐完成，处理了 {len(request.media_ids)} 个媒体",
            results=results,
            stats=recommender.get_recommendation_stats(),
            timestamp=datetime.now(),
        )

        return response

    except Exception as e:
        logger.error(f"批量推荐失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量推荐失败: {str(e)}")


@router.post("/media", summary="添加媒体内容")
async def add_media_items(
    media_items: List[Dict[str, Any]] = Body(..., description="媒体内容列表")
):
    """
    添加媒体内容到推荐系统

    Args:
        media_items: 媒体内容列表

    Returns:
        添加结果
    """
    try:
        recommender = get_recommender()

        # 添加媒体内容
        recommender.add_media_items(media_items)

        return {
            "success": True,
            "message": f"成功添加 {len(media_items)} 个媒体内容",
            "total_media_count": len(recommender.media_items),
            "timestamp": datetime.now(),
        }

    except Exception as e:
        logger.error(f"添加媒体内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@router.get("/stats", response_model=SystemStatsResponse, summary="系统统计")
async def get_system_stats():
    """获取推荐系统统计信息"""
    try:
        recommender = get_recommender()

        stats = recommender.get_recommendation_stats()

        response = SystemStatsResponse(
            success=True,
            message="系统统计信息获取成功",
            stats=stats,
            timestamp=datetime.now(),
        )

        return response

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


# 用户反馈和个性化推荐端点
@router.post("/feedback", summary="提交用户反馈")
async def submit_user_feedback(feedback: UserFeedbackRequest = Body(...)):
    """
    提交用户对推荐结果的反馈

    Args:
        feedback: 用户反馈数据

    Returns:
        反馈提交结果
    """
    try:
        recommender = get_recommender()

        if not feedback.user_id:
            raise HTTPException(status_code=400, detail="用户ID不能为空")

        # 记录用户交互
        interaction_type = "like" if feedback.feedback_type == "like" else "dislike"
        interaction_value = 1.0 if feedback.feedback_type == "like" else -1.0

        recommender.record_user_interaction(
            user_id=feedback.user_id,
            media_id=feedback.media_id,
            interaction_type=interaction_type,
            interaction_value=interaction_value,
            metadata={
                "recommendation_id": feedback.recommendation_id,
                "feedback_type": feedback.feedback_type,
                "timestamp": feedback.timestamp.isoformat(),
            },
        )

        return {
            "success": True,
            "message": "用户反馈提交成功",
            "feedback_id": f"feedback_{feedback.timestamp.timestamp()}",
            "user_id": feedback.user_id,
            "media_id": feedback.media_id,
            "feedback_type": feedback.feedback_type,
            "timestamp": datetime.now(),
        }

    except Exception as e:
        logger.error(f"提交用户反馈失败: {e}")
        raise HTTPException(status_code=500, detail=f"反馈提交失败: {str(e)}")


@router.post("/preferences", summary="设置用户偏好")
async def set_user_preferences(preferences: UserPreferenceRequest = Body(...)):
    """
    设置用户个性化偏好

    Args:
        preferences: 用户偏好设置

    Returns:
        偏好设置结果
    """
    try:
        recommender = get_recommender()

        # 保存用户偏好
        user_preferences = {
            "user_id": preferences.user_id,
            "preferences": preferences.preferences,
            "favorite_genres": preferences.favorite_genres or [],
            "favorite_directors": preferences.favorite_directors or [],
            "favorite_actors": preferences.favorite_actors or [],
            "excluded_genres": preferences.excluded_genres or [],
            "last_updated": datetime.now(),
        }

        # 这里可以集成到推荐系统的个性化机制
        # 实际实现需要保存到数据库并影响后续推荐

        return {
            "success": True,
            "message": "用户偏好设置成功",
            "user_id": preferences.user_id,
            "preferences_count": len(user_preferences["preferences"]),
            "timestamp": datetime.now(),
        }

    except Exception as e:
        logger.error(f"设置用户偏好失败: {e}")
        raise HTTPException(status_code=500, detail=f"偏好设置失败: {str(e)}")


@router.get("/preferences/{user_id}", summary="获取用户偏好")
async def get_user_preferences(user_id: str):
    """
    获取用户个性化偏好

    Args:
        user_id: 用户ID

    Returns:
        用户偏好信息
    """
    try:
        # 这里可以从数据库获取用户偏好
        # 暂时返回示例数据

        return {
            "success": True,
            "user_id": user_id,
            "preferences": {
                "favorite_genres": ["科幻", "动作", "悬疑"],
                "favorite_directors": ["诺兰", "斯皮尔伯格"],
                "favorite_actors": ["小李子", "汤姆·汉克斯"],
                "excluded_genres": ["恐怖", "惊悚"],
                "preferred_rating_min": 7.0,
                "preferred_year_min": 2010,
            },
            "timestamp": datetime.now(),
        }

    except Exception as e:
        logger.error(f"获取用户偏好失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取偏好失败: {str(e)}")


@router.post(
    "/personalized/{user_id}",
    response_model=RecommendationResponse,
    summary="个性化推荐",
)
async def get_personalized_recommendations(
    user_id: str, request: RecommendationRequest = Body(...)
):
    """
    基于用户偏好的个性化推荐

    Args:
        user_id: 用户ID
        request: 推荐请求参数

    Returns:
        个性化推荐结果
    """
    try:
        recommender = get_recommender()

        # 临时调整阈值
        original_threshold = recommender.config["similarity_threshold"]
        recommender.config["similarity_threshold"] = request.similarity_threshold

        # 获取个性化推荐
        personalized_recommendations = recommender.get_personalized_recommendations(
            user_id=user_id, query_text=request.query, top_k=request.top_k
        )

        # 恢复阈值
        recommender.config["similarity_threshold"] = original_threshold

        # 构建响应
        response = RecommendationResponse(
            success=True,
            message=f"基于用户偏好找到 {len(personalized_recommendations)} 个个性化推荐",
            recommendations=personalized_recommendations,
            query_info={
                "query": request.query,
                "user_id": user_id,
                "top_k": request.top_k,
                "similarity_threshold": request.similarity_threshold,
                "personalized": True,
            },
            stats={
                **recommender.get_recommendation_stats(),
                "user_preferences_applied": True,
                "personalization_score": (
                    sum(
                        item.get("personalized_score", 0)
                        for item in personalized_recommendations
                    )
                    / len(personalized_recommendations)
                    if personalized_recommendations
                    else 0
                ),
            },
            timestamp=datetime.now(),
        )

        return response

    except Exception as e:
        logger.error(f"个性化推荐失败: {e}")
        raise HTTPException(status_code=500, detail=f"个性化推荐失败: {str(e)}")


# GraphQL集成端点（可选）
@router.get("/graphql/schema", summary="GraphQL模式")
async def get_graphql_schema():
    """获取GraphQL模式定义"""
    # 这里可以返回GraphQL模式定义
    # 实际实现需要与现有的GraphQL API集成
    return {"message": "GraphQL模式端点（待实现）", "status": "planned"}


# 测试端点
@router.post("/test", summary="测试推荐")
async def test_recommendation():
    """测试推荐功能"""
    try:
        recommender = get_recommender()

        # 测试数据
        test_media = [
            {
                "id": "test_movie_1",
                "title": "测试电影1",
                "type": "movie",
                "genres": ["科幻", "动作"],
                "year": 2023,
                "directors": ["测试导演"],
                "description": "测试电影描述",
            },
            {
                "id": "test_movie_2",
                "title": "测试电影2",
                "type": "movie",
                "genres": ["科幻", "冒险"],
                "year": 2023,
                "directors": ["测试导演"],
                "description": "测试电影描述2",
            },
        ]

        # 添加测试数据
        recommender.add_media_items(test_media)

        # 测试推荐
        results = recommender.get_similar_items("科幻电影", top_k=5)

        return {
            "success": True,
            "test_data_added": len(test_media),
            "recommendations_found": len(results),
            "recommendations": results,
            "stats": recommender.get_recommendation_stats(),
            "timestamp": datetime.now(),
        }

    except Exception as e:
        logger.error(f"测试推荐失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


# 初始化推荐系统
@router.on_event("startup")
async def startup_event():
    """应用启动时初始化推荐系统"""
    try:
        recommender = get_recommender()
        logger.info("AI推荐系统API启动完成")
    except Exception as e:
        logger.error(f"AI推荐系统启动失败: {e}")


# 导出路由
__all__ = ["router"]
