#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多设备同步API路由
提供跨设备数据同步和统一用户画像功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

from core.multi_device_sync import multi_device_sync_manager


# 数据模型
class DeviceRegistrationRequest(BaseModel):
    device_name: str = Field(..., description="设备名称")
    device_type: str = Field(..., description="设备类型")
    os_version: str = Field(..., description="操作系统版本")
    app_version: str = Field(..., description="应用版本")
    capabilities: List[str] = Field(default=[], description="设备能力")

class SyncDataRequest(BaseModel):
    device_id: str = Field(..., description="设备ID")
    sync_data: Dict[str, Any] = Field(..., description="同步数据")

class UserProfileRequest(BaseModel):
    user_id: str = Field(default="user_id", description="用户ID")


# 创建路由器
router = APIRouter(prefix="/multi-device-sync", tags=["多设备同步"])


@router.get("/status", summary="获取多设备同步状态")
async def get_multi_device_sync_status():
    """获取多设备同步状态信息"""
    try:
        status = await multi_device_sync_manager.get_sync_status()
        
        if status["success"]:
            return {
                "success": True,
                "data": status["data"],
                "message": "多设备同步状态获取成功"
            }
        else:
            raise HTTPException(status_code=500, detail=status["message"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步状态失败: {str(e)}")


@router.post("/device/register", summary="注册新设备")
async def register_device(request: DeviceRegistrationRequest):
    """注册新设备到多设备同步系统"""
    try:
        device_info = {
            "device_name": request.device_name,
            "device_type": request.device_type,
            "os_version": request.os_version,
            "app_version": request.app_version,
            "capabilities": request.capabilities,
            "registration_time": ""  # 由管理器填充
        }
        
        result = await multi_device_sync_manager.register_device(device_info)
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": "设备注册成功"
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设备注册失败: {str(e)}")


@router.post("/data/sync", summary="同步设备数据")
async def sync_device_data(request: SyncDataRequest):
    """同步设备数据到云端"""
    try:
        result = await multi_device_sync_manager.sync_data(request.device_id, request.sync_data)
        
        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": "设备数据同步成功"
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据同步失败: {str(e)}")


@router.get("/user/profile", summary="获取统一用户画像")
async def get_unified_user_profile(request: UserProfileRequest):
    """获取基于多设备数据的统一用户画像"""
    try:
        result = await multi_device_sync_manager.get_unified_user_profile(request.user_id)
        
        if result["success"]:
            return {
                "success": True,
                "data": result["data"],
                "message": "统一用户画像获取成功"
            }
        else:
            raise HTTPException(status_code=404, detail=result["message"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户画像失败: {str(e)}")


@router.get("/devices/registered", summary="获取已注册设备列表")
async def get_registered_devices():
    """获取所有已注册的设备列表"""
    try:
        device_registry = multi_device_sync_manager.device_registry
        
        devices = []
        for device_id, device_info in device_registry.items():
            devices.append({
                "device_id": device_id,
                "device_name": device_info["device_info"].get("device_name", "未知"),
                "device_type": device_info["device_info"].get("device_type", "未知"),
                "registration_time": device_info.get("registration_time"),
                "last_sync_time": device_info.get("last_sync_time"),
                "sync_count": device_info.get("sync_count", 0),
                "status": device_info.get("sync_status", "unknown")
            })
        
        return {
            "success": True,
            "data": devices,
            "message": "已注册设备列表获取成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")


@router.get("/sync/history", summary="获取同步历史记录")
async def get_sync_history():
    """获取所有设备的同步历史记录"""
    try:
        sync_history = multi_device_sync_manager.sync_history
        
        # 格式化历史记录
        formatted_history = []
        for sync_id, sync_info in sync_history.items():
            formatted_history.append({
                "sync_id": sync_id,
                "device_id": sync_info.get("device_id"),
                "sync_time": sync_info.get("sync_time"),
                "data_types": sync_info.get("data_types", []),
                "sync_result": sync_info.get("sync_result", {})
            })
        
        # 按时间排序
        formatted_history.sort(key=lambda x: x.get("sync_time", ""), reverse=True)
        
        return {
            "success": True,
            "data": formatted_history,
            "message": "同步历史记录获取成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步历史失败: {str(e)}")


@router.post("/sync/start-auto", summary="启动自动同步")
async def start_auto_sync():
    """启动自动同步服务"""
    try:
        await multi_device_sync_manager.start_auto_sync()
        
        return {
            "success": True,
            "message": "自动同步服务已启动"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动自动同步失败: {str(e)}")


@router.get("/config", summary="获取同步配置")
async def get_sync_config():
    """获取多设备同步配置"""
    try:
        sync_config = multi_device_sync_manager.sync_config
        
        return {
            "success": True,
            "data": sync_config,
            "message": "同步配置获取成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步配置失败: {str(e)}")


@router.post("/config/update", summary="更新同步配置")
async def update_sync_config(config: Dict[str, Any]):
    """更新多设备同步配置"""
    try:
        # 验证配置参数
        valid_keys = ["sync_enabled", "sync_interval", "max_sync_retries", 
                     "sync_data_types", "encryption_enabled", "compression_enabled", 
                     "conflict_resolution"]
        
        for key in config.keys():
            if key not in valid_keys:
                raise HTTPException(status_code=400, detail=f"无效的配置项: {key}")
        
        # 更新配置
        multi_device_sync_manager.sync_config.update(config)
        await multi_device_sync_manager._save_sync_config()
        
        return {
            "success": True,
            "message": "同步配置更新成功",
            "data": multi_device_sync_manager.sync_config
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新同步配置失败: {str(e)}")


@router.get("/statistics", summary="获取同步统计信息")
async def get_sync_statistics():
    """获取多设备同步的统计信息"""
    try:
        device_registry = multi_device_sync_manager.device_registry
        sync_history = multi_device_sync_manager.sync_history
        
        statistics = {
            "total_devices": len(device_registry),
            "total_syncs": len(sync_history),
            "devices_by_type": {},
            "syncs_by_device": {},
            "data_types_synced": {}
        }
        
        # 按设备类型统计
        for device_info in device_registry.values():
            device_type = device_info["device_info"].get("device_type", "unknown")
            statistics["devices_by_type"][device_type] = statistics["devices_by_type"].get(device_type, 0) + 1
        
        # 按设备统计同步次数
        for sync_info in sync_history.values():
            device_id = sync_info.get("device_id")
            if device_id:
                statistics["syncs_by_device"][device_id] = statistics["syncs_by_device"].get(device_id, 0) + 1
        
        # 统计同步的数据类型
        for sync_info in sync_history.values():
            data_types = sync_info.get("data_types", [])
            for data_type in data_types:
                statistics["data_types_synced"][data_type] = statistics["data_types_synced"].get(data_type, 0) + 1
        
        return {
            "success": True,
            "data": statistics,
            "message": "同步统计信息获取成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/test/sync", summary="测试同步功能")
async def test_sync_functionality():
    """测试多设备同步功能"""
    try:
        # 模拟测试数据
        test_device_info = {
            "device_name": "Test Device",
            "device_type": "test",
            "os_version": "1.0.0",
            "app_version": "1.0.0",
            "capabilities": ["sync", "profile"]
        }
        
        # 注册测试设备
        registration_result = await multi_device_sync_manager.register_device(test_device_info)
        
        if not registration_result["success"]:
            return {
                "success": False,
                "message": "设备注册测试失败",
                "details": registration_result
            }
        
        device_id = registration_result["device_id"]
        
        # 测试数据同步
        test_sync_data = {
            "user_preferences": {
                "language": "zh-CN",
                "theme": "dark",
                "auto_play": True
            },
            "watch_history": [
                {
                    "media_id": "test_movie_1",
                    "title": "测试电影1",
                    "last_watched": "2024-01-01T20:00:00",
                    "watch_duration": 3600
                }
            ]
        }
        
        sync_result = await multi_device_sync_manager.sync_data(device_id, test_sync_data)
        
        # 测试用户画像获取
        profile_result = await multi_device_sync_manager.get_unified_user_profile()
        
        test_results = {
            "device_registration": registration_result,
            "data_sync": sync_result,
            "user_profile": profile_result
        }
        
        return {
            "success": True,
            "message": "同步功能测试完成",
            "data": test_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步功能测试失败: {str(e)}")