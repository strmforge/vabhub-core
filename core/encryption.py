#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 数据加密系统
提供敏感数据加密存储功能，保护API密钥、密码等敏感信息
"""

import base64
import os
import json
from typing import Any, Dict, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import structlog

logger = structlog.get_logger()


class DataEncryptor:
    """数据加密器"""
    
    def __init__(self, password: Optional[str] = None):
        """
        初始化加密器
        
        Args:
            password: 加密密码，如果为None则使用环境变量或默认密码
        """
        self.password = password or os.getenv('VABHUB_ENCRYPTION_PASSWORD', 'vabhub_default_key')
        self.salt = os.urandom(16)
        self.fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """创建Fernet加密器"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
        return Fernet(key)
    
    def encrypt_data(self, data: Union[str, Dict, list]) -> str:
        """加密数据"""
        try:
            if isinstance(data, (dict, list)):
                data_str = json.dumps(data, ensure_ascii=False)
            else:
                data_str = str(data)
            
            encrypted_data = self.fernet.encrypt(data_str.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error("数据加密失败", error=str(e))
            raise
    
    def decrypt_data(self, encrypted_data: str) -> Union[str, Dict, list]:
        """解密数据"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            decrypted_str = decrypted_bytes.decode()
            
            # 尝试解析为JSON
            try:
                return json.loads(decrypted_str)
            except json.JSONDecodeError:
                return decrypted_str
        except Exception as e:
            logger.error("数据解密失败", error=str(e))
            raise


class SensitiveDataManager:
    """敏感数据管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化敏感数据管理器
        
        Args:
            config_file: 敏感数据配置文件路径
        """
        self.config_file = config_file or os.path.join(
            os.path.expanduser('~'), '.vabhub', 'sensitive_data.json'
        )
        self.encryptor = DataEncryptor()
        self.sensitive_data = {}
        self._ensure_config_dir()
        self._load_sensitive_data()
    
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        config_dir = os.path.dirname(self.config_file)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, mode=0o700)
    
    def _load_sensitive_data(self):
        """加载敏感数据"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    encrypted_data = json.load(f)
                
                # 解密数据
                for key, encrypted_value in encrypted_data.items():
                    self.sensitive_data[key] = self.encryptor.decrypt_data(encrypted_value)
                
                logger.info("敏感数据加载成功", count=len(self.sensitive_data))
            except Exception as e:
                logger.error("加载敏感数据失败", error=str(e))
    
    def save_sensitive_data(self):
        """保存敏感数据"""
        try:
            encrypted_data = {}
            for key, value in self.sensitive_data.items():
                encrypted_data[key] = self.encryptor.encrypt_data(value)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(encrypted_data, f, ensure_ascii=False, indent=2)
            
            # 设置文件权限为600
            os.chmod(self.config_file, 0o600)
            
            logger.info("敏感数据保存成功", count=len(self.sensitive_data))
        except Exception as e:
            logger.error("保存敏感数据失败", error=str(e))
    
    def store_api_key(self, service_name: str, api_key: str, api_secret: Optional[str] = None):
        """存储API密钥"""
        key_data = {'api_key': api_key}
        if api_secret:
            key_data['api_secret'] = api_secret
        
        self.sensitive_data[f'{service_name}_api'] = key_data
        self.save_sensitive_data()
    
    def get_api_key(self, service_name: str) -> Optional[Dict[str, str]]:
        """获取API密钥"""
        return self.sensitive_data.get(f'{service_name}_api')
    
    def store_pt_cookies(self, site_name: str, cookies: Dict[str, str]):
        """存储PT站点Cookie"""
        self.sensitive_data[f'{site_name}_cookies'] = cookies
        self.save_sensitive_data()
    
    def get_pt_cookies(self, site_name: str) -> Optional[Dict[str, str]]:
        """获取PT站点Cookie"""
        return self.sensitive_data.get(f'{site_name}_cookies')
    
    def store_database_password(self, db_name: str, password: str):
        """存储数据库密码"""
        self.sensitive_data[f'{db_name}_password'] = password
        self.save_sensitive_data()
    
    def get_database_password(self, db_name: str) -> Optional[str]:
        """获取数据库密码"""
        return self.sensitive_data.get(f'{db_name}_password')
    
    def clear_sensitive_data(self):
        """清除所有敏感数据"""
        self.sensitive_data.clear()
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        logger.info("敏感数据已清除")


# 全局敏感数据管理器实例
sensitive_data_manager = SensitiveDataManager()


def encrypt_sensitive_field(data: Dict[str, Any], fields_to_encrypt: list) -> Dict[str, Any]:
    """加密敏感字段"""
    encryptor = DataEncryptor()
    encrypted_data = data.copy()
    
    for field in fields_to_encrypt:
        if field in encrypted_data and encrypted_data[field]:
            encrypted_data[field] = encryptor.encrypt_data(encrypted_data[field])
    
    return encrypted_data


def decrypt_sensitive_field(data: Dict[str, Any], fields_to_decrypt: list) -> Dict[str, Any]:
    """解密敏感字段"""
    encryptor = DataEncryptor()
    decrypted_data = data.copy()
    
    for field in fields_to_decrypt:
        if field in decrypted_data and decrypted_data[field]:
            try:
                decrypted_data[field] = encryptor.decrypt_data(decrypted_data[field])
            except Exception:
                # 如果解密失败，保持原值（可能是未加密的数据）
                pass
    
    return decrypted_data