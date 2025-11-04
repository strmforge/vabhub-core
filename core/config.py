"""
Core configuration module for VabHub
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 导入统一配置
from .config_manager import get_config


class Config:
    """Base configuration class"""

    def __init__(self):
        # Load .env file if it exists
        load_dotenv()
        
        # 使用统一配置
        self._unified_config = get_config()
        
        # Database settings
        self.DATABASE_URL = os.getenv("DATABASE_URL", self._unified_config.database.url)

        # API settings
        self.API_HOST = self._unified_config.server.host
        self.API_PORT = self._unified_config.server.port

        # Security settings
        self.SECRET_KEY = self._unified_config.secret_key or os.getenv("SECRET_KEY", "")

        # External API settings
        self.TMDB_API_KEY = self._unified_config.api.tmdb_api_key or os.getenv("TMDB_API_KEY", "")
        self.SPOTIFY_CLIENT_ID = self._unified_config.api.spotify_client_id or os.getenv(
            "SPOTIFY_CLIENT_ID", ""
        )
        self.SPOTIFY_CLIENT_SECRET = self._unified_config.api.spotify_client_secret or os.getenv(
            "SPOTIFY_CLIENT_SECRET", ""
        )
        self.APPLE_MUSIC_TOKEN = os.getenv("APPLE_MUSIC_TOKEN", "")
        self.BANGUMI_API_KEY = os.getenv("BANGUMI_API_KEY", "")

        # Cache settings
        cache_ttl_str = os.getenv("CACHE_TTL", str(self._unified_config.cache.ttl))
        try:
            self.CACHE_TTL = int(cache_ttl_str)
        except ValueError:
            self.CACHE_TTL = self._unified_config.cache.ttl
            
        self.REDIS_URL = os.getenv("REDIS_URL", self._unified_config.redis.url)

        # Logging settings
        self.LOG_LEVEL = self._unified_config.logging.level

        # JWT settings
        self.ALGORITHM = "HS256"
        access_token_expire_str = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        try:
            self.ACCESS_TOKEN_EXPIRE_MINUTES = int(access_token_expire_str)
        except ValueError:
            self.ACCESS_TOKEN_EXPIRE_MINUTES = 30

    def validate(self) -> bool:
        """Validate configuration values"""
        try:
            # Validate CACHE_TTL
            if self.CACHE_TTL < 0:
                return False
            
            # Validate ACCESS_TOKEN_EXPIRE_MINUTES
            if self.ACCESS_TOKEN_EXPIRE_MINUTES < 0:
                return False
                
            return True
        except Exception:
            return False

    def reload(self):
        """Reload configuration from environment"""
        # Reload .env file
        load_dotenv(override=True)
        
        # Reload unified config
        from .config_manager import reload_config
        self._unified_config = reload_config()
        
        # Re-read values from environment
        self.DATABASE_URL = os.getenv("DATABASE_URL", self._unified_config.database.url)
        self.SECRET_KEY = self._unified_config.secret_key or os.getenv("SECRET_KEY", "")
        self.REDIS_URL = os.getenv("REDIS_URL", self._unified_config.redis.url)
        
        cache_ttl_str = os.getenv("CACHE_TTL", str(self._unified_config.cache.ttl))
        try:
            self.CACHE_TTL = int(cache_ttl_str)
        except ValueError:
            self.CACHE_TTL = self._unified_config.cache.ttl
            
        access_token_expire_str = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        try:
            self.ACCESS_TOKEN_EXPIRE_MINUTES = int(access_token_expire_str)
        except ValueError:
            self.ACCESS_TOKEN_EXPIRE_MINUTES = 30

    def __str__(self) -> str:
        """String representation of config"""
        attrs = [attr for attr in dir(self) if not attr.startswith('_') and not callable(getattr(self, attr))]
        attrs_str = ', '.join(f"{attr}={getattr(self, attr)}" for attr in attrs if attr != 'SECRET_KEY')
        secret_key_display = "***" if self.SECRET_KEY else "None"
        return f"Config({attrs_str}, SECRET_KEY={secret_key_display})"

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert config to dictionary"""
        # Create an instance to access properties
        instance = cls()
        return {
            "DATABASE_URL": instance.DATABASE_URL,
            "API_HOST": instance.API_HOST,
            "API_PORT": instance.API_PORT,
            "SECRET_KEY": instance.SECRET_KEY,
            "TMDB_API_KEY": instance.TMDB_API_KEY,
            "SPOTIFY_CLIENT_ID": instance.SPOTIFY_CLIENT_ID,
            "SPOTIFY_CLIENT_SECRET": instance.SPOTIFY_CLIENT_SECRET,
            "APPLE_MUSIC_TOKEN": instance.APPLE_MUSIC_TOKEN,
            "BANGUMI_API_KEY": instance.BANGUMI_API_KEY,
            "REDIS_URL": instance.REDIS_URL,
            "CACHE_TTL": instance.CACHE_TTL,
            "LOG_LEVEL": instance.LOG_LEVEL,
            "ALGORITHM": instance.ALGORITHM,
            "ACCESS_TOKEN_EXPIRE_MINUTES": instance.ACCESS_TOKEN_EXPIRE_MINUTES,
        }


# Development configuration
class DevelopmentConfig(Config):
    """Development configuration"""

    def __init__(self):
        super().__init__()
        self.DEBUG = True
        self.LOG_LEVEL = "DEBUG"


# Production configuration
class ProductionConfig(Config):
    """Production configuration"""

    def __init__(self):
        super().__init__()
        self.DEBUG = False
        self.LOG_LEVEL = "WARNING"


def get_config_by_env(env: Optional[str] = None) -> Config:
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
