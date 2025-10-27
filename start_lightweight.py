#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 轻量级启动脚本
模仿 MoviePilot 模式，支持快速启动和库分离
"""

import os
import sys
import time
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import settings


class LightweightStarter:
    """轻量级启动器"""
    
    def __init__(self):
        self.system_info = self._get_system_info()
        self.libraries = self._detect_libraries()
        self.backend_status = self._check_backend_status()
        self.frontend_status = self._check_frontend_status()
    
    def _get_system_info(self) -> Dict:
        """获取系统信息"""
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.architecture()[0],
            "python_version": platform.python_version(),
            "working_directory": os.getcwd()
        }
    
    def _detect_libraries(self) -> Dict:
        """检测可用的库"""
        libraries = {
            "movie": {
                "name": "电影库",
                "enabled": False,
                "path": None,
                "type": "movie"
            },
            "tv": {
                "name": "电视剧库", 
                "enabled": False,
                "path": None,
                "type": "tv"
            },
            "music": {
                "name": "音乐库",
                "enabled": False,
                "path": None,
                "type": "music"
            },
            "anime": {
                "name": "动漫库",
                "enabled": False,
                "path": None,
                "type": "anime"
            }
        }
        
        # 检测库路径
        possible_paths = [
            "/data/media",
            "/media",
            "/mnt/media",
            "D:\\media",
            "E:\\media",
            str(Path.home() / "media"),
            str(Path.home() / "Movies"),
            str(Path.home() / "TV Shows")
        ]
        
        for lib_name, lib_config in libraries.items():
            # 检查配置中的路径
            config_path = getattr(settings, f"{lib_name}_output_path", "")
            if config_path and os.path.exists(config_path):
                libraries[lib_name]["enabled"] = True
                libraries[lib_name]["path"] = config_path
                continue
            
            # 检查常见路径
            for base_path in possible_paths:
                test_path = os.path.join(base_path, lib_name)
                if os.path.exists(test_path):
                    libraries[lib_name]["enabled"] = True
                    libraries[lib_name]["path"] = test_path
                    break
        
        return libraries
    
    def _check_backend_status(self) -> Dict:
        """检查后端服务状态"""
        status = {
            "python": self._check_python_installation(),
            "dependencies": self._check_dependencies(),
            "database": self._check_database(),
            "redis": self._check_redis(),
            "api_server": self._check_api_server()
        }
        
        status["overall"] = all(status.values())
        return status
    
    def _check_frontend_status(self) -> Dict:
        """检查前端服务状态"""
        status = {
            "web_interface": os.path.exists("ui") or os.path.exists("templates"),
            "static_files": os.path.exists("static") or os.path.exists("ui"),
            "frontend_build": self._check_frontend_build()
        }
        
        status["overall"] = any(status.values())
        return status
    
    def _check_python_installation(self) -> bool:
        """检查Python安装"""
        try:
            import sys
            return sys.version_info >= (3, 8)
        except:
            return False
    
    def _check_dependencies(self) -> bool:
        """检查依赖包"""
        try:
            import fastapi
            import uvicorn
            import pydantic
            return True
        except ImportError:
            return False
    
    def _check_database(self) -> bool:
        """检查数据库"""
        try:
            # 检查数据库连接配置
            db_url = getattr(settings, "database_url", None)
            if db_url and "sqlite" in db_url:
                # SQLite数据库，检查文件是否存在或可创建
                db_path = db_url.replace("sqlite:///", "")
                if os.path.exists(db_path) or os.path.exists(os.path.dirname(db_path)):
                    return True
            return True  # 如果没有配置数据库，也认为是正常的
        except:
            return False
    
    def _check_redis(self) -> bool:
        """检查Redis"""
        try:
            import redis
            redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
            # 简单检查，不实际连接
            return True
        except:
            return False
    
    def _check_api_server(self) -> bool:
        """检查API服务器"""
        # 检查必要的API文件是否存在
        required_files = ["app/main.py", "core/config.py"]
        return all(os.path.exists(f) for f in required_files)
    
    def _check_frontend_build(self) -> bool:
        """检查前端构建"""
        # 检查是否有前端构建文件
        frontend_files = [
            "ui/index.html",
            "templates/index.html", 
            "static/index.html",
            "dist/index.html"
        ]
        return any(os.path.exists(f) for f in frontend_files)
    
    def print_startup_info(self):
        """打印启动信息"""
        print("🚀 VabHub 轻量级启动器")
        print("=" * 60)
        print("📊 系统信息:")
        print(f"  平台: {self.system_info['platform']} {self.system_info['platform_version']}")
        print(f"  架构: {self.system_info['architecture']}")
        print(f"  Python: {self.system_info['python_version']}")
        print(f"  工作目录: {self.system_info['working_directory']}")
        
        print("\n📚 检测到的媒体库:")
        enabled_libs = [lib for lib in self.libraries.values() if lib["enabled"]]
        if enabled_libs:
            for lib in enabled_libs:
                print(f"  ✅ {lib['name']}: {lib['path']}")
        else:
            print("  ⚠️  未检测到媒体库，将使用默认配置")
        
        print("\n🔧 后端服务状态:")
        backend_checks = [
            ("Python环境", self.backend_status["python"]),
            ("依赖包", self.backend_status["dependencies"]),
            ("数据库", self.backend_status["database"]),
            ("Redis", self.backend_status["redis"]),
            ("API服务器", self.backend_status["api_server"])
        ]
        
        for check_name, status in backend_checks:
            icon = "✅" if status else "❌"
            print(f"  {icon} {check_name}")
        
        print("\n🎨 前端服务状态:")
        frontend_checks = [
            ("Web界面", self.frontend_status["web_interface"]),
            ("静态文件", self.frontend_status["static_files"]),
            ("前端构建", self.frontend_status["frontend_build"])
        ]
        
        for check_name, status in frontend_checks:
            icon = "✅" if status else "❌"
            print(f"  {icon} {check_name}")
        
        print("\n" + "=" * 60)
        
        # 总体状态
        overall_backend = self.backend_status["overall"]
        overall_frontend = self.frontend_status["overall"]
        
        if overall_backend and overall_frontend:
            print("🎉 系统准备就绪，可以启动完整服务")
        elif overall_backend:
            print("ℹ️  后端服务正常，前端服务需要配置")
        else:
            print("❌ 后端服务存在问题，请检查配置")
        
        print("=" * 60)
    
    def start_services(self, mode: str = "auto"):
        """启动服务"""
        if mode == "auto":
            if self.backend_status["overall"]:
                if self.frontend_status["overall"]:
                    return self._start_full_service()
                else:
                    return self._start_backend_only()
            else:
                print("❌ 后端服务不可用，无法启动")
                return False
        elif mode == "backend":
            return self._start_backend_only()
        elif mode == "full":
            return self._start_full_service()
        else:
            print(f"❌ 未知启动模式: {mode}")
            return False
    
    def _start_backend_only(self) -> bool:
        """仅启动后端服务"""
        print("\n🔧 启动后端API服务...")
        try:
            from app.main import create_app
            import uvicorn
            
            app = create_app()
            
            # 在后台启动服务器
            config = uvicorn.Config(
                app,
                host=settings.host,
                port=settings.port,
                log_level="info",
                access_log=False
            )
            
            server = uvicorn.Server(config)
            
            # 异步启动
            import asyncio
            asyncio.create_task(server.serve())
            
            print(f"✅ 后端服务已启动: http://{settings.host}:{settings.port}")
            print("📚 API文档: http://localhost:8090/docs")
            
            return True
            
        except Exception as e:
            print(f"❌ 后端服务启动失败: {e}")
            return False
    
    def _start_full_service(self) -> bool:
        """启动完整服务（前后端）"""
        print("\n🎯 启动完整服务...")
        
        # 先启动后端
        backend_started = self._start_backend_only()
        if not backend_started:
            return False
        
        # 检查并启动前端服务
        if self.frontend_status["web_interface"]:
            print("🎨 前端服务已就绪")
            print("🌐 访问地址: http://localhost:8090")
        else:
            print("⚠️  前端服务未配置，仅提供API接口")
        
        return True


def main():
    """主函数"""
    print("🚀 VabHub 轻量级启动器初始化...")
    
    # 创建启动器实例
    starter = LightweightStarter()
    
    # 显示启动信息
    starter.print_startup_info()
    
    # 询问启动模式
    print("\n🎯 选择启动模式:")
    print("1. 自动模式 (推荐)")
    print("2. 仅后端API")
    print("3. 完整服务")
    
    try:
        choice = input("请选择 (1-3, 默认1): ").strip()
        if not choice:
            choice = "1"
        
        mode_map = {"1": "auto", "2": "backend", "3": "full"}
        selected_mode = mode_map.get(choice, "auto")
        
        print(f"\n🎯 选择模式: {selected_mode}")
        
        # 启动服务
        success = starter.start_services(selected_mode)
        
        if success:
            print("\n🎉 服务启动成功!")
            print("💡 提示:")
            print("  • 按 Ctrl+C 停止服务")
            print("  • 访问 http://localhost:8090 使用Web界面")
            print("  • 访问 http://localhost:8090/docs 查看API文档")
            
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 服务已停止")
        else:
            print("\n❌ 服务启动失败，请检查错误信息")
            
    except KeyboardInterrupt:
        print("\n👋 用户取消启动")
    except Exception as e:
        print(f"\n❌ 启动过程中发生错误: {e}")


if __name__ == "__main__":
    main()