"""
用户管理API路由
集成MediaMaster的用户管理精华功能
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, List, Optional, Any
import hashlib
import secrets

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    """用户创建模型"""
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., description="密码")
    full_name: Optional[str] = Field(None, description="全名")
    role: str = Field("user", description="用户角色: admin, user")


class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, description="全名")
    role: Optional[str] = Field(None, description="用户角色")
    preferences: Optional[Dict[str, Any]] = Field(None, description="用户偏好设置")


class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户响应模型"""
    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: int
    last_login: Optional[int]
    preferences: Dict[str, Any]


class LoginResponse(BaseModel):
    """登录响应模型"""
    success: bool
    message: str
    access_token: Optional[str] = None
    user: Optional[UserResponse] = None


class UserManagementResponse(BaseModel):
    """用户管理响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# 模拟用户数据库（实际项目中应该使用真实数据库）
users_db = {}
sessions = {}


def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token() -> str:
    """生成访问令牌"""
    return secrets.token_urlsafe(32)


def get_current_user(token: str) -> Optional[Dict[str, Any]]:
    """根据令牌获取当前用户"""
    if token in sessions:
        user_id = sessions[token]
        return users_db.get(user_id)
    return None


@router.post("/register", response_model=UserManagementResponse)
async def register_user(user_data: UserCreate):
    """用户注册"""
    try:
        # 检查用户名是否已存在
        for user_id, user in users_db.items():
            if user["username"] == user_data.username:
                return UserManagementResponse(
                    success=False,
                    message="用户名已存在"
                )
            if user["email"] == user_data.email:
                return UserManagementResponse(
                    success=False,
                    message="邮箱已存在"
                )
        
        # 创建新用户
        user_id = str(len(users_db) + 1)
        new_user = {
            "user_id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": hash_password(user_data.password),
            "full_name": user_data.full_name,
            "role": user_data.role,
            "is_active": True,
            "created_at": 0,  # 实际项目中应该使用时间戳
            "last_login": None,
            "preferences": {}
        }
        
        users_db[user_id] = new_user
        
        return UserManagementResponse(
            success=True,
            message="用户注册成功",
            data={"user_id": user_id}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"用户注册失败: {str(e)}")


@router.post("/login", response_model=LoginResponse)
async def login_user(login_data: UserLogin):
    """用户登录"""
    try:
        # 查找用户
        user = None
        for user_id, user_data in users_db.items():
            if (user_data["username"] == login_data.username and 
                user_data["password_hash"] == hash_password(login_data.password)):
                user = user_data
                break
        
        if not user:
            return LoginResponse(
                success=False,
                message="用户名或密码错误"
            )
        
        if not user["is_active"]:
            return LoginResponse(
                success=False,
                message="用户账户已被禁用"
            )
        
        # 生成访问令牌
        token = generate_token()
        sessions[token] = user["user_id"]
        
        # 更新最后登录时间
        user["last_login"] = 0  # 实际项目中应该使用时间戳
        
        user_response = UserResponse(
            user_id=user["user_id"],
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user["last_login"],
            preferences=user["preferences"]
        )
        
        return LoginResponse(
            success=True,
            message="登录成功",
            access_token=token,
            user=user_response
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"用户登录失败: {str(e)}")


@router.post("/logout", response_model=UserManagementResponse)
async def logout_user(token: str):
    """用户登出"""
    try:
        if token in sessions:
            del sessions[token]
            
        return UserManagementResponse(
            success=True,
            message="登出成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"用户登出失败: {str(e)}")


@router.get("/profile", response_model=UserManagementResponse)
async def get_user_profile(token: str):
    """获取用户个人信息"""
    try:
        user = get_current_user(token)
        if not user:
            return UserManagementResponse(
                success=False,
                message="无效的访问令牌"
            )
        
        user_response = UserResponse(
            user_id=user["user_id"],
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user["last_login"],
            preferences=user["preferences"]
        )
        
        return UserManagementResponse(
            success=True,
            message="用户信息获取成功",
            data={"user": user_response.dict()}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")


@router.put("/profile", response_model=UserManagementResponse)
async def update_user_profile(update_data: UserUpdate, token: str):
    """更新用户个人信息"""
    try:
        user = get_current_user(token)
        if not user:
            return UserManagementResponse(
                success=False,
                message="无效的访问令牌"
            )
        
        # 更新用户信息
        if update_data.email:
            user["email"] = update_data.email
        if update_data.full_name:
            user["full_name"] = update_data.full_name
        if update_data.role:
            user["role"] = update_data.role
        if update_data.preferences:
            user["preferences"].update(update_data.preferences)
        
        return UserManagementResponse(
            success=True,
            message="用户信息更新成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新用户信息失败: {str(e)}")


@router.get("/list", response_model=UserManagementResponse)
async def list_users(token: str, page: int = 1, page_size: int = 20):
    """获取用户列表（管理员功能）"""
    try:
        current_user = get_current_user(token)
        if not current_user or current_user["role"] != "admin":
            return UserManagementResponse(
                success=False,
                message="权限不足"
            )
        
        # 分页逻辑
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        user_list = list(users_db.values())[start_idx:end_idx]
        
        # 移除密码哈希等敏感信息
        safe_user_list = []
        for user in user_list:
            safe_user = {
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "is_active": user["is_active"],
                "created_at": user["created_at"],
                "last_login": user["last_login"]
            }
            safe_user_list.append(safe_user)
        
        return UserManagementResponse(
            success=True,
            message="用户列表获取成功",
            data={
                "users": safe_user_list,
                "total_count": len(users_db),
                "page": page,
                "page_size": page_size
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


@router.put("/{user_id}/activate", response_model=UserManagementResponse)
async def activate_user(user_id: str, token: str):
    """激活用户（管理员功能）"""
    try:
        current_user = get_current_user(token)
        if not current_user or current_user["role"] != "admin":
            return UserManagementResponse(
                success=False,
                message="权限不足"
            )
        
        if user_id not in users_db:
            return UserManagementResponse(
                success=False,
                message="用户不存在"
            )
        
        users_db[user_id]["is_active"] = True
        
        return UserManagementResponse(
            success=True,
            message="用户激活成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"激活用户失败: {str(e)}")


@router.put("/{user_id}/deactivate", response_model=UserManagementResponse)
async def deactivate_user(user_id: str, token: str):
    """禁用用户（管理员功能）"""
    try:
        current_user = get_current_user(token)
        if not current_user or current_user["role"] != "admin":
            return UserManagementResponse(
                success=False,
                message="权限不足"
            )
        
        if user_id not in users_db:
            return UserManagementResponse(
                success=False,
                message="用户不存在"
            )
        
        users_db[user_id]["is_active"] = False
        
        return UserManagementResponse(
            success=True,
            message="用户禁用成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"禁用用户失败: {str(e)}")


@router.delete("/{user_id}", response_model=UserManagementResponse)
async def delete_user(user_id: str, token: str):
    """删除用户（管理员功能）"""
    try:
        current_user = get_current_user(token)
        if not current_user or current_user["role"] != "admin":
            return UserManagementResponse(
                success=False,
                message="权限不足"
            )
        
        if user_id not in users_db:
            return UserManagementResponse(
                success=False,
                message="用户不存在"
            )
        
        # 删除用户会话
        tokens_to_remove = [t for t, uid in sessions.items() if uid == user_id]
        for token_to_remove in tokens_to_remove:
            del sessions[token_to_remove]
        
        # 删除用户
        del users_db[user_id]
        
        return UserManagementResponse(
            success=True,
            message="用户删除成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除用户失败: {str(e)}")


@router.get("/stats", response_model=UserManagementResponse)
async def get_user_stats(token: str):
    """获取用户统计信息（管理员功能）"""
    try:
        current_user = get_current_user(token)
        if not current_user or current_user["role"] != "admin":
            return UserManagementResponse(
                success=False,
                message="权限不足"
            )
        
        total_users = len(users_db)
        active_users = sum(1 for user in users_db.values() if user["is_active"])
        admin_users = sum(1 for user in users_db.values() if user["role"] == "admin")
        
        # 计算最近登录用户
        recent_logins = sum(1 for user in users_db.values() if user["last_login"])
        
        stats = {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "admin_users": admin_users,
            "regular_users": total_users - admin_users,
            "recent_logins": recent_logins,
            "active_sessions": len(sessions)
        }
        
        return UserManagementResponse(
            success=True,
            message="用户统计信息获取成功",
            data={"stats": stats}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户统计失败: {str(e)}")