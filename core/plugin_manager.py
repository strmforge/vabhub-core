#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件管理器
支持插件市场的核心功能
"""

import os
import json
import importlib
import inspect
from typing import Dict, List, Any, Optional, Type
from pathlib import Path
from abc import ABC, abstractmethod


class PluginBase(ABC):
    """插件基类"""
    
    def __init__(self):
        self.name = ""
        self.version = "1.0.0"
        self.description = ""
        self.author = ""
        self.enabled = True
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    def execute(self, data: Any) -> Any:
        """执行插件功能"""
        pass
    
    def cleanup(self):
        """清理插件资源"""
        pass


class DataSourcePlugin(PluginBase):
    """数据源插件基类"""
    
    @abstractmethod
    def fetch_metadata(self, query: str) -> Dict[str, Any]:
        """获取元数据"""
        pass
    
    @abstractmethod
    def search_content(self, query: str) -> List[Dict[str, Any]]:
        """搜索内容"""
        pass


class ProcessorPlugin(PluginBase):
    """处理器插件基类"""
    
    @abstractmethod
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """处理文件"""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式"""
        pass


class NotificationPlugin(PluginBase):
    """通知插件基类"""
    
    @abstractmethod
    def send_notification(self, title: str, message: str, data: Dict[str, Any]) -> bool:
        """发送通知"""
        pass
    
    @abstractmethod
    def get_supported_channels(self) -> List[str]:
        """获取支持的渠道"""
        pass


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins_dir = "plugins"
        self.plugins_config = "plugins_config.json"
        self.loaded_plugins: Dict[str, PluginBase] = {}
        self.plugin_categories = {
            "data_source": [],
            "processor": [],
            "notification": [],
            "ui_theme": [],
            "analytics": []
        }
        
        # 创建插件目录
        os.makedirs(self.plugins_dir, exist_ok=True)
        
    def load_all_plugins(self) -> bool:
        """加载所有插件"""
        try:
            # 扫描插件目录
            for plugin_file in Path(self.plugins_dir).glob("*.py"):
                if plugin_file.name.startswith("__"):
                    continue
                    
                plugin_name = plugin_file.stem
                if self.load_plugin(plugin_name):
                    print(f"✅ 插件加载成功: {plugin_name}")
                else:
                    print(f"❌ 插件加载失败: {plugin_name}")
            
            return True
            
        except Exception as e:
            print(f"插件加载失败: {e}")
            return False
    
    def load_plugin(self, plugin_name: str) -> bool:
        """加载单个插件"""
        try:
            # 动态导入插件模块
            spec = importlib.util.spec_from_file_location(
                plugin_name, 
                os.path.join(self.plugins_dir, f"{plugin_name}.py")
            )
            
            if spec is None:
                return False
                
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
            
            if plugin_class is None:
                return False
            
            # 实例化插件
            plugin_instance = plugin_class()
            
            # 初始化插件
            if plugin_instance.initialize():
                self.loaded_plugins[plugin_name] = plugin_instance
                
                # 分类插件
                self._categorize_plugin(plugin_name, plugin_instance)
                
                return True
            
            return False
            
        except Exception as e:
            print(f"加载插件 {plugin_name} 失败: {e}")
            return False
    
    def _categorize_plugin(self, plugin_name: str, plugin_instance: PluginBase):
        """分类插件"""
        if isinstance(plugin_instance, DataSourcePlugin):
            self.plugin_categories["data_source"].append(plugin_name)
        elif isinstance(plugin_instance, ProcessorPlugin):
            self.plugin_categories["processor"].append(plugin_name)
        elif isinstance(plugin_instance, NotificationPlugin):
            self.plugin_categories["notification"].append(plugin_name)
        # 其他分类逻辑...
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """获取插件实例"""
        return self.loaded_plugins.get(plugin_name)
    
    def execute_plugin(self, plugin_name: str, data: Any) -> Any:
        """执行插件"""
        plugin = self.get_plugin(plugin_name)
        if plugin and plugin.enabled:
            return plugin.execute(data)
        return None
    
    def get_available_plugins(self) -> Dict[str, List[str]]:
        """获取可用插件列表"""
        return self.plugin_categories
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.enabled = True
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.enabled = False
            return True
        return False
    
    def install_plugin(self, plugin_url: str) -> bool:
        """安装插件"""
        # 这里可以实现从插件市场下载和安装插件
        # 支持GitHub、GitLab、插件市场等来源
        print(f"安装插件: {plugin_url}")
        return True
    
    def uninstall_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        if plugin_name in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_name]
            plugin.cleanup()
            del self.loaded_plugins[plugin_name]
            
            # 从分类中移除
            for category in self.plugin_categories.values():
                if plugin_name in category:
                    category.remove(plugin_name)
            
            return True
        return False
    
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """获取插件信息"""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "author": plugin.author,
                "enabled": plugin.enabled,
                "category": self._get_plugin_category(plugin_name)
            }
        return {}
    
    def _get_plugin_category(self, plugin_name: str) -> str:
        """获取插件分类"""
        for category, plugins in self.plugin_categories.items():
            if plugin_name in plugins:
                return category
        return "unknown"


# 示例插件实现
class DoubanDataSource(DataSourcePlugin):
    """豆瓣数据源插件"""
    
    def __init__(self):
        super().__init__()
        self.name = "douban_data_source"
        self.description = "豆瓣电影、音乐、图书数据源"
        self.author = "MediaRenamer Team"
    
    def initialize(self) -> bool:
        """初始化插件"""
        print("初始化豆瓣数据源插件")
        return True
    
    def execute(self, data: Any) -> Any:
        """执行插件功能"""
        return self.fetch_metadata(data)
    
    def fetch_metadata(self, query: str) -> Dict[str, Any]:
        """获取豆瓣元数据"""
        # 模拟豆瓣API调用
        return {
            "title": "示例电影",
            "year": 2024,
            "rating": 8.5,
            "genres": ["剧情", "科幻"],
            "directors": ["导演A", "导演B"],
            "actors": ["演员A", "演员B", "演员C"],
            "source": "douban"
        }
    
    def search_content(self, query: str) -> List[Dict[str, Any]]:
        """搜索内容"""
        # 模拟搜索功能
        return [
            {
                "title": f"{query} 搜索结果1",
                "year": 2024,
                "type": "movie"
            },
            {
                "title": f"{query} 搜索结果2", 
                "year": 2023,
                "type": "tv_series"
            }
        ]


class WeChatNotification(NotificationPlugin):
    """微信通知插件"""
    
    def __init__(self):
        super().__init__()
        self.name = "wechat_notification"
        self.description = "微信消息通知"
        self.author = "MediaRenamer Team"
    
    def initialize(self) -> bool:
        """初始化插件"""
        print("初始化微信通知插件")
        return True
    
    def execute(self, data: Any) -> Any:
        """执行插件功能"""
        return self.send_notification(
            data.get("title", ""),
            data.get("message", ""),
            data.get("extra", {})
        )
    
    def send_notification(self, title: str, message: str, data: Dict[str, Any]) -> bool:
        """发送微信通知"""
        print(f"发送微信通知: {title} - {message}")
        return True
    
    def get_supported_channels(self) -> List[str]:
        """获取支持的渠道"""
        return ["wechat_work", "wechat_public"]