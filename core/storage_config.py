"""
存储配置管理
基于MoviePilot设计，完整复刻存储管理功能
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from pydantic import BaseModel, validator


class StorageConfig(BaseModel):
    """存储配置"""
    enabled: bool = True
    name: str
    description: str
    transfer_types: List[str]
    
    @validator('transfer_types')
    def validate_transfer_types(cls, v):
        valid_types = ['hardlink', 'softlink', 'move', 'copy']
        for transfer_type in v:
            if transfer_type not in valid_types:
                raise ValueError(f'无效的传输类型: {transfer_type}')
        return v


class LocalStorageConfig(StorageConfig):
    """本地存储配置"""
    root_path: str


class Cloud123StorageConfig(StorageConfig):
    """123云盘存储配置"""
    app_id: str
    app_secret: str
    qrcode_login: bool = True


class FileManagerConfig(BaseModel):
    """文件管理器配置"""
    default_transfer_type: str = "copy"
    max_file_size: int = 10737418240  # 10GB
    max_batch_size: int = 100
    timeout: int = 300  # 5分钟
    
    @validator('default_transfer_type')
    def validate_default_transfer_type(cls, v):
        valid_types = ['hardlink', 'softlink', 'move', 'copy']
        if v not in valid_types:
            raise ValueError(f'无效的默认传输类型: {v}')
        return v


class RenamingConfig(BaseModel):
    """重命名配置"""
    movie_pattern: str = "{title} ({year})/{title} ({year}){quality}{edition}"
    tv_pattern: str = "{title} ({year})/Season {season:02d}/{title} - S{season:02d}E{episode:02d} - {episode_title}{quality}{edition}"
    anime_pattern: str = "{title}/Season {season:02d}/{title} - S{season:02d}E{episode:02d} - {episode_title}"
    supported_types: List[str] = ["movie", "tv", "anime", "music", "documentary"]


class OrganizationConfig(BaseModel):
    """整理配置"""
    auto_organize: bool = True
    
    class RuleConfig(BaseModel):
        enabled: bool = True
        target_path: str
        naming_rule: str
    
    rules: Dict[str, RuleConfig]


class CacheConfig(BaseModel):
    """缓存配置"""
    file_list_ttl: int = 300  # 5分钟
    storage_info_ttl: int = 600  # 10分钟
    space_info_ttl: int = 1800  # 30分钟


class SecurityConfig(BaseModel):
    """安全配置"""
    allowed_paths: List[str]
    forbidden_operations: List[str]


class PerformanceConfig(BaseModel):
    """性能配置"""
    max_workers: int = 10
    batch_size: int = 50
    memory_limit: int = 1073741824  # 1GB


class MonitoringConfig(BaseModel):
    """监控配置"""
    
    class StorageMonitorConfig(BaseModel):
        enabled: bool = True
        interval: int = 300  # 5分钟
    
    class FileOperationsConfig(BaseModel):
        enabled: bool = True
        track_success: bool = True
        track_failure: bool = True
    
    class PerformanceConfig(BaseModel):
        enabled: bool = True
        metrics: List[str] = ["response_time", "throughput", "error_rate"]
    
    storage_monitor: StorageMonitorConfig
    file_operations: FileOperationsConfig
    performance: PerformanceConfig


class StorageSettings(BaseModel):
    """存储设置"""
    storages: Dict[str, Dict[str, Any]]
    file_manager: FileManagerConfig
    renaming: RenamingConfig
    organization: OrganizationConfig
    cache: CacheConfig
    security: SecurityConfig
    performance: PerformanceConfig
    monitoring: MonitoringConfig


class StorageConfigManager:
    """存储配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.settings: Optional[StorageSettings] = None
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        # 优先使用VabHub-Resources中的配置
        resources_path = Path(__file__).parent.parent.parent / "VabHub-Resources" / "config" / "storage_config.yaml"
        if resources_path.exists():
            return str(resources_path)
        
        # 使用当前目录下的配置
        current_path = Path(__file__).parent / "config" / "storage_config.yaml"
        if current_path.exists():
            return str(current_path)
        
        # 创建默认配置目录
        config_dir = Path(__file__).parent / "config"
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "storage_config.yaml")
    
    def _load_config(self):
        """加载配置文件"""
        config_path = Path(self.config_path)
        
        if not config_path.exists():
            # 如果配置文件不存在，创建默认配置
            self._create_default_config(config_path)
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # 验证配置数据
            self.settings = StorageSettings(**config_data)
            
        except Exception as e:
            raise ValueError(f"配置文件加载失败: {str(e)}")
    
    def _create_default_config(self, config_path: Path):
        """创建默认配置文件"""
        default_config = {
            "storages": {
                "local": {
                    "enabled": True,
                    "name": "本地存储",
                    "description": "本地文件系统存储",
                    "root_path": "/data",
                    "transfer_types": ["hardlink", "softlink", "move", "copy"]
                },
                "123cloud": {
                    "enabled": True,
                    "name": "123云盘",
                    "description": "123云盘存储",
                    "app_id": "your_123cloud_app_id",
                    "app_secret": "your_123cloud_app_secret",
                    "transfer_types": ["move", "copy"],
                    "qrcode_login": True
                }
            },
            "file_manager": {
                "default_transfer_type": "copy",
                "max_file_size": 10737418240,
                "max_batch_size": 100,
                "timeout": 300
            },
            "renaming": {
                "movie_pattern": "{title} ({year})/{title} ({year}){quality}{edition}",
                "tv_pattern": "{title} ({year})/Season {season:02d}/{title} - S{season:02d}E{episode:02d} - {episode_title}{quality}{edition}",
                "anime_pattern": "{title}/Season {season:02d}/{title} - S{season:02d}E{episode:02d} - {episode_title}",
                "supported_types": ["movie", "tv", "anime", "music", "documentary"]
            },
            "organization": {
                "auto_organize": True,
                "rules": {
                    "movie": {
                        "enabled": True,
                        "target_path": "/movies",
                        "naming_rule": "movie"
                    },
                    "tv": {
                        "enabled": True,
                        "target_path": "/tv",
                        "naming_rule": "tv"
                    },
                    "anime": {
                        "enabled": True,
                        "target_path": "/anime",
                        "naming_rule": "anime"
                    }
                }
            },
            "cache": {
                "file_list_ttl": 300,
                "storage_info_ttl": 600,
                "space_info_ttl": 1800
            },
            "security": {
                "allowed_paths": ["/data", "/media", "/downloads"],
                "forbidden_operations": ["rm -rf /", "format", "delete_system_files"]
            },
            "performance": {
                "max_workers": 10,
                "batch_size": 50,
                "memory_limit": 1073741824
            },
            "monitoring": {
                "storage_monitor": {
                    "enabled": True,
                    "interval": 300
                },
                "file_operations": {
                    "enabled": True,
                    "track_success": True,
                    "track_failure": True
                },
                "performance": {
                    "enabled": True,
                    "metrics": ["response_time", "throughput", "error_rate"]
                }
            }
        }
        
        # 确保配置目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入默认配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True, indent=2)
    
    def get_storage_config(self, storage_type: str) -> Optional[Dict[str, Any]]:
        """获取指定存储类型的配置"""
        if self.settings and storage_type in self.settings.storages:
            return self.settings.storages[storage_type]
        return None
    
    def get_enabled_storages(self) -> List[str]:
        """获取启用的存储类型"""
        if not self.settings:
            return []
        
        enabled_storages = []
        for storage_type, config in self.settings.storages.items():
            if config.get('enabled', True):
                enabled_storages.append(storage_type)
        
        return enabled_storages
    
    def update_config(self, config_data: Dict[str, Any]):
        """更新配置"""
        try:
            # 验证新配置
            new_settings = StorageSettings(**config_data)
            
            # 更新配置
            self.settings = new_settings
            
            # 保存到文件
            self._save_config()
            
        except Exception as e:
            raise ValueError(f"配置更新失败: {str(e)}")
    
    def _save_config(self):
        """保存配置到文件"""
        if not self.settings:
            return
        
        config_path = Path(self.config_path)
        
        # 转换为字典格式
        config_dict = self.settings.dict()
        
        # 保存到文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, allow_unicode=True, indent=2)
    
    def validate_path(self, path: str) -> bool:
        """验证路径是否在允许的路径列表中"""
        if not self.settings:
            return False
        
        for allowed_path in self.settings.security.allowed_paths:
            if path.startswith(allowed_path):
                return True
        
        return False


# 全局配置管理器实例
_config_manager: Optional[StorageConfigManager] = None


def get_config_manager() -> StorageConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = StorageConfigManager()
    return _config_manager


def reload_config():
    """重新加载配置"""
    global _config_manager
    _config_manager = StorageConfigManager()