"""
VabHub 统一异常处理模块

提供统一的异常类、异常处理装饰器和错误响应格式
"""

import logging
import traceback
from typing import Any, Dict, Optional, Type
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


class VabHubException(Exception):
    """VabHub 基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.logger = logging.getLogger(__name__)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class DatabaseException(VabHubException):
    """数据库异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class CacheException(VabHubException):
    """缓存异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CACHE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class AuthenticationException(VabHubException):
    """认证异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationException(VabHubException):
    """授权异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ValidationException(VabHubException):
    """验证异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class NotFoundException(VabHubException):
    """资源未找到异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ExternalServiceException(VabHubException):
    """外部服务异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class RateLimitException(VabHubException):
    """限流异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class PluginException(VabHubException):
    """插件异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="PLUGIN_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    logger = logging.getLogger(__name__)

    # 处理 VabHub 自定义异常
    if isinstance(exc, VabHubException):
        logger.warning(
            f"VabHubException: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
            },
        )
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    # 处理 FastAPI 验证异常
    elif isinstance(exc, RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        logger.warning(
            f"请求验证失败: {exc}", extra={"path": request.url.path, "errors": errors}
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "error_code": "VALIDATION_ERROR",
                "message": "请求参数验证失败",
                "details": {"errors": errors},
            },
        )

    # 处理 Pydantic 验证异常
    elif isinstance(exc, ValidationError):
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        logger.error(
            f"数据验证失败: {exc}", extra={"path": request.url.path, "errors": errors}
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "error_code": "VALIDATION_ERROR",
                "message": "数据验证失败",
                "details": {"errors": errors},
            },
        )

    # 处理 FastAPI HTTP 异常
    elif isinstance(exc, HTTPException):
        logger.warning(
            f"HTTPException: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "error_code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": {},
            },
        )

    # 处理其他未捕获异常
    else:
        logger.error(
            f"未处理的异常: {exc}",
            extra={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc(),
                "path": request.url.path,
            },
        )

        # 生产环境下隐藏详细错误信息
        if request.app.debug:
            details = {"traceback": traceback.format_exc()}
        else:
            details = {}

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": details,
            },
        )


def error_handler(func):
    """异常处理装饰器"""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except VabHubException:
            # 自定义异常直接抛出
            raise
        except Exception as e:
            # 其他异常转换为 VabHubException
            logger = logging.getLogger(__name__)
            logger.error(f"函数 {func.__name__} 执行失败: {e}", exc_info=True)
            raise VabHubException(
                message=f"操作失败: {str(e)}",
                error_code="FUNCTION_ERROR",
                details={"function": func.__name__},
            )

    return wrapper


def safe_execute(
    func: callable,
    default_return: Any = None,
    exception_types: Optional[list] = None,
    log_error: bool = True,
):
    """安全执行函数，捕获异常并返回默认值"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if exception_types and not any(isinstance(e, t) for t in exception_types):
                raise

            if log_error:
                logger = logging.getLogger(__name__)
                logger.warning(f"安全执行失败: {func.__name__} - {e}")

            return default_return

    return wrapper


async def async_safe_execute(
    func: callable,
    default_return: Any = None,
    exception_types: Optional[list] = None,
    log_error: bool = True,
):
    """异步安全执行函数"""
    try:
        return await func
    except Exception as e:
        if exception_types and not any(isinstance(e, t) for t in exception_types):
            raise

        if log_error:
            logger = logging.getLogger(__name__)
            logger.warning(f"异步安全执行失败: {func.__name__} - {e}")

        return default_return
