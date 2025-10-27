#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 统一配置系统
参照MoviePilot的配置管理理念
提供增强的配置管理功能
"""

import os
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseSettings, Field, validator
from .enhanced_error_handler import retry_on_error, handle_errors


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    url: str = Field(default="sqlite:///vabhub.db", description="数据库连接URL")
    echo_sql: bool = Field(default=False, description="是否输出SQL日志")
    
    class Config:
        env_prefix = "DB_"


class APIConfig(BaseSettings):
    """API配置"""
    host: str = Field(default="0.0.0.0", description="API服务地址")
    port: int = Field(default=8090, description="API服务端口")
    debug: bool = Field(default=False, description="调试模式")
    cors_origins: list = Field(default=["*"], description="CORS允许的源")
    
    class Config:
        env_prefix = "API_"


class MediaConfig(BaseSettings):
    """媒体文件配置"""
    upload_dir: str = Field(default="uploads", description="上传文件目录")
    media_library: str = Field(default="media_library", description="媒体库目录")
    temp_dir: str = Field(default="temp", description="临时文件目录")
    max_file_size: int = Field(default=100, description="最大文件大小(MB)")
    
    class Config:
        env_prefix = "MEDIA_"


class PTSiteConfig(BaseSettings):
    """PT站点配置"""
    enabled_sites: list = Field(default=["M-Team", "HDHome"], description="启用的PT站点")
    search_timeout: int = Field(default=30, description="搜索超时时间(秒)")
    max_results: int = Field(default=50, description="最大搜索结果数")
    
    class Config:
        env_prefix = "PT_"


class RenameConfig(BaseSettings):
    """重命名配置"""
    strategy: str = Field(default="moviepilot", description="重命名策略")
    create_folders: bool = Field(default=True, description="是否创建文件夹")
    backup_original: bool = Field(default=True, description="是否备份原文件")
    
    class Config:
        env_prefix = "RENAME_"


class VabHubConfig(BaseSettings):
    """VabHub主配置"""
    # 基础配置
    app_name: str = Field(default="VabHub", description="应用名称")
    version: str = Field(default="5.0.0", description="版本号")
    debug: bool = Field(default=False, description="调试模式")
    
    # 模块配置
    database: DatabaseConfig = DatabaseConfig()
    api: APIConfig = APIConfig()
    media: MediaConfig = MediaConfig()
    pt_sites: PTSiteConfig = PTSiteConfig()
    rename: RenameConfig = RenameConfig()
    
    # 功能开关
    enable_file_organizer: bool = Field(default=True, description="启用文件整理")
    enable_duplicate_finder: bool = Field(default=True, description="启用重复检测")
    enable_smart_rename: bool = Field(default=True, description="启用智能重命名")
    enable_file_cleaner: bool = Field(default=True, description="启用文件清理")
    enable_batch_processor: bool = Field(default=True, description="启用批量处理")
    enable_pt_search: bool = Field(default=True, description="启用PT搜索")
    enable_media_library: bool = Field(default=True, description="启用媒体库")
    
    class Config:
        env_prefix = "VABHUB_"
        env_file = ".env"


class EnhancedConfigManager:
    """增强配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self._config: Optional[VabHubConfig] = None
        self._config_history: List[Dict] = []
        self._backup_dir = Path("config_backups")
        self._backup_dir.mkdir(exist_ok=True)
        self._load_config()
    
    @retry_on_error(max_retries=3, delay=1.0)
    def _load_config(self):
        """加载配置（支持重试）"""
        if self.config_file.exists():
            # 支持JSON和YAML格式
            if self.config_file.suffix.lower() in ['.json', '.yaml', '.yml']:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    if self.config_file.suffix.lower() == '.json':
                        config_data = json.load(f)
                    else:
                        config_data = yaml.safe_load(f)
                
                # 验证配置数据
                self._validate_config_data(config_data)
                self._config = VabHubConfig(**config_data)
            else:
                raise ValueError(f"不支持的配置文件格式: {self.config_file.suffix}")
        else:
            # 创建默认配置
            self._config = VabHubConfig()
            self._save_config()
        
        # 记录配置历史
        self._record_config_change("initial_load")
    
    @retry_on_error(max_retries=3, delay=1.0)
    def _save_config(self):
        """保存配置（支持重试）"""
        # 创建备份
        self._create_backup()
        
        config_data = self._config.dict()
        
        # 根据文件后缀选择格式
        if self.config_file.suffix.lower() == '.json':
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        else:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
    
    def _validate_config_data(self, config_data: Dict):
        """验证配置数据"""
        required_fields = ['app_name', 'version']
        for field in required_fields:
            if field not in config_data:
                raise ValueError(f"配置缺少必需字段: {field}")
    
    def _create_backup(self):
        """创建配置备份"""
        if self.config_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self._backup_dir / f"config_backup_{timestamp}{self.config_file.suffix}"
            
            import shutil
            shutil.copy2(self.config_file, backup_file)
            
            # 保留最近10个备份
            backups = sorted(self._backup_dir.glob(f"*{self.config_file.suffix}"))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    old_backup.unlink()
    
    def _record_config_change(self, action: str, changes: Dict = None):
        """记录配置变更"""
        change_record = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "changes": changes or {}
        }
        self._config_history.append(change_record)
        
        # 保留最近100条记录
        if len(self._config_history) > 100:
            self._config_history = self._config_history[-100:]
    
    @handle_errors(default_return=None, log_level="WARNING")
    def get_config(self) -> VabHubConfig:
        """获取配置"""
        return self._config
    
    @handle_errors(log_level="ERROR")
    def update_config(self, **kwargs):
        """更新配置"""
        changes = {}
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                old_value = getattr(self._config, key)
                setattr(self._config, key, value)
                changes[key] = {"old": old_value, "new": value}
        
        if changes:
            self._save_config()
            self._record_config_change("update", changes)
    
    def get_feature_status(self, feature_name: str) -> bool:
        """获取功能状态"""
        feature_map = {
            "file_organizer": "enable_file_organizer",
            "duplicate_finder": "enable_duplicate_finder", 
            "smart_rename": "enable_smart_rename",
            "file_cleaner": "enable_file_cleaner",
            "batch_processor": "enable_batch_processor",
            "pt_search": "enable_pt_search",
            "media_library": "enable_media_library"
        }
        
        if feature_name in feature_map:
            return getattr(self._config, feature_map[feature_name])
        return False
    
    def get_config_history(self, limit: int = 10) -> List[Dict]:
        """获取配置变更历史"""
        return self._config_history[-limit:]
    
    def restore_backup(self, backup_file: Path) -> bool:
        """从备份恢复配置"""
        try:
            if backup_file.exists():
                import shutil
                shutil.copy2(backup_file, self.config_file)
                self._load_config()
                self._record_config_change("restore_from_backup", {"backup_file": str(backup_file)})
                return True
            return False
        except Exception as e:
            logging.error(f"恢复备份失败: {e}")
            return False
    
    def export_config(self, export_path: Path, format: str = "json") -> bool:
        """导出配置"""
        try:
            config_data = self._config.dict()
            
            if format.lower() == "json":
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            elif format.lower() in ["yaml", "yml"]:
                with open(export_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            return True
        except Exception as e:
            logging.error(f"导出配置失败: {e}")
            return False


# 全局配置实例
config_manager = EnhancedConfigManager()


def get_config() -> VabHubConfig:
    """获取全局配置"""
    return config_manager.get_config()


def get_enhanced_config_manager() -> EnhancedConfigManager:
    """获取增强配置管理器"""
    return config_manager