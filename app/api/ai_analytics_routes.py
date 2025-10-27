#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析路由
提供AI分析数据、统计信息和仪表板功能
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional

from core.ai_dashboard import AIDashboard
from core.ai_config_manager import AIConfigManager

router = APIRouter(prefix="/ai/analytics", tags=["AI分析"])

# 全局实例
dashboard = AIDashboard()
config_manager = AIConfigManager()


@router.get("/overview", summary="获取AI分析概览")
async def get_ai_overview():
    """获取AI分析概览数据"""
    try:
        overview = dashboard.get_dashboard_overview()
        return {
            "success": True,
            "data": overview,
            "timestamp": dashboard.analysis_history[-1]["timestamp"] if dashboard.analysis_history else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概览失败: {str(e)}")


@router.get("/trends", summary="获取分析趋势")
async def get_analysis_trends(
    days: int = Query(30, description="分析天数", ge=1, le=365)
):
    """获取AI分析趋势数据"""
    try:
        trends = dashboard.get_analysis_trends(days)
        return {
            "success": True,
            "data": trends,
            "period": f"最近{days}天"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取趋势失败: {str(e)}")


@router.get("/service-comparison", summary="服务比较分析")
async def get_service_comparison():
    """获取AI服务比较数据"""
    try:
        comparison = dashboard.get_service_comparison()
        service_status = config_manager.get_all_service_status()
        
        return {
            "success": True,
            "data": {
                "performance_comparison": comparison,
                "service_status": service_status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取服务比较失败: {str(e)}")


@router.get("/user-insights", summary="用户行为洞察")
async def get_user_insights(
    user_id: Optional[str] = Query(None, description="用户ID")
):
    """获取用户行为洞察"""
    try:
        insights = dashboard.get_user_behavior_insights(user_id)
        return {
            "success": True,
            "data": insights,
            "user_id": user_id or "所有用户"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户洞察失败: {str(e)}")


@router.get("/recommendation-performance", summary="推荐性能分析")
async def get_recommendation_performance():
    """获取推荐性能分析"""
    try:
        performance = dashboard.get_recommendation_performance()
        return {
            "success": True,
            "data": performance
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推荐性能失败: {str(e)}")


@router.get("/export", summary="导出分析数据")
async def export_analytics_data(
    data_type: str = Query("all", description="数据类型: all, analyses, interactions, recommendations, metrics")
):
    """导出AI分析数据"""
    try:
        if data_type not in ["all", "analyses", "interactions", "recommendations", "metrics"]:
            raise HTTPException(status_code=400, detail="无效的数据类型")
        
        export_data = dashboard.export_data(data_type)
        return {
            "success": True,
            "data": export_data,
            "export_type": data_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出数据失败: {str(e)}")


@router.post("/record-interaction", summary="记录用户交互")
async def record_user_interaction(
    interaction_type: str,
    target: str,
    details: Optional[Dict[str, Any]] = None
):
    """记录用户交互"""
    try:
        dashboard.record_user_interaction(interaction_type, target, details)
        return {
            "success": True,
            "message": "交互记录成功",
            "interaction": {
                "type": interaction_type,
                "target": target,
                "timestamp": dashboard.user_interactions[-1]["timestamp"] if dashboard.user_interactions else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录交互失败: {str(e)}")


@router.post("/record-recommendation-impression", summary="记录推荐展示")
async def record_recommendation_impression(
    recommendation_id: str,
    user_id: str
):
    """记录推荐展示"""
    try:
        dashboard.record_recommendation_impression(recommendation_id, user_id)
        return {
            "success": True,
            "message": "推荐展示记录成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录推荐展示失败: {str(e)}")


@router.post("/record-recommendation-click", summary="记录推荐点击")
async def record_recommendation_click(
    recommendation_id: str,
    user_id: str
):
    """记录推荐点击"""
    try:
        dashboard.record_recommendation_click(recommendation_id, user_id)
        return {
            "success": True,
            "message": "推荐点击记录成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录推荐点击失败: {str(e)}")


@router.get("/service-status", summary="获取AI服务状态")
async def get_ai_service_status():
    """获取所有AI服务状态"""
    try:
        service_status = config_manager.get_all_service_status()
        preferred_service = config_manager.get_preferred_service()
        
        return {
            "success": True,
            "data": {
                "service_status": service_status,
                "preferred_service": preferred_service,
                "active_services": config_manager.active_services
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取服务状态失败: {str(e)}")


@router.get("/service-capabilities", summary="获取服务能力")
async def get_service_capabilities(
    service_name: Optional[str] = Query(None, description="服务名称")
):
    """获取AI服务能力信息"""
    try:
        if service_name:
            capabilities = config_manager.get_service_capabilities(service_name)
            return {
                "success": True,
                "data": {
                    service_name: capabilities
                }
            }
        else:
            all_capabilities = {}
            for service in ["openai", "baidu_ai", "google_ai", "local_ai", "simulation"]:
                all_capabilities[service] = config_manager.get_service_capabilities(service)
            
            return {
                "success": True,
                "data": all_capabilities
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取服务能力失败: {str(e)}")


@router.post("/clear-old-data", summary="清理旧数据")
async def clear_old_data(
    days_to_keep: int = Query(90, description="保留天数", ge=1, le=365)
):
    """清理指定天数之前的旧数据"""
    try:
        dashboard.clear_old_data(days_to_keep)
        return {
            "success": True,
            "message": f"已清理{days_to_keep}天之前的旧数据"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理数据失败: {str(e)}")


@router.get("/health", summary="AI分析健康检查")
async def ai_analytics_health():
    """AI分析系统健康检查"""
    try:
        # 检查基本功能
        overview = dashboard.get_dashboard_overview()
        service_status = config_manager.get_all_service_status()
        
        health_status = {
            "dashboard": "正常" if overview else "异常",
            "config_manager": "正常" if service_status else "异常",
            "data_consistency": "正常" if len(dashboard.analysis_history) >= 0 else "异常",
            "services_available": len(config_manager.active_services) > 0
        }
        
        return {
            "success": True,
            "status": "healthy",
            "details": health_status,
            "timestamp": dashboard.analysis_history[-1]["timestamp"] if dashboard.analysis_history else None
        }
    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }