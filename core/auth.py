#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证和授权系统
基于JWT的现代化认证，参照MoviePilot V2安全标准
支持API_TOKEN强度检查（≥16位复杂串）
"""

import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from core.config import settings
import structlog

logger = structlog.get_logger()

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token数据模型"""
    username: str
    expires: Optional[datetime] = None


class User(BaseModel):
    """用户模型"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    permissions: list = []


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.min_api_token_length = 16  # MoviePilot V2标准：≥16位复杂串
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            if username is None:
                return None
            
            expires = payload.get("exp")
            if expires:
                expires = datetime.fromtimestamp(expires)
            
            return TokenData(username=username, expires=expires)
        except JWTError:
            return None
    
    def get_current_user(self, token: str) -> Optional[User]:
        """获取当前用户"""
        token_data = self.verify_token(token)
        if token_data is None:
            return None
        
        # 这里可以从数据库获取用户信息
        # 暂时返回模拟用户
        return User(
            username=token_data.username,
            email=f"{token_data.username}@example.com",
            full_name=token_data.username.title(),
            permissions=["read", "write", "admin"]
        )
    
    def validate_api_token_strength(self, api_token: str) -> bool:
        """验证API_TOKEN强度（MoviePilot V2标准）"""
        if len(api_token) < self.min_api_token_length:
            logger.warning(f"API_TOKEN长度不足{self.min_api_token_length}位")
            return False
        
        # 检查复杂度：至少包含大写字母、小写字母、数字、特殊字符中的三种
        has_upper = bool(re.search(r'[A-Z]', api_token))
        has_lower = bool(re.search(r'[a-z]', api_token))
        has_digit = bool(re.search(r'\d', api_token))
        has_special = bool(re.search(r'[^A-Za-z0-9]', api_token))
        
        complexity_score = sum([has_upper, has_lower, has_digit, has_special])
        
        if complexity_score < 3:
            logger.warning("API_TOKEN复杂度不足，需要至少包含大写字母、小写字母、数字、特殊字符中的三种")
            return False
        
        logger.info("API_TOKEN强度验证通过")
        return True
    
    def generate_secure_api_token(self) -> str:
        """生成安全的API_TOKEN（MoviePilot V2标准）"""
        # 生成32位随机字符串
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            token = ''.join(secrets.choice(alphabet) for _ in range(32))
            if self.validate_api_token_strength(token):
                return token
    
    def reset_insecure_api_token(self) -> str:
        """重置不安全的API_TOKEN（MoviePilot V2策略）"""
        logger.warning("检测到不安全的API_TOKEN，正在自动重置...")
        new_token = self.generate_secure_api_token()
        logger.info(f"已生成新的安全API_TOKEN: {new_token[:8]}...")
        return new_token


# 全局认证管理器实例
auth_manager = AuthManager()