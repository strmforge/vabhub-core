#!/usr/bin/env python3
"""
VabHub Core 启动脚本
使用统一配置管理器
"""

import os
import sys
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.api import app
from core.logging_config import setup_logging, get_logger
from core.config_manager import get_config_manager

# 初始化配置管理器
config_manager = get_config_manager("../config")
config = config_manager.get_config()

# 设置日志配置
setup_logging(
    log_level=config.logging.level,
    log_file=config.logging.file,
    enable_json=False,
    enable_console=True
)

logger = get_logger("vabhub.startup")

if __name__ == "__main__":
    host = config.server.host
    port = config.server.port
    reload = config.server.reload
    
    logger.info(f"🚀 Starting VabHub Core on {host}:{port}")
    logger.info(f"📊 Environment: {config.environment}")
    logger.info(f"🔧 Debug mode: {config.debug}")
    logger.info(f"📋 Loaded {len(config.plugins.enabled_plugins)} plugins")
    logger.info(f"💾 Database: {config.database.url}")
    logger.info(f"🔴 Redis: {config.redis.url}")
    
    uvicorn.run(
        "core.api:app",
        host=host,
        port=port,
        reload=reload,
        workers=config.server.workers,
        log_level=config.logging.level.lower()
    )