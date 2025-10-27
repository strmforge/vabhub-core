#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版CookieCloud功能
集成MoviePilot的CookieCloud精华功能
"""

import asyncio
import base64
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin

import aiohttp
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

logger = logging.getLogger(__name__)


class CookieCloudEnhanced:
    """增强版CookieCloud客户端"""
    
    def __init__(self, server: str, key: str, password: str):
        self.server = server.rstrip('/')
        self.key = key
        self.password = password
        self.session = None
        self.fernet = None
        
        # 初始化加密器
        self._init_encryption()
    
    def _init_encryption(self):
        """初始化加密器"""
        # 使用PBKDF2从密码生成密钥
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'cookiecloud',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
        self.fernet = Fernet(key)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def download_data(self) -> Tuple[Optional[Dict], str]:
        """
        从CookieCloud下载数据
        :return: (Cookie数据, 错误信息)
        """
        try:
            if not all([self.server, self.key, self.password]):
                return None, "CookieCloud参数不完整"
            
            url = f"{self.server}/get/{self.key}"
            
            async with self.session.post(url, json={"password": self.password}) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('encrypted'):
                        # 解密数据
                        encrypted_data = data.get('data', '')
                        decrypted_data = self._decrypt_data(encrypted_data)
                        return decrypted_data, ""
                    else:
                        return data.get('data', {}), ""
                else:
                    return None, f"HTTP错误: {response.status}"
                    
        except aiohttp.ClientError as e:
            logger.error(f"CookieCloud请求失败: {e}")
            return None, f"网络请求失败: {str(e)}"
        except Exception as e:
            logger.error(f"CookieCloud数据处理失败: {e}")
            return None, f"数据处理失败: {str(e)}"
    
    def _decrypt_data(self, encrypted_data: str) -> Dict:
        """解密Cookie数据"""
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_data.encode())
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            logger.error(f"Cookie数据解密失败: {e}")
            return {}
    
    async def upload_data(self, cookies: Dict[str, Any]) -> Tuple[bool, str]:
        """
        上传Cookie数据到CookieCloud
        :param cookies: Cookie数据
        :return: (是否成功, 错误信息)
        """
        try:
            if not all([self.server, self.key, self.password]):
                return False, "CookieCloud参数不完整"
            
            # 加密数据
            encrypted_data = self._encrypt_data(cookies)
            
            url = f"{self.server}/update/{self.key}"
            payload = {
                "password": self.password,
                "data": encrypted_data,
                "encrypted": True
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    return True, ""
                else:
                    return False, f"上传失败: {response.status}"
                    
        except Exception as e:
            logger.error(f"CookieCloud上传失败: {e}")
            return False, f"上传失败: {str(e)}"
    
    def _encrypt_data(self, data: Dict) -> str:
        """加密Cookie数据"""
        json_str = json.dumps(data, ensure_ascii=False)
        encrypted_bytes = self.fernet.encrypt(json_str.encode())
        return encrypted_bytes.decode()
    
    async def get_cookie_for_domain(self, domain: str) -> Optional[Dict]:
        """
        获取指定域名的Cookie
        :param domain: 域名
        :return: Cookie数据
        """
        cookies_data, error = await self.download_data()
        if error:
            logger.error(f"获取Cookie数据失败: {error}")
            return None
        
        # 查找匹配的域名Cookie
        for cookie_domain, cookie_info in cookies_data.items():
            if domain in cookie_domain:
                return cookie_info
        
        return None
    
    def validate_config(self) -> Tuple[bool, str]:
        """验证配置有效性"""
        if not self.server:
            return False, "服务器地址不能为空"
        if not self.key:
            return False, "用户KEY不能为空"
        if not self.password:
            return False, "加密密码不能为空"
        
        # 验证服务器地址格式
        if not (self.server.startswith('http://') or self.server.startswith('https://')):
            return False, "服务器地址格式不正确"
        
        return True, ""


class CookieCloudManager:
    """CookieCloud管理器"""
    
    def __init__(self):
        self.clients: Dict[str, CookieCloudEnhanced] = {}
        self.sync_history: List[Dict] = []
        self.last_sync_time: Optional[float] = None
    
    async def create_client(self, name: str, server: str, key: str, password: str) -> Tuple[bool, str]:
        """创建CookieCloud客户端"""
        client = CookieCloudEnhanced(server, key, password)
        
        # 验证配置
        is_valid, error = client.validate_config()
        if not is_valid:
            return False, error
        
        # 测试连接
        async with client:
            cookies_data, error = await client.download_data()
            if error:
                return False, f"连接测试失败: {error}"
        
        self.clients[name] = client
        logger.info(f"创建CookieCloud客户端: {name}")
        return True, ""
    
    async def sync_cookies(self, client_name: str) -> Tuple[bool, str, Dict]:
        """同步Cookie数据"""
        if client_name not in self.clients:
            return False, "客户端不存在", {}
        
        client = self.clients[client_name]
        
        try:
            async with client:
                cookies_data, error = await client.download_data()
                
                if error:
                    return False, error, {}
                
                # 记录同步历史
                sync_record = {
                    'client': client_name,
                    'timestamp': time.time(),
                    'cookie_count': len(cookies_data),
                    'domains': list(cookies_data.keys())
                }
                self.sync_history.append(sync_record)
                self.last_sync_time = time.time()
                
                logger.info(f"CookieCloud同步成功: {len(cookies_data)}个域名的Cookie")
                return True, "同步成功", cookies_data
                
        except Exception as e:
            logger.error(f"CookieCloud同步失败: {e}")
            return False, str(e), {}
    
    async def get_cookie(self, client_name: str, domain: str) -> Optional[Dict]:
        """获取指定域名的Cookie"""
        if client_name not in self.clients:
            return None
        
        client = self.clients[client_name]
        async with client:
            return await client.get_cookie_for_domain(domain)
    
    def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """获取同步历史"""
        return self.sync_history[-limit:]
    
    def get_client_names(self) -> List[str]:
        """获取所有客户端名称"""
        return list(self.clients.keys())


# 全局CookieCloud管理器实例
cookiecloud_manager = CookieCloudManager()