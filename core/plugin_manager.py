"""
VabHub 插件管理器

提供插件加载、管理、执行和生命周期管理功能
"""

import asyncio
import importlib
import inspect
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum


class PluginStatus(Enum):
    """插件状态枚举"""
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginInfo:
    """插件信息"""
    id: str
    name: str
    version: str
    description: str
    author: str
    status: PluginStatus
    dependencies: List[str]
    config_schema: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugins_dir: Path = Path("plugins")):
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, PluginInfo] = {}
        self.plugin_instances: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # 确保插件目录存在
        self.plugins_dir.mkdir(exist_ok=True)
    
    async def discover_plugins(self) -> List[PluginInfo]:
        """
        发现可用插件
        
        Returns:
            插件信息列表
        """
        discovered = []
        
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir():
                plugin_info = await self._load_plugin_info(plugin_dir)
                if plugin_info:
                    discovered.append(plugin_info)
        
        return discovered
    
    async def _load_plugin_info(self, plugin_dir: Path) -> Optional[PluginInfo]:
        """
        加载插件信息
        
        Args:
            plugin_dir: 插件目录
            
        Returns:
            插件信息
        """
        try:
            # 读取插件清单
            manifest_path = plugin_dir / "plugin.json"
            if not manifest_path.exists():
                return None
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # 读取配置
            config_path = plugin_dir / "config.json"
            config = {}
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            return PluginInfo(
                id=manifest.get("id", plugin_dir.name),
                name=manifest.get("name", plugin_dir.name),
                version=manifest.get("version", "1.0.0"),
                description=manifest.get("description", ""),
                author=manifest.get("author", "Unknown"),
                status=PluginStatus.INSTALLED,
                dependencies=manifest.get("dependencies", []),
                config_schema=manifest.get("config_schema"),
                config=config
            )
        except Exception as e:
            self.logger.error(f"Failed to load plugin info from {plugin_dir}: {e}")
            return None
    
    async def load_plugin(self, plugin_id: str) -> bool:
        """
        加载插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            是否成功加载
        """
        try:
            # 查找插件目录
            plugin_dir = self.plugins_dir / plugin_id
            if not plugin_dir.exists():
                self.logger.error(f"Plugin directory not found: {plugin_dir}")
                return False
            
            # 加载插件信息
            plugin_info = await self._load_plugin_info(plugin_dir)
            if not plugin_info:
                return False
            
            # 检查依赖
            for dep in plugin_info.dependencies:
                if dep not in self.plugins:
                    self.logger.error(f"Missing dependency: {dep} for plugin {plugin_id}")
                    return False
            
            # 导入插件模块
            try:
                plugin_module = importlib.import_module(f"plugins.{plugin_id}.plugin")
            except ImportError:
                # 尝试直接导入目录
                import sys
                sys.path.insert(0, str(self.plugins_dir))
                try:
                    plugin_module = importlib.import_module(f"{plugin_id}.plugin")
                finally:
                    sys.path.pop(0)
            
            # 查找插件类
            plugin_class = None
            for name, obj in inspect.getmembers(plugin_module):
                if (inspect.isclass(obj) and 
                    hasattr(obj, 'is_plugin') and 
                    getattr(obj, 'is_plugin', False)):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                self.logger.error(f"No plugin class found in {plugin_id}")
                return False
            
            # 实例化插件
            plugin_instance = plugin_class()
            
            # 存储插件信息
            self.plugins[plugin_id] = plugin_info
            self.plugin_instances[plugin_id] = plugin_instance
            
            self.logger.info(f"Plugin loaded: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_id}: {e}")
            return False
    
    async def enable_plugin(self, plugin_id: str) -> bool:
        """
        启用插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            是否成功启用
        """
        if plugin_id not in self.plugin_instances:
            self.logger.error(f"Plugin not loaded: {plugin_id}")
            return False
        
        try:
            plugin_instance = self.plugin_instances[plugin_id]
            
            # 调用插件的启用方法
            if hasattr(plugin_instance, 'on_enable'):
                if asyncio.iscoroutinefunction(plugin_instance.on_enable):
                    await plugin_instance.on_enable()
                else:
                    plugin_instance.on_enable()
            
            # 更新插件状态
            self.plugins[plugin_id].status = PluginStatus.ENABLED
            
            self.logger.info(f"Plugin enabled: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enable plugin {plugin_id}: {e}")
            self.plugins[plugin_id].status = PluginStatus.ERROR
            return False
    
    async def disable_plugin(self, plugin_id: str) -> bool:
        """
        禁用插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            是否成功禁用
        """
        if plugin_id not in self.plugin_instances:
            self.logger.error(f"Plugin not loaded: {plugin_id}")
            return False
        
        try:
            plugin_instance = self.plugin_instances[plugin_id]
            
            # 调用插件的禁用方法
            if hasattr(plugin_instance, 'on_disable'):
                if asyncio.iscoroutinefunction(plugin_instance.on_disable):
                    await plugin_instance.on_disable()
                else:
                    plugin_instance.on_disable()
            
            # 更新插件状态
            self.plugins[plugin_id].status = PluginStatus.DISABLED
            
            self.logger.info(f"Plugin disabled: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disable plugin {plugin_id}: {e}")
            return False
    
    async def unload_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            是否成功卸载
        """
        if plugin_id not in self.plugin_instances:
            self.logger.error(f"Plugin not loaded: {plugin_id}")
            return False
        
        try:
            # 先禁用插件
            if self.plugins[plugin_id].status == PluginStatus.ENABLED:
                await self.disable_plugin(plugin_id)
            
            # 调用插件的卸载方法
            plugin_instance = self.plugin_instances[plugin_id]
            if hasattr(plugin_instance, 'on_unload'):
                if asyncio.iscoroutinefunction(plugin_instance.on_unload):
                    await plugin_instance.on_unload()
                else:
                    plugin_instance.on_unload()
            
            # 移除插件实例
            del self.plugin_instances[plugin_id]
            del self.plugins[plugin_id]
            
            self.logger.info(f"Plugin unloaded: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False
    
    async def execute_plugin_method(self, plugin_id: str, method_name: str, *args, **kwargs) -> Any:
        """
        执行插件方法
        
        Args:
            plugin_id: 插件ID
            method_name: 方法名
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            方法执行结果
        """
        if plugin_id not in self.plugin_instances:
            self.logger.error(f"Plugin not loaded: {plugin_id}")
            return None
        
        if self.plugins[plugin_id].status != PluginStatus.ENABLED:
            self.logger.error(f"Plugin not enabled: {plugin_id}")
            return None
        
        try:
            plugin_instance = self.plugin_instances[plugin_id]
            
            if not hasattr(plugin_instance, method_name):
                self.logger.error(f"Method not found: {method_name} in plugin {plugin_id}")
                return None
            
            method = getattr(plugin_instance, method_name)
            
            if asyncio.iscoroutinefunction(method):
                result = await method(*args, **kwargs)
            else:
                result = method(*args, **kwargs)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute method {method_name} in plugin {plugin_id}: {e}")
            return None
    
    async def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """
        获取插件信息
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            插件信息
        """
        return self.plugins.get(plugin_id)
    
    async def list_plugins(self) -> List[PluginInfo]:
        """
        列出所有插件
        
        Returns:
            插件信息列表
        """
        return list(self.plugins.values())
    
    async def update_plugin_config(self, plugin_id: str, config: Dict[str, Any]) -> bool:
        """
        更新插件配置
        
        Args:
            plugin_id: 插件ID
            config: 新配置
            
        Returns:
            是否成功更新
        """
        if plugin_id not in self.plugins:
            self.logger.error(f"Plugin not found: {plugin_id}")
            return False
        
        try:
            # 更新内存中的配置
            self.plugins[plugin_id].config = config
            
            # 保存到文件
            plugin_dir = self.plugins_dir / plugin_id
            config_path = plugin_dir / "config.json"
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 通知插件配置已更新
            if plugin_id in self.plugin_instances:
                plugin_instance = self.plugin_instances[plugin_id]
                if hasattr(plugin_instance, 'on_config_update'):
                    if asyncio.iscoroutinefunction(plugin_instance.on_config_update):
                        await plugin_instance.on_config_update(config)
                    else:
                        plugin_instance.on_config_update(config)
            
            self.logger.info(f"Plugin config updated: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update plugin config {plugin_id}: {e}")
            return False
    
    async def install_plugin(self, plugin_zip_path: Path) -> bool:
        """
        安装插件
        
        Args:
            plugin_zip_path: 插件ZIP文件路径
            
        Returns:
            是否成功安装
        """
        try:
            import zipfile
            import tempfile
            import shutil
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 解压ZIP文件
                with zipfile.ZipFile(plugin_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # 查找插件目录
                extracted_dir = Path(temp_dir)
                plugin_dirs = [d for d in extracted_dir.iterdir() if d.is_dir()]
                
                if len(plugin_dirs) != 1:
                    self.logger.error("Invalid plugin package structure")
                    return False
                
                plugin_dir = plugin_dirs[0]
                
                # 验证插件结构
                manifest_path = plugin_dir / "plugin.json"
                if not manifest_path.exists():
                    self.logger.error("Plugin manifest not found")
                    return False
                
                # 读取插件信息
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                plugin_id = manifest.get("id", plugin_dir.name)
                
                # 检查是否已存在
                target_dir = self.plugins_dir / plugin_id
                if target_dir.exists():
                    self.logger.error(f"Plugin already exists: {plugin_id}")
                    return False
                
                # 复制插件文件
                shutil.copytree(plugin_dir, target_dir)
                
                self.logger.info(f"Plugin installed: {plugin_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to install plugin: {e}")
            return False
    
    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            是否成功卸载
        """
        try:
            plugin_dir = self.plugins_dir / plugin_id
            
            if not plugin_dir.exists():
                self.logger.error(f"Plugin directory not found: {plugin_dir}")
                return False
            
            # 如果插件已加载，先卸载
            if plugin_id in self.plugin_instances:
                await self.unload_plugin(plugin_id)
            
            # 删除插件目录
            import shutil
            shutil.rmtree(plugin_dir)
            
            self.logger.info(f"Plugin uninstalled: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to uninstall plugin {plugin_id}: {e}")
            return False


# 插件基类
class BasePlugin:
    """插件基类"""
    
    is_plugin = True
    
    def __init__(self):
        self.plugin_info = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def on_enable(self):
        """插件启用时调用"""
        pass
    
    async def on_disable(self):
        """插件禁用时调用"""
        pass
    
    async def on_unload(self):
        """插件卸载时调用"""
        pass
    
    async def on_config_update(self, new_config: Dict[str, Any]):
        """插件配置更新时调用"""
        pass


# 全局插件管理器实例
plugin_manager = PluginManager()