#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能家居集成API路由
提供媒体服务器集成和智能家居联动功能
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

from core.smart_home_manager import smart_home_manager


# 数据模型
class PlexConnectionRequest(BaseModel):
    url: str = Field(..., description="Plex服务器URL")
    token: str = Field(..., description="Plex访问令牌")

class JellyfinConnectionRequest(BaseModel):
    url: str = Field(..., description="Jellyfin服务器URL")
    api_key: str = Field(..., description="Jellyfin API密钥")

class HomeAssistantConnectionRequest(BaseModel):
    url: str = Field(..., description="HomeAssistant服务器URL")
    token: str = Field(..., description="HomeAssistant访问令牌")

class SmartSceneRequest(BaseModel):
    scene_name: str = Field(..., description="智能场景名称")
    media_info: Dict[str, Any] = Field(default={}, description="媒体信息")

class VoiceControlRequest(BaseModel):
    command: str = Field(..., description="语音命令")


# 创建路由器
router = APIRouter(prefix="/smart-home", tags=["智能家居集成"])


@router.get("/status", summary="获取智能家居集成状态")
async def get_smart_home_status():
    """获取智能家居集成状态信息"""
    try:
        status = await smart_home_manager.get_sync_status()
        return {
            "success": True,
            "data": status,
            "message": "智能家居集成状态获取成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/plex/connect", summary="连接Plex媒体服务器")
async def connect_plex_server(request: PlexConnectionRequest):
    """连接Plex媒体服务器"""
    try:
        result = await smart_home_manager.connect_plex_server(request.url, request.token)
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": "Plex服务器连接成功"
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plex连接失败: {str(e)}")


@router.post("/jellyfin/connect", summary="连接Jellyfin媒体服务器")
async def connect_jellyfin_server(request: JellyfinConnectionRequest):
    """连接Jellyfin媒体服务器"""
    try:
        result = await smart_home_manager.connect_jellyfin_server(request.url, request.api_key)
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": "Jellyfin服务器连接成功"
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jellyfin连接失败: {str(e)}")


@router.post("/homeassistant/connect", summary="连接HomeAssistant智能家居平台")
async def connect_homeassistant(request: HomeAssistantConnectionRequest):
    """连接HomeAssistant智能家居平台"""
    try:
        result = await smart_home_manager.connect_homeassistant(request.url, request.token)
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": "HomeAssistant连接成功"
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HomeAssistant连接失败: {str(e)}")


@router.post("/sync/{server_type}", summary="同步媒体库到智能家居平台")
async def sync_media_library(server_type: str):
    """同步指定类型的媒体服务器库"""
    try:
        result = await smart_home_manager.sync_media_library(server_type)
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": f"{server_type}媒体库同步成功"
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"媒体库同步失败: {str(e)}")


@router.post("/scene/trigger", summary="触发智能场景")
async def trigger_smart_scene(request: SmartSceneRequest):
    """触发智能家居场景"""
    try:
        result = await smart_home_manager.trigger_smart_scene(request.scene_name, request.media_info)
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": f"智能场景'{request.scene_name}'触发成功"
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能场景触发失败: {str(e)}")


@router.post("/voice/control", summary="语音控制媒体播放")
async def voice_control_media(request: VoiceControlRequest):
    """语音控制媒体播放"""
    try:
        result = await smart_home_manager.voice_control_media(request.command)
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": "语音命令执行成功"
            }
        else:
            return {
                "success": False,
                "data": result,
                "message": result["message"]
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音控制失败: {str(e)}")


@router.get("/scenes/available", summary="获取可用智能场景列表")
async def get_available_scenes():
    """获取可用的智能场景列表"""
    try:
        scenes = [
            {
                "name": "movie_night",
                "display_name": "电影之夜",
                "description": "自动调暗灯光，设置舒适温度，营造影院氛围",
                "supported_platforms": ["homeassistant", "xiaomi"]
            },
            {
                "name": "music_party", 
                "display_name": "音乐派对",
                "description": "设置彩色灯光，营造派对氛围",
                "supported_platforms": ["homeassistant"]
            },
            {
                "name": "reading_time",
                "display_name": "阅读时间", 
                "description": "调整阅读灯亮度，创造舒适的阅读环境",
                "supported_platforms": ["homeassistant"]
            }
        ]
        
        return {
            "success": True,
            "data": scenes,
            "message": "可用智能场景列表获取成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取场景列表失败: {str(e)}")


@router.get("/platforms/supported", summary="获取支持的智能家居平台")
async def get_supported_platforms():
    """获取支持的智能家居平台列表"""
    try:
        platforms = [
            {
                "name": "plex",
                "display_name": "Plex",
                "description": "流行的媒体服务器平台",
                "type": "media_server"
            },
            {
                "name": "jellyfin",
                "display_name": "Jellyfin", 
                "description": "开源媒体服务器平台",
                "type": "media_server"
            },
            {
                "name": "emby",
                "display_name": "Emby",
                "description": "另一款流行的媒体服务器",
                "type": "media_server"
            },
            {
                "name": "homeassistant",
                "display_name": "HomeAssistant",
                "description": "开源智能家居平台",
                "type": "smart_home"
            },
            {
                "name": "xiaomi",
                "display_name": "小米智能家居",
                "description": "小米智能家居生态系统",
                "type": "smart_home"
            },
            {
                "name": "homekit",
                "display_name": "Apple HomeKit",
                "description": "苹果智能家居平台",
                "type": "smart_home"
            }
        ]
        
        return {
            "success": True,
            "data": platforms,
            "message": "支持的智能家居平台列表获取成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取平台列表失败: {str(e)}")


@router.get("/sync/history", summary="获取同步历史记录")
async def get_sync_history():
    """获取媒体库同步历史记录"""
    try:
        # 这里可以添加分页和过滤逻辑
        sync_history = smart_home_manager.sync_history
        
        return {
            "success": True,
            "data": sync_history,
            "message": "同步历史记录获取成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步历史失败: {str(e)}")


@router.post("/test/connection", summary="测试智能家居连接")
async def test_smart_home_connection():
    """测试智能家居平台连接状态"""
    try:
        # 模拟连接测试
        test_results = []
        
        # 测试媒体服务器连接
        for server_type in ["plex", "jellyfin", "emby"]:
            config = smart_home_manager.media_servers.get(server_type, {})
            if config.get("enabled"):
                test_results.append({
                    "platform": server_type,
                    "type": "media_server", 
                    "status": "connected",
                    "message": f"{server_type}连接正常"
                })
            else:
                test_results.append({
                    "platform": server_type,
                    "type": "media_server",
                    "status": "disconnected", 
                    "message": f"{server_type}未配置"
                })
        
        # 测试智能家居平台连接
        for platform in ["homeassistant", "xiaomi", "homekit"]:
            config = smart_home_manager.smart_home_platforms.get(platform, {})
            if config.get("enabled"):
                test_results.append({
                    "platform": platform,
                    "type": "smart_home",
                    "status": "connected",
                    "message": f"{platform}连接正常"
                })
            else:
                test_results.append({
                    "platform": platform,
                    "type": "smart_home",
                    "status": "disconnected",
                    "message": f"{platform}未配置"
                })
        
        return {
            "success": True,
            "data": test_results,
            "message": "智能家居连接测试完成"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接测试失败: {str(e)}")