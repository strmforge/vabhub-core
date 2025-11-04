"""
Logging integration for real-time log broadcasting
"""

import logging
import asyncio
from .websocket_manager import ConnectionManager, LogBroadcaster

# 创建全局实例
connection_manager = ConnectionManager()
log_broadcaster = LogBroadcaster(connection_manager)

# 定义LogLevel枚举
class LogLevel:
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class WebSocketLogHandler(logging.Handler):
    """Custom log handler that broadcasts logs to WebSocket clients"""

    def __init__(self):
        super().__init__()
        self.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.setFormatter(formatter)

    def emit(self, record):
        """Emit a log record to WebSocket clients"""
        try:
            # Convert log level
            level_map = {
                logging.DEBUG: LogLevel.DEBUG,
                logging.INFO: LogLevel.INFO,
                logging.WARNING: LogLevel.WARNING,
                logging.ERROR: LogLevel.ERROR,
                logging.CRITICAL: LogLevel.CRITICAL,
            }

            level = level_map.get(record.levelno, LogLevel.INFO)
            message = self.format(record)
            source = record.name

            # Broadcast log asynchronously
            asyncio.create_task(log_broadcaster.broadcast_log(level, message, source))

        except Exception as e:
            # Fallback to console logging if WebSocket broadcasting fails
            print(f"WebSocket log handler error: {e}")


def setup_realtime_logging():
    """Setup real-time logging integration"""
    # Get root logger
    root_logger = logging.getLogger()

    # Remove existing handlers to avoid duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add WebSocket log handler
    websocket_handler = WebSocketLogHandler()
    root_logger.addHandler(websocket_handler)

    # Set log level
    root_logger.setLevel(logging.INFO)

    return websocket_handler


# Utility functions for manual log broadcasting
async def log_system_event(message: str):
    """Log a system event"""
    await log_broadcaster.broadcast_log(LogLevel.INFO, "system", message)


async def log_download_event(message: str):
    """Log a download event"""
    await log_broadcaster.broadcast_log(LogLevel.INFO, "download", message)


async def log_plugin_event(message: str, plugin_name: str):
    """Log a plugin event"""
    await log_broadcaster.broadcast_log(LogLevel.INFO, plugin_name, message)
