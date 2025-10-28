#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 访问控制系统
提供基于角色的权限管理，支持细粒度的访问控制
"""

import json
import time
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class PermissionLevel(Enum):
    """权限级别枚举"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class ResourceType(Enum):
    """资源类型枚举"""
    MEDIA = "media"
    DOWNLOAD = "download"
    SUBSCRIPTION = "subscription"
    PLUGIN = "plugin"
    SYSTEM = "system"
    USER = "user"
    SETTINGS = "settings"


@dataclass
class User:
    """用户信息"""
    user_id: str
    username: str
    email: str
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True


@dataclass
class Permission:
    """权限定义"""
    resource_type: ResourceType
    resource_id: Optional[str] = None  # None表示所有资源
    permission_level: PermissionLevel = PermissionLevel.READ
    
    def __str__(self):
        if self.resource_id:
            return f"{self.resource_type.value}:{self.resource_id}:{self.permission_level.value}"
        else:
            return f"{self.resource_type.value}:*:{self.permission_level.value}"


class RoleManager:
    """角色管理器"""
    
    def __init__(self):
        self.roles = {
            'admin': {
                'description': '系统管理员',
                'permissions': [
                    Permission(ResourceType.SYSTEM, permission_level=PermissionLevel.ADMIN),
                    Permission(ResourceType.USER, permission_level=PermissionLevel.ADMIN),
                    Permission(ResourceType.SETTINGS, permission_level=PermissionLevel.ADMIN),
                    Permission(ResourceType.MEDIA, permission_level=PermissionLevel.WRITE),
                    Permission(ResourceType.DOWNLOAD, permission_level=PermissionLevel.WRITE),
                    Permission(ResourceType.SUBSCRIPTION, permission_level=PermissionLevel.WRITE),
                    Permission(ResourceType.PLUGIN, permission_level=PermissionLevel.WRITE),
                ]
            },
            'user': {
                'description': '普通用户',
                'permissions': [
                    Permission(ResourceType.MEDIA, permission_level=PermissionLevel.READ),
                    Permission(ResourceType.DOWNLOAD, permission_level=PermissionLevel.READ),
                    Permission(ResourceType.SUBSCRIPTION, permission_level=PermissionLevel.READ),
                ]
            },
            'guest': {
                'description': '访客',
                'permissions': [
                    Permission(ResourceType.MEDIA, permission_level=PermissionLevel.READ),
                ]
            }
        }
    
    def get_role_permissions(self, role: str) -> List[Permission]:
        """获取角色权限"""
        if role in self.roles:
            return self.roles[role]['permissions']
        return []
    
    def add_role(self, role_name: str, description: str, permissions: List[Permission]):
        """添加自定义角色"""
        self.roles[role_name] = {
            'description': description,
            'permissions': permissions
        }
    
    def list_roles(self) -> Dict[str, str]:
        """列出所有角色"""
        return {role: info['description'] for role, info in self.roles.items()}


class AccessControlManager:
    """访问控制管理器"""
    
    def __init__(self):
        self.role_manager = RoleManager()
        self.users: Dict[str, User] = {}
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = timedelta(hours=24)  # 会话超时时间
    
    def create_user(self, username: str, email: str, role: str = 'user') -> User:
        """创建用户"""
        user_id = f"user_{int(time.time())}_{len(self.users)}"
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            created_at=datetime.now()
        )
        self.users[user_id] = user
        logger.info("用户创建成功", user_id=user_id, username=username, role=role)
        return user
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证（简化版，实际应使用密码哈希）"""
        for user in self.users.values():
            if user.username == username and user.is_active:
                # 简化认证，实际应使用密码哈希验证
                user.last_login = datetime.now()
                return user
        return None
    
    def create_session(self, user: User) -> str:
        """创建用户会话"""
        session_id = f"session_{int(time.time())}_{len(self.user_sessions)}"
        self.user_sessions[session_id] = {
            'user_id': user.user_id,
            'username': user.username,
            'role': user.role,
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        logger.info("用户会话创建成功", session_id=session_id, username=user.username)
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """验证会话有效性"""
        if session_id in self.user_sessions:
            session = self.user_sessions[session_id]
            
            # 检查会话超时
            if datetime.now() - session['last_activity'] > self.session_timeout:
                del self.user_sessions[session_id]
                logger.info("会话已超时", session_id=session_id)
                return None
            
            # 更新最后活动时间
            session['last_activity'] = datetime.now()
            return session
        return None
    
    def check_permission(self, session_id: str, resource_type: ResourceType, 
                        action: PermissionLevel, resource_id: Optional[str] = None) -> bool:
        """检查权限"""
        session = self.validate_session(session_id)
        if not session:
            return False
        
        user_role = session['role']
        permissions = self.role_manager.get_role_permissions(user_role)
        
        for permission in permissions:
            # 检查资源类型匹配
            if permission.resource_type != resource_type:
                continue
            
            # 检查资源ID匹配（如果指定了资源ID）
            if permission.resource_id and permission.resource_id != resource_id:
                continue
            
            # 检查权限级别
            if self._check_permission_level(permission.permission_level, action):
                return True
        
        logger.warning("权限检查失败", 
                      username=session['username'], 
                      resource_type=resource_type.value,
                      action=action.value)
        return False
    
    def _check_permission_level(self, user_level: PermissionLevel, required_level: PermissionLevel) -> bool:
        """检查权限级别"""
        level_hierarchy = {
            PermissionLevel.READ: 1,
            PermissionLevel.WRITE: 2,
            PermissionLevel.DELETE: 3,
            PermissionLevel.ADMIN: 4
        }
        
        user_level_value = level_hierarchy.get(user_level, 0)
        required_level_value = level_hierarchy.get(required_level, 0)
        
        return user_level_value >= required_level_value
    
    def get_user_permissions(self, session_id: str) -> List[str]:
        """获取用户所有权限"""
        session = self.validate_session(session_id)
        if not session:
            return []
        
        user_role = session['role']
        permissions = self.role_manager.get_role_permissions(user_role)
        return [str(perm) for perm in permissions]
    
    def logout(self, session_id: str) -> bool:
        """用户登出"""
        if session_id in self.user_sessions:
            username = self.user_sessions[session_id]['username']
            del self.user_sessions[session_id]
            logger.info("用户登出成功", session_id=session_id, username=username)
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.user_sessions.items():
            if current_time - session['last_activity'] > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.user_sessions[session_id]
        
        if expired_sessions:
            logger.info("清理过期会话", count=len(expired_sessions))


# 全局访问控制管理器实例
access_control_manager = AccessControlManager()


def require_permission(resource_type: ResourceType, action: PermissionLevel, 
                      resource_id: Optional[str] = None):
    """权限检查装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 从请求中获取会话ID（这里需要根据实际框架调整）
            session_id = kwargs.get('session_id') or args[0].headers.get('X-Session-ID')
            
            if not session_id:
                raise PermissionError("未提供会话ID")
            
            if not access_control_manager.check_permission(session_id, resource_type, action, resource_id):
                raise PermissionError(f"权限不足: {resource_type.value}:{action.value}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def create_default_users():
    """创建默认用户"""
    # 创建管理员用户
    admin_user = access_control_manager.create_user(
        username="admin",
        email="admin@vabhub.com",
        role="admin"
    )
    
    # 创建普通用户
    user_user = access_control_manager.create_user(
        username="user",
        email="user@vabhub.com",
        role="user"
    )
    
    logger.info("默认用户创建完成")


# 初始化时创建默认用户
create_default_users()