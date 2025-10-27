#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 系统检测器
自动检测前后端安装状态和系统环境
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any


class SystemDetector:
    """系统检测器"""
    
    def __init__(self):
        self.system_info = self._get_system_info()
        self.detection_results = {}
    
    def _get_system_info(self) -> Dict:
        """获取系统信息"""
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.architecture()[0],
            "python_version": platform.python_version(),
            "working_directory": os.getcwd(),
            "project_root": str(Path(__file__).parent.parent)
        }
    
    def detect_python_environment(self) -> Dict:
        """检测Python环境"""
        result = {
            "python_version": self.system_info["python_version"],
            "virtual_env": os.environ.get("VIRTUAL_ENV"),
            "pip_available": False,
            "pip_version": None,
            "requirements_installed": False
        }
        
        # 检查pip是否可用
        try:
            pip_version = subprocess.check_output([
                sys.executable, "-m", "pip", "--version"
            ], text=True).strip()
            result["pip_available"] = True
            result["pip_version"] = pip_version
        except:
            result["pip_available"] = False
        
        # 检查requirements.txt是否已安装
        if os.path.exists("requirements.txt"):
            try:
                # 检查关键依赖是否已安装
                key_dependencies = ["fastapi", "uvicorn", "pydantic"]
                installed_packages = subprocess.check_output([
                    sys.executable, "-m", "pip", "list", "--format=json"
                ], text=True)
                
                import json
                packages = json.loads(installed_packages)
                package_names = [p["name"].lower() for p in packages]
                
                # 检查关键依赖
                missing_deps = [dep for dep in key_dependencies if dep not in package_names]
                result["requirements_installed"] = len(missing_deps) == 0
                result["missing_dependencies"] = missing_deps
                
            except:
                result["requirements_installed"] = False
        
        return result
    
    def detect_backend_services(self) -> Dict:
        """检测后端服务"""
        result = {
            "fastapi": False,
            "uvicorn": False,
            "app_structure": False,
            "config_files": False,
            "database": False,
            "redis": False
        }
        
        # 检查FastAPI和Uvicorn
        try:
            import fastapi
            result["fastapi"] = True
        except ImportError:
            result["fastapi"] = False
        
        try:
            import uvicorn
            result["uvicorn"] = True
        except ImportError:
            result["uvicorn"] = False
        
        # 检查应用结构
        required_files = [
            "app/main.py",
            "core/config.py", 
            "requirements.txt"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        result["app_structure"] = len(missing_files) == 0
        result["missing_files"] = missing_files
        
        # 检查配置文件
        config_files = [
            "config/config.yaml",
            "config/categories.yaml"
        ]
        
        config_exists = []
        for config_file in config_files:
            if os.path.exists(config_file):
                config_exists.append(config_file)
        
        result["config_files"] = len(config_exists) > 0
        result["existing_configs"] = config_exists
        
        # 检查数据库
        try:
            from core.config import settings
            if hasattr(settings, "database_url") and settings.database_url:
                result["database"] = True
        except:
            result["database"] = False
        
        # 检查Redis
        try:
            import redis
            result["redis"] = True
        except ImportError:
            result["redis"] = False
        
        return result
    
    def detect_frontend_services(self) -> Dict:
        """检测前端服务"""
        result = {
            "web_interface": False,
            "static_files": False,
            "templates": False,
            "frontend_build": False,
            "ui_framework": None
        }
        
        # 检查Web界面文件
        web_files = [
            "ui/index.html",
            "templates/index.html",
            "static/index.html",
            "dist/index.html"
        ]
        
        existing_web_files = []
        for web_file in web_files:
            if os.path.exists(web_file):
                existing_web_files.append(web_file)
        
        result["web_interface"] = len(existing_web_files) > 0
        result["web_files"] = existing_web_files
        
        # 检查静态文件目录
        static_dirs = ["ui", "static", "dist"]
        existing_static_dirs = []
        for static_dir in static_dirs:
            if os.path.exists(static_dir) and os.path.isdir(static_dir):
                existing_static_dirs.append(static_dir)
        
        result["static_files"] = len(existing_static_dirs) > 0
        result["static_dirs"] = existing_static_dirs
        
        # 检查模板目录
        if os.path.exists("templates") and os.path.isdir("templates"):
            result["templates"] = True
        
        # 检查前端构建
        build_files = ["package.json", "vue.config.js", "react.config.js"]
        existing_build_files = []
        for build_file in build_files:
            if os.path.exists(build_file):
                existing_build_files.append(build_file)
        
        result["frontend_build"] = len(existing_build_files) > 0
        result["build_files"] = existing_build_files
        
        # 检测UI框架
        if os.path.exists("package.json"):
            try:
                with open("package.json", "r") as f:
                    import json
                    package_data = json.load(f)
                    dependencies = package_data.get("dependencies", {})
                    
                    if "vue" in dependencies:
                        result["ui_framework"] = "Vue.js"
                    elif "react" in dependencies:
                        result["ui_framework"] = "React"
                    elif "@angular/core" in dependencies:
                        result["ui_framework"] = "Angular"
                    else:
                        result["ui_framework"] = "Unknown"
                        
            except:
                result["ui_framework"] = None
        
        return result
    
    def detect_library_services(self) -> Dict:
        """检测库服务"""
        result = {
            "library_manager": False,
            "library_config": False,
            "libraries_configured": False,
            "library_paths_valid": False
        }
        
        # 检查库管理器
        try:
            from core.library_manager import LibraryManager
            result["library_manager"] = True
        except ImportError:
            result["library_manager"] = False
        
        # 检查库配置文件
        library_config_file = "config/libraries.yaml"
        if os.path.exists(library_config_file):
            result["library_config"] = True
            
            # 检查配置的库
            try:
                import yaml
                with open(library_config_file, "r") as f:
                    config_data = yaml.safe_load(f)
                    libraries = config_data.get("libraries", {})
                    result["libraries_configured"] = len(libraries) > 0
                    result["library_count"] = len(libraries)
                    
                    # 检查路径有效性
                    valid_paths = 0
                    for lib_id, lib_config in libraries.items():
                        if "path" in lib_config and os.path.exists(lib_config["path"]):
                            valid_paths += 1
                    
                    result["library_paths_valid"] = valid_paths > 0
                    result["valid_path_count"] = valid_paths
                    
            except:
                result["libraries_configured"] = False
        
        return result
    
    def detect_deployment_options(self) -> Dict:
        """检测部署选项"""
        result = {
            "docker": False,
            "docker_compose": False,
            "kubernetes": False,
            "systemd": False
        }
        
        # 检查Docker
        docker_files = ["Dockerfile", "Dockerfile.enhanced"]
        for docker_file in docker_files:
            if os.path.exists(docker_file):
                result["docker"] = True
                break
        
        # 检查Docker Compose
        compose_files = ["docker-compose.yml", "docker-compose.enhanced.yml"]
        for compose_file in compose_files:
            if os.path.exists(compose_file):
                result["docker_compose"] = True
                break
        
        # 检查Kubernetes
        if os.path.exists("kubernetes") and os.path.isdir("kubernetes"):
            k8s_files = os.listdir("kubernetes")
            if any(file.endswith(".yaml") or file.endswith(".yml") for file in k8s_files):
                result["kubernetes"] = True
        
        # 检查systemd服务文件
        if os.path.exists("deploy") and os.path.isdir("deploy"):
            deploy_files = os.listdir("deploy")
            if any("service" in file.lower() for file in deploy_files):
                result["systemd"] = True
        
        return result
    
    def run_comprehensive_detection(self) -> Dict:
        """运行全面检测"""
        print("🔍 开始系统检测...")
        
        detection_results = {
            "system_info": self.system_info,
            "python_environment": self.detect_python_environment(),
            "backend_services": self.detect_backend_services(),
            "frontend_services": self.detect_frontend_services(),
            "library_services": self.detect_library_services(),
            "deployment_options": self.detect_deployment_options()
        }
        
        # 计算总体状态
        backend_ok = detection_results["backend_services"]["app_structure"]
        frontend_ok = detection_results["frontend_services"]["web_interface"]
        python_ok = detection_results["python_environment"]["requirements_installed"]
        
        detection_results["overall_status"] = {
            "backend_ready": backend_ok,
            "frontend_ready": frontend_ok,
            "python_ready": python_ok,
            "system_ready": backend_ok and python_ok
        }
        
        self.detection_results = detection_results
        return detection_results
    
    def print_detection_summary(self):
        """打印检测摘要"""
        if not self.detection_results:
            self.run_comprehensive_detection()
        
        results = self.detection_results
        overall = results["overall_status"]
        
        print("\n📊 系统检测摘要")
        print("=" * 60)
        
        # Python环境
        python_env = results["python_environment"]
        print("🐍 Python环境:")
        print(f"  版本: {python_env['python_version']}")
        print(f"  虚拟环境: {python_env['virtual_env'] or '无'}")
        print(f"  Pip可用: {'✅' if python_env['pip_available'] else '❌'}")
        print(f"  依赖安装: {'✅' if python_env['requirements_installed'] else '❌'}")
        
        # 后端服务
        backend = results["backend_services"]
        print("\n🔧 后端服务:")
        print(f"  FastAPI: {'✅' if backend['fastapi'] else '❌'}")
        print(f"  Uvicorn: {'✅' if backend['uvicorn'] else '❌'}")
        print(f"  应用结构: {'✅' if backend['app_structure'] else '❌'}")
        print(f"  配置文件: {'✅' if backend['config_files'] else '❌'}")
        print(f"  数据库: {'✅' if backend['database'] else '❌'}")
        print(f"  Redis: {'✅' if backend['redis'] else '❌'}")
        
        # 前端服务
        frontend = results["frontend_services"]
        print("\n🎨 前端服务:")
        print(f"  Web界面: {'✅' if frontend['web_interface'] else '❌'}")
        print(f"  静态文件: {'✅' if frontend['static_files'] else '❌'}")
        print(f"  模板: {'✅' if frontend['templates'] else '❌'}")
        print(f"  前端构建: {'✅' if frontend['frontend_build'] else '❌'}")
        print(f"  UI框架: {frontend['ui_framework'] or '无'}")
        
        # 库服务
        library = results["library_services"]
        print("\n📚 库服务:")
        print(f"  库管理器: {'✅' if library['library_manager'] else '❌'}")
        print(f"  库配置: {'✅' if library['library_config'] else '❌'}")
        print(f"  配置库数: {library.get('library_count', 0)}")
        print(f"  有效路径: {library.get('valid_path_count', 0)}")
        
        # 部署选项
        deployment = results["deployment_options"]
        print("\n🚀 部署选项:")
        print(f"  Docker: {'✅' if deployment['docker'] else '❌'}")
        print(f"  Docker Compose: {'✅' if deployment['docker_compose'] else '❌'}")
        print(f"  Kubernetes: {'✅' if deployment['kubernetes'] else '❌'}")
        print(f"  Systemd: {'✅' if deployment['systemd'] else '❌'}")
        
        print("\n" + "=" * 60)
        
        # 总体状态
        print("🎯 总体状态:")
        print(f"  后端就绪: {'✅' if overall['backend_ready'] else '❌'}")
        print(f"  前端就绪: {'✅' if overall['frontend_ready'] else '❌'}")
        print(f"  Python就绪: {'✅' if overall['python_ready'] else '❌'}")
        print(f"  系统就绪: {'✅' if overall['system_ready'] else '❌'}")
        
        print("=" * 60)
        
        # 建议
        if overall["system_ready"]:
            print("🎉 系统准备就绪，可以启动服务")
        else:
            print("⚠️  系统需要配置，请检查以下问题:")
            
            if not overall["python_ready"]:
                print("  • 安装Python依赖: pip install -r requirements.txt")
            
            if not overall["backend_ready"]:
                print("  • 检查后端应用结构")
            
            if not overall["frontend_ready"]:
                print("  • 配置前端界面或使用API模式")


def create_system_detector() -> SystemDetector:
    """创建系统检测器实例"""
    return SystemDetector()


# 测试代码
if __name__ == "__main__":
    detector = create_system_detector()
    detector.run_comprehensive_detection()
    detector.print_detection_summary()