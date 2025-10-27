"""
多用户认证系统 - 基于JWT的企业级认证框架
支持角色权限管理、用户配置隔离、操作审计日志
"""

import jwt
import time
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"
    GUEST = "guest"

class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE_USERS = "manage_users"
    SYSTEM_ADMIN = "system_admin"

@dataclass
class User:
    """用户信息"""
    user_id: str
    username: str
    email: str
    role: UserRole
    permissions: List[Permission]
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool
    config: Dict[str, Any]  # 用户个性化配置

@dataclass
class AuditLog:
    """审计日志"""
    log_id: str
    user_id: str
    action: str
    resource: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    details: Dict[str, Any]
    status: str  # success, failed

class MultiUserAuth:
    """多用户认证系统"""
    
    def __init__(self, secret_key: str, token_expire_hours: int = 24):
        self.secret_key = secret_key
        self.token_expire_hours = token_expire_hours
        
        # 用户存储（生产环境应该使用数据库）
        self.users: Dict[str, User] = {}
        self.user_configs: Dict[str, Dict[str, Any]] = {}
        
        # 审计日志
        self.audit_logs: List[AuditLog] = []
        self.max_audit_logs = 10000  # 最大审计日志数量
        
        # 角色权限映射
        self.role_permissions = {
            UserRole.ADMIN: [
                Permission.READ, Permission.WRITE, Permission.DELETE,
                Permission.MANAGE_USERS, Permission.SYSTEM_ADMIN
            ],
            UserRole.USER: [Permission.READ, Permission.WRITE],
            UserRole.READONLY: [Permission.READ],
            UserRole.GUEST: []
        }
        
        # 初始化默认管理员用户
        self._create_default_admin()
    
    def _create_default_admin(self):
        """创建默认管理员用户"""
        admin_user = User(
            user_id="admin_001",
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
            permissions=self.role_permissions[UserRole.ADMIN],
            created_at=datetime.now(),
            last_login=None,
            is_active=True,
            config={"theme": "dark", "language": "zh-CN"}
        )
        
        # 设置默认密码（生产环境应该从配置读取）
        self.users[admin_user.user_id] = admin_user
        self.user_configs[admin_user.user_id] = {
            "password_hash": self._hash_password("admin123"),
            "api_keys": {},
            "preferences": admin_user.config
        }
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = secrets.token_hex(16)
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        # 简化实现，生产环境需要更安全的验证
        try:
            salt = password_hash[:32]  # 假设salt是前32字符
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
            return new_hash == password_hash
        except:
            return False
    
    def create_user(self, username: str, email: str, password: str, 
                   role: UserRole = UserRole.USER, config: Dict[str, Any] = None) -> Optional[User]:
        """创建新用户"""
        # 检查用户名是否已存在
        if any(user.username == username for user in self.users.values()):
            logger.warning(f"用户名 {username} 已存在")
            return None
        
        # 生成用户ID
        user_id = f"user_{int(time.time())}_{secrets.token_hex(4)}"
        
        # 创建用户对象
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=self.role_permissions[role],
            created_at=datetime.now(),
            last_login=None,
            is_active=True,
            config=config or {}
        )
        
        # 保存用户信息
        self.users[user_id] = user
        self.user_configs[user_id] = {
            "password_hash": self._hash_password(password),
            "api_keys": {},
            "preferences": user.config
        }
        
        # 记录审计日志
        self._log_audit("system", "user_create", f"user:{user_id}", 
                       {"username": username, "role": role.value})
        
        logger.info(f"用户 {username} 创建成功")
        return user
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """用户认证，返回JWT token"""
        # 查找用户
        user = None
        for u in self.users.values():
            if u.username == username and u.is_active:
                user = u
                break
        
        if not user:
            self._log_audit("unknown", "login_failed", "auth", 
                          {"username": username, "reason": "user_not_found"})
            return None
        
        # 验证密码
        user_config = self.user_configs.get(user.user_id)
        if not user_config or not self._verify_password(password, user_config["password_hash"]):
            self._log_audit(user.user_id, "login_failed", "auth", 
                          {"username": username, "reason": "invalid_password"})
            return None
        
        # 更新最后登录时间
        user.last_login = datetime.now()
        
        # 生成JWT token
        payload = {
            'user_id': user.user_id,
            'username': user.username,
            'role': user.role.value,
            'permissions': [p.value for p in user.permissions],
            'exp': datetime.utcnow() + timedelta(hours=self.token_expire_hours)
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        
        # 记录审计日志
        self._log_audit(user.user_id, "login_success", "auth", {"username": username})
        
        logger.info(f"用户 {username} 登录成功")
        return token
    
    def verify_token(self, token: str) -> Optional[User]:
        """验证JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            if not user_id or user_id not in self.users:
                return None
            
            user = self.users[user_id]
            if not user.is_active:
                return None
            
            return user
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return None
        except jwt.InvalidTokenError:
            logger.warning("无效的Token")
            return None
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """检查用户是否具有指定权限"""
        return permission in user.permissions
    
    def update_user_config(self, user_id: str, config: Dict[str, Any]):
        """更新用户配置"""
        if user_id in self.user_configs:
            self.user_configs[user_id]["preferences"].update(config)
            
            # 同时更新用户对象的配置
            if user_id in self.users:
                self.users[user_id].config.update(config)
            
            self._log_audit(user_id, "config_update", "user_preferences", {"config": config})
    
    def get_user_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户配置"""
        user_config = self.user_configs.get(user_id)
        return user_config.get("preferences") if user_config else None
    
    def _log_audit(self, user_id: str, action: str, resource: str, details: Dict[str, Any]):
        """记录审计日志"""
        log = AuditLog(
            log_id=f"log_{int(time.time())}_{secrets.token_hex(4)}",
            user_id=user_id,
            action=action,
            resource=resource,
            timestamp=datetime.now(),
            ip_address="127.0.0.1",  # 实际应该从请求中获取
            user_agent="system",     # 实际应该从请求中获取
            details=details,
            status="success" if "failed" not in action else "failed"
        )
        
        self.audit_logs.append(log)
        
        # 限制日志数量
        if len(self.audit_logs) > self.max_audit_logs:
            self.audit_logs = self.audit_logs[-self.max_audit_logs:]
    
    def get_audit_logs(self, user_id: str = None, action: str = None, 
                      start_time: datetime = None, end_time: datetime = None) -> List[AuditLog]:
        """获取审计日志"""
        logs = self.audit_logs
        
        if user_id:
            logs = [log for log in logs if log.user_id == user_id]
        if action:
            logs = [log for log in logs if log.action == action]
        if start_time:
            logs = [log for log in logs if log.timestamp >= start_time]
        if end_time:
            logs = [log for log in logs if log.timestamp <= end_time]
        
        return logs
    
    def get_user_stats(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        total_users = len(self.users)
        active_users = len([u for u in self.users.values() if u.is_active])
        admin_users = len([u for u in self.users.values() if u.role == UserRole.ADMIN])
        
        # 最近24小时登录用户
        recent_login_count = len([
            u for u in self.users.values() 
            if u.last_login and (datetime.now() - u.last_login).total_seconds() < 86400
        ])
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "admin_users": admin_users,
            "recent_login_users": recent_login_count,
            "audit_log_count": len(self.audit_logs)
        }