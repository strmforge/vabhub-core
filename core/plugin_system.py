#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件系统
集成 MoviePilot 的插件化架构精华功能
"""

import asyncio
import importlib
import inspect
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Type

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """插件类型"""
    SITE_MANAGEMENT = "site_management"
    DOWNLOADER = "downloader"
    NOTIFICATION = "notification"
    METADATA = "metadata"
    SUBSCRIPTION = "subscription"
    ANALYTICS = "analytics"


class PluginStatus(Enum):
    """插件状态"""
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    status: PluginStatus = PluginStatus.LOADED
    config_schema: Optional[Dict[str, Any]] = None
    dependencies: List[str] = field(default_factory=list)


class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self):
        self.plugin_info = PluginInfo(
            name=self.__class__.__name__,
            version="1.0.0",
            description="",
            author="",
            plugin_type=PluginType.SITE_MANAGEMENT
        )
        self.config = {}
        self.logger = logging.getLogger(f"plugin.{self.plugin_info.name}")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行插件功能"""
        pass
    
    async def cleanup(self):
        """清理资源"""
        pass


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_info: Dict[str, PluginInfo] = {}
        self.plugin_directories: List[Path] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
    
    def add_plugin_directory(self, directory: Path):
        """添加插件目录"""
        if directory.exists() and directory.is_dir():
            self.plugin_directories.append(directory)
            logger.info(f"添加插件目录: {directory}")
    
    async def load_plugins(self):
        """加载所有插件"""
        for plugin_dir in self.plugin_directories:
            await self._load_plugins_from_directory(plugin_dir)
    
    async def _load_plugins_from_directory(self, directory: Path):
        """从目录加载插件"""
        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name == "__init__.py":
                continue
            
            try:
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 查找插件类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BasePlugin) and 
                        obj != BasePlugin):
                        
                        plugin_instance = obj()
                        await plugin_instance.initialize()
                        
                        self.plugins[plugin_instance.plugin_info.name] = plugin_instance
                        self.plugin_info[plugin_instance.plugin_info.name] = plugin_instance.plugin_info
                        
                        logger.info(f"加载插件: {plugin_instance.plugin_info.name}")
                        
            except Exception as e:
                logger.error(f"加载插件 {py_file} 失败: {e}")
    
    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        if plugin_name not in self.plugins:
            logger.error(f"插件 {plugin_name} 不存在")
            return False
        
        plugin = self.plugins[plugin_name]
        plugin.plugin_info.status = PluginStatus.ENABLED
        logger.info(f"启用插件: {plugin_name}")
        return True
    
    async def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        if plugin_name not in self.plugins:
            logger.error(f"插件 {plugin_name} 不存在")
            return False
        
        plugin = self.plugins[plugin_name]
        plugin.plugin_info.status = PluginStatus.DISABLED
        await plugin.cleanup()
        logger.info(f"禁用插件: {plugin_name}")
        return True
    
    async def execute_plugin(self, plugin_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行插件"""
        if plugin_name not in self.plugins:
            return {"success": False, "error": f"插件 {plugin_name} 不存在"}
        
        plugin = self.plugins[plugin_name]
        if plugin.plugin_info.status != PluginStatus.ENABLED:
            return {"success": False, "error": f"插件 {plugin_name} 未启用"}
        
        try:
            result = await plugin.execute(data)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"执行插件 {plugin_name} 失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self.plugin_info.get(plugin_name)
    
    def list_plugins(self) -> List[PluginInfo]:
        """列出所有插件"""
        return list(self.plugin_info.values())
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        """触发事件"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if inspect.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"事件处理器执行失败: {e}")


# 全局插件管理器实例
plugin_manager = PluginManager()


# 示例插件实现
class DoubanSyncPlugin(BasePlugin):
    """豆瓣同步插件"""
    
    def __init__(self):
        super().__init__()
        self.plugin_info = PluginInfo(
            name="douban_sync",
            version="1.0.0",
            description="从豆瓣同步想看列表到订阅系统",
            author="SmartMedia Hub",
            plugin_type=PluginType.SUBSCRIPTION
        )
    
    async def initialize(self) -> bool:
        """初始化插件"""
        self.logger.info("豆瓣同步插件初始化完成")
        return True
    
    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行豆瓣同步"""
        user_id = data.get("user_id")
        if not user_id:
            return {"success": False, "error": "缺少用户ID"}
        
        # 模拟豆瓣同步逻辑
        self.logger.info(f"同步豆瓣用户 {user_id} 的想看列表")
        
        # 这里应该实现实际的豆瓣API调用
        # 暂时返回模拟数据
        return {
            "success": True,
            "synced_count": 5,
            "movies": [
                {"title": "电影1", "year": 2024},
                {"title": "电影2", "year": 2023}
            ]
        }


class SiteManagementPlugin(BasePlugin):
    """站点管理插件"""
    
    def __init__(self):
        super().__init__()
        self.plugin_info = PluginInfo(
            name="site_management",
            version="1.0.0",
            description="PT站点自动签到和Cookie管理",
            author="SmartMedia Hub",
            plugin_type=PluginType.SITE_MANAGEMENT
        )
    
    async def initialize(self) -> bool:
        """初始化插件"""
        self.logger.info("站点管理插件初始化完成")
        return True
    
    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行站点管理任务"""
        task_type = data.get("task_type", "signin")
        
        if task_type == "signin":
            return await self._auto_signin(data)
        elif task_type == "cookie_sync":
            return await self._cookie_sync(data)
        else:
            return {"success": False, "error": f"未知任务类型: {task_type}"}
    
    async def _auto_signin(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """自动签到"""
        site_name = data.get("site_name")
        self.logger.info(f"执行站点 {site_name} 自动签到")
        
        # 模拟签到逻辑
        return {
            "success": True,
            "site": site_name,
            "signin_result": "success",
            "points": 100
        }
    
    async def _cookie_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cookie同步"""
        self.logger.info("执行Cookie同步")
        
        # 模拟Cookie同步逻辑
        return {
            "success": True,
            "synced_sites": 3,
            "updated_cookies": 5
        }