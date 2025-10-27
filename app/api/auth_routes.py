#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证API路由
用户认证和授权接口
"""

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from core.auth import auth_manager, User
from core.config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


class Token(BaseModel):
    """令牌响应模型"""
    access_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    """用户响应模型"""
    username: str
    email: str
    full_name: str
    permissions: list


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """获取当前用户依赖"""
    user = auth_manager.get_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """获取访问令牌"""
    # 这里应该验证用户名和密码
    # 暂时使用模拟验证
    if form_data.username != "admin" or form_data.password != "password":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=auth_manager.access_token_expire_minutes)
    access_token = auth_manager.create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    
    logger.info("用户登录成功", username=form_data.username)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": auth_manager.access_token_expire_minutes * 60
    }


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return UserResponse(
        username=current_user.username,
        email=current_user.email or "",
        full_name=current_user.full_name or "",
        permissions=current_user.permissions
    )


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_active_user)):
    """刷新访问令牌"""
    access_token_expires = timedelta(minutes=auth_manager.access_token_expire_minutes)
    access_token = auth_manager.create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": auth_manager.access_token_expire_minutes * 60
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """用户登出"""
    # 在实际应用中，这里应该将令牌加入黑名单
    logger.info("用户登出", username=current_user.username)
    return {"message": "登出成功"}