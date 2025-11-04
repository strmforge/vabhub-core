"""
统一配置管理模块
"""

import os
from typing import Any, Dict, Optional
from pydantic import BaseSettings, validator  # type: ignore
from pathlib import Path


class DatabaseConfig(BaseSettings):  # type: ignore
    """数据库配置"""
    url: str = "postgresql://vabhub:password@localhost:5432/vabhub"
    pool_size: int = 20
    max_overflow: int = 30
    echo: bool = False
    
    class Config:
        env_prefix = "DB_"


class CacheConfig(BaseSettings):  # type: ignore
    """缓存配置"""
    redis_url: str = "redis://localhost:6379"
    redis_prefix: str = "vabhub:"
    memory_cache_size: int = 1000
    disk_cache_size: int = 10000
    default_ttl: int = 3600
    
    class Config:
        env_prefix = "CACHE_"


class AuthConfig(BaseSettings):  # type: ignore
    """认证配置"""
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_prefix = "AUTH_"


class MediaConfig(BaseSettings):  # type: ignore
    """媒体配置"""
    library_path: str = os.environ.get("MEDIA_LIBRARY_PATH", "/srv/media/library")
    temp_path: str = os.environ.get("MEDIA_TEMP_PATH", "/tmp/vabhub")
    supported_formats: list = ["mp4", "mkv", "avi", "mov"]
    max_file_size: int = 1024 * 1024 * 1024  # 1GB
    
    class Config:
        env_prefix = "MEDIA_"


class PluginConfig(BaseSettings):  # type: ignore
    """插件配置"""
    plugin_dir: str = "plugins"
    auto_discover: bool = True
    enable_third_party: bool = False
    
    class Config:
        env_prefix = "PLUGIN_"


class LoggingConfig(BaseSettings):  # type: ignore
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    class Config:
        env_prefix = "LOG_"


class Config(BaseSettings):  # type: ignore
    """主配置类"""
    
    # 基础配置
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # 子配置
    database: DatabaseConfig = DatabaseConfig()
    cache: CacheConfig = CacheConfig()
    auth: AuthConfig = AuthConfig()
    media: MediaConfig = MediaConfig()
    plugin: PluginConfig = PluginConfig()
    logging: LoggingConfig = LoggingConfig()
    
    class Config:
        env_prefix = "VABHUB_"
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @validator("debug", pre=True)
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)
    
    @validator("reload", pre=True)
    def parse_reload(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "debug": self.debug,
            "host": self.host,
            "port": self.port,
            "reload": self.reload,
            "database": self.database.dict(),
            "cache": self.cache.dict(),
            "auth": self.auth.dict(),
            "media": self.media.dict(),
            "plugin": self.plugin.dict(),
            "logging": self.logging.dict()
        }


# 全局配置实例
config = Config()


def load_config(env_file: Optional[str] = None) -> Config:
    """加载配置"""
    if env_file:
        return Config(_env_file=env_file)
    return Config()


def validate_config() -> bool:
    """验证配置"""
    try:
        # 检查必要目录
        Path(config.media.library_path).mkdir(parents=True, exist_ok=True)
        Path(config.media.temp_path).mkdir(parents=True, exist_ok=True)
        
        # 检查插件目录
        if config.plugin.auto_discover:
            Path(config.plugin.plugin_dir).mkdir(parents=True, exist_ok=True)
        
        return True
    except Exception as e:
        print(f"配置验证失败: {e}")
        return False