#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT站点认证管理器
提供PT站点认证的替代方案，支持CookieCloud集成和本地存储
"""

import json
import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from .encryption import SensitiveDataManager

logger = structlog.get_logger()


class PTAuthManager:
    """PT站点认证管理器"""
    
    def __init__(self):
        self.sensitive_data_manager = SensitiveDataManager()
        self.pt_sites = {}
        self.cookie_jar = {}
        self.auth_cache = {}
        self.cache_timeout = timedelta(hours=1)
        
        # 初始化支持的PT站点配置
        self._init_pt_sites()
    
    def _init_pt_sites(self):
        """初始化支持的PT站点配置"""
        self.pt_sites = {
            'mteam': {
                'name': 'M-Team',
                'base_url': 'https://tp.m-team.cc',
                'login_url': '/takelogin.php',
                'cookie_domain': '.m-team.cc',
                'required_cookies': ['tp', 'ipb_member_id', 'ipb_pass_hash']
            },
            'hdchina': {
                'name': 'HDChina',
                'base_url': 'https://hdchina.org',
                'login_url': '/login.php',
                'cookie_domain': '.hdchina.org',
                'required_cookies': ['hdchina', 'session']
            },
            'ttg': {
                'name': 'TTG',
                'base_url': 'https://totheglory.im',
                'login_url': '/login.php',
                'cookie_domain': '.totheglory.im',
                'required_cookies': ['ttg', 'session']
            },
            'chdbits': {
                'name': 'CHDBits',
                'base_url': 'https://chdbits.co',
                'login_url': '/login.php',
                'cookie_domain': '.chdbits.co',
                'required_cookies': ['chdbits', 'session']
            },
            'hdbits': {
                'name': 'HDBits',
                'base_url': 'https://hdbits.org',
                'login_url': '/login.php',
                'cookie_domain': '.hdbits.org',
                'required_cookies': ['hdbits', 'session']
            }
        }
    
    async def login_with_cookie(self, site_name: str, cookies: Dict[str, str]) -> bool:
        """使用Cookie登录PT站点"""
        try:
            if site_name not in self.pt_sites:
                logger.error("不支持的PT站点", site_name=site_name)
                return False
            
            site_config = self.pt_sites[site_name]
            
            # 验证必要的Cookie
            required_cookies = site_config['required_cookies']
            missing_cookies = [cookie for cookie in required_cookies if cookie not in cookies]
            
            if missing_cookies:
                logger.error("缺少必要的Cookie", site_name=site_name, missing_cookies=missing_cookies)
                return False
            
            # 保存Cookie到敏感数据管理器
            self.sensitive_data_manager.store_pt_cookies(site_name, cookies)
            
            # 更新Cookie jar
            self.cookie_jar[site_name] = {
                'cookies': cookies,
                'login_time': datetime.now(),
                'last_used': datetime.now(),
                'is_valid': True
            }
            
            logger.info("PT站点登录成功", site_name=site_name)
            return True
            
        except Exception as e:
            logger.error("PT站点登录失败", site_name=site_name, error=str(e))
            return False
    
    async def validate_cookie(self, site_name: str) -> bool:
        """验证Cookie有效性"""
        try:
            if site_name not in self.cookie_jar:
                return False
            
            cookie_info = self.cookie_jar[site_name]
            
            # 检查缓存时间
            if datetime.now() - cookie_info['last_used'] > self.cache_timeout:
                # 需要重新验证
                cookie_info['is_valid'] = await self._check_cookie_validity(site_name)
                cookie_info['last_used'] = datetime.now()
            
            return cookie_info['is_valid']
            
        except Exception as e:
            logger.error("验证Cookie失败", site_name=site_name, error=str(e))
            return False
    
    async def _check_cookie_validity(self, site_name: str) -> bool:
        """检查Cookie有效性（通过访问用户信息页面）"""
        try:
            if site_name not in self.cookie_jar:
                return False
            
            site_config = self.pt_sites[site_name]
            cookies = self.cookie_jar[site_name]['cookies']
            
            # 这里可以添加实际的HTTP请求来验证Cookie
            # 暂时返回True，实际实现需要根据具体站点API
            return True
            
        except Exception as e:
            logger.error("检查Cookie有效性失败", site_name=site_name, error=str(e))
            return False
    
    def get_cookie_for_site(self, site_name: str) -> Optional[Dict[str, str]]:
        """获取指定站点的Cookie"""
        try:
            if site_name in self.cookie_jar:
                cookie_info = self.cookie_jar[site_name]
                cookie_info['last_used'] = datetime.now()
                return cookie_info['cookies']
            
            # 尝试从敏感数据管理器加载
            cookies = self.sensitive_data_manager.get_pt_cookies(site_name)
            if cookies:
                self.cookie_jar[site_name] = {
                    'cookies': cookies,
                    'login_time': datetime.now(),
                    'last_used': datetime.now(),
                    'is_valid': True
                }
                return cookies
            
            return None
            
        except Exception as e:
            logger.error("获取Cookie失败", site_name=site_name, error=str(e))
            return None
    
    async def import_from_cookiecloud(self, cookiecloud_data: Dict[str, Any]) -> Dict[str, bool]:
        """从CookieCloud导入Cookie"""
        results = {}
        
        try:
            if 'cookie_data' not in cookiecloud_data:
                logger.error("CookieCloud数据格式错误")
                return results
            
            cookie_data = cookiecloud_data['cookie_data']
            
            for site_name, site_cookies in cookie_data.items():
                if site_name in self.pt_sites:
                    success = await self.login_with_cookie(site_name, site_cookies)
                    results[site_name] = success
                else:
                    logger.warning("跳过不支持的站点", site_name=site_name)
            
            logger.info("CookieCloud导入完成", results=results)
            return results
            
        except Exception as e:
            logger.error("CookieCloud导入失败", error=str(e))
            return results
    
    def export_to_cookiecloud(self) -> Dict[str, Any]:
        """导出为CookieCloud格式"""
        try:
            cookiecloud_data = {
                'version': '1.0',
                'export_time': datetime.now().isoformat(),
                'cookie_data': {}
            }
            
            for site_name, cookie_info in self.cookie_jar.items():
                if cookie_info['is_valid']:
                    cookiecloud_data['cookie_data'][site_name] = cookie_info['cookies']
            
            return cookiecloud_data
            
        except Exception as e:
            logger.error("导出CookieCloud格式失败", error=str(e))
            return {}
    
    def get_supported_sites(self) -> List[Dict[str, str]]:
        """获取支持的PT站点列表"""
        return [
            {
                'name': site_config['name'],
                'code': site_name,
                'base_url': site_config['base_url']
            }
            for site_name, site_config in self.pt_sites.items()
        ]
    
    def get_login_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有站点的登录状态"""
        status = {}
        
        for site_name in self.pt_sites:
            if site_name in self.cookie_jar:
                cookie_info = self.cookie_jar[site_name]
                status[site_name] = {
                    'is_logged_in': True,
                    'login_time': cookie_info['login_time'].isoformat(),
                    'last_used': cookie_info['last_used'].isoformat(),
                    'is_valid': cookie_info['is_valid']
                }
            else:
                status[site_name] = {
                    'is_logged_in': False,
                    'login_time': None,
                    'last_used': None,
                    'is_valid': False
                }
        
        return status
    
    async def logout(self, site_name: str) -> bool:
        """登出指定站点"""
        try:
            if site_name in self.cookie_jar:
                del self.cookie_jar[site_name]
            
            # 从敏感数据管理器中删除
            # 注意：这里需要扩展SensitiveDataManager以支持删除特定数据
            
            logger.info("PT站点登出成功", site_name=site_name)
            return True
            
        except Exception as e:
            logger.error("PT站点登出失败", site_name=site_name, error=str(e))
            return False
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        expired_sites = []
        
        for site_name, cookie_info in self.cookie_jar.items():
            if current_time - cookie_info['last_used'] > timedelta(days=7):  # 7天未使用
                expired_sites.append(site_name)
        
        for site_name in expired_sites:
            del self.cookie_jar[site_name]
            logger.info("清理过期会话", site_name=site_name)


# 全局PT认证管理器实例
pt_auth_manager = PTAuthManager()