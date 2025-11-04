"""
VabHub 统一配置管理器

负责加载、验证和管理所有系统配置，支持环境变量覆盖和配置热重载。
"""

import os
import yaml  # type: ignore
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
import logging


class DatabaseConfig(BaseSettings):
    """数据库配置"""

    url: str = Field(default="sqlite:///vabhub.db", env="DATABASE_URL")
    host: str = Field(default="localhost", env="DATABASE_HOST")
    port: int = Field(default=5432, env="DATABASE_PORT")
    name: str = Field(default="vabhub", env="DATABASE_NAME")
    user: str = Field(default="vabhub", env="DATABASE_USER")
    password: str = Field(default="", env="DATABASE_PASSWORD")
    pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    echo: bool = Field(default=False, env="DATABASE_ECHO")

    model_config = {"env_prefix": "DATABASE_"}


class RedisConfig(BaseSettings):
    """Redis配置"""

    url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: str = Field(default="", env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")
    max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")
    prefix: str = Field(default="vabhub:", env="REDIS_PREFIX")

    model_config = {"env_prefix": "REDIS_"}


class CacheConfig(BaseSettings):
    """缓存配置"""

    ttl: int = Field(default=3600, env="CACHE_TTL")
    memory_max_size: int = Field(default=1000, env="CACHE_MEMORY_MAX_SIZE")
    memory_policy: str = Field(default="lru", env="CACHE_MEMORY_POLICY")
    disk_max_size: int = Field(default=10000, env="CACHE_DISK_MAX_SIZE")
    disk_directory: str = Field(default=".cache", env="CACHE_DISK_DIRECTORY")
    redis_prefix: str = Field(default="vabhub:", env="CACHE_REDIS_PREFIX")
    redis_max_connections: int = Field(default=10, env="CACHE_REDIS_MAX_CONNECTIONS")

    model_config = {"env_prefix": "CACHE_"}


class ServerConfig(BaseSettings):
    """服务器配置"""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    access_log: bool = True
    cors_origins: List[str] = ["*"]

    class Config:
        env_prefix = "SERVER_"


class LoggingConfig(BaseSettings):
    """日志配置"""

    level: str = "INFO"
    file: str = "logs/vabhub.log"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_size: int = 10485760  # 10MB
    backup_count: int = 5

    class Config:
        env_prefix = "LOG_"


class APIConfig(BaseSettings):
    """外部API配置"""

    tmdb_api_key: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    y123_client_id: str = ""
    y123_client_secret: str = ""
    y123_refresh_token: str = ""
    y115_client_id: str = ""
    y115_client_secret: str = ""
    y115_refresh_token: str = ""

    class Config:
        env_prefix = ""


class PluginConfig(BaseSettings):
    """插件配置"""

    enabled_plugins: List[str] = [
        "media_info",
        "download_manager",
        "notification",
        "search",
        "douban_fallback",
        "jellyfin_parity",
        "stream_gateway",
    ]
    plugin_dir: str = "plugins"
    auto_discover: bool = True
    hot_reload: bool = False

    class Config:
        env_prefix = "PLUGIN_"


class PerformanceConfig(BaseSettings):
    """性能配置"""

    max_workers: int = 10
    timeout: int = 30
    retry_attempts: int = 3
    rate_limit: int = 100
    batch_size: int = 50

    class Config:
        env_prefix = "PERFORMANCE_"


class VabHubConfig(BaseSettings):
    """VabHub 主配置类"""

    # 应用基础配置
    app_name: str = "VabHub"
    app_version: str = "1.6.0"
    environment: str = "development"
    debug: bool = False
    secret_key: str = ""

    # 子配置
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    cache: CacheConfig = CacheConfig()
    server: ServerConfig = ServerConfig()
    logging: LoggingConfig = LoggingConfig()
    api: APIConfig = APIConfig()
    plugins: PluginConfig = PluginConfig()
    performance: PerformanceConfig = PerformanceConfig()

    class Config:
        env_prefix = "VABHUB_"
        env_file = ".env"
        env_file_encoding = "utf-8"


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: str = "config", env_file: str = ".env"):
        self.config_dir = Path(config_dir)
        self.env_file = Path(env_file)
        self.logger = logging.getLogger(__name__)
        self._config: Optional[VabHubConfig] = None
        self._config_files: List[Path] = []

        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)

    def load_config(self) -> VabHubConfig:
        """加载配置"""
        try:
            # 加载环境变量
            self._load_env_vars()

            # 加载配置文件
            config_data = self._load_config_files()

            # 创建配置对象
            self._config = VabHubConfig(**config_data)

            self.logger.info(f"配置加载成功 - 环境: {self._config.environment}")
            return self._config

        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            # 返回默认配置
            return VabHubConfig()

    def _load_env_vars(self):
        """加载环境变量"""
        if self.env_file.exists():
            self.logger.info(f"加载环境变量文件: {self.env_file}")
            # 环境变量会自动通过pydantic加载

    def _load_config_files(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_data = {}

        # 主配置文件
        main_config_file = self.config_dir / "config.yaml"
        if main_config_file.exists():
            config_data.update(self._load_yaml_file(main_config_file))

        # 环境特定配置文件
        env_config_file = self.config_dir / f"config.{self._get_environment()}.yaml"
        if env_config_file.exists():
            config_data.update(self._load_yaml_file(env_config_file))

        # 加载其他配置文件
        for config_file in self.config_dir.glob("*.yaml"):
            if config_file.name not in [
                "config.yaml",
                f"config.{self._get_environment()}.yaml",
            ]:
                # 根据文件名确定配置段
                section_name = config_file.stem
                section_data = self._load_yaml_file(config_file)
                if section_data:
                    config_data[section_name] = section_data

        return config_data

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """加载YAML文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"加载配置文件失败 {file_path}: {e}")
            return {}

    def _get_environment(self) -> str:
        """获取当前环境"""
        return os.getenv("VABHUB_ENVIRONMENT", "development")

    def get_config(self) -> VabHubConfig:
        """获取当前配置"""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def reload_config(self) -> VabHubConfig:
        """重新加载配置"""
        self._config = None
        return self.load_config()

    def validate_config(self) -> bool:
        """验证配置"""
        try:
            config = self.get_config()
            # Pydantic会自动验证，这里可以添加额外的验证逻辑
            return True
        except Exception as e:
            self.logger.error(f"配置验证失败: {e}")
            return False

    def export_config(self, format: str = "yaml") -> str:
        """导出配置"""
        config = self.get_config()
        config_dict = config.dict()

        if format == "yaml":
            return yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
        elif format == "json":
            return json.dumps(config_dict, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        config = self.get_config()
        return {
            "app_name": config.app_name,
            "app_version": config.app_version,
            "environment": config.environment,
            "debug": config.debug,
            "server": {"host": config.server.host, "port": config.server.port},
            "database": {
                "url": config.database.url,
                "host": config.database.host,
                "port": config.database.port,
            },
            "redis": {
                "url": config.redis.url,
                "host": config.redis.host,
                "port": config.redis.port,
            },
            "plugins": {
                "enabled_count": len(config.plugins.enabled_plugins),
                "auto_discover": config.plugins.auto_discover,
            },
        }


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: str = "config") -> ConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    return _config_manager


def get_config() -> VabHubConfig:
    """获取当前配置"""
    return get_config_manager().get_config()


def reload_config() -> VabHubConfig:
    """重新加载配置"""
    return get_config_manager().reload_config()


def validate_config() -> bool:
    """验证配置"""
    return get_config_manager().validate_config()


def export_config(format: str = "yaml") -> str:
    """导出配置"""
    return get_config_manager().export_config(format)


def get_config_summary() -> Dict[str, Any]:
    """获取配置摘要"""
    return get_config_manager().get_config_summary()
