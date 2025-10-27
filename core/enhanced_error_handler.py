#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 增强错误处理系统
提供统一的错误处理、重试机制和错误报告
"""

import asyncio
import logging
from typing import Callable, Any, Optional, Type, Union
from functools import wraps
from dataclasses import dataclass
from enum import Enum


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """错误信息"""
    error_type: str
    severity: ErrorSeverity
    message: str
    context: dict
    retry_count: int = 0
    max_retries: int = 3


class EnhancedErrorHandler:
    """增强错误处理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_stats = {
            "total_errors": 0,
            "by_severity": {severity.value: 0 for severity in ErrorSeverity},
            "by_type": {}
        }
    
    def retry_on_error(
        self, 
        max_retries: int = 3, 
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        """重试装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_error = None
                for attempt in range(max_retries + 1):
                    try:
                        if asyncio.iscoroutinefunction(func):
                            return await func(*args, **kwargs)
                        else:
                            return func(*args, **kwargs)
                    except exceptions as e:
                        last_error = e
                        
                        # 记录错误统计
                        self._record_error(
                            error_type=type(e).__name__,
                            severity=self._determine_severity(e),
                            message=str(e),
                            context={
                                "function": func.__name__,
                                "attempt": attempt,
                                "max_retries": max_retries
                            }
                        )
                        
                        if attempt < max_retries:
                            wait_time = delay * (backoff_factor ** attempt)
                            self.logger.warning(
                                f"操作失败，{wait_time:.1f}秒后重试... "
                                f"({attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(wait_time)
                        else:
                            self.logger.error(
                                f"操作失败，已达到最大重试次数: {e}"
                            )
                            raise
                
                raise last_error
            
            return async_wrapper
        return decorator
    
    def handle_errors(
        self,
        default_return: Any = None,
        exceptions: tuple = (Exception,),
        log_level: str = "ERROR"
    ):
        """错误处理装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except exceptions as e:
                    # 记录错误
                    self._record_error(
                        error_type=type(e).__name__,
                        severity=self._determine_severity(e),
                        message=str(e),
                        context={
                            "function": func.__name__,
                            "args": str(args),
                            "kwargs": str(kwargs)
                        }
                    )
                    
                    # 记录日志
                    log_method = getattr(self.logger, log_level.lower())
                    log_method(f"函数 {func.__name__} 执行失败: {e}")
                    
                    return default_return
            
            return async_wrapper
        return decorator
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """确定错误严重程度"""
        error_type = type(error).__name__
        
        # 网络相关错误
        if error_type in ["ConnectionError", "TimeoutError", "SSLError"]:
            return ErrorSeverity.MEDIUM
        
        # 配置相关错误
        elif error_type in ["ConfigError", "ValidationError"]:
            return ErrorSeverity.HIGH
        
        # 文件系统错误
        elif error_type in ["FileNotFoundError", "PermissionError"]:
            return ErrorSeverity.MEDIUM
        
        # 其他错误
        else:
            return ErrorSeverity.LOW
    
    def _record_error(self, error_type: str, severity: ErrorSeverity, 
                     message: str, context: dict):
        """记录错误统计"""
        self.error_stats["total_errors"] += 1
        self.error_stats["by_severity"][severity.value] += 1
        
        if error_type not in self.error_stats["by_type"]:
            self.error_stats["by_type"][error_type] = 0
        self.error_stats["by_type"][error_type] += 1
    
    def get_error_stats(self) -> dict:
        """获取错误统计"""
        return self.error_stats
    
    def reset_stats(self):
        """重置错误统计"""
        self.error_stats = {
            "total_errors": 0,
            "by_severity": {severity.value: 0 for severity in ErrorSeverity},
            "by_type": {}
        }


# 全局错误处理器实例
error_handler = EnhancedErrorHandler()


def retry_on_error(max_retries: int = 3, delay: float = 1.0, 
                  backoff_factor: float = 2.0, 
                  exceptions: tuple = (Exception,)):
    """全局重试装饰器"""
    return error_handler.retry_on_error(
        max_retries, delay, backoff_factor, exceptions
    )


def handle_errors(default_return: Any = None, 
                  exceptions: tuple = (Exception,), 
                  log_level: str = "ERROR"):
    """全局错误处理装饰器"""
    return error_handler.handle_errors(
        default_return, exceptions, log_level
    )