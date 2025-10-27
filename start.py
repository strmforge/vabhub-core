#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartMedia Hub v4.2 - 启动脚本
现代化AI智能媒体管理平台
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import settings
from app.main import create_app
import uvicorn


def main():
    """主函数"""
    print("🚀 SmartMedia Hub v4.2 启动中...")
    print(f"📊 应用名称: {settings.app_name}")
    print(f"🔢 版本号: {settings.version}")
    print(f"🌐 服务器地址: http://{settings.host}:{settings.port}")
    print(f"🔧 调试模式: {settings.debug}")
    print("-" * 50)
    
    # 创建FastAPI应用
    app = create_app()
    
    # 启动服务器
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
        log_level="info"
    )


if __name__ == "__main__":
    main()