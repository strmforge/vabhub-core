"""
Core configuration module for VabHub
"""

import os
from typing import Dict, Any

# 导入统一配置
from .config_manager import get_config


class Config:
    """Base configuration class"""

    # 使用统一配置
    _unified_config = get_config()

    # Database settings
    DATABASE_URL = _unified_config.database.url

    # API settings
    API_HOST = _unified_config.server.host
    API_PORT = _unified_config.server.port

    # Security settings
    SECRET_KEY = _unified_config.secret_key

    # External API settings
    TMDB_API_KEY = _unified_config.api.tmdb_api_key or os.getenv("TMDB_API_KEY", "")
    SPOTIFY_CLIENT_ID = _unified_config.api.spotify_client_id or os.getenv(
        "SPOTIFY_CLIENT_ID", ""
    )
    SPOTIFY_CLIENT_SECRET = _unified_config.api.spotify_client_secret or os.getenv(
        "SPOTIFY_CLIENT_SECRET", ""
    )
    APPLE_MUSIC_TOKEN = os.getenv("APPLE_MUSIC_TOKEN", "")
    BANGUMI_API_KEY = os.getenv("BANGUMI_API_KEY", "")

    # Cache settings
    REDIS_URL = _unified_config.redis.url
    CACHE_TTL = _unified_config.cache.ttl

    # Logging settings
    LOG_LEVEL = _unified_config.logging.level

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }


# Development configuration
class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    LOG_LEVEL = "DEBUG"


# Production configuration
class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    LOG_LEVEL = "WARNING"


def get_config_by_env(env: str = None) -> Config:
    """根据环境变量获取配置类

    Args:
        env: 环境名称，如'dev'、'prod'等

    Returns:
        对应的配置类实例
    """
    if env is None:
        env = os.getenv("VABHUB_ENV", "dev")

    if env.lower() in ["prod", "production"]:
        return ProductionConfig()
    else:
        return DevelopmentConfig()
