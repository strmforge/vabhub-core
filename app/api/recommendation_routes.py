"""
推荐系统API路由
集成MediaMaster的智能推荐精华功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

from core.recommendation_engine import RecommendationEngine

router = APIRouter(prefix="/recommendation", tags=["recommendation"])

# 全局推荐引擎实例
recommendation_engine = RecommendationEngine()


class WatchHistory(BaseModel):
    """观看历史模型"""
    media_id: str = Field(..., description="媒体ID")
    media_type: str = Field(..., description="媒体类型: movie, tv, anime")
    title: str = Field(..., description="媒体标题")
    watch_time: int = Field(..., description="观看时长(秒)")
    total_duration: int = Field(..., description="总时长(秒)")
    rating: Optional[int] = Field(None, description="用户评分(1-5)")
    tags: Optional[List[str]] = Field(None, description="用户标签")


class UserPreference(BaseModel):
    """用户偏好模型"""
    preferred_genres: List[str] = Field(..., description="偏好类型")
    preferred_languages: List[str] = Field(..., description="偏好语言")
    quality_preference: str = Field(..., description="画质偏好: 1080p, 4k, etc")
    content_rating: str = Field(..., description="内容分级: G, PG, R, etc")


class RecommendationRequest(BaseModel):
    """推荐请求模型"""
    user_id: str = Field(..., description="用户ID")
    limit: int = Field(10, description="推荐数量")
    media_type: Optional[str] = Field(None, description="媒体类型过滤")
    exclude_watched: bool = Field(True, description="是否排除已观看")


class RecommendationResponse(BaseModel):
    """推荐响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@router.on_event("startup")
async def startup_event():
    """应用启动时初始化推荐引擎"""
    await recommendation_engine.initialize()


@router.get("/status", response_model=RecommendationResponse)
async def get_recommendation_status():
    """获取推荐系统状态"""
    try:
        status = recommendation_engine.get_status()
        return RecommendationResponse(
            success=True,
            message="推荐系统状态获取成功",
            data=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/watch_history", response_model=RecommendationResponse)
async def add_watch_history(history: WatchHistory):
    """添加观看历史"""
    try:
        success = recommendation_engine.add_watch_history(
            media_id=history.media_id,
            media_type=history.media_type,
            title=history.title,
            watch_time=history.watch_time,
            total_duration=history.total_duration,
            rating=history.rating,
            tags=history.tags or []
        )
        
        if success:
            return RecommendationResponse(
                success=True,
                message="观看历史添加成功",
                data={"media_id": history.media_id}
            )
        else:
            return RecommendationResponse(
                success=False,
                message="观看历史添加失败",
                data={"media_id": history.media_id}
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加观看历史失败: {str(e)}")


@router.get("/watch_history/{user_id}", response_model=RecommendationResponse)
async def get_watch_history(user_id: str):
    """获取用户观看历史"""
    try:
        history = recommendation_engine.get_watch_history(user_id)
        return RecommendationResponse(
            success=True,
            message="观看历史获取成功",
            data={"history": history}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取观看历史失败: {str(e)}")


@router.post("/user_preferences/{user_id}", response_model=RecommendationResponse)
async def update_user_preferences(user_id: str, preferences: UserPreference):
    """更新用户偏好设置"""
    try:
        success = recommendation_engine.update_user_preferences(
            user_id=user_id,
            preferred_genres=preferences.preferred_genres,
            preferred_languages=preferences.preferred_languages,
            quality_preference=preferences.quality_preference,
            content_rating=preferences.content_rating
        )
        
        if success:
            return RecommendationResponse(
                success=True,
                message="用户偏好更新成功",
                data={"user_id": user_id}
            )
        else:
            return RecommendationResponse(
                success=False,
                message="用户偏好更新失败",
                data={"user_id": user_id}
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新用户偏好失败: {str(e)}")


@router.get("/user_preferences/{user_id}", response_model=RecommendationResponse)
async def get_user_preferences(user_id: str):
    """获取用户偏好设置"""
    try:
        preferences = recommendation_engine.get_user_preferences(user_id)
        return RecommendationResponse(
            success=True,
            message="用户偏好获取成功",
            data={"preferences": preferences}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户偏好失败: {str(e)}")


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """获取个性化推荐"""
    try:
        recommendations = recommendation_engine.get_recommendations(
            user_id=request.user_id,
            limit=request.limit,
            media_type=request.media_type,
            exclude_watched=request.exclude_watched
        )
        
        return RecommendationResponse(
            success=True,
            message="推荐列表获取成功",
            data={"recommendations": recommendations}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推荐失败: {str(e)}")


@router.get("/trending", response_model=RecommendationResponse)
async def get_trending_recommendations():
    """获取热门推荐"""
    try:
        trending = recommendation_engine.get_trending_recommendations()
        return RecommendationResponse(
            success=True,
            message="热门推荐获取成功",
            data={"trending": trending}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取热门推荐失败: {str(e)}")


@router.get("/similar/{media_id}", response_model=RecommendationResponse)
async def get_similar_recommendations(media_id: str, limit: int = 10):
    """获取相似内容推荐"""
    try:
        similar = recommendation_engine.get_similar_recommendations(media_id, limit)
        return RecommendationResponse(
            success=True,
            message="相似推荐获取成功",
            data={"similar": similar}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取相似推荐失败: {str(e)}")


@router.get("/stats", response_model=RecommendationResponse)
async def get_recommendation_stats():
    """获取推荐系统统计信息"""
    try:
        stats = recommendation_engine.get_stats()
        return RecommendationResponse(
            success=True,
            message="推荐统计信息获取成功",
            data={"stats": stats}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推荐统计失败: {str(e)}")


@router.post("/train", response_model=RecommendationResponse)
async def train_recommendation_model():
    """训练推荐模型"""
    try:
        success = recommendation_engine.train_model()
        if success:
            return RecommendationResponse(
                success=True,
                message="推荐模型训练完成"
            )
        else:
            return RecommendationResponse(
                success=False,
                message="推荐模型训练失败"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"训练推荐模型失败: {str(e)}")


@router.get("/model/info", response_model=RecommendationResponse)
async def get_model_info():
    """获取推荐模型信息"""
    try:
        model_info = recommendation_engine.get_model_info()
        return RecommendationResponse(
            success=True,
            message="模型信息获取成功",
            data={"model_info": model_info}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型信息失败: {str(e)}")


@router.post("/feedback", response_model=RecommendationResponse)
async def add_recommendation_feedback(
    user_id: str,
    media_id: str,
    feedback_type: str,
    rating: Optional[int] = None
):
    """添加推荐反馈"""
    try:
        success = recommendation_engine.add_feedback(
            user_id=user_id,
            media_id=media_id,
            feedback_type=feedback_type,
            rating=rating
        )
        
        if success:
            return RecommendationResponse(
                success=True,
                message="推荐反馈添加成功"
            )
        else:
            return RecommendationResponse(
                success=False,
                message="推荐反馈添加失败"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加推荐反馈失败: {str(e)}")