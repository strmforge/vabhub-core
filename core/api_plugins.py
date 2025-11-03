"""
插件管理API路由

提供插件的安装、卸载、启用、禁用等管理功能
"""

from fastapi import APIRouter, HTTPException, Query, Body, Body
from typing import List, Dict, Any
from pydantic import BaseModel

from .plugin_manager import PluginManager, PluginInfo, PluginStatus


class PluginResponse(BaseModel):
    """插件响应模型"""
    id: str
    name: str
    version: str
    description: str
    author: str
    status: str
    dependencies: List[str]
    config_schema: Dict[str, Any] = {}
    config: Dict[str, Any] = {}


class PluginInstallRequest(BaseModel):
    """插件安装请求模型"""
    plugin_id: str
    source_url: str = ""
    version: str = "latest"


class PluginConfigUpdate(BaseModel):
    """插件配置更新模型"""
    config: Dict[str, Any]


router = APIRouter(prefix="/api/plugins", tags=["plugins"])

# 创建插件管理器实例
plugin_manager = PluginManager()


@router.get("/", response_model=List[PluginResponse])
async def list_plugins():
    """
    列出所有插件
    
    Returns:
        插件列表
    """
    try:
        plugins = await plugin_manager.list_plugins()
        return [
            PluginResponse(
                id=plugin.id,
                name=plugin.name,
                version=plugin.version,
                description=plugin.description,
                author=plugin.author,
                status=plugin.status.value,
                dependencies=plugin.dependencies,
                config_schema=plugin.config_schema or {},
                config=plugin.config or {}
            )
            for plugin in plugins
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list plugins: {str(e)}")


@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: str):
    """
    获取插件详情
    
    Args:
        plugin_id: 插件ID
        
    Returns:
        插件详情
    """
    try:
        plugin_info = await plugin_manager.get_plugin_info(plugin_id)
        if not plugin_info:
            raise HTTPException(status_code=404, detail="Plugin not found")
        
        return PluginResponse(
            id=plugin_info.id,
            name=plugin_info.name,
            version=plugin_info.version,
            description=plugin_info.description,
            author=plugin_info.author,
            status=plugin_info.status.value,
            dependencies=plugin_info.dependencies,
            config_schema=plugin_info.config_schema or {},
            config=plugin_info.config or {}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get plugin: {str(e)}")


@router.post("/{plugin_id}/install")
async def install_plugin(plugin_id: str, request: PluginInstallRequest):
    """
    安装插件
    
    Args:
        plugin_id: 插件ID
        request: 安装请求
        
    Returns:
        安装结果
    """
    try:
        # 这里应该实现从远程仓库下载插件的逻辑
        # 目前先实现本地插件的加载
        success = await plugin_manager.load_plugin(plugin_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to install plugin")
        
        return {"ok": True, "id": plugin_id, "message": "Plugin installed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to install plugin: {str(e)}")


@router.delete("/{plugin_id}/uninstall")
async def uninstall_plugin(plugin_id: str):
    """
    卸载插件
    
    Args:
        plugin_id: 插件ID
        
    Returns:
        卸载结果
    """
    try:
        success = await plugin_manager.unload_plugin(plugin_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to uninstall plugin")
        
        return {"ok": True, "id": plugin_id, "message": "Plugin uninstalled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to uninstall plugin: {str(e)}")


@router.post("/{plugin_id}/enable")
async def enable_plugin(plugin_id: str):
    """
    启用插件
    
    Args:
        plugin_id: 插件ID
        
    Returns:
        启用结果
    """
    try:
        success = await plugin_manager.enable_plugin(plugin_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to enable plugin")
        
        return {"ok": True, "id": plugin_id, "message": "Plugin enabled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable plugin: {str(e)}")


@router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str):
    """
    禁用插件
    
    Args:
        plugin_id: 插件ID
        
    Returns:
        禁用结果
    """
    try:
        success = await plugin_manager.disable_plugin(plugin_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to disable plugin")
        
        return {"ok": True, "id": plugin_id, "message": "Plugin disabled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable plugin: {str(e)}")


@router.get("/{plugin_id}/config")
async def get_plugin_config(plugin_id: str):
    """
    获取插件配置
    
    Args:
        plugin_id: 插件ID
        
    Returns:
        插件配置
    """
    try:
        plugin_info = await plugin_manager.get_plugin_info(plugin_id)
        if not plugin_info:
            raise HTTPException(status_code=404, detail="Plugin not found")
        
        return {"config": plugin_info.config or {}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get plugin config: {str(e)}")


@router.put("/{plugin_id}/config")
async def update_plugin_config(plugin_id: str, config_update: PluginConfigUpdate):
    """
    更新插件配置
    
    Args:
        plugin_id: 插件ID
        config_update: 配置更新
        
    Returns:
        更新结果
    """
    try:
        plugin_info = await plugin_manager.get_plugin_info(plugin_id)
        if not plugin_info:
            raise HTTPException(status_code=404, detail="Plugin not found")
        
        # 这里应该实现配置验证和保存逻辑
        # 目前先简单返回成功
        return {"ok": True, "id": plugin_id, "message": "Plugin config updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update plugin config: {str(e)}")


@router.get("/registry/discover")
async def discover_plugins():
    """
    发现可用插件
    
    Returns:
        可发现的插件列表
    """
    try:
        discovered = await plugin_manager.discover_plugins()
        return [
            {
                "id": plugin.id,
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "author": plugin.author,
                "status": plugin.status.value
            }
            for plugin in discovered
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover plugins: {str(e)}")


@router.post("/{plugin_id}/execute")
async def execute_plugin_method(
    plugin_id: str,
    method_name: str = Query(..., description="要执行的方法名"),
    args: List[Any] = Query([], description="方法参数"),
    kwargs: Dict[str, Any] = Body({}, description="方法关键字参数")
):
    """
    执行插件方法
    
    Args:
        plugin_id: 插件ID
        method_name: 方法名
        args: 位置参数
        kwargs: 关键字参数
        
    Returns:
        方法执行结果
    """
    try:
        result = await plugin_manager.execute_plugin_method(plugin_id, method_name, *args, **kwargs)
        return {"ok": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute plugin method: {str(e)}")