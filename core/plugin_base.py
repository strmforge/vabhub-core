#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件基础架构
参考StrataMedia的插件设计模式
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from pathlib import Path
import importlib
import inspect


class Plugin(ABC):
    """插件基类"""
    
    name: str = ""
    version: str = "1.0.0"
    enabled: bool = True
    priority: int = 100
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化插件"""
        pass
    
    def cleanup(self) -> None:
        """清理插件资源"""
        pass


class CloudSource(Plugin):
    """云存储源插件"""
    
    def walk(self, base_path: str) -> List[str]:
        """遍历云存储目录"""
        raise NotImplementedError
    
    def download(self, remote_path: str, local_path: str) -> bool:
        """下载文件"""
        raise NotImplementedError
    
    def upload(self, local_path: str, remote_path: str) -> bool:
        """上传文件"""
        raise NotImplementedError


class Downloader(Plugin):
    """下载器插件"""
    
    def add_torrent(self, torrent_or_magnet: str, category: Optional[str] = None) -> Any:
        """添加种子"""
        raise NotImplementedError
    
    def get_download_status(self, torrent_id: str) -> Dict[str, Any]:
        """获取下载状态"""
        raise NotImplementedError


class MetadataProvider(Plugin):
    """元数据提供者插件"""
    
    def fetch_video(self, title: str, year: Optional[int] = None) -> Dict[str, Any]:
        """获取视频元数据"""
        raise NotImplementedError


class MusicMetadataProvider(Plugin):
    """音乐元数据提供者插件"""
    
    def search_track(self, artist: str, title: str, album: Optional[str] = None) -> Dict[str, Any]:
        """搜索音乐轨道"""
        raise NotImplementedError
    
    def get_audio_fingerprint(self, file_path: str) -> Optional[str]:
        """获取音频指纹"""
        raise NotImplementedError


class LibraryNotifier(Plugin):
    """媒体库通知插件"""
    
    def notify(self, path: str, library: str) -> bool:
        """通知媒体库刷新"""
        raise NotImplementedError


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, Dict[str, Plugin]] = {
            'cloud': {},
            'downloader': {},
            'metadata': {},
            'music_metadata': {},
            'notifier': {}
        }
        self.loaded_plugins: List[Plugin] = []
    
    def register_plugin(self, plugin: Plugin) -> bool:
        """注册插件"""
        if not plugin.enabled:
            return False
        
        plugin_type = self._get_plugin_type(plugin)
        if plugin_type:
            self.plugins[plugin_type][plugin.name] = plugin
            self.loaded_plugins.append(plugin)
            return True
        return False
    
    def _get_plugin_type(self, plugin: Plugin) -> Optional[str]:
        """获取插件类型"""
        if isinstance(plugin, CloudSource):
            return 'cloud'
        elif isinstance(plugin, Downloader):
            return 'downloader'
        elif isinstance(plugin, MetadataProvider):
            return 'metadata'
        elif isinstance(plugin, MusicMetadataProvider):
            return 'music_metadata'
        elif isinstance(plugin, LibraryNotifier):
            return 'notifier'
        return None
    
    def load_plugins_from_directory(self, directory: str) -> None:
        """从目录加载插件"""
        plugins_dir = Path(directory)
        if not plugins_dir.exists():
            return
        
        for py_file in plugins_dir.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name == "base.py":
                continue
            
            try:
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # 查找插件类
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, Plugin) and 
                            obj != Plugin):
                            plugin_instance = obj()
                            if plugin_instance.initialize():
                                self.register_plugin(plugin_instance)
                                print(f"加载插件: {plugin_instance.name}")
            
            except Exception as e:
                print(f"加载插件 {py_file} 失败: {e}")
    
    def get_plugin(self, plugin_type: str, name: str) -> Optional[Plugin]:
        """获取指定插件"""
        return self.plugins.get(plugin_type, {}).get(name)
    
    def get_plugins_by_type(self, plugin_type: str) -> List[Plugin]:
        """获取指定类型的插件"""
        return list(self.plugins.get(plugin_type, {}).values())
    
    def shutdown(self) -> None:
        """关闭所有插件"""
        for plugin in self.loaded_plugins:
            try:
                plugin.cleanup()
            except Exception as e:
                print(f"清理插件 {plugin.name} 失败: {e}")


# 全局插件管理器实例
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def register_plugin(plugin: Plugin) -> bool:
    """注册插件（装饰器方式）"""
    return get_plugin_manager().register_plugin(plugin)