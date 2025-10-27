#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能API路由
提供AI相关的智能媒体处理功能
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from core.smart_processor import smart_processor
from core.ai_processor import ai_processor

# 创建AI API路由器
ai_router = APIRouter(prefix="/ai", tags=["AI智能功能"])


# 请求/响应模型
class AIAnalysisRequest(BaseModel):
    file_paths: List[str]
    use_cache: bool = True


class SmartProcessRequest(BaseModel):
    file_paths: List[str]
    use_ai: bool = True
    strategy: str = "auto"


class AIAnalysisResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class BatchAnalysisResponse(BaseModel):
    status: str
    message: str
    results: List[Dict[str, Any]]
    stats: Dict[str, Any]


@ai_router.post("/analyze", response_model=AIAnalysisResponse)
async def analyze_video_content(request: AIAnalysisRequest):
    """分析视频内容"""
    try:
        if not request.file_paths:
            raise HTTPException(status_code=400, detail="文件路径列表不能为空")
        
        # 分析第一个文件（演示用）
        file_path = request.file_paths[0]
        analysis_result = await ai_processor.analyze_video_content(file_path)
        
        return AIAnalysisResponse(
            status="success",
            message="视频内容分析完成",
            data=analysis_result
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@ai_router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def batch_analyze_videos(request: AIAnalysisRequest):
    """批量分析视频"""
    try:
        if not request.file_paths:
            raise HTTPException(status_code=400, detail="文件路径列表不能为空")
        
        results = await ai_processor.batch_analyze(request.file_paths)
        
        # 统计信息
        stats = {
            "total_files": len(request.file_paths),
            "analyzed_files": len(results),
            "average_confidence": sum(r.get("ai_confidence", 0) for r in results) / len(results),
            "success_rate": len([r for r in results if r.get("ai_confidence", 0) > 0.5]) / len(results)
        }
        
        return BatchAnalysisResponse(
            status="success",
            message=f"批量分析完成，共分析 {len(results)} 个文件",
            results=results,
            stats=stats
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量分析失败: {str(e)}")


@ai_router.post("/process/smart", response_model=BatchAnalysisResponse)
async def smart_process_files(request: SmartProcessRequest, background_tasks: BackgroundTasks):
    """智能处理文件"""
    try:
        if not request.file_paths:
            raise HTTPException(status_code=400, detail="文件路径列表不能为空")
        
        # 验证策略
        valid_strategies = ["auto", "skip", "replace", "keep_both"]
        if request.strategy not in valid_strategies:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的处理策略，必须是: {valid_strategies}"
            )
        
        # 在后台处理
        async def process_task():
            await smart_processor.smart_process_files(
                request.file_paths, 
                use_ai=request.use_ai
            )
        
        background_tasks.add_task(process_task)
        
        return BatchAnalysisResponse(
            status="success",
            message="智能处理任务已开始",
            results=[],
            stats={
                "total_files": len(request.file_paths),
                "use_ai": request.use_ai,
                "strategy": request.strategy,
                "task_status": "started"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能处理失败: {str(e)}")


@ai_router.get("/stats")
async def get_ai_stats():
    """获取AI处理统计"""
    try:
        stats = smart_processor.get_processing_stats()
        
        return {
            "status": "success",
            "message": "统计信息获取成功",
            "data": stats
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@ai_router.post("/cache/clear")
async def clear_ai_cache():
    """清除AI缓存"""
    try:
        # 重置AI处理器缓存
        ai_processor.cache_data = {}
        ai_processor._save_cache()
        
        return {
            "status": "success",
            "message": "AI缓存已清除"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")


@ai_router.get("/capabilities")
async def get_ai_capabilities():
    """获取AI功能能力"""
    return {
        "status": "success",
        "message": "AI功能能力获取成功",
        "data": {
            "video_analysis": True,
            "content_classification": True,
            "smart_renaming": True,
            "quality_assessment": True,
            "batch_processing": True,
            "cache_support": True,
            "real_ai_integration": False,  # 当前为模拟AI
            "supported_formats": ["mp4", "mkv", "avi", "mov", "wmv"],
            "max_batch_size": 100,
            "analysis_methods": ["filename_pattern", "metadata_extraction", "ai_simulation"]
        }
    }