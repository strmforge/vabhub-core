"""
用户权限管理系统
基于现有用户操作记录进行增强，支持多用户和角色权限控制
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import secrets

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    MODERATOR = "moderator"


class Permission(Enum):
    """权限枚举"""
    # 媒体管理权限
    MEDIA_READ = "media:read"
    MEDIA_WRITE = "media:write"
    MEDIA_DELETE = "media:delete"
    
    # 下载管理权限
    DOWNLOAD_READ = "download:read"
    DOWNLOAD_WRITE = "download:write"
    DOWNLOAD_DELETE = "download:delete"
    
    # 订阅管理权限
    SUBSCRIPTION_READ = "subscription:read"
    SUBSCRIPTION_WRITE = "subscription:write"
    SUBSCRIPTION_DELETE = "subscription:delete"
    
    # 插件管理权限
    PLUGIN_READ = "plugin:read"
    PLUGIN_WRITE = "plugin:write"
    PLUGIN_DELETE = "plugin:delete"
    
    # 系统管理权限
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    USER_MANAGE = "user:manage"


@dataclass
class User:
    """用户信息"""
    user_id: str
    username: str
    email: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool
    permissions: List[Permission]
    profile: Dict[str, Any]


@dataclass
class UserSession:
    """用户会话"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str


@dataclass
class AuditLog:
    """审计日志"""
    log_id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    timestamp: datetime
    ip_address: str


class UserManager:
    """用户管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, UserSession] = {}
        self.audit_logs: List[AuditLog] = []
        self.role_permissions: Dict[UserRole, List[Permission]] = {}
        
        # 初始化角色权限映射
        self._initialize_role_permissions()
        
        # 创建默认管理员用户
        self._create_default_admin()
    
    def _initialize_role_permissions(self):
        """初始化角色权限映射"""
        self.role_permissions = {
            UserRole.ADMIN: [
                Permission.MEDIA_READ, Permission.MEDIA_WRITE, Permission.MEDIA_DELETE,
                Permission.DOWNLOAD_READ, Permission.DOWNLOAD_WRITE, Permission.DOWNLOAD_DELETE,
                Permission.SUBSCRIPTION_READ, Permission.SUBSCRIPTION_WRITE, Permission.SUBSCRIPTION_DELETE,
                Permission.PLUGIN_READ, Permission.PLUGIN_WRITE, Permission.PLUGIN_DELETE,
                Permission.SYSTEM_READ, Permission.SYSTEM_WRITE, Permission.USER_MANAGE
            ],
            UserRole.MODERATOR: [
                Permission.MEDIA_READ, Permission.MEDIA_WRITE,
                Permission.DOWNLOAD_READ, Permission.DOWNLOAD_WRITE,
                Permission.SUBSCRIPTION_READ, Permission.SUBSCRIPTION_WRITE,
                Permission.PLUGIN_READ,
                Permission.SYSTEM_READ
            ],
            UserRole.USER: [
                Permission.MEDIA_READ,
                Permission.DOWNLOAD_READ, Permission.DOWNLOAD_WRITE,
                Permission.SUBSCRIPTION_READ,
                Permission.PLUGIN_READ
            ],
            UserRole.GUEST: [
                Permission.MEDIA_READ,
                Permission.DOWNLOAD_READ
            ]
        }
    
    def _create_default_admin(self):
        """创建默认管理员用户"""
        admin_user = User(
            user_id="admin",
            username="admin",
            email="admin@vabhub.org",
            role=UserRole.ADMIN,
            created_at=datetime.now(),
            last_login=None,
            is_active=True,
            permissions=self.role_permissions[UserRole.ADMIN],
            profile={"display_name": "系统管理员"}
        )
        self.users["admin"] = admin_user
        logger.info("创建默认管理员用户")
    
    async def create_user(self, username: str, email: str, password: str, 
                         role: UserRole = UserRole.USER, profile: Dict[str, Any] = None) -> Optional[User]:
        """创建新用户"""
        # 检查用户名是否已存在
        if any(user.username == username for user in self.users.values()):
            logger.warning(f"用户名已存在: {username}")
            return None
        
        # 检查邮箱是否已存在
        if any(user.email == email for user in self.users.values()):
            logger.warning(f"邮箱已存在: {email}")
            return None
        
        # 生成用户ID
        user_id = self._generate_user_id()
        
        # 创建用户
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            created_at=datetime.now(),
            last_login=None,
            is_active=True,
            permissions=self.role_permissions[role],
            profile=profile or {}
        )
        
        # 存储用户（实际应该存储到数据库）
        self.users[user_id] = user
        
        # 记录审计日志
        await self._log_audit(
            user_id="system",
            action="user_create",
            resource_type="user",
            resource_id=user_id,
            details={"username": username, "role": role.value}
        )
        
        logger.info(f"创建用户成功: {username}")
        return user
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        # 查找用户
        user = next((u for u in self.users.values() if u.username == username), None)
        
        if not user:
            logger.warning(f"用户不存在: {username}")
            return None
        
        if not user.is_active:
            logger.warning(f"用户已被禁用: {username}")
            return None
        
        # 这里应该验证密码（简化实现）
        # 实际应该使用安全的密码哈希
        if not self._verify_password(password, user):
            logger.warning(f"密码错误: {username}")
            return None
        
        # 更新最后登录时间
        user.last_login = datetime.now()
        
        # 记录审计日志
        await self._log_audit(
            user_id=user.user_id,
            action="user_login",
            resource_type="user",
            resource_id=user.user_id,
            details={"username": username}
        )
        
        logger.info(f"用户认证成功: {username}")
        return user
    
    async def create_session(self, user: User, ip_address: str, user_agent: str) -> UserSession:
        """创建用户会话"""
        session_id = self._generate_session_id()
        
        session = UserSession(
            session_id=session_id,
            user_id=user.user_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),  # 7天有效期
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.sessions[session_id] = session
        
        logger.info(f"创建用户会话: {user.username}")
        return session
    
    async def validate_session(self, session_id: str) -> Optional[User]:
        """验证会话"""
        session = self.sessions.get(session_id)
        
        if not session:
            return None
        
        if session.expires_at < datetime.now():
            # 会话已过期
            del self.sessions[session_id]
            return None
        
        user = self.users.get(session.user_id)
        if not user or not user.is_active:
            return None
        
        # 更新会话过期时间（滑动过期）
        session.expires_at = datetime.now() + timedelta(days=7)
        
        return user
    
    async def destroy_session(self, session_id: str) -> bool:
        """销毁会话"""
        if session_id in self.sessions:
            user_id = self.sessions[session_id].user_id
            del self.sessions[session_id]
            
            # 记录审计日志
            await self._log_audit(
                user_id=user_id,
                action="user_logout",
                resource_type="user",
                resource_id=user_id,
                details={"session_id": session_id}
            )
            
            logger.info(f"销毁用户会话: {session_id}")
            return True
        
        return False
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """检查用户是否具有指定权限"""
        return permission in user.permissions
    
    async def check_permission(self, user: User, permission: Permission, 
                              resource_type: str, resource_id: str) -> bool:
        """检查权限并记录审计日志"""
        has_perm = self.has_permission(user, permission)
        
        # 记录权限检查审计日志
        await self._log_audit(
            user_id=user.user_id,
            action="permission_check",
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "permission": permission.value,
                "granted": has_perm,
                "resource_type": resource_type,
                "resource_id": resource_id
            }
        )
        
        return has_perm
    
    async def update_user_role(self, admin_user: User, target_user_id: str, 
                              new_role: UserRole) -> bool:
        """更新用户角色"""
        # 检查管理员权限
        if not self.has_permission(admin_user, Permission.USER_MANAGE):
            logger.warning(f"用户无权限管理其他用户: {admin_user.username}")
            return False
        
        target_user = self.users.get(target_user_id)
        if not target_user:
            logger.warning(f"目标用户不存在: {target_user_id}")
            return False
        
        # 更新用户角色和权限
        old_role = target_user.role
        target_user.role = new_role
        target_user.permissions = self.role_permissions[new_role]
        
        # 记录审计日志
        await self._log_audit(
            user_id=admin_user.user_id,
            action="user_role_update",
            resource_type="user",
            resource_id=target_user_id,
            details={
                "target_username": target_user.username,
                "old_role": old_role.value,
                "new_role": new_role.value
            }
        )
        
        logger.info(f"更新用户角色: {target_user.username} -> {new_role.value}")
        return True
    
    async def disable_user(self, admin_user: User, target_user_id: str) -> bool:
        """禁用用户"""
        # 检查管理员权限
        if not self.has_permission(admin_user, Permission.USER_MANAGE):
            logger.warning(f"用户无权限管理其他用户: {admin_user.username}")
            return False
        
        target_user = self.users.get(target_user_id)
        if not target_user:
            logger.warning(f"目标用户不存在: {target_user_id}")
            return False
        
        # 禁用用户
        target_user.is_active = False
        
        # 销毁用户的所有会话
        sessions_to_remove = [
            session_id for session_id, session in self.sessions.items() 
            if session.user_id == target_user_id
        ]
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
        
        # 记录审计日志
        await self._log_audit(
            user_id=admin_user.user_id,
            action="user_disable",
            resource_type="user",
            resource_id=target_user_id,
            details={"target_username": target_user.username}
        )
        
        logger.info(f"禁用用户: {target_user.username}")
        return True
    
    async def get_audit_logs(self, user: User, days: int = 7, 
                           action_filter: str = None) -> List[AuditLog]:
        """获取审计日志"""
        # 检查权限
        if not self.has_permission(user, Permission.SYSTEM_READ):
            logger.warning(f"用户无权限查看审计日志: {user.username}")
            return []
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        filtered_logs = [
            log for log in self.audit_logs 
            if log.timestamp >= cutoff_time
        ]
        
        if action_filter:
            filtered_logs = [
                log for log in filtered_logs 
                if log.action == action_filter
            ]
        
        # 按时间倒序排序
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        return filtered_logs
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        stats = {
            'total_users': len(self.users),
            'active_users': len([u for u in self.users.values() if u.is_active]),
            'active_sessions': len(self.sessions),
            'audit_logs_count': len(self.audit_logs),
            'users_by_role': {}
        }
        
        # 按角色统计用户数
        for role in UserRole:
            stats['users_by_role'][role.value] = len([
                u for u in self.users.values() 
                if u.role == role and u.is_active
            ])
        
        return stats
    
    def _generate_user_id(self) -> str:
        """生成用户ID"""
        return secrets.token_hex(8)
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return secrets.token_hex(16)
    
    def _verify_password(self, password: str, user: User) -> bool:
        """验证密码（简化实现）"""
        # 实际应该使用安全的密码哈希算法
        # 这里简化实现，实际项目中应该使用bcrypt或类似算法
        return True  # 简化实现，总是返回True
    
    async def _log_audit(self, user_id: str, action: str, resource_type: str, 
                        resource_id: str, details: Dict[str, Any]):
        """记录审计日志"""
        log = AuditLog(
            log_id=secrets.token_hex(8),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            timestamp=datetime.now(),
            ip_address="127.0.0.1"  # 实际应该获取真实IP
        )
        
        self.audit_logs.append(log)
        
        # 限制审计日志大小
        if len(self.audit_logs) > 10000:
            self.audit_logs = self.audit_logs[-10000:]


# 使用示例
async def main():
    """使用示例"""
    config = {}
    manager = UserManager(config)
    
    # 创建测试用户
    test_user = await manager.create_user(
        username="testuser",
        email="test@example.com",
        password="password123",
        role=UserRole.USER,
        profile={"display_name": "测试用户"}
    )
    
    if test_user:
        # 用户认证
        authenticated_user = await manager.authenticate_user("testuser", "password123")
        
        if authenticated_user:
            # 创建会话
            session = await manager.create_session(
                authenticated_user, 
                "192.168.1.100", 
                "Mozilla/5.0..."
            )
            
            # 验证会话
            validated_user = await manager.validate_session(session.session_id)
            
            if validated_user:
                print(f"用户验证成功: {validated_user.username}")
                
                # 检查权限
                has_perm = manager.has_permission(validated_user, Permission.MEDIA_READ)
                print(f"用户有媒体读取权限: {has_perm}")
                
                # 获取用户统计
                stats = await manager.get_user_stats()
                print(f"用户统计: {stats}")
            
            # 销毁会话
            await manager.destroy_session(session.session_id)


if __name__ == "__main__":
    asyncio.run(main())