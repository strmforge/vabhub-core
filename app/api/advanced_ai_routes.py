#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级AI功能路由
集成增强AI处理器和智能推荐系统
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

from core.enhanced_ai import EnhancedAIProcessor
from core.ai_recommender import AIRecommender

# 创建路由实例
advanced_ai_router = APIRouter(prefix="/ai", tags=["高级AI功能"])

# 初始化AI处理器和推荐系统
enhanced_ai = EnhancedAIProcessor()
ai_recommender = AIRecommender()


# 请求/响应模型
class AIAnalysisRequest(BaseModel):
    file_path: str
    ai_service: Optional[str] = "auto"  # auto, openai, baidu


class AIAnalysisResponse(BaseModel):
    success: bool
    analysis_result: Dict[str, Any]
    ai_service_used: str
    processing_time: float


class ServiceComparisonRequest(BaseModel):
    file_path: str
    services: List[str] = ["openai", "baidu"]


class ServiceComparisonResponse(BaseModel):
    file_path: str
    comparisons: Dict[str, Any]
    best_service: str
    confidence_scores: Dict[str, float]


class UserActionRequest(BaseModel):
    user_id: str
    action_type: str  # watch, search, rate
    media_info: Dict[str, Any]


class RecommendationRequest(BaseModel):
    user_id: str
    limit: int = 10


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[Dict[str, Any]]
    total_count: int
    recommendation_types: Dict[str, int]


class ServiceConfigurationRequest(BaseModel):
    service: str  # openai, baidu, google
    api_key: str


# API端点

@advanced_ai_router.post("/analyze/enhanced", response_model=AIAnalysisResponse)
async def enhanced_ai_analysis(request: AIAnalysisRequest):
    """增强AI分析 - 使用真实AI服务分析媒体内容"""
    try:
        import time
        start_time = time.time()
        
        if request.ai_service == "openai":
            analysis_result = await enhanced_ai.analyze_with_openai(request.file_path)
            service_used = "openai"
        elif request.ai_service == "baidu":
            analysis_result = await enhanced_ai.analyze_with_baidu_ai(request.file_path)
            service_used = "baidu"
        else:
            # 自动选择最佳服务
            if enhanced_ai.ai_services["openai"]["enabled"]:
                analysis_result = await enhanced_ai.analyze_with_openai(request.file_path)
                service_used = "openai"
            elif enhanced_ai.ai_services["baidu"]["enabled"]:
                analysis_result = await enhanced_ai.analyze_with_baidu_ai(request.file_path)
                service_used = "baidu"
            else:
                raise HTTPException(status_code=400, detail="没有可用的AI服务")
        
        processing_time = time.time() - start_time
        
        return AIAnalysisResponse(
            success=True,
            analysis_result=analysis_result,
            ai_service_used=service_used,
            processing_time=processing_time
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")


@advanced_ai_router.post("/analyze/comparison", response_model=ServiceComparisonResponse)
async def compare_ai_services(request: ServiceComparisonRequest):
    """比较不同AI服务的分析结果"""
    try:
        comparison_result = await enhanced_ai.compare_ai_services(request.file_path)
        
        # 提取置信度分数
        confidence_scores = {}
        for service, result in comparison_result.get("results", {}).items():
            if "error" not in result:
                confidence = result.get("analysis", {}).get("confidence_score", 0)
                confidence_scores[service] = confidence
        
        return ServiceComparisonResponse(
            file_path=request.file_path,
            comparisons=comparison_result,
            best_service=comparison_result.get("summary", {}).get("recommendation", ""),
            confidence_scores=confidence_scores
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务比较失败: {str(e)}")


@advanced_ai_router.post("/title/generate")
async def generate_smart_title(analysis_result: Dict[str, Any]):
    """生成智能标题"""
    try:
        title = await enhanced_ai.generate_smart_title(analysis_result)
        return {
            "success": True,
            "smart_title": title,
            "original_title": analysis_result.get("file_name", "")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"标题生成失败: {str(e)}")


@advanced_ai_router.post("/description/generate")
async def generate_detailed_description(analysis_result: Dict[str, Any]):
    """生成详细描述"""
    try:
        description = await enhanced_ai.generate_detailed_description(analysis_result)
        return {
            "success": True,
            "detailed_description": description,
            "ai_service": analysis_result.get("ai_service", "unknown")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"描述生成失败: {str(e)}")


@advanced_ai_router.post("/user/action")
async def record_user_action(request: UserActionRequest):
    """记录用户行为"""
    try:
        ai_recommender.record_user_action(
            request.user_id,
            request.action_type,
            request.media_info
        )
        
        return {
            "success": True,
            "user_id": request.user_id,
            "action_type": request.action_type,
            "message": "用户行为记录成功"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"用户行为记录失败: {str(e)}")


@advanced_ai_router.post("/recommendations", response_model=RecommendationResponse)
async def get_personalized_recommendations(request: RecommendationRequest):
    """获取个性化推荐"""
    try:
        recommendations = ai_recommender.get_recommendations(
            request.user_id, 
            request.limit
        )
        
        # 统计推荐类型
        recommendation_types = {}
        for rec in recommendations:
            rec_type = rec.get("recommendation_type", "unknown")
            recommendation_types[rec_type] = recommendation_types.get(rec_type, 0) + 1
        
        return RecommendationResponse(
            user_id=request.user_id,
            recommendations=recommendations,
            total_count=len(recommendations),
            recommendation_types=recommendation_types
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐获取失败: {str(e)}")


@advanced_ai_router.get("/user/{user_id}/profile")
async def get_user_profile(user_id: str):
    """获取用户画像"""
    try:
        profile = ai_recommender.get_user_profile(user_id)
        
        if "error" in profile:
            raise HTTPException(status_code=404, detail=profile["error"])
        
        return {
            "success": True,
            "user_id": user_id,
            "profile": profile
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"用户画像获取失败: {str(e)}")


@advanced_ai_router.get("/user/{user_id}/insights")
async def get_recommendation_insights(user_id: str):
    """获取推荐洞察"""
    try:
        insights = ai_recommender.get_recommendation_insights(user_id)
        
        if "error" in insights:
            raise HTTPException(status_code=404, detail=insights["error"])
        
        return {
            "success": True,
            "user_id": user_id,
            "insights": insights
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"洞察获取失败: {str(e)}")


@advanced_ai_router.post("/service/configure")
async def configure_ai_service(request: ServiceConfigurationRequest):
    """配置AI服务"""
    try:
        success = enhanced_ai.configure_service(request.service, request.api_key)
        
        if success:
            return {
                "success": True,
                "service": request.service,
                "message": f"{request.service}服务配置成功"
            }
        else:
            raise HTTPException(status_code=400, detail=f"不支持的AI服务: {request.service}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务配置失败: {str(e)}")


@advanced_ai_router.get("/service/status")
async def get_ai_service_status():
    """获取AI服务状态"""
    try:
        status = enhanced_ai.get_service_status()
        capabilities = enhanced_ai.get_capabilities()
        
        return {
            "success": True,
            "service_status": status,
            "capabilities": capabilities
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务状态获取失败: {str(e)}")


@advanced_ai_router.post("/cache/clear")
async def clear_ai_cache():
    """清除AI缓存"""
    try:
        enhanced_ai.clear_cache()
        
        return {
            "success": True,
            "message": "AI缓存清除成功"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"缓存清除失败: {str(e)}")


@advanced_ai_router.post("/media/add")
async def add_media_to_database(media_info: Dict[str, Any]):
    """添加媒体到数据库"""
    try:
        ai_recommender.add_media_to_database(media_info)
        
        return {
            "success": True,
            "media_id": media_info.get("id", "unknown"),
            "message": "媒体添加成功"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"媒体添加失败: {str(e)}")


@advanced_ai_router.get("/capabilities")
async def get_ai_capabilities():
    """获取AI能力信息"""
    try:
        enhanced_capabilities = enhanced_ai.get_capabilities()
        
        # 组合所有AI能力信息
        capabilities = {
            "enhanced_ai": enhanced_capabilities,
            "recommendation_system": {
                "features": [
                    "personalized_recommendations",
                    "user_behavior_tracking", 
                    "content_analysis",
                    "multi_factor_scoring"
                ],
                "version": "1.0.0"
            },
            "supported_operations": [
                "video_content_analysis",
                "smart_title_generation",
                "detailed_description",
                "service_comparison",
                "personalized_recommendations",
                "user_profile_analysis"
            ]
        }
        
        return {
            "success": True,
            "capabilities": capabilities
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"能力信息获取失败: {str(e)}")


@advanced_ai_router.get("/demo")
async def ai_demo():
    """AI功能演示"""
    try:
        # 演示数据
        demo_file_path = "/path/to/sample/video.mp4"
        demo_user_id = "demo_user_001"
        
        # 获取服务状态
        service_status = enhanced_ai.get_service_status()
        
        # 模拟AI分析
        demo_analysis = {
            "file_path": demo_file_path,
            "file_name": "复仇者联盟4.2019.1080p.BluRay.mp4",
            "ai_service": "demo",
            "analysis": {
                "content_description": "这是一个高质量的动作科幻电影",
                "media_type": "movie",
                "estimated_genre": ["action", "sci-fi", "adventure"],
                "quality_rating": 8.7,
                "key_elements": ["超级英雄", "宇宙", "战斗"],
                "confidence_score": 0.89
            }
        }
        
        # 生成演示推荐
        demo_recommendations = [
            {
                "id": "movie_001",
                "title": "复仇者联盟3：无限战争",
                "recommendation_type": "similar_content",
                "recommendation_score": 0.85,
                "similarity_reason": "与前作相关"
            },
            {
                "id": "movie_002",
                "title": "银河护卫队",
                "recommendation_type": "similar_genre",
                "recommendation_score": 0.78,
                "similarity_reason": "同属漫威宇宙"
            }
        ]
        
        return {
            "success": True,
            "demo": {
                "service_status": service_status,
                "sample_analysis": demo_analysis,
                "sample_recommendations": demo_recommendations,
                "available_endpoints": [
                    "POST /ai/analyze/enhanced - 增强AI分析",
                    "POST /ai/analyze/comparison - 服务比较",
                    "POST /ai/recommendations - 个性化推荐",
                    "GET /ai/service/status - 服务状态",
                    "GET /ai/capabilities - 能力信息"
                ]
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"演示数据生成失败: {str(e)}")