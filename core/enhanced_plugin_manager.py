#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 增强版插件管理器
基于MoviePilot插件系统设计，提供完整的插件生命周期管理
"""

import asyncio
import importlib
import inspect
import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel, Field


class PluginStatus(Enum):
    """插件状态枚举"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    LOADING = "loading"
    ERROR = "error"
    UNINSTALLED = "uninstalled"


class PluginType(Enum):
    """插件类型枚举"""
    CORE = "core"  # 核心插件
    MEDIA = "media"  # 媒体处理插件
    DOWNLOAD = "download"  # 下载相关插件
    SEARCH = "search"  # 搜索相关插件
    NOTIFICATION = "notification"  # 通知插件
    ANALYTICS = "analytics"  # 分析插件
    CUSTOM = "custom"  # 自定义插件


@dataclass
class PluginMetadata:
    """插件元数据"""
    id: str  # 插件唯一标识
    name: str  # 插件名称
    version: str  # 插件版本
    description: str  # 插件描述
    author: str  # 作者
    plugin_type: PluginType  # 插件类型
    dependencies: List[str] = field(default_factory=list)  # 依赖插件列表
    config_schema: Optional[Dict[str, Any]] = None  # 配置模式
    dashboard_config: Optional[Dict[str, Any]] = None  # 仪表盘配置
    

class PluginConfig(BaseModel):
    """插件配置模型"""
    enabled: bool = Field(default=True, description="是否启用插件")
    priority: int = Field(default=50, ge=1, le=100, description="插件优先级")
    config: Dict[str, Any] = Field(default_factory=dict, description="插件配置")


class PluginEvent(Enum):
    """插件事件类型"""
    LOAD = "load"  # 插件加载
    UNLOAD = "unload"  # 插件卸载
    CONFIG_CHANGE = "config_change"  # 配置变更
    ERROR = "error"  # 错误事件


class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self, plugin_manager: 'EnhancedPluginManager'):
        self.plugin_manager = plugin_manager
        self.logger = logging.getLogger(f"plugin.{self.get_metadata().id}")
        self._config: Optional[PluginConfig] = None
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        pass
    
    @abstractmethod
    async def init(self) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    async def destroy(self):
        """销毁插件"""
        pass
    
    async def on_config_change(self, old_config: PluginConfig, new_config: PluginConfig):
        """配置变更回调"""
        self.logger.info(f"插件配置已变更: {old_config} -> {new_config}")
    
    def get_dashboard_config(self) -> Optional[Dict[str, Any]]:
        """获取仪表盘配置"""
        metadata = self.get_metadata()
        return metadata.dashboard_config


class EnhancedPluginManager:
    """增强版插件管理器"""
    
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("plugin_manager")
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_configs: Dict[str, PluginConfig] = {}
        self.plugin_status: Dict[str, PluginStatus] = {}
        self.event_handlers: Dict[PluginEvent, List[callable]] = {}
        
        # 加载插件配置
        self._load_configs()
    
    def _load_configs(self):
        """加载插件配置"""
        config_file = self.plugin_dir / "plugins.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    for plugin_id, config in config_data.items():
                        self.plugin_configs[plugin_id] = PluginConfig(**config)
            except Exception as e:
                self.logger.error(f"加载插件配置失败: {e}")
    
    def _save_configs(self):
        """保存插件配置"""
        config_file = self.plugin_dir / "plugins.json"
        try:
            config_data = {}
            for plugin_id, config in self.plugin_configs.items():
                config_data[plugin_id] = config.dict()
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存插件配置失败: {e}")
    
    async def load_plugin(self, plugin_class: Type[BasePlugin]) -> bool:
        """加载插件"""
        try:
            plugin_instance = plugin_class(self)
            metadata = plugin_instance.get_metadata()
            plugin_id = metadata.id
            
            # 检查依赖
            if not await self._check_dependencies(metadata.dependencies):
                self.logger.error(f"插件 {plugin_id} 依赖检查失败")
                return False
            
            # 设置插件状态
            self.plugin_status[plugin_id] = PluginStatus.LOADING
            
            # 初始化配置
            if plugin_id not in self.plugin_configs:
                self.plugin_configs[plugin_id] = PluginConfig()
            
            # 初始化插件
            if await plugin_instance.init():
                self.plugins[plugin_id] = plugin_instance
                self.plugin_status[plugin_id] = PluginStatus.ENABLED
                self._emit_event(PluginEvent.LOAD, plugin_id)
                self.logger.info(f"插件 {plugin_id} 加载成功")
                return True
            else:
                self.plugin_status[plugin_id] = PluginStatus.ERROR
                self.logger.error(f"插件 {plugin_id} 初始化失败")
                return False
                
        except Exception as e:
            self.plugin_status[plugin_id] = PluginStatus.ERROR
            self.logger.error(f"加载插件 {plugin_id} 失败: {e}")
            return False
    
    async def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        if plugin_id not in self.plugins:
            return False
        
        try:
            plugin = self.plugins[plugin_id]
            await plugin.destroy()
            del self.plugins[plugin_id]
            self.plugin_status[plugin_id] = PluginStatus.DISABLED
            self._emit_event(PluginEvent.UNLOAD, plugin_id)
            self.logger.info(f"插件 {plugin_id} 卸载成功")
            return True
        except Exception as e:
            self.logger.error(f"卸载插件 {plugin_id} 失败: {e}")
            return False
    
    async def reload_plugin(self, plugin_id: str) -> bool:
        """重新加载插件"""
        if await self.unload_plugin(plugin_id):
            # 这里需要重新实例化插件类，实际实现中需要更复杂的逻辑
            self.logger.warning(f"插件 {plugin_id} 热重载需要重启服务")
            return False
        return False
    
    async def update_plugin_config(self, plugin_id: str, config: PluginConfig) -> bool:
        """更新插件配置"""
        if plugin_id not in self.plugin_configs:
            return False
        
        old_config = self.plugin_configs[plugin_id]
        self.plugin_configs[plugin_id] = config
        
        # 保存配置
        self._save_configs()
        
        # 通知插件配置变更
        if plugin_id in self.plugins:
            plugin = self.plugins[plugin_id]
            await plugin.on_config_change(old_config, config)
        
        self._emit_event(PluginEvent.CONFIG_CHANGE, plugin_id, {"old": old_config, "new": config})
        return True
    
    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """获取插件信息"""
        if plugin_id not in self.plugins:
            return None
        
        plugin = self.plugins[plugin_id]
        metadata = plugin.get_metadata()
        config = self.plugin_configs.get(plugin_id)
        status = self.plugin_status.get(plugin_id)
        
        return {
            "metadata": metadata.__dict__,
            "config": config.dict() if config else {},
            "status": status.value if status else PluginStatus.DISABLED.value
        }
    
    def get_all_plugins_info(self) -> List[Dict[str, Any]]:
        """获取所有插件信息"""
        plugins_info = []
        for plugin_id in set(list(self.plugins.keys()) + list(self.plugin_configs.keys())):
            info = self.get_plugin_info(plugin_id)
            if info:
                plugins_info.append(info)
        return plugins_info
    
    async def _check_dependencies(self, dependencies: List[str]) -> bool:
        """检查插件依赖"""
        for dep_id in dependencies:
            if dep_id not in self.plugins or self.plugin_status.get(dep_id) != PluginStatus.ENABLED:
                self.logger.error(f"依赖插件 {dep_id} 未加载或未启用")
                return False
        return True
    
    def _emit_event(self, event: PluginEvent, plugin_id: str, data: Optional[Dict] = None):
        """触发插件事件"""
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    handler(plugin_id, data or {})
                except Exception as e:
                    self.logger.error(f"插件事件处理失败: {e}")
    
    def register_event_handler(self, event: PluginEvent, handler: callable):
        """注册事件处理器"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    def unregister_event_handler(self, event: PluginEvent, handler: callable):
        """注销事件处理器"""
        if event in self.event_handlers:
            if handler in self.event_handlers[event]:
                self.event_handlers[event].remove(handler)


# 示例插件实现
class ExampleMediaPlugin(BasePlugin):
    """示例媒体处理插件"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="example_media_plugin",
            name="示例媒体插件",
            version="1.0.0",
            description="示例媒体处理插件",
            author="VabHub Team",
            plugin_type=PluginType.MEDIA,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "auto_scan": {"type": "boolean", "default": True},
                    "scan_interval": {"type": "integer", "default": 3600}
                }
            },
            dashboard_config={
                "title": "媒体处理",
                "component": "MediaProcessor",
                "width": 6,
                "height": 400
            }
        )
    
    async def init(self) -> bool:
        self.logger.info("示例媒体插件初始化")
        # 初始化逻辑
        return True
    
    async def destroy(self):
        self.logger.info("示例媒体插件销毁")
        # 清理逻辑


# 插件管理器单例
_plugin_manager_instance: Optional[EnhancedPluginManager] = None


def get_plugin_manager() -> EnhancedPluginManager:
    """获取插件管理器单例"""
    global _plugin_manager_instance
    if _plugin_manager_instance is None:
        _plugin_manager_instance = EnhancedPluginManager()
    return _plugin_manager_instance


async def initialize_plugins():
    """初始化所有插件"""
    plugin_manager = get_plugin_manager()
    
    # 注册示例插件
    await plugin_manager.load_plugin(ExampleMediaPlugin)
    
    # 这里可以自动扫描和加载插件目录中的插件
    # await _auto_discover_plugins(plugin_manager)


async def _auto_discover_plugins(plugin_manager: EnhancedPluginManager):
    """自动发现和加载插件"""
    # 实现自动插件发现逻辑
    pass