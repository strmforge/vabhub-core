#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件驱动系统
支持插件和模块间的松耦合通信
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional, Set, Type
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()


class EventType(Enum):
    """事件类型枚举"""
    FILE_SCAN_STARTED = "file_scan_started"
    FILE_SCAN_COMPLETED = "file_scan_completed"
    FILE_PROCESSING_STARTED = "file_processing_started"
    FILE_PROCESSING_COMPLETED = "file_processing_completed"
    FILE_RENAMED = "file_renamed"
    ERROR_OCCURRED = "error_occurred"
    DOWNLOAD_STARTED = "download_started"
    DOWNLOAD_COMPLETED = "download_completed"
    SUBSCRIPTION_ADDED = "subscription_added"
    SUBSCRIPTION_TRIGGERED = "subscription_triggered"


@dataclass
class Event:
    """事件基类"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime = None
    source: str = "system"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class FileProcessedEvent(Event):
    """文件处理完成事件"""
    file_path: str
    original_name: str
    new_name: str
    media_type: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class DownloadEvent(Event):
    """下载事件"""
    download_url: str
    file_path: str
    file_size: Optional[int] = None
    download_speed: Optional[float] = None


class EventManager:
    """事件管理器"""
    
    def __init__(self):
        self._listeners: Dict[EventType, Set[Callable]] = {}
        self._async_listeners: Dict[EventType, Set[Callable]] = {}
        
    def subscribe(self, event_type: EventType, listener: Callable, is_async: bool = False):
        """订阅事件"""
        listeners = self._async_listeners if is_async else self._listeners
        if event_type not in listeners:
            listeners[event_type] = set()
        listeners[event_type].add(listener)
        
    def unsubscribe(self, event_type: EventType, listener: Callable, is_async: bool = False):
        """取消订阅"""
        listeners = self._async_listeners if is_async else self._listeners
        if event_type in listeners:
            listeners[event_type].discard(listener)
    
    def publish(self, event: Event):
        """发布事件（同步）"""
        logger.debug("发布事件", event_type=event.event_type.value, source=event.source)
        
        # 处理同步监听器
        if event.event_type in self._listeners:
            for listener in self._listeners[event.event_type]:
                try:
                    listener(event)
                except Exception as e:
                    logger.error("事件监听器执行失败", listener=str(listener), error=str(e))
    
    async def publish_async(self, event: Event):
        """发布事件（异步）"""
        logger.debug("发布异步事件", event_type=event.event_type.value, source=event.source)
        
        # 处理异步监听器
        if event.event_type in self._async_listeners:
            tasks = []
            for listener in self._async_listeners[event.event_type]:
                if inspect.iscoroutinefunction(listener):
                    tasks.append(listener(event))
                else:
                    # 如果是同步函数，在事件循环中运行
                    def sync_wrapper():
                        try:
                            listener(event)
                        except Exception as e:
                            logger.error("异步事件监听器执行失败", listener=str(listener), error=str(e))
                    
                    tasks.append(asyncio.get_event_loop().run_in_executor(None, sync_wrapper))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)


class PluginManager:
    """插件管理器"""
    
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager
        self.plugins: Dict[str, Any] = {}
    
    def register_plugin(self, plugin_name: str, plugin_instance: Any):
        """注册插件"""
        self.plugins[plugin_name] = plugin_instance
        logger.info("插件已注册", plugin=plugin_name)
    
    def load_plugins(self, plugins_dir: str = "plugins"):
        """从目录加载插件"""
        import importlib.util
        import os
        
        if not os.path.exists(plugins_dir):
            return
        
        for filename in os.listdir(plugins_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                plugin_name = filename[:-3]
                plugin_path = os.path.join(plugins_dir, filename)
                
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'Plugin'):
                        plugin_instance = module.Plugin(self.event_manager)
                        self.register_plugin(plugin_name, plugin_instance)
                        
                except Exception as e:
                    logger.error("插件加载失败", plugin=plugin_name, error=str(e))


# 全局事件管理器实例
event_manager = EventManager()
plugin_manager = PluginManager(event_manager)