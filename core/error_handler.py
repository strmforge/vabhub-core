#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API错误处理和日志记录模块
提供统一的错误处理和日志记录功能
"""

import logging
import traceback
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import structlog

logger = structlog.get_logger()


class VabHubError(Exception):
    """VabHub自定义错误基类"""
    
    def __init__(self, message: str, code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(VabHubError):
    """数据库错误"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, 500, details)


class PluginError(VabHubError):
    """插件错误"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, 500, details)


class MediaNotFoundError(VabHubError):
    """媒体不存在错误"""
    
    def __init__(self, media_id: str):
        super().__init__(f"媒体不存在: {media_id}", 404)


class PluginNotFoundError(VabHubError):
    """插件不存在错误"""
    
    def __init__(self, plugin_id: str):
        super().__init__(f"插件不存在: {plugin_id}", 404)


class ValidationError(VabHubError):
    """验证错误"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, 400, details)


class AuthenticationError(VabHubError):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, 401)


class PermissionError(VabHubError):
    """权限错误"""
    
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, 403)


class RateLimitError(VabHubError):
    """频率限制错误"""
    
    def __init__(self, message: str = "请求频率过高"):
        super().__init__(message, 429)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    
    # 记录错误日志
    logger.error(
        "API请求异常",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error_message=str(exc),
        traceback=traceback.format_exc()
    )
    
    # 处理不同类型的异常
    if isinstance(exc, VabHubError):
        return JSONResponse(
            status_code=exc.code,
            content={
                "success": False,
                "message": exc.message,
                "error_code": exc.code,
                "details": exc.details
            }
        )
    
    elif isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "error_code": exc.status_code
            }
        )
    
    elif isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "请求参数验证失败",
                "error_code": 422,
                "details": {
                    "errors": exc.errors()
                }
            }
        )
    
    else:
        # 未知异常
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误",
                "error_code": 500
            }
        )


def setup_exception_handlers(app):
    """设置异常处理器"""
    
    # 注册全局异常处理器
    app.add_exception_handler(Exception, global_exception_handler)
    
    # 注册自定义异常处理器
    app.add_exception_handler(VabHubError, global_exception_handler)
    app.add_exception_handler(HTTPException, global_exception_handler)
    app.add_exception_handler(RequestValidationError, global_exception_handler)


def log_api_request(request: Request, response: JSONResponse, duration: float):
    """记录API请求日志"""
    
    log_data = {
        "path": request.url.path,
        "method": request.method,
        "status_code": response.status_code,
        "duration": duration,
        "client_ip": request.client.host if request.client else "unknown"
    }
    
    # 根据状态码决定日志级别
    if response.status_code >= 500:
        logger.error("API请求错误", **log_data)
    elif response.status_code >= 400:
        logger.warning("API请求警告", **log_data)
    else:
        logger.info("API请求成功", **log_data)


def log_plugin_event(plugin_name: str, event: str, details: Dict[str, Any] = None):
    """记录插件事件日志"""
    logger.info(
        "插件事件",
        plugin_name=plugin_name,
        event=event,
        details=details or {}
    )


def log_media_event(event: str, media_id: str, details: Dict[str, Any] = None):
    """记录媒体事件日志"""
    logger.info(
        "媒体事件",
        event=event,
        media_id=media_id,
        details=details or {}
    )


def log_system_event(event: str, details: Dict[str, Any] = None):
    """记录系统事件日志"""
    logger.info(
        "系统事件",
        event=event,
        details=details or {}
    )


def get_error_response(message: str, code: int = 500, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """获取标准错误响应格式"""
    return {
        "success": False,
        "message": message,
        "error_code": code,
        "details": details or {}
    }


def get_success_response(message: str = "", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """获取标准成功响应格式"""
    return {
        "success": True,
        "message": message,
        "data": data or {}
    }