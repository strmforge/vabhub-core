#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 主应用入口
统一的应用启动和管理
"""

import uvicorn
import asyncio
from pathlib import Path
import sys

from core.services import get_service_manager
from app.api import app

# 获取服务管理器实例
service_manager = get_service_manager()


class VabHubApplication:
    """VabHub应用主类"""
    
    def __init__(self):
        self.config = service_manager.config
        self.is_running = False
    
    async def initialize(self) -> bool:
        """初始化应用"""
        print("🚀 正在启动 VabHub 应用...")
        
        # 初始化服务管理器
        if not await service_manager.initialize():
            print("❌ 服务初始化失败")
            return False
        
        print("✅ 服务初始化成功")
        
        # 检查功能状态
        self._print_feature_status()
        
        return True
    
    def _print_feature_status(self):
        """打印功能状态"""
        print("\n📋 功能状态:")
        features = {
            "file_organizer": "文件整理",
            "duplicate_finder": "重复检测", 
            "smart_rename": "智能重命名",
            "pt_search": "PT搜索",
            "media_library": "媒体库"
        }
        
        for feature_key, feature_name in features.items():
            status = "✅ 启用" if service_manager.config.get_feature_status(feature_key) else "❌ 禁用"
            print(f"  {feature_name}: {status}")
    
    async def run(self):
        """运行应用"""
        if not await self.initialize():
            return
        
        self.is_running = True
        
        print(f"\n🌐 VabHub 服务已启动")
        print(f"   访问地址: http://{self.config.api.host}:{self.config.api.port}")
        print(f"   API文档: http://{self.config.api.host}:{self.config.api.port}/docs")
        print(f"   健康检查: http://{self.config.api.host}:{self.config.api.port}/health")
        
        # 启动FastAPI服务
        uvicorn.run(
            app,
            host=self.config.api.host,
            port=self.config.api.port,
            log_level="info" if self.config.debug else "warning"
        )
    
    async def shutdown(self):
        """关闭应用"""
        if self.is_running:
            print("\n🛑 正在关闭 VabHub 应用...")
            self.is_running = False
            print("✅ VabHub 应用已关闭")


async def main():
    """主函数"""
    application = VabHubApplication()
    
    try:
        await application.run()
    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在关闭...")
    except Exception as e:
        print(f"\n❌ 应用运行出错: {e}")
    finally:
        await application.shutdown()


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ VabHub 需要 Python 3.8 或更高版本")
        sys.exit(1)
    
    # 运行应用
    asyncio.run(main())