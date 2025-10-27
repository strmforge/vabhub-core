#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热加载插件管理器
支持动态插件加载、卸载和热更新
"""

import os
import json
import importlib
import inspect
import threading
import time
import asyncio
from typing import Dict, List, Any, Optional, Type, Callable
from pathlib import Path
import logging
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core.plugin_base import Plugin, PluginManager, get_plugin_manager

logger = logging.getLogger(__name__)


class PluginFileEventHandler(FileSystemEventHandler):
    """插件文件事件处理器"""
    
    def __init__(self, plugin_manager, plugins_dir: str):
        self.plugin_manager = plugin_manager
        self.plugins_dir = plugins_dir
        self.last_modified = {}
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not file_path.endswith('.py'):
            return
        
        # 检查文件是否在插件目录中
        if not file_path.startswith(self.plugins_dir):
            return
        
        # 防止重复触发
        current_time = time.time()
        last_time = self.last_modified.get(file_path, 0)
        
        if current_time - last_time < 2:  # 2秒防抖
            return
        
        self.last_modified[file_path] = current_time
        
        # 异步处理文件修改
        asyncio.create_task(self.handle_plugin_change(file_path))
    
    async def handle_plugin_change(self, file_path: str):
        """处理插件文件变化"""
        try:
            logger.info(f"检测到插件文件变化: {file_path}")
            
            # 获取插件名称
            plugin_name = Path(file_path).stem
            
            # 检查文件是否被删除
            if not os.path.exists(file_path):
                await self.plugin_manager.unload_plugin(plugin_name)
                return
            
            # 重新加载插件
            await self.plugin_manager.reload_plugin(plugin_name)
            
        except Exception as e:
            logger.error(f"处理插件文件变化失败: {e}")


class HotPluginManager(PluginManager):
    """热加载插件管理器"""
    
    def __init__(self):
        super().__init__()
        
        # 热加载相关属性
        self.plugins_dir = "plugins"
        self.watchdog_enabled = True
        self.observer = None
        self.file_watcher = None
        
        # 插件状态跟踪
        self.plugin_states: Dict[str, Dict[str, Any]] = {}
        self.plugin_dependencies: Dict[str, List[str]] = {}
        
        # 线程安全
        self.lock = threading.RLock()
        
        # 插件配置
        self.plugin_configs = self._load_plugin_configs()
    
    def _load_plugin_configs(self) -> Dict[str, Any]:
        """加载插件配置"""
        config_file = "plugin_configs.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载插件配置失败: {e}")
        return {}
    
    def _save_plugin_configs(self):
        """保存插件配置"""
        try:
            with open("plugin_configs.json", 'w', encoding='utf-8') as f:
                json.dump(self.plugin_configs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存插件配置失败: {e}")
    
    def start_watching(self):
        """开始监控插件目录"""
        if not self.watchdog_enabled:
            return
        
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir, exist_ok=True)
        
        self.file_watcher = PluginFileEventHandler(self, self.plugins_dir)
        self.observer = Observer()
        self.observer.schedule(
            self.file_watcher, 
            self.plugins_dir, 
            recursive=True
        )
        self.observer.start()
        
        logger.info(f"开始监控插件目录: {self.plugins_dir}")
    
    def stop_watching(self):
        """停止监控插件目录"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("停止监控插件目录")
    
    async def load_plugin(self, plugin_file: str) -> bool:
        """加载单个插件"""
        with self.lock:
            try:
                plugin_name = Path(plugin_file).stem
                
                # 检查插件是否已加载
                if self._is_plugin_loaded(plugin_name):
                    logger.info(f"插件 {plugin_name} 已加载，跳过")
                    return True
                
                # 加载插件模块
                plugin_module = self._import_plugin_module(plugin_file)
                if not plugin_module:
                    return False
                
                # 查找插件类
                plugin_class = self._find_plugin_class(plugin_module)
                if not plugin_class:
                    logger.error(f"在 {plugin_file} 中未找到插件类")
                    return False
                
                # 获取插件配置
                plugin_config = self.plugin_configs.get(plugin_name, {})
                
                # 创建插件实例
                plugin_instance = plugin_class(plugin_config)
                
                # 初始化插件
                if not await self._initialize_plugin(plugin_instance):
                    logger.error(f"插件 {plugin_name} 初始化失败")
                    return False
                
                # 注册插件
                if self.register_plugin(plugin_instance):
                    # 更新插件状态
                    self.plugin_states[plugin_name] = {
                        'file_path': plugin_file,
                        'loaded_at': time.time(),
                        'status': 'loaded',
                        'version': plugin_instance.version,
                        'enabled': plugin_instance.enabled
                    }
                    
                    logger.info(f"插件 {plugin_name} 加载成功")
                    return True
                else:
                    logger.error(f"插件 {plugin_name} 注册失败")
                    return False
                
            except Exception as e:
                logger.error(f"加载插件 {plugin_file} 失败: {e}")
                return False
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        with self.lock:
            try:
                # 查找插件
                plugin = None
                plugin_type = None
                
                for p_type, plugins in self.plugins.items():
                    if plugin_name in plugins:
                        plugin = plugins[plugin_name]
                        plugin_type = p_type
                        break
                
                if not plugin:
                    logger.warning(f"插件 {plugin_name} 未找到")
                    return False
                
                # 清理插件资源
                if hasattr(plugin, 'cleanup'):
                    plugin.cleanup()
                
                # 从插件管理器中移除
                if plugin_type and plugin_name in self.plugins[plugin_type]:
                    del self.plugins[plugin_type][plugin_name]
                
                # 从已加载插件列表中移除
                self.loaded_plugins = [p for p in self.loaded_plugins 
                                      if p.name != plugin_name]
                
                # 更新插件状态
                if plugin_name in self.plugin_states:
                    self.plugin_states[plugin_name]['status'] = 'unloaded'
                    self.plugin_states[plugin_name]['unloaded_at'] = time.time()
                
                logger.info(f"插件 {plugin_name} 卸载成功")
                return True
                
            except Exception as e:
                logger.error(f"卸载插件 {plugin_name} 失败: {e}")
                return False
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        with self.lock:
            try:
                # 获取插件文件路径
                plugin_state = self.plugin_states.get(plugin_name)
                if not plugin_state:
                    logger.error(f"插件 {plugin_name} 状态信息不存在")
                    return False
                
                plugin_file = plugin_state['file_path']
                
                # 先卸载插件
                await self.unload_plugin(plugin_name)
                
                # 等待一小段时间确保文件写入完成
                await asyncio.sleep(0.5)
                
                # 重新加载插件
                success = await self.load_plugin(plugin_file)
                
                if success:
                    logger.info(f"插件 {plugin_name} 重新加载成功")
                    # 触发插件重新加载事件
                    await self._notify_plugin_reloaded(plugin_name)
                else:
                    logger.error(f"插件 {plugin_name} 重新加载失败")
                
                return success
                
            except Exception as e:
                logger.error(f"重新加载插件 {plugin_name} 失败: {e}")
                return False
    
    async def load_plugins_from_directory(self, directory: str = None) -> None:
        """从目录加载所有插件"""
        if directory:
            self.plugins_dir = directory
        
        if not os.path.exists(self.plugins_dir):
            logger.warning(f"插件目录不存在: {self.plugins_dir}")
            return
        
        # 加载所有插件文件
        plugin_files = []
        for py_file in Path(self.plugins_dir).glob("*.py"):
            if py_file.name.startswith("_") or py_file.name == "base.py":
                continue
            plugin_files.append(str(py_file))
        
        # 并行加载插件
        tasks = [self.load_plugin(plugin_file) for plugin_file in plugin_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计加载结果
        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful
        
        logger.info(f"插件加载完成: 成功 {successful} 个, 失败 {failed} 个")
    
    def _import_plugin_module(self, plugin_file: str):
        """导入插件模块"""
        try:
            plugin_name = Path(plugin_file).stem
            
            # 计算文件哈希，用于检测文件变化
            file_hash = self._calculate_file_hash(plugin_file)
            
            # 如果模块已导入，先移除
            if plugin_name in sys.modules:
                del sys.modules[plugin_name]
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 保存文件哈希
                self.plugin_states[plugin_name] = {
                    'file_hash': file_hash,
                    'file_path': plugin_file
                }
                
                return module
            
            return None
            
        except Exception as e:
            logger.error(f"导入插件模块失败 {plugin_file}: {e}")
            return None
    
    def _find_plugin_class(self, module) -> Optional[Type[Plugin]]:
        """查找插件类"""
        try:
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, Plugin) and 
                    obj != Plugin and
                    hasattr(obj, 'name')):
                    return obj
            return None
        except Exception as e:
            logger.error(f"查找插件类失败: {e}")
            return None
    
    async def _initialize_plugin(self, plugin_instance: Plugin) -> bool:
        """初始化插件"""
        try:
            # 检查插件是否启用
            if not plugin_instance.enabled:
                logger.info(f"插件 {plugin_instance.name} 被禁用，跳过初始化")
                return False
            
            # 执行初始化
            if hasattr(plugin_instance, 'initialize'):
                # 支持异步初始化
                if inspect.iscoroutinefunction(plugin_instance.initialize):
                    result = await plugin_instance.initialize()
                else:
                    result = plugin_instance.initialize()
                
                return bool(result)
            else:
                # 没有initialize方法，默认成功
                return True
                
        except Exception as e:
            logger.error(f"插件 {plugin_instance.name} 初始化失败: {e}")
            return False
    
    def _is_plugin_loaded(self, plugin_name: str) -> bool:
        """检查插件是否已加载"""
        for plugin in self.loaded_plugins:
            if plugin.name == plugin_name:
                return True
        return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    async def _notify_plugin_reloaded(self, plugin_name: str):
        """通知插件重新加载事件"""
        # 这里可以添加事件通知机制
        # 例如：通知其他插件或系统组件
        pass
    
    def get_plugin_status(self, plugin_name: str) -> Dict[str, Any]:
        """获取插件状态"""
        return self.plugin_states.get(plugin_name, {})
    
    def get_all_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件状态"""
        return self.plugin_states.copy()
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        try:
            plugin = self.get_plugin_by_name(plugin_name)
            if plugin:
                plugin.enabled = True
                
                # 更新配置
                if plugin_name not in self.plugin_configs:
                    self.plugin_configs[plugin_name] = {}
                self.plugin_configs[plugin_name]['enabled'] = True
                self._save_plugin_configs()
                
                # 更新状态
                if plugin_name in self.plugin_states:
                    self.plugin_states[plugin_name]['enabled'] = True
                
                logger.info(f"插件 {plugin_name} 已启用")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"启用插件 {plugin_name} 失败: {e}")
            return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        try:
            plugin = self.get_plugin_by_name(plugin_name)
            if plugin:
                plugin.enabled = False
                
                # 更新配置
                if plugin_name not in self.plugin_configs:
                    self.plugin_configs[plugin_name] = {}
                self.plugin_configs[plugin_name]['enabled'] = False
                self._save_plugin_configs()
                
                # 更新状态
                if plugin_name in self.plugin_states:
                    self.plugin_states[plugin_name]['enabled'] = False
                
                logger.info(f"插件 {plugin_name} 已禁用")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"禁用插件 {plugin_name} 失败: {e}")
            return False
    
    def get_plugin_by_name(self, plugin_name: str) -> Optional[Plugin]:
        """根据名称获取插件"""
        for plugin in self.loaded_plugins:
            if plugin.name == plugin_name:
                return plugin
        return None
    
    async def shutdown(self):
        """关闭插件管理器"""
        # 停止文件监控
        self.stop_watching()
        
        # 清理所有插件
        for plugin in self.loaded_plugins:
            try:
                if hasattr(plugin, 'cleanup'):
                    plugin.cleanup()
            except Exception as e:
                logger.error(f"清理插件 {plugin.name} 失败: {e}")
        
        # 清空插件列表
        self.loaded_plugins.clear()
        self.plugins = {
            'cloud': {},
            'downloader': {},
            'metadata': {},
            'music_metadata': {},
            'notifier': {}
        }
        
        logger.info("插件管理器已关闭")


# 全局热加载插件管理器实例
_hot_plugin_manager: Optional[HotPluginManager] = None


def get_hot_plugin_manager() -> HotPluginManager:
    """获取全局热加载插件管理器"""
    global _hot_plugin_manager
    if _hot_plugin_manager is None:
        _hot_plugin_manager = HotPluginManager()
    return _hot_plugin_manager


async def initialize_hot_plugin_manager(plugins_dir: str = "plugins") -> HotPluginManager:
    """初始化热加载插件管理器"""
    manager = get_hot_plugin_manager()
    
    # 设置插件目录
    manager.plugins_dir = plugins_dir
    
    # 加载插件
    await manager.load_plugins_from_directory(plugins_dir)
    
    # 开始监控
    manager.start_watching()
    
    return manager


# 兼容性函数
def get_plugin_manager() -> PluginManager:
    """获取插件管理器（兼容性函数）"""
    return get_hot_plugin_manager()


# 测试代码
if __name__ == "__main__":
    import asyncio
    
    async def test_hot_plugin_manager():
        """测试热加载插件管理器"""
        
        # 初始化插件管理器
        manager = await initialize_hot_plugin_manager()
        
        # 打印插件状态
        print("插件状态:")
        for plugin_name, status in manager.get_all_plugin_status().items():
            print(f"  {plugin_name}: {status}")
        
        # 等待一段时间观察热加载
        print("\n等待文件变化... (Ctrl+C 退出)")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        
        # 关闭插件管理器
        await manager.shutdown()
    
    # 运行测试
    asyncio.run(test_hot_plugin_manager())