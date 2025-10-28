#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 安全API端点
完全对标MoviePilot的安全策略：敏感信息排除
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.config import settings
from core.security import verify_token

router = APIRouter()


class SystemInfoResponse(BaseModel):
    """系统信息响应（排除敏感字段）"""
    version: str
    environment: str
    user_unique_id: str
    # 排除所有敏感信息


@router.get("/system/info", response_model=SystemInfoResponse)
async def get_system_info(token: str = Depends(verify_token)):
    """
    获取非敏感系统信息（完全对标MoviePilot安全策略）
    """
    if token != "vabhub":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # FIXME: 新增敏感配置项时要在此处添加排除项（仿MoviePilot）
    info = settings.dict(
        exclude={
            "SECRET_KEY", "API_TOKEN", "TMDB_API_KEY", "TVDB_API_KEY", 
            "FANART_API_KEY", "GITHUB_TOKEN", "REPO_GITHUB_TOKEN",
            "U115_APP_ID", "U115_APP_KEY", "ALIPAN_APP_ID", "ALIPAN_APP_KEY",
            "DB_PASSWORD", "REDIS_PASSWORD", "COOKIECLOUD_KEY", "COOKIECLOUD_PASSWORD"
        }
    )
    
    # 返回安全的系统信息
    return SystemInfoResponse(
        version=info.get("VERSION", "1.0.0"),
        environment=info.get("ENVIRONMENT", "production"),
        user_unique_id=info.get("USER_UNIQUE_ID", "")
    )


@router.get("/system/config/secure")
async def get_secure_config(token: str = Depends(verify_token)):
    """
    获取安全配置状态（不暴露实际值）
    """
    if token != "vabhub":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {
        "u115_configured": bool(settings.u115_app_id and settings.u115_app_key),
        "alipan_configured": bool(settings.alipan_app_id and settings.alipan_app_key),
        "tmdb_configured": bool(settings.tmdb_api_key),
        "total_services": 3  # 不暴露具体服务名称
    }