"""
VabHub 结构化日志配置模块
"""

import logging
import logging.config
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为结构化JSON"""
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """控制台日志格式化器"""

    # 颜色映射
    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",  # 重置
    }

    def format(self, record: logging.LogRecord) -> str:
        """格式化控制台日志"""
        level_color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset_color = self.COLORS["RESET"]

        timestamp = self.formatTime(record, self.datefmt)
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()

        formatted = (
            f"{timestamp} {level_color}{level:8}{reset_color} [{logger_name}] {message}"
        )

        # 添加异常信息
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_json: bool = False,
    enable_console: bool = True,
) -> None:
    """
    设置日志配置

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，如果为None则不写入文件
        enable_json: 是否启用JSON格式
        enable_console: 是否启用控制台输出
    """

    # 创建日志目录
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # 配置日志处理器，使用更通用的类型
    handlers: List[logging.Handler] = []

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        if enable_json:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(ConsoleFormatter())
        handlers.append(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(StructuredFormatter())
        handlers.append(file_handler)

    # 配置根日志器
    logging.basicConfig(
        level=getattr(logging, log_level.upper()), handlers=handlers, force=True
    )

    # 配置特定日志器的级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取配置好的日志器"""
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger, level: str, message: str, **kwargs
) -> None:
    """
    记录带上下文的日志

    Args:
        logger: 日志器
        level: 日志级别
        message: 日志消息
        **kwargs: 额外上下文字段
    """
    log_method = getattr(logger, level.lower())

    # 创建带额外字段的日志记录
    extra = {"extra_fields": kwargs}
    log_method(message, extra=extra)


# 预定义的日志器
API_LOGGER = get_logger("vabhub.api")
DB_LOGGER = get_logger("vabhub.database")
CACHE_LOGGER = get_logger("vabhub.cache")
PLUGIN_LOGGER = get_logger("vabhub.plugins")
AUTH_LOGGER = get_logger("vabhub.auth")
MEDIA_LOGGER = get_logger("vabhub.media")


if __name__ == "__main__":
    # 测试日志配置
    setup_logging(log_level="DEBUG", enable_json=False)

    logger = get_logger("test")
    logger.debug("调试信息")
    logger.info("普通信息")
    logger.warning("警告信息")
    logger.error("错误信息")

    # 测试带上下文的日志
    log_with_context(
        logger, "info", "用户操作", user_id="123", action="login", ip="192.168.1.1"
    )
