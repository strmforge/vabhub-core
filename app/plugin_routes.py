#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件管理API路由
集成 MoviePilot 的插件化架构精华功能
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

from core.plugin_system import plugin_manager, PluginInfo, PluginType, PluginStatus

router = APIRouter(prefix="/plugins", tags=["plugins"])


class PluginResponse(BaseModel):
    """插件响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class PluginCreate(BaseModel):
    """插件创建模型"""
    name: str = Field(..., description="插件名称")
    version: str = Field(..., description="插件版本")
    description: str = Field(..., description="插件描述")
    author: str = Field(..., description="插件作者")
    plugin_type: PluginType = Field(..., description="插件类型")


class PluginExecuteRequest(BaseModel):
    """插件执行请求模型"""
    plugin_name: str = Field(..., description="插件名称")
    data: Dict[str, Any] = Field(default_factory=dict, description="执行数据")


@router.on_event("startup")
async def startup_event():
    """应用启动时初始化插件管理器"""
    # 添加插件目录
    from pathlib import Path
    plugin_dir = Path(__file__).parent.parent.parent / "plugins"
    plugin_dir.mkdir(exist_ok=True)
    plugin_manager.add_plugin_directory(plugin_dir)
    
    # 加载插件
    await plugin_manager.load_plugins()
    
    # 启用默认插件
    for plugin_name in ["douban_sync", "site_management"]:
        if plugin_name in plugin_manager.plugins:
            await plugin_manager.enable_plugin(plugin_name)


@router.get("/status", response_model=PluginResponse)
async def get_plugin_status():
    """获取插件系统状态"""
    try:
        plugins = plugin_manager.list_plugins()
        status = {
            "total_plugins": len(plugins),
            "enabled_plugins": len([p for p in plugins if p.status == PluginStatus.ENABLED]),
            "disabled_plugins": len([p for p in plugins if p.status == PluginStatus.DISABLED]),
            "plugins": [{
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "type": p.plugin_type.value,
                "status": p.status.value
            } for p in plugins]
        }
        return PluginResponse(
            success=True,
            message="插件系统状态获取成功",
            data=status
        )
    except Exception as e:
        return PluginResponse(
            success=False,
            message=f"获取插件状态失败: {str(e)}"
        )


@router.get("/list", response_model=PluginResponse)
async def list_plugins():
    """获取所有插件列表"""
    try:
        plugins = plugin_manager.list_plugins()
        plugin_list = [{
            "name": p.name,
            "version": p.version,
            "description": p.description,
            "author": p.author,
            "type": p.plugin_type.value,
            "status": p.status.value,
            "dependencies": p.dependencies
        } for p in plugins]
        
        return PluginResponse(
            success=True,
            message="插件列表获取成功",
            data={"plugins": plugin_list}
        )
    except Exception as e:
        return PluginResponse(
            success=False,
            message=f"获取插件列表失败: {str(e)}"
        )


@router.get("/info/{plugin_name}", response_model=PluginResponse)
async def get_plugin_info(plugin_name: str):
    """获取插件详细信息"""
    try:
        plugin_info = plugin_manager.get_plugin_info(plugin_name)
        if not plugin_info:
            return PluginResponse(
                success=False,
                message=f"插件 {plugin_name} 不存在"
            )
        
        return PluginResponse(
            success=True,
            message="插件信息获取成功",
            data={
                "plugin": {
                    "name": plugin_info.name,
                    "version": plugin_info.version,
                    "description": plugin_info.description,
                    "author": plugin_info.author,
                    "type": plugin_info.plugin_type.value,
                    "status": plugin_info.status.value,
                    "dependencies": plugin_info.dependencies,
                    "config_schema": plugin_info.config_schema
                }
            }
        )
    except Exception as e:
        return PluginResponse(
            success=False,
            message=f"获取插件信息失败: {str(e)}"
        )


@router.post("/{plugin_name}/enable", response_model=PluginResponse)
async def enable_plugin(plugin_name: str):
    """启用插件"""
    try:
        success = await plugin_manager.enable_plugin(plugin_name)
        if success:
            return PluginResponse(
                success=True,
                message=f"插件 {plugin_name} 启用成功"
            )
        else:
            return PluginResponse(
                success=False,
                message=f"插件 {plugin_name} 启用失败"
            )
    except Exception as e:
        return PluginResponse(
            success=False,
            message=f"启用插件失败: {str(e)}"
        )


@router.post("/{plugin_name}/disable", response_model=PluginResponse)
async def disable_plugin(plugin_name: str):
    """禁用插件"""
    try:
        success = await plugin_manager.disable_plugin(plugin_name)
        if success:
            return PluginResponse(
                success=True,
                message=f"插件 {plugin_name} 禁用成功"
            )
        else:
            return PluginResponse(
                success=False,
                message=f"插件 {plugin_name} 禁用失败"
            )
    except Exception as e:
        return PluginResponse(
            success=False,
            message=f"禁用插件失败: {str(e)}"
        )


@router.post("/execute", response_model=PluginResponse)
async def execute_plugin(request: PluginExecuteRequest):
    """执行插件"""
    try:
        result = await plugin_manager.execute_plugin(
            request.plugin_name, 
            request.data
        )
        
        if result["success"]:
            return PluginResponse(
                success=True,
                message=f"插件 {request.plugin_name} 执行成功",
                data=result.get("data", {})
            )
        else:
            return PluginResponse(
                success=False,
                message=f"插件执行失败: {result.get('error', '未知错误')}"
            )
    except Exception as e:
        return PluginResponse(
            success=False,
            message=f"执行插件失败: {str(e)}"
        )


@router.post("/reload", response_model=PluginResponse)
async def reload_plugins(background_tasks: BackgroundTasks):
    """重新加载所有插件"""
    try:
        # 在后台任务中重新加载插件
        async def reload_task():
            # 先禁用所有插件
            for plugin_name in list(plugin_manager.plugins.keys()):
                await plugin_manager.disable_plugin(plugin_name)
            
            # 清空插件列表
            plugin_manager.plugins.clear()
            plugin_manager.plugin_info.clear()
            
            # 重新加载插件
            await plugin_manager.load_plugins()
            
            # 重新启用插件
            for plugin_name in ["douban_sync", "site_management"]:
                if plugin_name in plugin_manager.plugins:
                    await plugin_manager.enable_plugin(plugin_name)
        
        background_tasks.add_task(reload_task)
        
        return PluginResponse(
            success=True,
            message="插件重新加载任务已启动"
        )
    except Exception as e:
        return PluginResponse(
            success=False,
            message=f"重新加载插件失败: {str(e)}"
        )


# 特定插件的快捷API
@router.post("/douban/sync", response_model=PluginResponse)
async def sync_douban_wishlist(user_id: str = "default"):
    """同步豆瓣想看列表"""
    try:
        result = await plugin_manager.execute_plugin(
            "douban_sync",
            {"user_id": user_id}
        )
        
        if result["success"]:
            return PluginResponse(
                success=True,
                message="豆瓣同步成功",
                data=result.get("data", {})
            )
        else:
            return PluginResponse(
                success=False,
                message=f"豆瓣同步失败: {result.get('error', '未知错误')}"
            )
    except Exception as e:
        return PluginResponse(
            success=False,
            message=f"豆瓣同步失败: {str(e)}"
        )


@router.post("/sites/signin", response_model=PluginResponse)
async def auto_signin_sites(site_name: Optional[str] = None):
    """自动签到站点"""
    try:
        data = {"task_type": "signin"}
        if site_name:
            data["site_name"] = site_name
        
        result = await plugin_manager.execute_plugin(
            "site_management",
            data
        )
        
        if result["success"]:
            return PluginResponse(
                success=True,
                message="站点签到成功",
                data=result.get("data", {})
            )
        else:
            return PluginResponse(
                success=False,
                message=f"站点签到失败: {result.get('error', '未知错误')}"
            )
    except Exception as e:
        return PluginResponse(
            success=False,
            message=f"站点签到失败: {str(e)}"
        )


@router.post("/sites/cookie-sync", response_model=PluginResponse)
async def sync_site_cookies():
    """同步站点Cookie"""
    try:
        result = await plugin_manager.execute_plugin(
            "site_management",
            {"task_type": "cookie_sync"}
        )
        
        if result["success"]:
            return PluginResponse(
                success=True,
                message="Cookie同步成功",
                data=result.get("data", {})
            )
        else:
            return PluginResponse(
                success=False,
                message=f"Cookie同步失败: {result.get('error', '未知错误')}"
            )
    except Exception as e:
        return PluginResponse(
            success=False,
            message=f"Cookie同步失败: {str(e)}"
        )