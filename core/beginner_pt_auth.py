#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初级用户PT站点认证助手
利用内置CookieCloud服务为初级用户提供简化的PT站点认证流程
"""

import json
import os
import time
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from .encryption import SensitiveDataManager
from .cookiecloud_enhanced import cookiecloud_manager

logger = structlog.get_logger()


class BeginnerPTAuthHelper:
    """初级用户PT认证助手"""
    
    def __init__(self):
        self.sensitive_data_manager = SensitiveDataManager()
        self.user_sessions = {}
        self.guide_steps = self._init_guide_steps()
        self.builtin_cookiecloud_enabled = True
        self.user_auth_status = {}  # 用户认证状态存储
        self.auth_histories = {}    # 认证历史记录
    
    def _init_guide_steps(self) -> Dict[str, Dict[str, Any]]:
        """初始化认证指导步骤"""
        return {
            'step1': {
                'title': '检查浏览器插件状态',
                'description': '系统将检测您的浏览器CookieCloud插件安装状态',
                'fields': [],
                'tips': [
                    '如果您已安装CookieCloud插件，系统将自动同步Cookie',
                    '如果未安装，系统将引导您安装或使用备选方案',
                    '安装插件后，后续认证将更加便捷'
                ]
            },
            'step2': {
                'title': '选择认证方式',
                'description': '根据您的插件状态选择最适合的认证方式',
                'options': [
                    {
                        'name': '智能CookieCloud认证',
                        'description': '自动检测插件状态，提供最优认证方案',
                        'difficulty': '非常简单',
                        'recommended': True,
                        'builtin': True,
                        'requires_plugin': 'auto'
                    },
                    {
                        'name': '账号密码登录',
                        'description': '直接使用账号密码进行认证',
                        'difficulty': '简单',
                        'recommended': False,
                        'builtin': False,
                        'requires_plugin': False
                    },
                    {
                        'name': '手动输入Cookie',
                        'description': '从浏览器手动复制Cookie信息',
                        'difficulty': '中等',
                        'recommended': False,
                        'builtin': False,
                        'requires_plugin': False
                    }
                ]
            },
            'step3': {
                'title': '完成认证',
                'description': '系统将自动完成认证流程',
                'success_message': '认证成功！您现在可以使用PT功能了',
                'failure_message': '认证失败，请检查账号信息或联系管理员'
            }
        }
    
    async def manual_cookie_auth(self, site_name: str, cookies: Dict[str, str]) -> Dict[str, Any]:
        """手动Cookie认证"""
        try:
            # 验证Cookie格式
            if not cookies or len(cookies) == 0:
                return {
                    'success': False,
                    'message': 'Cookie信息为空，请检查输入',
                    'next_step': '重新输入Cookie'
                }
            
            # 保存Cookie到安全存储
            self.sensitive_data_manager.store_pt_cookies(site_name, cookies)
            
            # 创建用户会话
            self.user_sessions[site_name] = {
                'auth_type': 'manual_cookie',
                'auth_time': datetime.now(),
                'last_used': datetime.now(),
                'status': 'authenticated'
            }
            
            logger.info("手动Cookie认证成功", site_name=site_name)
            
            return {
                'success': True,
                'message': f'{site_name} 认证成功！',
                'next_step': '开始使用PT功能'
            }
            
        except Exception as e:
            logger.error("手动Cookie认证失败", site_name=site_name, error=str(e))
            return {
                'success': False,
                'message': f'认证失败：{str(e)}',
                'next_step': '检查网络连接或Cookie格式'
            }
    
    async def username_password_auth(self, site_name: str, username: str, password: str) -> Dict[str, Any]:
        """账号密码认证"""
        try:
            # 验证输入
            if not username or not password:
                return {
                    'success': False,
                    'message': '账号或密码不能为空',
                    'next_step': '重新输入账号密码'
                }
            
            # 模拟登录过程（实际实现需要根据具体站点）
            login_result = await self._simulate_pt_login(site_name, username, password)
            
            if login_result['success']:
                # 保存认证信息到安全存储
                auth_data = {
                    'username': username,
                    'site_name': site_name,
                    'login_time': datetime.now().isoformat()
                }
                self.sensitive_data_manager.store_pt_auth(site_name, auth_data)
                
                # 创建用户会话
                self.user_sessions[site_name] = {
                    'auth_type': 'username_password',
                    'auth_time': datetime.now(),
                    'last_used': datetime.now(),
                    'status': 'authenticated',
                    'username': username
                }
                
                logger.info("账号密码认证成功", site_name=site_name, username=username)
                
                return {
                    'success': True,
                    'message': f'{site_name} 登录成功！',
                    'next_step': '开始使用PT功能',
                    'user_info': {
                        'username': username,
                        'site_name': site_name
                    }
                }
            else:
                return {
                    'success': False,
                    'message': login_result['message'],
                    'next_step': '检查账号密码或网络连接'
                }
            
        except Exception as e:
            logger.error("账号密码认证失败", site_name=site_name, error=str(e))
            return {
                'success': False,
                'message': f'登录失败：{str(e)}',
                'next_step': '联系管理员或稍后重试'
            }
    
    async def smart_cookiecloud_auth(self, site_name: str, username: str = None, password: str = None) -> Dict[str, Any]:
        """智能CookieCloud认证 - 自动检测插件状态并提供最优方案"""
        try:
            # 获取PT站点的域名
            site_domain = self._get_site_domain(site_name)
            if not site_domain:
                return {
                    'success': False,
                    'message': f'不支持的PT站点: {site_name}',
                    'next_step': '请选择其他认证方式'
                }
            
            # 检测CookieCloud插件状态
            plugin_status = await self._check_cookiecloud_plugin_status()
            
            if plugin_status['installed']:
                # 插件已安装，尝试使用CookieCloud认证
                return await self._cookiecloud_auth_with_plugin(site_name, site_domain, username, password)
            else:
                # 插件未安装，提供安装引导或备选方案
                return await self._auth_without_plugin(site_name, site_domain, username, password, plugin_status)
            
        except Exception as e:
            logger.error("智能CookieCloud认证失败", site_name=site_name, error=str(e))
            return {
                'success': False,
                'message': f'认证失败：{str(e)}',
                'next_step': '请检查网络连接或选择其他认证方式'
            }
    
    async def _check_cookiecloud_plugin_status(self) -> Dict[str, Any]:
        """检测CookieCloud插件状态"""
        try:
            # 尝试连接内置CookieCloud服务检测插件状态
            default_client = 'vabhub_builtin'
            
            if default_client not in cookiecloud_manager.clients:
                builtin_config = self._get_builtin_cookiecloud_config()
                if builtin_config:
                    success, message = await cookiecloud_manager.create_client(
                        default_client, 
                        builtin_config['server'],
                        builtin_config['key'], 
                        builtin_config['password']
                    )
                    
                    if success:
                        # 尝试同步数据检测插件状态
                        success, message, cookies_data = await cookiecloud_manager.sync_cookies(default_client)
                        
                        return {
                            'installed': success and cookies_data is not None,
                            'has_data': bool(cookies_data),
                            'message': message,
                            'recommend_installation': not success
                        }
            
            return {
                'installed': False,
                'has_data': False,
                'message': 'CookieCloud插件未检测到',
                'recommend_installation': True
            }
            
        except Exception as e:
            logger.warning("检测CookieCloud插件状态失败", error=str(e))
            return {
                'installed': False,
                'has_data': False,
                'message': f'检测失败：{str(e)}',
                'recommend_installation': True
            }
    
    async def _cookiecloud_auth_with_plugin(self, site_name: str, site_domain: str, username: str = None, password: str = None) -> Dict[str, Any]:
        """使用已安装的CookieCloud插件进行认证"""
        # 首先尝试从内置CookieCloud获取现有Cookie
        cookie_data = await self._get_cookie_from_builtin_service(site_domain)
        
        if cookie_data:
            # 已有Cookie，直接使用
            return await self._complete_builtin_auth(site_name, cookie_data, 'existing_cookie')
        
        # 如果没有Cookie但提供了账号密码，则先登录再获取Cookie
        elif username and password:
            # 使用账号密码登录
            login_result = await self._simulate_pt_login(site_name, username, password)
            
            if login_result['success']:
                # 登录成功，获取Cookie并保存到CookieCloud
                cookie_data = login_result.get('cookies', {})
                
                # 保存Cookie到内置CookieCloud
                await self._save_cookie_to_builtin_service(site_domain, cookie_data)
                
                # 完成认证
                return await self._complete_builtin_auth(site_name, cookie_data, 'new_login')
            else:
                return {
                    'success': False,
                    'message': login_result['message'],
                    'next_step': '请检查账号密码或选择其他认证方式'
                }
        
        else:
            # 没有Cookie且未提供账号密码
            return {
                'success': False,
                'message': f'未找到 {site_name} 的Cookie信息',
                'next_step': '请先在浏览器中登录PT站点，或使用账号密码登录',
                'requires_credentials': True,
                'plugin_installed': True
            }
    
    async def _auth_without_plugin(self, site_name: str, site_domain: str, username: str = None, password: str = None, plugin_status: Dict[str, Any]) -> Dict[str, Any]:
        """插件未安装时的认证方案"""
        # 如果提供了账号密码，直接使用账号密码认证
        if username and password:
            login_result = await self._simulate_pt_login(site_name, username, password)
            
            if login_result['success']:
                cookie_data = login_result.get('cookies', {})
                
                # 保存Cookie到安全存储（即使没有CookieCloud）
                self.sensitive_data_manager.store_pt_cookies(site_name, cookie_data)
                
                # 创建用户会话
                self.user_sessions[site_name] = {
                    'auth_type': 'username_password',
                    'auth_time': datetime.now(),
                    'last_used': datetime.now(),
                    'status': 'authenticated',
                    'username': username,
                    'auth_source': 'direct_login'
                }
                
                logger.info("账号密码认证成功（无插件）", site_name=site_name)
                
                return {
                    'success': True,
                    'message': f'{site_name} 认证成功！',
                    'next_step': '开始使用PT功能',
                    'auth_type': 'username_password',
                    'plugin_installation_recommended': True,
                    'installation_guide': self._get_plugin_installation_guide()
                }
            else:
                return {
                    'success': False,
                    'message': login_result['message'],
                    'next_step': '请检查账号密码',
                    'plugin_installation_recommended': True
                }
        
        else:
            # 未提供账号密码，建议安装插件或使用其他方式
            return {
                'success': False,
                'message': 'CookieCloud插件未安装',
                'next_step': '请安装CookieCloud插件或使用账号密码登录',
                'requires_plugin_installation': True,
                'plugin_status': plugin_status,
                'alternative_methods': [
                    {
                        'name': '安装CookieCloud插件',
                        'description': '安装后认证更便捷',
                        'steps': self._get_plugin_installation_guide()
                    },
                    {
                        'name': '使用账号密码登录',
                        'description': '直接输入账号密码',
                        'requires_credentials': True
                    }
                ]
            }
    
    async def _complete_builtin_auth(self, site_name: str, cookie_data: Dict[str, str], auth_source: str) -> Dict[str, Any]:
        """完成内置CookieCloud认证"""
        # 保存Cookie到安全存储
        self.sensitive_data_manager.store_pt_cookies(site_name, cookie_data)
        
        # 创建用户会话
        self.user_sessions[site_name] = {
            'auth_type': 'builtin_cookiecloud',
            'auth_time': datetime.now(),
            'last_used': datetime.now(),
            'status': 'authenticated',
            'auth_source': auth_source
        }
        
        logger.info("内置CookieCloud认证成功", site_name=site_name, auth_source=auth_source)
        
        return {
            'success': True,
            'message': f'{site_name} 内置CookieCloud认证成功！',
            'next_step': '开始使用PT功能',
            'cookie_count': len(cookie_data),
            'auth_source': auth_source
        }
    
    def _get_site_domain(self, site_name: str) -> Optional[str]:
        """获取PT站点的域名"""
        domain_mapping = {
            'mteam': 'm-team.cc',
            'hdchina': 'hdchina.org', 
            'ttg': 'totheglory.im',
            'chdbits': 'chdbits.co',
            'hdbits': 'hdbits.org'
        }
        return domain_mapping.get(site_name)
    
    async def _get_cookie_from_builtin_service(self, domain: str) -> Optional[Dict[str, str]]:
        """从内置CookieCloud服务获取Cookie"""
        try:
            # 使用默认的内置CookieCloud客户端
            default_client = 'vabhub_builtin'
            
            # 如果默认客户端不存在，尝试创建
            if default_client not in cookiecloud_manager.clients:
                # 这里应该使用系统内置的CookieCloud配置
                builtin_config = self._get_builtin_cookiecloud_config()
                if builtin_config:
                    success, message = await cookiecloud_manager.create_client(
                        default_client, 
                        builtin_config['server'],
                        builtin_config['key'], 
                        builtin_config['password']
                    )
                    if not success:
                        logger.warning("创建内置CookieCloud客户端失败", error=message)
                        return None
            
            # 同步Cookie数据
            success, message, cookies_data = await cookiecloud_manager.sync_cookies(default_client)
            
            if success and cookies_data:
                # 查找匹配域名的Cookie
                for cookie_domain, cookie_info in cookies_data.items():
                    if domain in cookie_domain:
                        return cookie_info
            
            return None
            
        except Exception as e:
            logger.error("从内置CookieCloud服务获取Cookie失败", domain=domain, error=str(e))
            return None
    
    async def _save_cookie_to_builtin_service(self, domain: str, cookie_data: Dict[str, str]) -> bool:
        """保存Cookie到内置CookieCloud服务"""
        try:
            # 使用默认的内置CookieCloud客户端
            default_client = 'vabhub_builtin'
            
            # 如果默认客户端不存在，尝试创建
            if default_client not in cookiecloud_manager.clients:
                builtin_config = self._get_builtin_cookiecloud_config()
                if builtin_config:
                    success, message = await cookiecloud_manager.create_client(
                        default_client, 
                        builtin_config['server'],
                        builtin_config['key'], 
                        builtin_config['password']
                    )
                    if not success:
                        logger.warning("创建内置CookieCloud客户端失败", error=message)
                        return False
            
            # 保存Cookie到CookieCloud
            success, message = await cookiecloud_manager.update_cookies(
                default_client, 
                domain, 
                cookie_data
            )
            
            if success:
                logger.info("Cookie保存到内置CookieCloud成功", domain=domain)
                return True
            else:
                logger.warning("Cookie保存到内置CookieCloud失败", domain=domain, error=message)
                return False
                
        except Exception as e:
            logger.error("保存Cookie到内置CookieCloud服务失败", domain=domain, error=str(e))
            return False
    
    def _get_builtin_cookiecloud_config(self) -> Optional[Dict[str, str]]:
        """获取内置CookieCloud配置"""
        # 这里应该从系统配置中读取内置CookieCloud的设置
        # 暂时返回默认配置
        return {
            'server': 'http://localhost:8088',  # 内置CookieCloud服务地址
            'key': 'vabhub_builtin_user',
            'password': 'vabhub_default_password'
        }
    
    def _get_plugin_installation_guide(self) -> Dict[str, Any]:
        """获取插件安装指南"""
        return {
            'title': 'CookieCloud插件安装指南',
            'description': '安装插件后认证体验更佳，支持一键认证',
            'browsers': [
                {
                    'name': 'Chrome/Edge',
                    'url': 'https://chrome.google.com/webstore/detail/cookiecloud',
                    'steps': [
                        '打开Chrome网上应用店',
                        '搜索"CookieCloud"',
                        '点击"添加至Chrome"',
                        '按照提示完成安装',
                        '重启浏览器生效'
                    ],
                    'icon': 'chrome'
                },
                {
                    'name': 'Firefox',
                    'url': 'https://addons.mozilla.org/firefox/addon/cookiecloud',
                    'steps': [
                        '打开Firefox附加组件页面',
                        '搜索"CookieCloud"',
                        '点击"添加到Firefox"',
                        '按照提示完成安装',
                        '重启浏览器生效'
                    ],
                    'icon': 'firefox'
                }
            ],
            'benefits': [
                '一键同步浏览器Cookie',
                '支持多设备同步',
                '无需重复输入账号密码',
                '加密存储保证安全'
            ],
            'estimated_time': '3分钟'
        }
    
    async def _simulate_pt_login(self, site_name: str, username: str, password: str) -> Dict[str, Any]:
        """模拟PT站点登录（实际实现需要HTTP请求）"""
        try:
            # 这里应该是实际的HTTP登录请求
            # 暂时模拟成功登录
            
            # 模拟网络延迟
            await asyncio.sleep(1)
            
            # 简单的账号密码验证（实际应该发送到PT站点）
            if len(username) < 3 or len(password) < 6:
                return {
                    'success': False,
                    'message': '账号或密码格式不正确'
                }
            
            # 模拟登录成功
            return {
                'success': True,
                'message': '登录成功',
                'cookies': {
                    'session_id': f'simulated_session_{int(time.time())}',
                    'user_token': f'simulated_token_{username}'
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'登录过程出错：{str(e)}'
            }
    
    def get_auth_guide(self) -> Dict[str, Any]:
        """获取认证指导信息"""
        return {
            'title': '初级用户PT认证指南',
            'description': '为不同技术水平的用户提供多种认证方案',
            'steps': self.guide_steps,
            'recommended_method': '智能CookieCloud认证',
            'estimated_time': '2-10分钟',
            'difficulty': '简单',
            'plugin_installation_guide': {
                'title': 'CookieCloud插件安装指南',
                'description': '安装插件后认证体验更佳',
                'browsers': [
                    {
                        'name': 'Chrome/Edge',
                        'url': 'https://chrome.google.com/webstore/detail/cookiecloud',
                        'steps': [
                            '打开Chrome网上应用店',
                            '搜索"CookieCloud"',
                            '点击"添加至Chrome"',
                            '按照提示完成安装'
                        ]
                    },
                    {
                        'name': 'Firefox',
                        'url': 'https://addons.mozilla.org/firefox/addon/cookiecloud',
                        'steps': [
                            '打开Firefox附加组件页面',
                            '搜索"CookieCloud"',
                            '点击"添加到Firefox"',
                            '按照提示完成安装'
                        ]
                    }
                ]
            },
            'alternative_methods': {
                'title': '备选认证方案',
                'description': '无需安装插件也能完成认证',
                'methods': [
                    {
                        'name': '账号密码登录',
                        'description': '直接输入账号密码进行认证',
                        'difficulty': '简单',
                        'steps': 3
                    },
                    {
                        'name': '手动Cookie输入',
                        'description': '从浏览器复制Cookie信息',
                        'difficulty': '中等',
                        'steps': 5
                    }
                ]
            }
        }
    
    def get_supported_pt_sites(self) -> List[Dict[str, str]]:
        """获取支持的PT站点列表"""
        return [
            {
                'name': 'M-Team',
                'code': 'mteam',
                'base_url': 'https://tp.m-team.cc',
                'difficulty': '中等',
                'recommended': True
            },
            {
                'name': 'HDChina',
                'code': 'hdchina',
                'base_url': 'https://hdchina.org',
                'difficulty': '简单',
                'recommended': True
            },
            {
                'name': 'TTG',
                'code': 'ttg',
                'base_url': 'https://totheglory.im',
                'difficulty': '中等',
                'recommended': False
            },
            {
                'name': 'CHDBits',
                'code': 'chdbits',
                'base_url': 'https://chdbits.co',
                'difficulty': '困难',
                'recommended': False
            }
        ]
    
    def get_user_session_status(self, site_name: str) -> Dict[str, Any]:
        """获取用户会话状态"""
        if site_name in self.user_sessions:
            session = self.user_sessions[site_name]
            return {
                'is_authenticated': True,
                'auth_type': session['auth_type'],
                'auth_time': session['auth_time'].isoformat(),
                'last_used': session['last_used'].isoformat(),
                'status': session['status'],
                'auth_source': session.get('auth_source', 'unknown'),
                'username': session.get('username', ''),
                'features_available': self._get_available_features(session)
            }
        else:
            return {
                'is_authenticated': False,
                'auth_type': 'none',
                'auth_time': None,
                'last_used': None,
                'status': 'unauthenticated',
                'auth_source': 'none',
                'username': '',
                'features_available': self._get_available_features(None)
            }
    
    async def validate_session(self, site_name: str) -> bool:
        """验证会话有效性"""
        try:
            if site_name not in self.user_sessions:
                return False
            
            session = self.user_sessions[site_name]
            
            # 检查会话是否过期（24小时）
            if datetime.now() - session['last_used'] > timedelta(hours=24):
                session['status'] = 'expired'
                return False
            
            # 更新最后使用时间
            session['last_used'] = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error("验证会话失败", site_name=site_name, error=str(e))
            return False
    
    def get_troubleshooting_guide(self) -> Dict[str, Any]:
        """获取故障排除指南"""
        return {
            'common_issues': [
                {
                    'issue': '认证失败',
                    'solution': '检查账号密码是否正确，确保网络连接正常',
                    'priority': '高'
                },
                {
                    'issue': '无法连接到PT站点',
                    'solution': '检查网络设置，尝试使用代理或VPN',
                    'priority': '高'
                },
                {
                    'issue': 'Cookie格式错误',
                    'solution': '确保Cookie格式正确，参考浏览器开发者工具',
                    'priority': '中'
                },
                {
                    'issue': '会话过期',
                    'solution': '重新登录或刷新会话',
                    'priority': '低'
                }
            ],
            'contact_support': {
                'email': 'support@vabhub.org',
                'documentation': 'https://docs.vabhub.org/beginner-guide',
                'community': 'https://community.vabhub.org'
            }
        }
    
    def _get_available_features(self, session: Optional[Dict[str, Any]]) -> Dict[str, bool]:
        """获取可用功能列表"""
        if not session or session.get('status') != 'authenticated':
            # 未认证用户的功能限制（类似MoviePilot的限制机制）
            return {
                'plugin_management': False,      # 插件管理
                'subscription_management': False, # 订阅管理
                'search_function': False,        # 搜索功能
                'download_management': False,    # 下载管理
                'site_browsing': False,          # 站点浏览
                'torrent_download': False,       # 种子下载
                'auto_download': False,          # 自动下载
                'notification_system': False,    # 通知系统
                'basic_info': True,              # 基本信息（始终可用）
                'auth_management': True          # 认证管理（始终可用）
            }
        else:
            # 已认证用户的完整功能
            return {
                'plugin_management': True,
                'subscription_management': True,
                'search_function': True,
                'download_management': True,
                'site_browsing': True,
                'torrent_download': True,
                'auto_download': True,
                'notification_system': True,
                'basic_info': True,
                'auth_management': True
            }
    
    def check_feature_access(self, site_name: str, feature: str) -> Dict[str, Any]:
        """检查特定功能访问权限（类似MoviePilot的认证限制）"""
        try:
            # 验证会话有效性
            if not self.validate_session(site_name):
                return {
                    'has_access': False,
                    'message': '会话已过期或未认证',
                    'required_action': '重新认证',
                    'features_available': self._get_available_features(None),
                    'restricted_features': ['插件管理', '订阅管理', '搜索功能', '下载管理']
                }
            
            session = self.user_sessions[site_name]
            features = self._get_available_features(session)
            
            if feature not in features:
                return {
                    'has_access': False,
                    'message': f'未知功能: {feature}',
                    'required_action': '联系管理员',
                    'features_available': features
                }
            
            if not features[feature]:
                return {
                    'has_access': False,
                    'message': f'功能受限: {feature}（需要完成PT站点认证）',
                    'required_action': '完成PT站点认证',
                    'features_available': features,
                    'restricted_features': self._get_restricted_features(features)
                }
            
            return {
                'has_access': True,
                'message': '功能可用',
                'features_available': features
            }
            
        except Exception as e:
            logger.error("检查功能访问权限失败", site_name=site_name, feature=feature, error=str(e))
            return {
                'has_access': False,
                'message': f'检查失败: {str(e)}',
                'required_action': '重新认证',
                'features_available': self._get_available_features(None)
            }
    
    def _get_restricted_features(self, features: Dict[str, bool]) -> List[str]:
        """获取受限功能列表"""
        restricted = []
        feature_names = {
            'plugin_management': '插件管理',
            'subscription_management': '订阅管理', 
            'search_function': '搜索功能',
            'download_management': '下载管理',
            'site_browsing': '站点浏览',
            'torrent_download': '种子下载',
            'auto_download': '自动下载',
            'notification_system': '通知系统'
        }
        
        for feature_key, feature_name in feature_names.items():
            if not features.get(feature_key, False):
                restricted.append(feature_name)
        
        return restricted
    
    def get_feature_restrictions_info(self, site_name: str) -> Dict[str, Any]:
        """获取功能限制信息（类似MoviePilot的提示）"""
        status = self.get_user_session_status(site_name)
        features = status['features_available']
        
        if status['is_authenticated']:
            return {
                'is_authenticated': True,
                'message': '认证已完成，所有功能可用',
                'available_features': [name for name, available in features.items() if available],
                'restricted_features': [],
                'next_steps': ['开始使用PT功能']
            }
        else:
            restricted = self._get_restricted_features(features)
            return {
                'is_authenticated': False,
                'message': '未完成PT站点认证，部分功能受限',
                'available_features': [name for name, available in features.items() if available],
                'restricted_features': restricted,
                'next_steps': [
                    '完成PT站点认证以解锁全部功能',
                    '认证后可使用的功能：' + ', '.join(restricted)
                ]
            }
    
    def get_user_auth_status(self, user_id: str) -> Dict[str, Any]:
        """获取用户认证状态（类似MoviePilot的用户菜单状态）"""
        try:
            if user_id not in self.user_auth_status:
                # 新用户，初始化认证状态
                self.user_auth_status[user_id] = {
                    'is_authenticated': False,
                    'auth_sites': [],
                    'last_auth_time': None,
                    'auth_required': True,
                    'show_auth_menu': True  # 显示认证入口
                }
            
            status = self.user_auth_status[user_id]
            
            # 检查是否有活跃的认证会话
            active_sessions = [site for site in status.get('auth_sites', []) 
                             if self.validate_session(site)]
            
            if active_sessions:
                status['is_authenticated'] = True
                status['auth_required'] = False
                status['show_auth_menu'] = False  # 认证后隐藏认证入口
            else:
                status['is_authenticated'] = False
                status['auth_required'] = True
                status['show_auth_menu'] = True  # 未认证显示认证入口
            
            return status
            
        except Exception as e:
            logger.error("获取用户认证状态失败", user_id=user_id, error=str(e))
            return {
                'is_authenticated': False,
                'auth_sites': [],
                'last_auth_time': None,
                'auth_required': True,
                'show_auth_menu': True,
                'error': str(e)
            }
    
    async def complete_user_auth(self, user_id: str, site_name: str, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """完成用户认证（类似MoviePilot的认证流程）"""
        try:
            # 执行认证
            auth_result = await self.smart_cookiecloud_auth(
                site_name, 
                auth_data.get('username'), 
                auth_data.get('password')
            )
            
            if auth_result['success']:
                # 更新用户认证状态
                if user_id not in self.user_auth_status:
                    self.user_auth_status[user_id] = {
                        'is_authenticated': True,
                        'auth_sites': [site_name],
                        'last_auth_time': datetime.now().isoformat(),
                        'auth_required': False,
                        'show_auth_menu': False
                    }
                else:
                    self.user_auth_status[user_id].update({
                        'is_authenticated': True,
                        'auth_sites': list(set(self.user_auth_status[user_id].get('auth_sites', []) + [site_name])),
                        'last_auth_time': datetime.now().isoformat(),
                        'auth_required': False,
                        'show_auth_menu': False
                    })
                
                # 记录认证历史
                if user_id not in self.auth_histories:
                    self.auth_histories[user_id] = []
                
                self.auth_histories[user_id].append({
                    'site_name': site_name,
                    'auth_time': datetime.now().isoformat(),
                    'auth_type': auth_data.get('auth_type', 'smart_cookiecloud'),
                    'success': True
                })
                
                logger.info("用户认证完成", user_id=user_id, site_name=site_name)
                
                return {
                    'success': True,
                    'message': f'{site_name} 认证成功！',
                    'requires_relogin': True,  # 需要重新登录
                    'auth_completed': True,
                    'user_status': self.user_auth_status[user_id]
                }
            else:
                # 认证失败
                logger.warning("用户认证失败", user_id=user_id, site_name=site_name, error=auth_result['message'])
                
                return {
                    'success': False,
                    'message': auth_result['message'],
                    'requires_relogin': False,
                    'auth_completed': False,
                    'error_details': auth_result
                }
            
        except Exception as e:
            logger.error("完成用户认证失败", user_id=user_id, site_name=site_name, error=str(e))
            return {
                'success': False,
                'message': f'认证过程中出现错误：{str(e)}',
                'requires_relogin': False,
                'auth_completed': False,
                'error': str(e)
            }
    
    def get_available_auth_sites(self) -> List[Dict[str, Any]]:
        """获取可用的认证站点列表（类似MoviePilot的认证弹窗）"""
        supported_sites = self.get_supported_pt_sites()
        
        auth_sites = []
        for site_code, site_info in supported_sites.items():
            auth_sites.append({
                'site_code': site_code,
                'site_name': site_info['name'],
                'description': site_info.get('description', ''),
                'auth_methods': ['smart_cookiecloud', 'username_password', 'manual_cookie'],
                'recommended_method': 'smart_cookiecloud',
                'difficulty': site_info.get('difficulty', '中等'),
                'icon': site_info.get('icon', '🌐')
            })
        
        return auth_sites
    
    def clear_user_auth_status(self, user_id: str) -> bool:
        """清除用户认证状态（用于重新登录）"""
        try:
            if user_id in self.user_auth_status:
                # 保留认证历史，清除当前状态
                self.user_auth_status[user_id] = {
                    'is_authenticated': False,
                    'auth_sites': [],
                    'last_auth_time': None,
                    'auth_required': True,
                    'show_auth_menu': True
                }
                
                # 清除用户会话
                for site_name in list(self.user_sessions.keys()):
                    if site_name.startswith(f"{user_id}_"):
                        del self.user_sessions[site_name]
                
                logger.info("用户认证状态已清除", user_id=user_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("清除用户认证状态失败", user_id=user_id, error=str(e))
            return False


# 全局初级认证助手实例
beginner_auth_helper = BeginnerPTAuthHelper()