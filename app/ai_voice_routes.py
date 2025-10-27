#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI语音和视频分析路由
支持语音控制、自然语言交互和高级视频分析
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

from core.ai_voice_processor import AIVoiceProcessor
from core.ai_video_analyzer import AIVideoAnalyzer

router = APIRouter(prefix="/ai", tags=["AI语音和视频分析"])

# 初始化处理器
voice_processor = AIVoiceProcessor()
video_analyzer = AIVideoAnalyzer()


class VoiceCommandRequest(BaseModel):
    """语音命令请求"""
    voice_input: str
    user_id: Optional[str] = None


class VideoAnalysisRequest(BaseModel):
    """视频分析请求"""
    video_path: str
    frame_interval: Optional[int] = 30
    analyze_scenes: Optional[bool] = True
    analyze_faces: Optional[bool] = True
    analyze_objects: Optional[bool] = True
    analyze_text: Optional[bool] = True


class BatchVideoAnalysisRequest(BaseModel):
    """批量视频分析请求"""
    video_paths: List[str]
    frame_interval: Optional[int] = 30


@router.post("/voice/command", summary="处理语音命令")
async def process_voice_command(request: VoiceCommandRequest):
    """
    处理语音命令，支持自然语言交互
    
    - **voice_input**: 语音输入文本
    - **user_id**: 用户ID（可选）
    """
    try:
        result = await voice_processor.process_voice_command(request.voice_input)
        return {
            "success": True,
            "data": result,
            "user_id": request.user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音命令处理失败: {str(e)}")


@router.get("/voice/capabilities", summary="获取语音能力信息")
async def get_voice_capabilities():
    """获取语音处理能力信息"""
    try:
        capabilities = voice_processor.get_voice_capabilities()
        return {
            "success": True,
            "data": capabilities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取语音能力失败: {str(e)}")


@router.get("/voice/history", summary="获取对话历史")
async def get_conversation_history(limit: int = Query(10, ge=1, le=100)):
    """
    获取对话历史记录
    
    - **limit**: 返回的历史记录数量（1-100）
    """
    try:
        history = voice_processor.get_conversation_history(limit)
        return {
            "success": True,
            "data": {
                "history": history,
                "total_count": len(voice_processor.conversation_history)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")


@router.post("/voice/history/clear", summary="清空对话历史")
async def clear_conversation_history():
    """清空对话历史记录"""
    try:
        voice_processor.clear_conversation_history()
        return {
            "success": True,
            "message": "对话历史已清空"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空对话历史失败: {str(e)}")


@router.post("/video/analyze", summary="分析视频内容")
async def analyze_video_content(request: VideoAnalysisRequest):
    """
    分析视频内容，包括场景检测、人脸识别、物体识别等
    
    - **video_path**: 视频文件路径
    - **frame_interval**: 帧间隔（默认30）
    - **analyze_scenes**: 是否分析场景（默认True）
    - **analyze_faces**: 是否识别人脸（默认True）
    - **analyze_objects**: 是否识别物体（默认True）
    - **analyze_text**: 是否识别文本（默认True）
    """
    try:
        # 配置分析选项
        video_analyzer.scene_detection_enabled = request.analyze_scenes
        video_analyzer.face_recognition_enabled = request.analyze_faces
        video_analyzer.object_detection_enabled = request.analyze_objects
        video_analyzer.text_recognition_enabled = request.analyze_text
        
        result = await video_analyzer.analyze_video_frames(
            request.video_path, 
            request.frame_interval
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频分析失败: {str(e)}")


@router.post("/video/analyze/batch", summary="批量分析视频")
async def batch_analyze_videos(request: BatchVideoAnalysisRequest):
    """
    批量分析多个视频文件
    
    - **video_paths**: 视频文件路径列表
    - **frame_interval**: 帧间隔（默认30）
    """
    try:
        results = []
        
        for video_path in request.video_paths:
            result = await video_analyzer.analyze_video_frames(
                video_path, 
                request.frame_interval
            )
            results.append({
                "video_path": video_path,
                "analysis": result
            })
        
        # 生成批量分析统计
        batch_stats = _generate_batch_analysis_stats(results)
        
        return {
            "success": True,
            "data": {
                "results": results,
                "batch_statistics": batch_stats
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量视频分析失败: {str(e)}")


@router.get("/video/capabilities", summary="获取视频分析能力")
async def get_video_analysis_capabilities():
    """获取视频分析能力信息"""
    try:
        capabilities = video_analyzer.get_capabilities()
        return {
            "success": True,
            "data": capabilities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取视频分析能力失败: {str(e)}")


@router.get("/video/supported-formats", summary="获取支持的视频格式")
async def get_supported_video_formats():
    """获取支持的视频文件格式"""
    try:
        capabilities = video_analyzer.get_capabilities()
        return {
            "success": True,
            "data": {
                "supported_formats": capabilities.get("supported_formats", [])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取支持的视频格式失败: {str(e)}")


@router.get("/combined/capabilities", summary="获取综合AI能力")
async def get_combined_ai_capabilities():
    """获取所有AI功能的综合能力信息"""
    try:
        voice_capabilities = voice_processor.get_voice_capabilities()
        video_capabilities = video_analyzer.get_capabilities()
        
        return {
            "success": True,
            "data": {
                "voice_processing": voice_capabilities,
                "video_analysis": video_capabilities,
                "combined_features": {
                    "natural_language_interface": True,
                    "voice_control": True,
                    "video_content_analysis": True,
                    "batch_processing": True,
                    "real_time_analysis": False,  # 当前版本不支持实时分析
                    "multi_modal_ai": True
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取综合AI能力失败: {str(e)}")


@router.post("/demo/voice-interaction", summary="语音交互演示")
async def demo_voice_interaction():
    """语音交互功能演示"""
    try:
        # 演示对话
        demo_conversation = [
            {
                "user_input": "你好",
                "expected_response": "greeting"
            },
            {
                "user_input": "扫描我的电影文件",
                "expected_response": "scan_files"
            },
            {
                "user_input": "分析一下这个视频",
                "expected_response": "analyze_media"
            },
            {
                "user_input": "帮我重命名文件",
                "expected_response": "smart_rename"
            },
            {
                "user_input": "当前状态怎么样",
                "expected_response": "get_status"
            }
        ]
        
        demo_results = []
        
        for demo in demo_conversation:
            result = await voice_processor.process_voice_command(demo["user_input"])
            demo_results.append({
                "user_input": demo["user_input"],
                "system_response": result,
                "expected_action": demo["expected_response"]
            })
        
        return {
            "success": True,
            "data": {
                "demo_conversation": demo_results,
                "voice_capabilities": voice_processor.get_voice_capabilities()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音交互演示失败: {str(e)}")


@router.post("/demo/video-analysis", summary="视频分析演示")
async def demo_video_analysis():
    """视频分析功能演示"""
    try:
        # 创建模拟视频分析结果
        demo_analysis = {
            "video_info": {
                "resolution": "1920x1080",
                "duration_seconds": 120,
                "fps": 30,
                "frame_count": 3600
            },
            "analysis_summary": {
                "total_key_frames": 40,
                "total_faces_detected": 15,
                "total_objects_detected": 28,
                "total_text_regions": 3,
                "scene_type_distribution": {
                    "normal": 25,
                    "vibrant": 10,
                    "dark": 5
                },
                "average_brightness": 127.5,
                "average_contrast": 45.2
            },
            "quality_assessment": {
                "resolution_score": 0.8,
                "brightness_score": 0.9,
                "contrast_score": 0.85,
                "overall_score": 0.85,
                "quality_level": "good"
            }
        }
        
        return {
            "success": True,
            "data": {
                "demo_analysis": demo_analysis,
                "video_capabilities": video_analyzer.get_capabilities()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频分析演示失败: {str(e)}")


def _generate_batch_analysis_stats(results: List[Dict]) -> Dict[str, Any]:
    """生成批量分析统计信息"""
    if not results:
        return {}
    
    total_videos = len(results)
    successful_analyses = sum(1 for r in results if r.get("analysis", {}).get("success", False))
    
    # 统计视频质量分布
    quality_distribution = {}
    total_faces = 0
    total_objects = 0
    
    for result in results:
        analysis = result.get("analysis", {})
        if analysis.get("success"):
            data = analysis.get("data", {})
            quality_assessment = data.get("quality_assessment", {})
            analysis_summary = data.get("analysis_summary", {})
            
            quality_level = quality_assessment.get("quality_level", "unknown")
            quality_distribution[quality_level] = quality_distribution.get(quality_level, 0) + 1
            
            total_faces += analysis_summary.get("total_faces_detected", 0)
            total_objects += analysis_summary.get("total_objects_detected", 0)
    
    return {
        "total_videos": total_videos,
        "successful_analyses": successful_analyses,
        "success_rate": successful_analyses / total_videos if total_videos > 0 else 0,
        "quality_distribution": quality_distribution,
        "total_faces_detected": total_faces,
        "total_objects_detected": total_objects,
        "average_faces_per_video": total_faces / total_videos if total_videos > 0 else 0,
        "average_objects_per_video": total_objects / total_videos if total_videos > 0 else 0
    }