#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CookieCloud API路由
提供增强的CookieCloud功能接口
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.cookiecloud_enhanced import cookiecloud_manager

router = APIRouter()


class CookieCloudConfig(BaseModel):
    """CookieCloud配置模型"""
    name: str
    server: str
    key: str
    password: str


class CookieCloudSyncRequest(BaseModel):
    """CookieCloud同步请求模型"""
    client_name: str


class CookieCloudSyncResponse(BaseModel):
    """CookieCloud同步响应模型"""
    success: bool
    message: str
    cookie_count: int = 0
    domains: List[str] = []


class CookieCloudGetRequest(BaseModel):
    """获取Cookie请求模型"""
    client_name: str
    domain: str


@router.post("/cookiecloud/create", response_model=Dict[str, Any])
async def create_cookiecloud_client(config: CookieCloudConfig):
    """
    创建CookieCloud客户端
    """
    try:
        success, message = await cookiecloud_manager.create_client(
            config.name, config.server, config.key, config.password
        )
        
        if success:
            return {
                "success": True,
                "message": "CookieCloud客户端创建成功",
                "client_name": config.name
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.post("/cookiecloud/sync", response_model=CookieCloudSyncResponse)
async def sync_cookiecloud(request: CookieCloudSyncRequest):
    """
    同步CookieCloud数据
    """
    try:
        success, message, cookies_data = await cookiecloud_manager.sync_cookies(
            request.client_name
        )
        
        return CookieCloudSyncResponse(
            success=success,
            message=message,
            cookie_count=len(cookies_data),
            domains=list(cookies_data.keys())
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/cookiecloud/get")
async def get_cookie(request: CookieCloudGetRequest):
    """
    获取指定域名的Cookie
    """
    try:
        cookie_data = await cookiecloud_manager.get_cookie(
            request.client_name, request.domain
        )
        
        if cookie_data:
            return {
                "success": True,
                "cookie": cookie_data
            }
        else:
            return {
                "success": False,
                "message": f"未找到域名 {request.domain} 的Cookie"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/cookiecloud/clients")
async def list_cookiecloud_clients():
    """
    列出所有CookieCloud客户端
    """
    try:
        client_names = cookiecloud_manager.get_client_names()
        return {
            "success": True,
            "clients": client_names
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/cookiecloud/history")
async def get_sync_history(limit: int = 10):
    """
    获取同步历史
    """
    try:
        history = cookiecloud_manager.get_sync_history(limit)
        return {
            "success": True,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.delete("/cookiecloud/{client_name}")
async def delete_cookiecloud_client(client_name: str):
    """
    删除CookieCloud客户端
    """
    try:
        if client_name in cookiecloud_manager.clients:
            del cookiecloud_manager.clients[client_name]
            return {
                "success": True,
                "message": f"客户端 {client_name} 已删除"
            }
        else:
            raise HTTPException(status_code=404, detail="客户端不存在")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")