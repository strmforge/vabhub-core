#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强插件管理器
整合NASTools的插件热加载和生命周期管理功能
"""

import asyncio
import importlib
import inspect
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import Thread, Lock, Event as ThreadEvent
from typing import Any, Dict, List, Optional, Type

import structlog
from app.utils.commons import SingletonMeta

from .enhanced_event import EventType, Event, event_manager

logger = structlog.get_logger()


class PluginStatus(Enum):
    """插件状态枚举"""
    LOADED = "loaded"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    status: PluginStatus
    load_time: datetime
    config: Dict[str, Any]


class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        self.description = ""
        self.author = ""
        self.config = {}
        self.status = PluginStatus.LOADED
        self._stop_event = ThreadEvent()
    
    @abstractmethod
    async def start(self):
        """启动插件"""
        pass
    
    @abstractmethod
    async def stop(self):
        """停止插件"""
        pass
    
    def update_config(self, config: Dict[str, Any]):
        """更新插件配置"""
        self.config.update(config)
        logger.info("插件配置已更新", plugin=self.name)
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            status=self.status,
            load_time=datetime.now(),
            config=self.config.copy()
        )


class EnhancedPluginManager(metaclass=SingletonMeta):
    """增强插件管理器 - 整合NASTools的热加载机制"""
    
    def __init__(self):
        # 插件目录
        self.plugins_dir = Path("plugins")
        self.user_plugins_dir = Path("user_plugins")
        
        # 插件存储
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_info: Dict[str, PluginInfo] = {}
        
        # 热加载监控
        self._monitor_thread = None
        self._stop_monitor = ThreadEvent()
        self._file_timestamps: Dict[str, float] = {}
        
        # 线程安全
        self._lock = Lock()
        
        # 创建插件目录
        self._create_directories()
    
    def _create_directories(self):
        """创建插件目录"""
        self.plugins_dir.mkdir(exist_ok=True)
        self.user_plugins_dir.mkdir(exist_ok=True)
    
    def start(self):
        """启动插件管理器"""
        # 加载所有插件
        self.load_all_plugins()
        
        # 启动热加载监控
        self._start_hot_reload_monitor()
        
        logger.info("增强插件管理器已启动")
    
    def stop(self):
        """停止插件管理器"""
        # 停止热加载监控
        self._stop_hot_reload_monitor()
        
        # 停止所有插件
        self.stop_all_plugins()
        
        logger.info("增强插件管理器已停止")
    
    def load_all_plugins(self):
        """加载所有插件"""
        with self._lock:
            # 加载系统插件
            self._load_plugins_from_dir(self.plugins_dir)
            
            # 加载用户插件
            self._load_plugins_from_dir(self.user_plugins_dir)
            
            logger.info("所有插件加载完成", count=len(self.plugins))
    
    def _load_plugins_from_dir(self, directory: Path):
        """从目录加载插件"""
        for plugin_file in directory.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                self._load_plugin(plugin_file)
            except Exception as e:
                logger.error("插件加载失败", 
                           plugin_file=str(plugin_file), 
                           error=str(e))
    
    def _load_plugin(self, plugin_file: Path):
        """加载单个插件"""
        plugin_name = plugin_file.stem
        
        # 检查是否已加载
        if plugin_name in self.plugins:
            logger.debug("插件已加载，跳过", plugin=plugin_name)
            return
        
        # 动态导入插件
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
        if spec is None:
            raise ImportError(f"无法导入插件: {plugin_name}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[plugin_name] = module
        spec.loader.exec_module(module)
        
        # 查找插件类
        plugin_class = None
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, BasePlugin) and 
                obj != BasePlugin):
                plugin_class = obj
                break
        
        if plugin_class is None:
            raise ValueError(f"插件文件中未找到BasePlugin的子类: {plugin_name}")
        
        # 创建插件实例
        plugin_instance = plugin_class()
        
        # 存储插件
        self.plugins[plugin_name] = plugin_instance
        self.plugin_info[plugin_name] = plugin_instance.get_info()
        
        # 记录文件时间戳
        self._file_timestamps[str(plugin_file)] = plugin_file.stat().st_mtime
        
        # 发布插件加载事件
        event = Event(
            event_type=EventType.PLUGIN_LOADED,
            data={"plugin_name": plugin_name, "plugin_info": self.plugin_info[plugin_name]}
        )
        event_manager.publish(event)
        
        logger.info("插件加载成功", plugin=plugin_name)
    
    def unload_plugin(self, plugin_name: str):
        """卸载插件"""
        with self._lock:
            if plugin_name not in self.plugins:
                logger.warning("插件不存在，无法卸载", plugin=plugin_name)
                return
            
            # 停止插件
            plugin = self.plugins[plugin_name]
            if plugin.status == PluginStatus.RUNNING:
                asyncio.create_task(plugin.stop())
            
            # 移除插件
            del self.plugins[plugin_name]
            del self.plugin_info[plugin_name]
            
            # 发布插件卸载事件
            event = Event(
                event_type=EventType.PLUGIN_UNLOADED,
                data={"plugin_name": plugin_name}
            )
            event_manager.publish(event)
            
            logger.info("插件卸载成功", plugin=plugin_name)
    
    async def start_plugin(self, plugin_name: str):
        """启动插件"""
        with self._lock:
            if plugin_name not in self.plugins:
                logger.error("插件不存在，无法启动", plugin=plugin_name)
                return False
            
            plugin = self.plugins[plugin_name]
            
            if plugin.status == PluginStatus.RUNNING:
                logger.warning("插件已在运行", plugin=plugin_name)
                return True
            
            try:
                await plugin.start()
                plugin.status = PluginStatus.RUNNING
                self.plugin_info[plugin_name] = plugin.get_info()
                
                logger.info("插件启动成功", plugin=plugin_name)
                return True
                
            except Exception as e:
                plugin.status = PluginStatus.ERROR
                logger.error("插件启动失败", plugin=plugin_name, error=str(e))
                return False
    
    async def stop_plugin(self, plugin_name: str):
        """停止插件"""
        with self._lock:
            if plugin_name not in self.plugins:
                logger.error("插件不存在，无法停止", plugin=plugin_name)
                return False
            
            plugin = self.plugins[plugin_name]
            
            if plugin.status != PluginStatus.RUNNING:
                logger.warning("插件未在运行", plugin=plugin_name)
                return True
            
            try:
                await plugin.stop()
                plugin.status = PluginStatus.STOPPED
                self.plugin_info[plugin_name] = plugin.get_info()
                
                logger.info("插件停止成功", plugin=plugin_name)
                return True
                
            except Exception as e:
                plugin.status = PluginStatus.ERROR
                logger.error("插件停止失败", plugin=plugin_name, error=str(e))
                return False
    
    async def start_all_plugins(self):
        """启动所有插件"""
        results = []
        for plugin_name in list(self.plugins.keys()):
            result = await self.start_plugin(plugin_name)
            results.append((plugin_name, result))
        
        success_count = sum(1 for _, result in results if result)
        logger.info("所有插件启动完成", 
                   total=len(results), 
                   success=success_count)
        
        return results
    
    async def stop_all_plugins(self):
        """停止所有插件"""
        results = []
        for plugin_name in list(self.plugins.keys()):
            result = await self.stop_plugin(plugin_name)
            results.append((plugin_name, result))
        
        success_count = sum(1 for _, result in results if result)
        logger.info("所有插件停止完成", 
                   total=len(results), 
                   success=success_count)
        
        return results
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self.plugin_info.get(plugin_name)
    
    def list_plugins(self) -> List[PluginInfo]:
        """列出所有插件信息"""
        return list(self.plugin_info.values())
    
    def _start_hot_reload_monitor(self):
        """启动热加载监控"""
        self._stop_monitor.clear()
        self._monitor_thread = Thread(target=self._hot_reload_monitor, daemon=True)
        self._monitor_thread.start()
        
        logger.info("插件热加载监控已启动")
    
    def _stop_hot_reload_monitor(self):
        """停止热加载监控"""
        if self._monitor_thread:
            self._stop_monitor.set()
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None
        
        logger.info("插件热加载监控已停止")
    
    def _hot_reload_monitor(self):
        """热加载监控循环"""
        while not self._stop_monitor.is_set():
            try:
                self._check_plugin_files()
                time.sleep(5)  # 每5秒检查一次
            except Exception as e:
                logger.error("热加载监控异常", error=str(e))
                time.sleep(10)  # 出错后等待更长时间
    
    def _check_plugin_files(self):
        """检查插件文件变化"""
        plugin_dirs = [self.plugins_dir, self.user_plugins_dir]
        
        for plugin_dir in plugin_dirs:
            for plugin_file in plugin_dir.glob("*.py"):
                if plugin_file.name.startswith("_"):
                    continue
                
                file_path = str(plugin_file)
                current_mtime = plugin_file.stat().st_mtime
                
                # 检查文件是否被修改
                if file_path in self._file_timestamps:
                    if current_mtime > self._file_timestamps[file_path]:
                        logger.info("检测到插件文件修改，重新加载", plugin=plugin_file.stem)
                        self._reload_plugin(plugin_file)
                else:
                    # 新文件，加载插件
                    logger.info("检测到新插件文件，加载", plugin=plugin_file.stem)
                    self._load_plugin(plugin_file)
    
    def _reload_plugin(self, plugin_file: Path):
        """重新加载插件"""
        plugin_name = plugin_file.stem
        
        # 先卸载旧插件
        if plugin_name in self.plugins:
            self.unload_plugin(plugin_name)
        
        # 重新加载插件
        try:
            self._load_plugin(plugin_file)
            
            # 如果插件之前是运行状态，自动启动
            if plugin_name in self.plugins:
                asyncio.create_task(self.start_plugin(plugin_name))
                
        except Exception as e:
            logger.error("插件重新加载失败", plugin=plugin_name, error=str(e))


# 全局插件管理器实例
plugin_manager = EnhancedPluginManager()


# 插件注册装饰器
def register_plugin(config: Dict[str, Any] = None):
    """插件注册装饰器"""
    def decorator(cls):
        # 设置插件配置
        if config:
            cls.default_config = config
        
        # 标记为插件类
        cls.is_plugin = True
        
        return cls
    
    return decorator