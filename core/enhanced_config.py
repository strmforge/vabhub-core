#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强配置系统
整合云原生配置管理和动态配置更新功能
"""

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog
import yaml
from app.utils.commons import SingletonMeta

from .enhanced_event import EventType, Event, event_manager

logger = structlog.get_logger()


class ConfigSource(Enum):
    """配置源枚举"""
    FILE = "file"
    ENVIRONMENT = "environment"
    DATABASE = "database"
    CONSUL = "consul"
    ETCD = "etcd"


class ConfigFormat(Enum):
    """配置格式枚举"""
    JSON = "json"
    YAML = "yaml"
    INI = "ini"
    ENV = "env"


@dataclass
class ConfigItem:
    """配置项"""
    key: str
    value: Any
    source: ConfigSource
    format: ConfigFormat
    last_updated: datetime
    description: Optional[str] = None
    version: int = 1
    encrypted: bool = False


@dataclass
class ConfigChange:
    """配置变更"""
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    source: str
    user: Optional[str] = None


class ConfigProvider(ABC):
    """配置提供器基类"""
    
    @abstractmethod
    async def get_config(self, key: str) -> Optional[ConfigItem]:
        """获取配置"""
        pass
    
    @abstractmethod
    async def set_config(self, key: str, value: Any) -> bool:
        """设置配置"""
        pass
    
    @abstractmethod
    async def watch_config(self, key: str, callback) -> bool:
        """监听配置变更"""
        pass


class ConfigValidator(ABC):
    """配置验证器基类"""
    
    @abstractmethod
    def validate(self, key: str, value: Any) -> bool:
        """验证配置"""
        pass
    
    @abstractmethod
    def get_schema(self, key: str) -> Dict[str, Any]:
        """获取配置模式"""
        pass


class EnhancedConfigManager(metaclass=SingletonMeta):
    """增强配置管理器 - 整合云原生配置管理"""
    
    def __init__(self):
        # 配置存储
        self.configs: Dict[str, ConfigItem] = {}
        self.config_providers: Dict[ConfigSource, ConfigProvider] = {}
        
        # 配置验证器
        self.validators: Dict[str, ConfigValidator] = {}
        
        # 配置变更历史
        self.change_history: List[ConfigChange] = []
        
        # 监听器
        self.listeners: Dict[str, List] = {}
        
        # 默认配置源
        self.default_source = ConfigSource.FILE
        
        # 注册内置提供器和验证器
        self._register_builtin_providers()
        self._register_builtin_validators()
        
        # 加载默认配置
        self._load_default_configs()
    
    def _register_builtin_providers(self):
        """注册内置提供器"""
        self.register_provider(ConfigSource.FILE, FileConfigProvider())
        self.register_provider(ConfigSource.ENVIRONMENT, EnvironmentConfigProvider())
    
    def _register_builtin_validators(self):
        """注册内置验证器"""
        self.register_validator("string", StringValidator())
        self.register_validator("number", NumberValidator())
        self.register_validator("boolean", BooleanValidator())
        self.register_validator("array", ArrayValidator())
        self.register_validator("object", ObjectValidator())
    
    def _load_default_configs(self):
        """加载默认配置"""
        # 系统默认配置
        default_configs = {
            "app.name": "MediaRenamer",
            "app.version": "2.0.0",
            "app.debug": False,
            "app.log_level": "INFO",
            
            "database.host": "localhost",
            "database.port": 5432,
            "database.name": "media_renamer",
            "database.user": "postgres",
            "database.password": "",
            
            "redis.host": "localhost",
            "redis.port": 6379,
            "redis.db": 0,
            
            "web.host": "0.0.0.0",
            "web.port": 8000,
            "web.debug": False,
            
            "pt.max_concurrent_downloads": 5,
            "pt.download_path": "/downloads",
            "pt.auto_cleanup": True,
            
            "ai.recognition_enabled": True,
            "ai.search_enabled": True,
            "ai.recommendation_enabled": False,
            
            "workflow.auto_start": True,
            "workflow.max_parallel": 3,
            
            "plugin.auto_load": True,
            "plugin.hot_reload": False,
            
            "security.encryption_enabled": False,
            "security.api_key_required": False
        }
        
        for key, value in default_configs.items():
            config_item = ConfigItem(
                key=key,
                value=value,
                source=ConfigSource.FILE,
                format=ConfigFormat.JSON,
                last_updated=datetime.now()
            )
            self.configs[key] = config_item
    
    def register_provider(self, source: ConfigSource, provider: ConfigProvider):
        """注册配置提供器"""
        self.config_providers[source] = provider
        logger.info("配置提供器已注册", source=source.value)
    
    def register_validator(self, validator_type: str, validator: ConfigValidator):
        """注册配置验证器"""
        self.validators[validator_type] = validator
        logger.info("配置验证器已注册", validator_type=validator_type)
    
    async def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        # 首先检查内存中的配置
        if key in self.configs:
            return self.configs[key].value
        
        # 尝试从各个配置源获取
        for source, provider in self.config_providers.items():
            try:
                config_item = await provider.get_config(key)
                if config_item:
                    # 缓存配置
                    self.configs[key] = config_item
                    return config_item.value
            except Exception as e:
                logger.warning("配置获取失败", source=source.value, key=key, error=str(e))
        
        # 返回默认值
        return default
    
    async def set(self, key: str, value: Any, source: ConfigSource = None) -> bool:
        """设置配置值"""
        source = source or self.default_source
        
        if source not in self.config_providers:
            logger.error("不支持的配置源", source=source.value)
            return False
        
        # 验证配置值
        if not await self._validate_config(key, value):
            logger.error("配置验证失败", key=key)
            return False
        
        provider = self.config_providers[source]
        
        try:
            # 记录变更历史
            old_value = None
            if key in self.configs:
                old_value = self.configs[key].value
            
            # 设置配置
            success = await provider.set_config(key, value)
            
            if success:
                # 更新内存中的配置
                config_item = ConfigItem(
                    key=key,
                    value=value,
                    source=source,
                    format=ConfigFormat.JSON,
                    last_updated=datetime.now()
                )
                self.configs[key] = config_item
                
                # 记录变更
                change = ConfigChange(
                    key=key,
                    old_value=old_value,
                    new_value=value,
                    timestamp=datetime.now(),
                    source=source.value
                )
                self.change_history.append(change)
                
                # 通知监听器
                await self._notify_listeners(key, old_value, value)
                
                # 发布配置变更事件
                event = Event(
                    event_type=EventType.CONFIG_CHANGED,
                    data={
                        "key": key,
                        "old_value": old_value,
                        "new_value": value,
                        "source": source.value
                    }
                )
                event_manager.publish(event)
                
                logger.info("配置已更新", key=key, source=source.value)
            
            return success
            
        except Exception as e:
            logger.error("配置设置失败", key=key, source=source.value, error=str(e))
            return False
    
    async def watch(self, key: str, callback) -> bool:
        """监听配置变更"""
        if key not in self.listeners:
            self.listeners[key] = []
        
        self.listeners[key].append(callback)
        
        # 注册到配置提供器
        for source, provider in self.config_providers.items():
            try:
                await provider.watch_config(key, lambda k, v: self._on_config_change(k, v, source))
            except Exception as e:
                logger.warning("配置监听注册失败", source=source.value, key=key, error=str(e))
        
        logger.info("配置监听已注册", key=key)
        return True
    
    async def _on_config_change(self, key: str, value: Any, source: ConfigSource):
        """配置变更回调"""
        # 更新内存中的配置
        old_value = None
        if key in self.configs:
            old_value = self.configs[key].value
        
        config_item = ConfigItem(
            key=key,
            value=value,
            source=source,
            format=ConfigFormat.JSON,
            last_updated=datetime.now()
        )
        self.configs[key] = config_item
        
        # 记录变更
        change = ConfigChange(
            key=key,
            old_value=old_value,
            new_value=value,
            timestamp=datetime.now(),
            source=source.value
        )
        self.change_history.append(change)
        
        # 通知监听器
        await self._notify_listeners(key, old_value, value)
    
    async def _notify_listeners(self, key: str, old_value: Any, new_value: Any):
        """通知监听器"""
        if key in self.listeners:
            for callback in self.listeners[key]:
                try:
                    await callback(key, old_value, new_value)
                except Exception as e:
                    logger.error("配置监听器通知失败", key=key, error=str(e))
    
    async def _validate_config(self, key: str, value: Any) -> bool:
        """验证配置"""
        # 根据key推断验证器类型
        validator_type = self._infer_validator_type(key)
        
        if validator_type in self.validators:
            validator = self.validators[validator_type]
            return validator.validate(key, value)
        
        # 如果没有特定的验证器，使用通用验证
        return self._generic_validate(key, value)
    
    def _infer_validator_type(self, key: str) -> str:
        """推断验证器类型"""
        # 简单的类型推断逻辑
        if key.endswith('.port') or key.endswith('.max_parallel') or key.endswith('.max_concurrent'):
            return "number"
        elif key.endswith('.enabled') or key.endswith('.debug') or key.endswith('.required'):
            return "boolean"
        elif key.endswith('.hosts') or key.endswith('.plugins') or key.endswith('.extensions'):
            return "array"
        elif '.' in key and not key.endswith('.password') and not key.endswith('.key'):
            return "object"
        else:
            return "string"
    
    def _generic_validate(self, key: str, value: Any) -> bool:
        """通用验证"""
        # 基本类型检查
        if key.endswith('.port'):
            return isinstance(value, int) and 0 < value < 65536
        elif key.endswith('.password') or key.endswith('.key'):
            return isinstance(value, str)
        elif key.endswith('.enabled') or key.endswith('.debug'):
            return isinstance(value, bool)
        
        return True
    
    def get_change_history(self, key: str = None, limit: int = 100) -> List[ConfigChange]:
        """获取变更历史"""
        history = self.change_history[-limit:]
        
        if key:
            history = [change for change in history if change.key == key]
        
        return history
    
    def export_config(self, format: ConfigFormat = ConfigFormat.JSON) -> str:
        """导出配置"""
        config_dict = {}
        for key, item in self.configs.items():
            config_dict[key] = item.value
        
        if format == ConfigFormat.JSON:
            return json.dumps(config_dict, indent=2, ensure_ascii=False)
        elif format == ConfigFormat.YAML:
            return yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
        else:
            return str(config_dict)


# 内置配置提供器实现
class FileConfigProvider(ConfigProvider):
    """文件配置提供器"""
    
    async def get_config(self, key: str) -> Optional[ConfigItem]:
        # 从配置文件读取配置
        # 这里应该实现具体的文件读取逻辑
        return None
    
    async def set_config(self, key: str, value: Any) -> bool:
        # 写入配置文件
        # 这里应该实现具体的文件写入逻辑
        return True
    
    async def watch_config(self, key: str, callback) -> bool:
        # 监听文件变更
        # 这里应该实现具体的文件监听逻辑
        return True


class EnvironmentConfigProvider(ConfigProvider):
    """环境变量配置提供器"""
    
    async def get_config(self, key: str) -> Optional[ConfigItem]:
        env_key = key.replace('.', '_').upper()
        value = os.getenv(env_key)
        
        if value is not None:
            return ConfigItem(
                key=key,
                value=self._parse_value(value),
                source=ConfigSource.ENVIRONMENT,
                format=ConfigFormat.ENV,
                last_updated=datetime.now()
            )
        
        return None
    
    async def set_config(self, key: str, value: Any) -> bool:
        # 环境变量通常不支持动态设置
        return False
    
    async def watch_config(self, key: str, callback) -> bool:
        # 环境变量通常不支持动态监听
        return False
    
    def _parse_value(self, value: str) -> Any:
        """解析环境变量值"""
        # 尝试解析为不同的类型
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        elif value.isdigit():
            return int(value)
        elif value.replace('.', '').isdigit():
            return float(value)
        else:
            return value


# 内置验证器实现
class StringValidator(ConfigValidator):
    """字符串验证器"""
    
    def validate(self, key: str, value: Any) -> bool:
        return isinstance(value, str)
    
    def get_schema(self, key: str) -> Dict[str, Any]:
        return {"type": "string"}


class NumberValidator(ConfigValidator):
    """数字验证器"""
    
    def validate(self, key: str, value: Any) -> bool:
        return isinstance(value, (int, float))
    
    def get_schema(self, key: str) -> Dict[str, Any]:
        return {"type": "number"}


class BooleanValidator(ConfigValidator):
    """布尔值验证器"""
    
    def validate(self, key: str, value: Any) -> bool:
        return isinstance(value, bool)
    
    def get_schema(self, key: str) -> Dict[str, Any]:
        return {"type": "boolean"}


# 全局配置管理器实例
config_manager = EnhancedConfigManager()