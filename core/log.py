#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 日志系统
参照MoviePilot的日志系统设计，提供完善的日志管理功能
"""

import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class LogConfigModel:
    """日志配置模型"""
    
    def __init__(self, 
                 level: str = "INFO",
                 file: str = "logs/vabhub.log",
                 max_size: str = "10MB",
                 backup_count: int = 5,
                 format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"):
        self.level = level
        self.file = file
        self.max_size = max_size
        self.backup_count = backup_count
        self.format = format


class LogSettings:
    """日志设置"""
    
    def __init__(self):
        self.LOG_PATH = Path("logs")
        self.LOG_PATH.mkdir(exist_ok=True)
        
        # 默认日志配置
        self.log_config = LogConfigModel()


log_settings = LogSettings()


def setup_logging(config: Optional[LogConfigModel] = None):
    """
    设置日志配置
    """
    if config is None:
        config = log_settings.log_config
    
    # 确保日志目录存在
    log_dir = Path(config.file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 日志配置字典
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': config.format
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            }
        },
        'handlers': {
            'default': {
                'level': config.level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'level': config.level,
                'formatter': 'detailed',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': config.file,
                'maxBytes': _parse_size(config.max_size),
                'backupCount': config.backup_count,
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['default', 'file'],
                'level': config.level,
                'propagate': True
            },
            'vabhub': {
                'handlers': ['default', 'file'],
                'level': config.level,
                'propagate': False
            },
            'uvicorn': {
                'handlers': ['default', 'file'],
                'level': 'INFO',
                'propagate': False
            },
            'fastapi': {
                'handlers': ['default', 'file'],
                'level': 'INFO',
                'propagate': False
            }
        }
    }
    
    # 应用日志配置
    logging.config.dictConfig(logging_config)


def _parse_size(size_str: str) -> int:
    """
    解析大小字符串（如 "10MB", "1GB"）为字节数
    """
    size_str = size_str.upper().strip()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    elif size_str.endswith('B'):
        return int(size_str[:-1])
    else:
        return int(size_str)


class Logger:
    """
    增强的日志记录器
    """
    
    def __init__(self, name: str = "vabhub"):
        self.logger = logging.getLogger(name)
    
    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self.logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message: str, **kwargs):
        """记录一般信息"""
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """记录警告信息"""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """记录错误信息"""
        self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message: str, **kwargs):
        """记录严重错误信息"""
        self.logger.critical(self._format_message(message, **kwargs))
    
    def _format_message(self, message: str, **kwargs) -> str:
        """格式化消息"""
        if kwargs:
            extra_info = " ".join([f"{k}={v}" for k, v in kwargs.items()])
            return f"{message} [{extra_info}]"
        return message


# 全局日志记录器
logger = Logger()


def get_logger(name: str) -> Logger:
    """
    获取指定名称的日志记录器
    """
    return Logger(name)


class PerformanceLogger:
    """
    性能日志记录器
    """
    
    def __init__(self, name: str = "performance"):
        self.logger = get_logger(name)
        self.timers = {}
    
    def start_timer(self, operation: str):
        """开始计时"""
        import time
        self.timers[operation] = time.time()
    
    def stop_timer(self, operation: str):
        """停止计时并记录"""
        import time
        if operation in self.timers:
            duration = time.time() - self.timers[operation]
            self.logger.info(f"操作 {operation} 耗时: {duration:.3f}秒")
            del self.timers[operation]
            return duration
        return 0


class AuditLogger:
    """
    审计日志记录器
    """
    
    def __init__(self, name: str = "audit"):
        self.logger = get_logger(name)
    
    def log_operation(self, user: str, operation: str, target: str, status: str = "success"):
        """记录操作审计"""
        self.logger.info(f"用户 {user} 执行操作 {operation} 于 {target} - 状态: {status}")
    
    def log_security_event(self, event_type: str, details: str):
        """记录安全事件"""
        self.logger.warning(f"安全事件: {event_type} - {details}")


# 初始化日志系统
setup_logging()


if __name__ == "__main__":
    # 测试日志系统
    logger.info("日志系统初始化完成")
    
    # 测试性能日志
    perf_logger = PerformanceLogger()
    perf_logger.start_timer("test_operation")
    import time
    time.sleep(0.1)
    perf_logger.stop_timer("test_operation")
    
    # 测试审计日志
    audit_logger = AuditLogger()
    audit_logger.log_operation("admin", "file_upload", "/path/to/file.txt")
    
    logger.info("日志系统测试完成")