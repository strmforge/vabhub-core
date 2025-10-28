#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 插件系统框架
参照MoviePilot的插件系统设计，提供强大的插件化扩展能力
"""

import asyncio
import importlib.util
import inspect
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union, Callable, Tuple

from .config import VabHubConfig
from .event import EventType, Event, event_manager
from .log import logger
from .singleton import Singleton


class PluginBase:
    """
    插件基类（对标MoviePilot的_PluginBase）
    所有插件都应该继承这个基类
    """
    
    # 插件基本信息
    plugin_id: str = ""  # 插件ID，必须唯一
    plugin_name: str = ""  # 插件名称
    plugin_desc: str = ""  # 插件描述
    plugin_icon: str = ""  # 插件图标
    plugin_version: str = "1.0.0"  # 插件版本
    plugin_author: str = ""  # 插件作者
    plugin_url: str = ""  # 插件主页
    
    # 插件配置
    plugin_config: Dict = {}  # 插件配置项
    
    # 插件状态
    _enabled: bool = True  # 插件是否启用
    _loaded: bool = False  # 插件是否已加载
    
    def __init__(self):
        """初始化插件"""
        self.config = VabHubConfig()
        self.event_manager = event_manager
        
    def init_plugin(self, config: Dict = None) -> bool:
        """
        初始化插件
        :param config: 插件配置
        :return: 初始化是否成功
        """
        try:
            if config:
                self.plugin_config.update(config)
            
            # 调用子类的初始化方法
            if hasattr(self, 'init'):
                self.init()
            
            self._loaded = True
            logger.info(f"插件 {self.plugin_name} 初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"插件 {self.plugin_name} 初始化失败: {e}")
            return False
    
    def get_state(self) -> Dict:
        """获取插件状态"""
        return {
            "plugin_id": self.plugin_id,
            "plugin_name": self.plugin_name,
            "plugin_desc": self.plugin_desc,
            "plugin_version": self.plugin_version,
            "plugin_author": self.plugin_author,
            "enabled": self._enabled,
            "loaded": self._loaded
        }
    
    def get_config(self) -> Dict:
        """获取插件配置"""
        return self.plugin_config
    
    def update_config(self, config: Dict) -> bool:
        """更新插件配置"""
        try:
            self.plugin_config.update(config)
            
            # 调用配置更新方法
            if hasattr(self, 'update_config'):
                self.update_config()
            
            return True
        except Exception as e:
            logger.error(f"更新插件配置失败: {e}")
            return False
    
    def enable(self):
        """启用插件"""
        self._enabled = True
        logger.info(f"插件 {self.plugin_name} 已启用")
    
    def disable(self):
        """禁用插件"""
        self._enabled = False
        logger.info(f"插件 {self.plugin_name} 已禁用")
    
    def stop(self):
        """停止插件"""
        self._loaded = False
        if hasattr(self, 'stop'):
            self.stop()
        logger.info(f"插件 {self.plugin_name} 已停止")


class PluginManager(metaclass=Singleton):
    """
    插件管理器（单例模式）
    对标MoviePilot的PluginManager
    """

    def __init__(self):
        # 插件列表
        self._plugins: Dict[str, PluginBase] = {}
        # 运行态插件列表
        self._running_plugins: Dict[str, PluginBase] = {}
        # 插件模块映射
        self._plugin_modules: Dict[str, Dict[str, Callable]] = {}
        # 插件目录
        self._plugin_path: Path = Path("plugins")
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=10)
        
        # 配置
        self.config = VabHubConfig()
        
        # 初始化插件管理器
        self._init_plugin_manager()

    def _init_plugin_manager(self):
        """初始化插件管理器"""
        # 创建插件目录
        self._plugin_path.mkdir(exist_ok=True)
        
        logger.info("插件管理器初始化完成")

    def scan_plugins(self) -> List[Dict]:
        """
        扫描插件目录，发现可用插件
        :return: 插件信息列表
        """
        plugins = []
        
        if not self._plugin_path.exists():
            logger.warning(f"插件目录不存在: {self._plugin_path}")
            return plugins
        
        # 扫描插件目录
        for plugin_dir in self._plugin_path.iterdir():
            if not plugin_dir.is_dir():
                continue
                
            # 检查是否是有效的插件目录
            init_file = plugin_dir / "__init__.py"
            if not init_file.exists():
                continue
            
            # 尝试加载插件信息
            plugin_info = self._load_plugin_info(plugin_dir)
            if plugin_info:
                plugins.append(plugin_info)
        
        logger.info(f"扫描到 {len(plugins)} 个插件")
        return plugins

    def _load_plugin_info(self, plugin_dir: Path) -> Optional[Dict]:
        """
        加载插件信息
        :param plugin_dir: 插件目录
        :return: 插件信息
        """
        try:
            # 动态导入插件模块
            spec = importlib.util.spec_from_file_location(
                plugin_dir.name, 
                plugin_dir / "__init__.py"
            )
            if not spec or not spec.loader:
                return None
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找插件类
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginBase) and 
                    obj != PluginBase):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                return None
            
            # 创建插件实例获取信息
            plugin_instance = plugin_class()
            
            return {
                "plugin_id": plugin_instance.plugin_id,
                "plugin_name": plugin_instance.plugin_name,
                "plugin_desc": plugin_instance.plugin_desc,
                "plugin_version": plugin_instance.plugin_version,
                "plugin_author": plugin_instance.plugin_author,
                "plugin_path": str(plugin_dir),
                "plugin_class": plugin_class
            }
            
        except Exception as e:
            logger.error(f"加载插件信息失败 {plugin_dir}: {e}")
            return None

    def load_plugin(self, plugin_id: str, plugin_config: Dict = None) -> bool:
        """
        加载插件
        :param plugin_id: 插件ID
        :param plugin_config: 插件配置
        :return: 加载是否成功
        """
        try:
            # 检查插件是否已加载
            if plugin_id in self._running_plugins:
                logger.warning(f"插件 {plugin_id} 已加载")
                return True
            
            # 扫描插件目录找到插件
            plugins = self.scan_plugins()
            target_plugin = None
            
            for plugin_info in plugins:
                if plugin_info["plugin_id"] == plugin_id:
                    target_plugin = plugin_info
                    break
            
            if not target_plugin:
                logger.error(f"未找到插件: {plugin_id}")
                return False
            
            # 加载插件
            plugin_class = target_plugin["plugin_class"]
            plugin_instance = plugin_class()
            
            # 初始化插件
            if not plugin_instance.init_plugin(plugin_config):
                return False
            
            # 注册插件
            self._running_plugins[plugin_id] = plugin_instance
            
            # 注册插件模块
            self._register_plugin_modules(plugin_id, plugin_instance)
            
            # 发送插件加载事件
            self.event_manager.send_event(Event(
                EventType.PLUGIN_LOADED,
                {"plugin_id": plugin_id, "plugin_name": plugin_instance.plugin_name}
            ))
            
            logger.info(f"插件 {plugin_id} 加载成功")
            return True
            
        except Exception as e:
            logger.error(f"加载插件失败 {plugin_id}: {e}")
            return False

    def _register_plugin_modules(self, plugin_id: str, plugin_instance: PluginBase):
        """
        注册插件模块
        :param plugin_id: 插件ID
        :param plugin_instance: 插件实例
        """
        # 获取插件类的所有方法
        methods = [method for method in dir(plugin_instance) 
                  if not method.startswith('_') and callable(getattr(plugin_instance, method))]
        
        # 注册模块方法
        for method in methods:
            module_key = f"{plugin_id}.{method}"
            self._plugin_modules[module_key] = getattr(plugin_instance, method)

    def unload_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件
        :param plugin_id: 插件ID
        :return: 卸载是否成功
        """
        try:
            if plugin_id not in self._running_plugins:
                logger.warning(f"插件 {plugin_id} 未加载")
                return True
            
            # 停止插件
            plugin_instance = self._running_plugins[plugin_id]
            plugin_instance.stop()
            
            # 移除插件模块
            self._unregister_plugin_modules(plugin_id)
            
            # 移除插件
            del self._running_plugins[plugin_id]
            
            # 发送插件卸载事件
            self.event_manager.send_event(Event(
                EventType.PLUGIN_UNLOADED,
                {"plugin_id": plugin_id, "plugin_name": plugin_instance.plugin_name}
            ))
            
            logger.info(f"插件 {plugin_id} 卸载成功")
            return True
            
        except Exception as e:
            logger.error(f"卸载插件失败 {plugin_id}: {e}")
            return False

    def _unregister_plugin_modules(self, plugin_id: str):
        """
        注销插件模块
        :param plugin_id: 插件ID
        """
        # 移除所有相关的模块
        modules_to_remove = [key for key in self._plugin_modules.keys() 
                            if key.startswith(f"{plugin_id}.")]
        
        for module_key in modules_to_remove:
            del self._plugin_modules[module_key]

    def get_plugin_modules(self) -> Dict[str, Dict[str, Callable]]:
        """
        获取插件模块
        :return: 插件模块字典
        """
        # 按插件ID分组
        result = {}
        
        for module_key, module_func in self._plugin_modules.items():
            plugin_id, method_name = module_key.split(".", 1)
            
            if plugin_id not in result:
                result[plugin_id] = {}
            
            result[plugin_id][method_name] = module_func
        
        return result

    def get_running_plugins(self) -> List[Dict]:
        """
        获取运行中的插件列表
        :return: 插件状态列表
        """
        plugins = []
        
        for plugin_id, plugin_instance in self._running_plugins.items():
            plugins.append(plugin_instance.get_state())
        
        return plugins

    def execute_plugin_method(self, plugin_id: str, method_name: str, 
                            *args, **kwargs) -> Any:
        """
        执行插件方法
        :param plugin_id: 插件ID
        :param method_name: 方法名
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 执行结果
        """
        try:
            if plugin_id not in self._running_plugins:
                raise ValueError(f"插件 {plugin_id} 未加载")
            
            plugin_instance = self._running_plugins[plugin_id]
            
            if not hasattr(plugin_instance, method_name):
                raise ValueError(f"插件 {plugin_id} 没有方法 {method_name}")
            
            method = getattr(plugin_instance, method_name)
            
            # 执行方法
            return method(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"执行插件方法失败 {plugin_id}.{method_name}: {e}")
            raise

    async def async_execute_plugin_method(self, plugin_id: str, method_name: str,
                                        *args, **kwargs) -> Any:
        """
        异步执行插件方法
        :param plugin_id: 插件ID
        :param method_name: 方法名
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 执行结果
        """
        # 在线程池中执行同步方法
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, 
            self.execute_plugin_method, 
            plugin_id, method_name, *args, **kwargs
        )

    def reload_plugin(self, plugin_id: str) -> bool:
        """
        重新加载插件
        :param plugin_id: 插件ID
        :return: 重载是否成功
        """
        try:
            # 保存当前配置
            if plugin_id in self._running_plugins:
                plugin_instance = self._running_plugins[plugin_id]
                current_config = plugin_instance.get_config()
                
                # 卸载插件
                self.unload_plugin(plugin_id)
                
                # 重新加载插件
                return self.load_plugin(plugin_id, current_config)
            
            return False
            
        except Exception as e:
            logger.error(f"重载插件失败 {plugin_id}: {e}")
            return False

    def stop_all_plugins(self):
        """停止所有插件"""
        for plugin_id in list(self._running_plugins.keys()):
            self.unload_plugin(plugin_id)


# 全局插件管理器实例
plugin_manager = PluginManager()


def get_plugin_manager() -> PluginManager:
    """获取插件管理器实例"""
    return plugin_manager


# 示例插件实现
class ExamplePlugin(PluginBase):
    """示例插件"""
    
    plugin_id = "example_plugin"
    plugin_name = "示例插件"
    plugin_desc = "这是一个示例插件"
    plugin_version = "1.0.0"
    plugin_author = "VabHub Team"
    
    def init(self):
        """初始化插件"""
        logger.info("示例插件初始化完成")
    
    def process_media(self, media_info: Dict) -> Dict:
        """处理媒体信息"""
        logger.info(f"处理媒体信息: {media_info}")
        return {"status": "processed", "media": media_info}
    
    async def async_process_media(self, media_info: Dict) -> Dict:
        """异步处理媒体信息"""
        # 模拟异步处理
        await asyncio.sleep(0.1)
        return self.process_media(media_info)


if __name__ == "__main__":
    # 测试插件系统
    manager = PluginManager()
    
    # 扫描插件
    plugins = manager.scan_plugins()
    print(f"扫描到的插件: {plugins}")
    
    # 加载示例插件
    if manager.load_plugin("example_plugin"):
        print("示例插件加载成功")
        
        # 执行插件方法
        result = manager.execute_plugin_method("example_plugin", "process_media", {"title": "Test"})
        print(f"插件执行结果: {result}")
        
        # 获取运行中的插件
        running_plugins = manager.get_running_plugins()
        print(f"运行中的插件: {running_plugins}")
        
        # 卸载插件
        manager.unload_plugin("example_plugin")
        print("示例插件已卸载")
    else:
        print("示例插件加载失败")