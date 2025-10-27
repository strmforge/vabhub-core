#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证和授权系统
基于JWT的现代化认证
"""

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


# 全局认证管理器实例
auth_manager = AuthManager()