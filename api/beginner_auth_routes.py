#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初级用户认证API路由
为前端提供认证相关的API接口
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import structlog

from ..core.beginner_pt_auth import beginner_auth_helper

logger = structlog.get_logger()
router = APIRouter(prefix="/api/beginner-auth", tags=["beginner-auth"])


class UsernamePasswordAuthRequest(BaseModel):
    """账号密码认证请求"""
    site_name: str
    username: str
    password: str


class ManualCookieAuthRequest(BaseModel):
    """手动Cookie认证请求"""
    site_name: str
    cookies: Dict[str, str]


class BuiltinCookiecloudAuthRequest(BaseModel):
    """内置CookieCloud认证请求"""
    site_name: str
    username: Optional[str] = None
    password: Optional[str] = None


class AuthResponse(BaseModel):
    """认证响应"""
    success: bool
    message: str
    next_step: Optional[str] = None
    user_info: Optional[Dict[str, Any]] = None
    cookie_count: Optional[int] = None
    auth_type: Optional[str] = None


class SessionStatusResponse(BaseModel):
    """会话状态响应"""
    is_authenticated: bool
    auth_type: Optional[str] = None
    auth_time: Optional[str] = None
    last_used: Optional[str] = None
    status: str


@router.get("/guide", summary="获取认证指导信息")
async def get_auth_guide():
    """获取初级用户认证指导信息"""
    try:
        guide_info = beginner_auth_helper.get_auth_guide()
        return {
            "success": True,
            "data": guide_info
        }
    except Exception as e:
        logger.error("获取认证指导信息失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取认证指导信息失败")


@router.get("/supported-sites", summary="获取支持的PT站点列表")
async def get_supported_sites():
    """获取支持的PT站点列表"""
    try:
        sites = beginner_auth_helper.get_supported_pt_sites()
        return {
            "success": True,
            "data": sites
        }
    except Exception as e:
        logger.error("获取支持的PT站点列表失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取支持的PT站点列表失败")


@router.post("/username-password", response_model=AuthResponse, summary="账号密码认证")
async def username_password_auth(request: UsernamePasswordAuthRequest):
    """使用账号密码进行PT站点认证"""
    try:
        result = await beginner_auth_helper.username_password_auth(
            request.site_name,
            request.username,
            request.password
        )
        
        return AuthResponse(**result)
        
    except Exception as e:
        logger.error("账号密码认证失败", 
                    site_name=request.site_name, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="账号密码认证失败")


@router.post("/builtin-cookiecloud", response_model=AuthResponse, summary="内置CookieCloud认证")
async def builtin_cookiecloud_auth(request: BuiltinCookiecloudAuthRequest):
    """使用内置CookieCloud服务进行PT站点认证"""
    try:
        result = await beginner_auth_helper.builtin_cookiecloud_auth(
            request.site_name
        )
        
        return AuthResponse(**result)
        
    except Exception as e:
        logger.error("内置CookieCloud认证失败", 
                    site_name=request.site_name, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="内置CookieCloud认证失败")


@router.post("/manual-cookie", response_model=AuthResponse, summary="手动Cookie认证")
async def manual_cookie_auth(request: ManualCookieAuthRequest):
    """使用手动输入的Cookie进行PT站点认证"""
    try:
        result = await beginner_auth_helper.manual_cookie_auth(
            request.site_name,
            request.cookies
        )
        
        return AuthResponse(**result)
        
    except Exception as e:
        logger.error("手动Cookie认证失败", 
                    site_name=request.site_name, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="手动CookieCloud认证失败")


@router.get("/session/{site_name}", response_model=SessionStatusResponse, summary="获取会话状态")
async def get_session_status(site_name: str):
    """获取指定站点的会话状态"""
    try:
        status = beginner_auth_helper.get_user_session_status(site_name)
        return SessionStatusResponse(**status)
        
    except Exception as e:
        logger.error("获取会话状态失败", site_name=site_name, error=str(e))
        raise HTTPException(status_code=500, detail="获取会话状态失败")


@router.post("/session/{site_name}/validate", summary="验证会话有效性")
async def validate_session(site_name: str):
    """验证指定站点的会话有效性"""
    try:
        is_valid = await beginner_auth_helper.validate_session(site_name)
        return {
            "success": True,
            "is_valid": is_valid
        }
        
    except Exception as e:
        logger.error("验证会话失败", site_name=site_name, error=str(e))
        raise HTTPException(status_code=500, detail="验证会话失败")


@router.delete("/session/{site_name}", summary="登出指定站点")
async def logout(site_name: str):
    """登出指定PT站点"""
    try:
        # 这里需要扩展beginner_auth_helper以支持登出功能
        # 暂时返回成功
        return {
            "success": True,
            "message": f"{site_name} 登出成功"
        }
        
    except Exception as e:
        logger.error("登出失败", site_name=site_name, error=str(e))
        raise HTTPException(status_code=500, detail="登出失败")


@router.get("/troubleshooting", summary="获取故障排除指南")
async def get_troubleshooting_guide():
    """获取故障排除指南"""
    try:
        guide = beginner_auth_helper.get_troubleshooting_guide()
        return {
            "success": True,
            "data": guide
        }
        
    except Exception as e:
        logger.error("获取故障排除指南失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取故障排除指南失败")


@router.get("/health", summary="健康检查")
async def health_check():
    """认证服务健康检查"""
    return {
        "status": "healthy",
        "service": "beginner-auth",
        "timestamp": "2024-01-01T00:00:00Z"  # 实际应该使用当前时间
    }


@router.post("/check-feature-access", response_model=FeatureAccessResponse, summary="检查功能访问权限")
async def check_feature_access(request: FeatureAccessRequest):
    """检查特定功能访问权限（类似MoviePilot的认证限制）"""
    try:
        result = beginner_auth_helper.check_feature_access(
            request.site_name,
            request.feature
        )
        
        return FeatureAccessResponse(**result)
        
    except Exception as e:
        logger.error("检查功能访问权限失败", 
                    site_name=request.site_name, 
                    feature=request.feature,
                    error=str(e))
        raise HTTPException(status_code=500, detail="检查功能访问权限失败")


@router.get("/feature-restrictions/{site_name}", response_model=FeatureRestrictionsResponse, summary="获取功能限制信息")
async def get_feature_restrictions(site_name: str):
    """获取功能限制信息（类似MoviePilot的提示）"""
    try:
        result = beginner_auth_helper.get_feature_restrictions_info(site_name)
        
        return FeatureRestrictionsResponse(**result)
        
    except Exception as e:
        logger.error("获取功能限制信息失败", 
                    site_name=site_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail="获取功能限制信息失败")


@router.post("/user-auth-status", response_model=UserAuthStatusResponse, summary="获取用户认证状态")
async def get_user_auth_status(request: UserAuthStatusRequest):
    """获取用户认证状态（类似MoviePilot的用户菜单状态）"""
    try:
        result = beginner_auth_helper.get_user_auth_status(request.user_id)
        
        return UserAuthStatusResponse(**result)
        
    except Exception as e:
        logger.error("获取用户认证状态失败", 
                    user_id=request.user_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="获取用户认证状态失败")


@router.post("/complete-user-auth", response_model=CompleteUserAuthResponse, summary="完成用户认证")
async def complete_user_auth(request: CompleteUserAuthRequest):
    """完成用户认证（类似MoviePilot的认证流程）"""
    try:
        result = await beginner_auth_helper.complete_user_auth(
            request.user_id,
            request.site_name,
            request.auth_data
        )
        
        return CompleteUserAuthResponse(**result)
        
    except Exception as e:
        logger.error("完成用户认证失败", 
                    user_id=request.user_id,
                    site_name=request.site_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail="完成用户认证失败")


@router.post("/clear-user-auth", response_model=ClearUserAuthResponse, summary="清除用户认证状态")
async def clear_user_auth(request: ClearUserAuthRequest):
    """清除用户认证状态（用于重新登录）"""
    try:
        success = beginner_auth_helper.clear_user_auth_status(request.user_id)
        
        if success:
            return ClearUserAuthResponse(
                success=True,
                message="用户认证状态已清除"
            )
        else:
            return ClearUserAuthResponse(
                success=False,
                message="清除用户认证状态失败"
            )
        
    except Exception as e:
        logger.error("清除用户认证状态失败", 
                    user_id=request.user_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="清除用户认证状态失败")


@router.get("/available-auth-sites", summary="获取可用认证站点列表")
async def get_available_auth_sites():
    """获取可用的认证站点列表（类似MoviePilot的认证弹窗）"""
    try:
        sites = beginner_auth_helper.get_available_auth_sites()
        
        return {
            "success": True,
            "data": sites
        }
        
    except Exception as e:
        logger.error("获取可用认证站点列表失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取可用认证站点列表失败")