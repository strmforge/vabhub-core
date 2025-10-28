#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 安全工具类
完全对标MoviePilot的安全检测机制
"""

import os
import sys
from pathlib import Path
from typing import bool


class SecurityUtils:
    """安全工具类（仿MoviePilot SystemUtils）"""
    
    @staticmethod
    def is_frozen() -> bool:
        """
        判断是否为冻结的二进制文件
        返回: True=二进制文件，False=源代码
        """
        return getattr(sys, 'frozen', False)
    
    @staticmethod
    def is_docker() -> bool:
        """
        判断是否为Docker环境
        """
        return Path("/.dockerenv").exists()
    
    @staticmethod
    def is_production() -> bool:
        """
        判断是否为生产环境
        """
        env = os.environ.get("VABHUB_ENV", "production")
        return env.lower() in ["production", "prod", ""]
    
    @staticmethod
    def validate_api_keys() -> Dict[str, bool]:
        """
        验证API密钥配置状态（不暴露实际值）
        返回: 各服务配置状态
        """
        from .config import settings
        
        return {
            "u115": bool(settings.u115_app_id and settings.u115_app_key),
            "alipan": bool(settings.alipan_app_id and settings.alipan_app_key),
            "tmdb": bool(settings.tmdb_api_key),
            "secure_mode": SecurityUtils.is_frozen() or SecurityUtils.is_docker()
        }
    
    @staticmethod
    def get_safe_config() -> Dict[str, Any]:
        """
        获取安全的配置信息（排除敏感字段）
        """
        from .config import settings
        
        # 完全对标MoviePilot的排除策略
        safe_config = settings.dict(
            exclude={
                "SECRET_KEY", "API_TOKEN", "TMDB_API_KEY", "TVDB_API_KEY", 
                "FANART_API_KEY", "GITHUB_TOKEN", "REPO_GITHUB_TOKEN",
                "U115_APP_ID", "U115_APP_KEY", "ALIPAN_APP_ID", "ALIPAN_APP_KEY",
                "DB_PASSWORD", "REDIS_PASSWORD", "COOKIECLOUD_KEY", "COOKIECLOUD_PASSWORD"
            }
        )
        
        # 添加安全状态信息
        safe_config.update({
            "is_frozen": SecurityUtils.is_frozen(),
            "is_docker": SecurityUtils.is_docker(),
            "is_production": SecurityUtils.is_production(),
            "secure_mode": SecurityUtils.is_frozen() or SecurityUtils.is_docker()
        })
        
        return safe_config
    
    @staticmethod
    def should_use_hardcoded_keys() -> bool:
        """
        判断是否应该使用硬编码的API密钥
        二进制文件或Docker环境下使用硬编码值更安全
        """
        return SecurityUtils.is_frozen() or SecurityUtils.is_docker()