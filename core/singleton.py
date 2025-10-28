#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单例模式实现
参照MoviePilot的单例模式设计
"""

import threading
from typing import Any


class Singleton(type):
    """单例元类"""
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class SingletonMeta(type):
    """
    线程安全的单例元类
    """
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


class ThreadSafeSingleton:
    """
    线程安全的单例基类
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance


class LazySingleton:
    """
    懒加载单例模式
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


class ConfigurableSingleton:
    """
    可配置的单例模式
    """
    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        config_key = cls._get_config_key(*args, **kwargs)
        
        if config_key not in cls._instances:
            with cls._lock:
                if config_key not in cls._instances:
                    instance = super().__new__(cls)
                    cls._instances[config_key] = instance
        
        return cls._instances[config_key]

    @classmethod
    def _get_config_key(cls, *args, **kwargs):
        """
        根据参数生成配置键
        子类可以重写此方法来实现不同的配置策略
        """
        return cls.__name__


class SingletonFactory:
    """
    单例工厂类
    """
    _registry = {}
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, class_type, *args, **kwargs):
        """
        获取指定类型的单例实例
        """
        if class_type not in cls._registry:
            with cls._lock:
                if class_type not in cls._registry:
                    cls._registry[class_type] = class_type(*args, **kwargs)
        
        return cls._registry[class_type]

    @classmethod
    def clear_instance(cls, class_type):
        """
        清除指定类型的单例实例
        """
        if class_type in cls._registry:
            with cls._lock:
                if class_type in cls._registry:
                    del cls._registry[class_type]


# 使用示例
class DatabaseConnection(metaclass=Singleton):
    """数据库连接单例"""
    
    def __init__(self, connection_string: str = ""):
        self.connection_string = connection_string
        self._connection = None

    def connect(self):
        """连接数据库"""
        if not self._connection:
            # 模拟数据库连接
            print(f"连接到数据库: {self.connection_string}")
            self._connection = "database_connection"
        return self._connection


class CacheManager(ThreadSafeSingleton):
    """缓存管理器单例"""
    
    def __init__(self):
        self._cache = {}

    def set(self, key: str, value: Any):
        """设置缓存"""
        self._cache[key] = value

    def get(self, key: str) -> Any:
        """获取缓存"""
        return self._cache.get(key)


class ServiceRegistry(LazySingleton):
    """服务注册表单例"""
    
    def __init__(self):
        self._services = {}

    def register(self, name: str, service: Any):
        """注册服务"""
        self._services[name] = service

    def get(self, name: str) -> Any:
        """获取服务"""
        return self._services.get(name)


if __name__ == "__main__":
    # 测试单例模式
    db1 = DatabaseConnection("sqlite:///test.db")
    db2 = DatabaseConnection("mysql://localhost/test")
    
    print(f"db1 is db2: {db1 is db2}")  # 应该输出 True
    print(f"db1.connection_string: {db1.connection_string}")
    print(f"db2.connection_string: {db2.connection_string}")
    
    # 测试线程安全单例
    cache1 = CacheManager()
    cache2 = CacheManager()
    
    print(f"cache1 is cache2: {cache1 is cache2}")  # 应该输出 True
    
    # 测试懒加载单例
    registry1 = ServiceRegistry()
    registry2 = ServiceRegistry()
    
    print(f"registry1 is registry2: {registry1 is registry2}")  # 应该输出 True