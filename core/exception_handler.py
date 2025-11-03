"""
VabHub 统一异常处理模块

提供统一的异常处理机制，包括自定义异常类、异常处理器和错误响应格式化。
"""

import logging
import traceback
from typing import Dict, Any, Optional, Callable
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class VabHubError(Exception):
    """VabHub 基础异常类"""
    
    def __init__(
        self, 
        message: str, 
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "status_code": self.status_code
            }
        }


class ValidationError(VabHubError):
    """验证错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class AuthenticationError(VabHubError):
    """认证错误"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AuthorizationError(VabHubError):
    """授权错误"""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403
        )


class NotFoundError(VabHubError):
    """资源未找到错误"""
    
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            message=f"{resource} not found",
            code="NOT_FOUND",
            status_code=404
        )


class ConflictError(VabHubError):
    """资源冲突错误"""
    
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409
        )


class RateLimitError(VabHubError):
    """速率限制错误"""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429
        )


class ExternalServiceError(VabHubError):
    """外部服务错误"""
    
    def __init__(self, service: str, message: str = "External service error"):
        super().__init__(
            message=f"{service}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service}
        )


class DatabaseError(VabHubError):
    """数据库错误"""
    
    def __init__(self, message: str = "Database error"):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500
        )


class CacheError(VabHubError):
    """缓存错误"""
    
    def __init__(self, message: str = "Cache error"):
        super().__init__(
            message=message,
            code="CACHE_ERROR",
            status_code=500
        )


class PluginError(VabHubError):
    """插件错误"""
    
    def __init__(self, plugin_name: str, message: str = "Plugin error"):
        super().__init__(
            message=f"Plugin {plugin_name}: {message}",
            code="PLUGIN_ERROR",
            status_code=500,
            details={"plugin": plugin_name}
        )


class ExceptionHandler:
    """异常处理器"""
    
    def __init__(self, app: FastAPI, debug: bool = False):
        self.app = app
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        
        # 注册异常处理器
        self._register_handlers()
    
    def _register_handlers(self):
        """注册异常处理器"""
        
        @self.app.exception_handler(VabHubError)
        async def vabhub_error_handler(request: Request, exc: VabHubError):
            """处理 VabHub 自定义异常"""
            self.logger.error(
                f"VabHubError: {exc.code} - {exc.message}",
                extra={
                    "status_code": exc.status_code,
                    "details": exc.details,
                    "path": request.url.path
                }
            )
            
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.to_dict()
            )
        
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            """处理 HTTP 异常"""
            self.logger.warning(
                f"HTTPException: {exc.status_code} - {exc.detail}",
                extra={
                    "status_code": exc.status_code,
                    "path": request.url.path
                }
            )
            
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": "HTTP_ERROR",
                        "message": exc.detail,
                        "status_code": exc.status_code
                    }
                }
            )
        
        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            """处理请求验证错误"""
            self.logger.warning(
                f"ValidationError: {exc.errors()}",
                extra={
                    "status_code": 422,
                    "path": request.url.path,
                    "errors": exc.errors()
                }
            )
            
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "details": {
                            "errors": exc.errors()
                        },
                        "status_code": 422
                    }
                }
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """处理通用异常"""
            # 记录详细错误信息
            error_info = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc() if self.debug else None,
                "path": request.url.path,
                "method": request.method
            }
            
            self.logger.error(
                f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
                extra=error_info,
                exc_info=True
            )
            
            # 生产环境下隐藏内部错误详情
            if self.debug:
                error_response = {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": str(exc),
                        "details": error_info,
                        "status_code": 500
                    }
                }
            else:
                error_response = {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Internal server error",
                        "status_code": 500
                    }
                }
            
            return JSONResponse(
                status_code=500,
                content=error_response
            )
    
    def add_custom_handler(self, exception_type: type, handler: Callable):
        """添加自定义异常处理器"""
        @self.app.exception_handler(exception_type)
        async def custom_handler(request: Request, exc: Exception):
            return await handler(request, exc)


def setup_exception_handlers(app: FastAPI, debug: bool = False):
    """设置异常处理器"""
    ExceptionHandler(app, debug)


def handle_async_exception(func):
    """异步函数异常处理装饰器"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except VabHubError:
            # VabHubError 直接抛出
            raise
        except Exception as e:
            # 其他异常转换为 VabHubError
            logger = logging.getLogger(func.__module__)
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise VabHubError(
                message="An unexpected error occurred",
                cause=e
            )
    return wrapper


def handle_sync_exception(func):
    """同步函数异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except VabHubError:
            # VabHubError 直接抛出
            raise
        except Exception as e:
            # 其他异常转换为 VabHubError
            logger = logging.getLogger(func.__module__)
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise VabHubError(
                message="An unexpected error occurred",
                cause=e
            )
    return wrapper


# 快捷异常创建函数
def validation_error(message: str, details: Optional[Dict[str, Any]] = None) -> ValidationError:
    """创建验证错误"""
    return ValidationError(message, details)


def not_found_error(resource: str = "Resource") -> NotFoundError:
    """创建未找到错误"""
    return NotFoundError(resource)


def authentication_error(message: str = "Authentication failed") -> AuthenticationError:
    """创建认证错误"""
    return AuthenticationError(message)


def authorization_error(message: str = "Access denied") -> AuthorizationError:
    """创建授权错误"""
    return AuthorizationError(message)


def conflict_error(message: str = "Resource conflict") -> ConflictError:
    """创建冲突错误"""
    return ConflictError(message)


def external_service_error(service: str, message: str = "External service error") -> ExternalServiceError:
    """创建外部服务错误"""
    return ExternalServiceError(service, message)


def plugin_error(plugin_name: str, message: str = "Plugin error") -> PluginError:
    """创建插件错误"""
    return PluginError(plugin_name, message)