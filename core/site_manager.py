#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点管理器
基于MoviePilot的站点管理功能，支持站点资料维护、登录状态维护
支持爬虫模式和RSS模式作为订阅来源
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict

from .cookiecloud_enhanced import CookieCloudEnhanced
import structlog

logger = structlog.get_logger()


class SiteAccessMode(Enum):
    """站点访问模式"""
    SPIDER = "spider"  # 爬虫模式，可获取促销、做种数等详细信息
    RSS = "rss"        # RSS模式，轻量但无促销与做种判断


class SiteStatus(Enum):
    """站点状态"""
    ACTIVE = "active"      # 活跃
    INACTIVE = "inactive"  # 不活跃
    ERROR = "error"        # 错误
    MAINTENANCE = "maintenance"  # 维护中


@dataclass
class SiteInfo:
    """站点信息"""
    name: str
    url: str
    access_mode: SiteAccessMode
    status: SiteStatus
    last_login: Optional[datetime] = None
    cookies: Optional[Dict[str, Any]] = None
    rss_url: Optional[str] = None
    spider_config: Optional[Dict[str, Any]] = None
    priority: int = 0  # 优先级，数值越大优先级越高
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['access_mode'] = self.access_mode.value
        result['status'] = self.status.value
        if self.last_login:
            result['last_login'] = self.last_login.isoformat()
        return result


@dataclass
class SiteStatistics:
    """站点统计信息"""
    site_name: str
    total_searches: int = 0
    successful_searches: int = 0
    failed_searches: int = 0
    last_search_time: Optional[datetime] = None
    average_response_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        if self.last_search_time:
            result['last_search_time'] = self.last_search_time.isoformat()
        return result


class SiteManager:
    """站点管理器"""
    
    def __init__(self):
        self.sites: Dict[str, SiteInfo] = {}
        self.statistics: Dict[str, SiteStatistics] = {}
        self.cookiecloud_enabled = False
        self.cookiecloud_manager: Optional[CookieCloudEnhanced] = None
        self._load_default_sites()
    
    def _load_default_sites(self):
        """加载默认站点配置"""
        default_sites = [
            SiteInfo(
                name="M-Team",
                url="https://tp.m-team.cc",
                access_mode=SiteAccessMode.SPIDER,
                status=SiteStatus.ACTIVE,
                priority=10
            ),
            SiteInfo(
                name="HDChina",
                url="https://hdchina.org",
                access_mode=SiteAccessMode.RSS,
                status=SiteStatus.ACTIVE,
                priority=8
            ),
            SiteInfo(
                name="TTG",
                url="https://totheglory.im",
                access_mode=SiteAccessMode.SPIDER,
                status=SiteStatus.ACTIVE,
                priority=9
            )
        ]
        
        for site in default_sites:
            self.sites[site.name] = site
            self.statistics[site.name] = SiteStatistics(site_name=site.name)
    
    async def initialize_cookiecloud(self, server: str, key: str, password: str) -> bool:
        """初始化CookieCloud"""
        try:
            self.cookiecloud_manager = CookieCloudEnhanced(server, key, password)
            await self.sync_cookiecloud_data()
            self.cookiecloud_enabled = True
            logger.info("CookieCloud初始化成功")
            return True
        except Exception as e:
            logger.error("CookieCloud初始化失败", error=str(e))
            return False
    
    async def sync_cookiecloud_data(self) -> bool:
        """同步CookieCloud数据"""
        if not self.cookiecloud_manager:
            return False
        
        try:
            async with self.cookiecloud_manager as cc:
                cookies_data, error = await cc.download_data()
                
                if error:
                    logger.error("CookieCloud数据同步失败", error=error)
                    return False
                
                # 更新站点Cookie信息
                for site_name, site_info in self.sites.items():
                    if site_name in cookies_data:
                        site_info.cookies = cookies_data[site_name]
                        site_info.last_login = datetime.now()
                        logger.info(f"更新站点 {site_name} 的Cookie信息")
                
                return True
                
        except Exception as e:
            logger.error("CookieCloud数据同步异常", error=str(e))
            return False
    
    def add_site(self, site_info: SiteInfo) -> bool:
        """添加站点"""
        try:
            self.sites[site_info.name] = site_info
            self.statistics[site_info.name] = SiteStatistics(site_name=site_info.name)
            logger.info(f"添加站点: {site_info.name}")
            return True
        except Exception as e:
            logger.error(f"添加站点失败: {e}")
            return False
    
    def update_site(self, site_name: str, updates: Dict[str, Any]) -> bool:
        """更新站点信息"""
        if site_name not in self.sites:
            return False
        
        try:
            site = self.sites[site_name]
            
            # 更新站点属性
            for key, value in updates.items():
                if hasattr(site, key):
                    setattr(site, key, value)
            
            logger.info(f"更新站点: {site_name}")
            return True
        except Exception as e:
            logger.error(f"更新站点失败: {e}")
            return False
    
    def get_site(self, site_name: str) -> Optional[SiteInfo]:
        """获取站点信息"""
        return self.sites.get(site_name)
    
    def get_all_sites(self) -> List[SiteInfo]:
        """获取所有站点信息"""
        return list(self.sites.values())
    
    def get_enabled_sites(self) -> List[SiteInfo]:
        """获取启用的站点"""
        return [site for site in self.sites.values() if site.enabled]
    
    def get_sites_by_mode(self, access_mode: SiteAccessMode) -> List[SiteInfo]:
        """按访问模式获取站点"""
        return [site for site in self.sites.values() 
                if site.access_mode == access_mode and site.enabled]
    
    def update_site_statistics(self, site_name: str, success: bool, response_time: float):
        """更新站点统计信息"""
        if site_name not in self.statistics:
            return
        
        stats = self.statistics[site_name]
        stats.total_searches += 1
        
        if success:
            stats.successful_searches += 1
        else:
            stats.failed_searches += 1
        
        stats.last_search_time = datetime.now()
        
        # 计算平均响应时间
        if stats.total_searches > 1:
            stats.average_response_time = (
                (stats.average_response_time * (stats.total_searches - 1) + response_time) 
                / stats.total_searches
            )
        else:
            stats.average_response_time = response_time
    
    def get_site_statistics(self, site_name: str) -> Optional[SiteStatistics]:
        """获取站点统计信息"""
        return self.statistics.get(site_name)
    
    def get_all_statistics(self) -> Dict[str, SiteStatistics]:
        """获取所有站点统计信息"""
        return self.statistics.copy()
    
    def export_sites_config(self) -> Dict[str, Any]:
        """导出站点配置"""
        return {
            "sites": {name: site.to_dict() for name, site in self.sites.items()},
            "statistics": {name: stats.to_dict() for name, stats in self.statistics.items()},
            "cookiecloud_enabled": self.cookiecloud_enabled,
            "last_updated": datetime.now().isoformat()
        }
    
    def import_sites_config(self, config: Dict[str, Any]) -> bool:
        """导入站点配置"""
        try:
            if "sites" in config:
                for name, site_data in config["sites"].items():
                    site_info = SiteInfo(
                        name=site_data["name"],
                        url=site_data["url"],
                        access_mode=SiteAccessMode(site_data["access_mode"]),
                        status=SiteStatus(site_data["status"]),
                        priority=site_data.get("priority", 0),
                        enabled=site_data.get("enabled", True)
                    )
                    self.sites[name] = site_info
            
            if "statistics" in config:
                for name, stats_data in config["statistics"].items():
                    stats = SiteStatistics(
                        site_name=stats_data["site_name"],
                        total_searches=stats_data.get("total_searches", 0),
                        successful_searches=stats_data.get("successful_searches", 0),
                        failed_searches=stats_data.get("failed_searches", 0),
                        average_response_time=stats_data.get("average_response_time", 0.0)
                    )
                    if stats_data.get("last_search_time"):
                        stats.last_search_time = datetime.fromisoformat(stats_data["last_search_time"])
                    self.statistics[name] = stats
            
            logger.info("站点配置导入成功")
            return True
            
        except Exception as e:
            logger.error("站点配置导入失败", error=str(e))
            return False


# 全局站点管理器实例
site_manager = SiteManager()