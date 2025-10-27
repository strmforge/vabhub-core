#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一异常处理系统
现代化错误处理和日志记录
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import logging
import traceback
from datetime import datetime


class ErrorCode(Enum):
    """错误代码枚举"""
    # 文件相关错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_ACCESS_DENIED = "FILE_ACCESS_DENIED"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    
    # 处理相关错误
    PROCESSING_FAILED = "PROCESSING_FAILED"
    METADATA_EXTRACTION_FAILED = "METADATA_EXTRACTION_FAILED"
    AI_SERVICE_UNAVAILABLE = "AI_SERVICE_UNAVAILABLE"
    BATCH_PROCESSING_FAILED = "BATCH_PROCESSING_FAILED"
    
    # 配置相关错误
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    MISSING_API_KEY = "MISSING_API_KEY"
    PATH_NOT_CONFIGURED = "PATH_NOT_CONFIGURED"
    
    # 网络相关错误
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    API_RATE_LIMIT_EXCEEDED = "API_RATE_LIMIT_EXCEEDED"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    
    # 系统相关错误
    INSUFFICIENT_STORAGE = "INSUFFICIENT_STORAGE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    
    # 业务逻辑错误
    DUPLICATE_OPERATION = "DUPLICATE_OPERATION"
    INVALID_OPERATION_STATE = "INVALID_OPERATION_STATE"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MediaProcessingError(Exception):
    """媒体处理基础异常类"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        details: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        file_path: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.severity = severity
        self.file_path = file_path
        self.suggestions = suggestions or []
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "details": self.details,
            "suggestions": self.suggestions,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback if self.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code.value}] {self.message}"


class FileProcessingError(MediaProcessingError):
    """文件处理异常"""
    
    def __init__(self, message: str, file_path: str, error_code: ErrorCode = ErrorCode.PROCESSING_FAILED, **kwargs):
        super().__init__(message, error_code, file_path=file_path, **kwargs)


class AIServiceError(MediaProcessingError):
    """AI服务异常"""
    
    def __init__(self, message: str, service_name: str, error_code: ErrorCode = ErrorCode.AI_SERVICE_UNAVAILABLE, **kwargs):
        details = kwargs.get('details', {})
        details['service_name'] = service_name
        kwargs['details'] = details
        super().__init__(message, error_code, **kwargs)


class ConfigurationError(MediaProcessingError):
    """配置异常"""
    
    def __init__(self, message: str, config_key: str, error_code: ErrorCode = ErrorCode.INVALID_CONFIGURATION, **kwargs):
        details = kwargs.get('details', {})
        details['config_key'] = config_key
        kwargs['details'] = details
        super().__init__(message, error_code, **kwargs)


class NetworkError(MediaProcessingError):
    """网络异常"""
    
    def __init__(self, message: str, url: Optional[str] = None, error_code: ErrorCode = ErrorCode.NETWORK_TIMEOUT, **kwargs):
        details = kwargs.get('details', {})
        if url:
            details['url'] = url
        kwargs['details'] = details
        super().__init__(message, error_code, **kwargs)


class ValidationError(MediaProcessingError):
    """验证异常"""
    
    def __init__(self, message: str, field: str, value: Any, error_code: ErrorCode = ErrorCode.VALIDATION_FAILED, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'field': field,
            'value': str(value),
            'validation_type': 'field_validation'
        })
        kwargs['details'] = details
        super().__init__(message, error_code, **kwargs)


class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_stats = {
            'total_errors': 0,
            'errors_by_code': {},
            'errors_by_severity': {},
            'recent_errors': []
        }
    
    def handle_error(self, error: MediaProcessingError) -> Dict[str, Any]:
        """处理错误"""
        # 更新统计信息
        self._update_error_stats(error)
        
        # 记录日志
        self._log_error(error)
        
        # 返回错误信息
        return error.to_dict()
    
    def _update_error_stats(self, error: MediaProcessingError):
        """更新错误统计"""
        self.error_stats['total_errors'] += 1
        
        # 按错误代码统计
        code = error.error_code.value
        self.error_stats['errors_by_code'][code] = self.error_stats['errors_by_code'].get(code, 0) + 1
        
        # 按严重程度统计
        severity = error.severity.value
        self.error_stats['errors_by_severity'][severity] = self.error_stats['errors_by_severity'].get(severity, 0) + 1
        
        # 保留最近的错误
        self.error_stats['recent_errors'].append(error.to_dict())
        if len(self.error_stats['recent_errors']) > 100:
            self.error_stats['recent_errors'] = self.error_stats['recent_errors'][-100:]
    
    def _log_error(self, error: MediaProcessingError):
        """记录错误日志"""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error.severity, logging.ERROR)
        
        log_message = f"[{error.error_code.value}] {error.message}"
        if error.file_path:
            log_message += f" (文件: {error.file_path})"
        
        self.logger.log(log_level, log_message, extra={
            'error_code': error.error_code.value,
            'severity': error.severity.value,
            'details': error.details,
            'file_path': error.file_path
        })
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return self.error_stats.copy()
    
    def clear_error_stats(self):
        """清除错误统计"""
        self.error_stats = {
            'total_errors': 0,
            'errors_by_code': {},
            'errors_by_severity': {},
            'recent_errors': []
        }


class ErrorSuggestionEngine:
    """错误建议引擎"""
    
    @staticmethod
    def get_suggestions(error: MediaProcessingError) -> List[str]:
        """根据错误类型提供建议"""
        suggestions = []
        
        if error.error_code == ErrorCode.FILE_NOT_FOUND:
            suggestions.extend([
                "检查文件路径是否正确",
                "确认文件是否已被移动或删除",
                "检查文件权限设置"
            ])
        elif error.error_code == ErrorCode.AI_SERVICE_UNAVAILABLE:
            suggestions.extend([
                "检查网络连接",
                "验证API密钥是否有效",
                "尝试使用备用AI服务",
                "稍后重试"
            ])
        elif error.error_code == ErrorCode.INSUFFICIENT_STORAGE:
            suggestions.extend([
                "清理磁盘空间",
                "检查输出目录配置",
                "考虑使用外部存储"
            ])
        elif error.error_code == ErrorCode.INVALID_CONFIGURATION:
            suggestions.extend([
                "检查配置文件格式",
                "验证必需的配置项",
                "重置为默认配置"
            ])
        elif error.error_code == ErrorCode.NETWORK_TIMEOUT:
            suggestions.extend([
                "检查网络连接稳定性",
                "增加超时时间设置",
                "使用代理服务器"
            ])
        
        return suggestions


# 全局错误处理器实例
error_handler = ErrorHandler()
suggestion_engine = ErrorSuggestionEngine()


def handle_exception(func):
    """异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MediaProcessingError as e:
            return error_handler.handle_error(e)
        except Exception as e:
