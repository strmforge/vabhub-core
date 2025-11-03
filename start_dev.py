#!/usr/bin/env python3
"""
VabHub 开发环境启动脚本
同时启动后端API服务和前端开发服务器
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "vabhub-Core"
FRONTEND_DIR = PROJECT_ROOT / "vabhub-frontend"

class DevServer:
    """开发服务器管理器"""
    
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.running = False
    
    def start_backend(self):
        """启动后端API服务"""
        print("🚀 启动 VabHub 后端服务...")
        
        # 检查后端目录是否存在
        if not BACKEND_DIR.exists():
            print(f"❌ 后端目录不存在: {BACKEND_DIR}")
            return False
        
        # 检查requirements.txt是否存在
        requirements_file = BACKEND_DIR / "requirements.txt"
        if not requirements_file.exists():
            print(f"❌ 后端依赖文件不存在: {requirements_file}")
            return False
        
        # 安装后端依赖
        print("📦 安装后端依赖...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", 
                str(requirements_file)
            ], cwd=BACKEND_DIR, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ 后端依赖安装失败: {e}")
            return False
        
        # 启动后端服务
        print("🔧 启动后端API服务...")
        try:
            self.backend_process = subprocess.Popen([
                sys.executable, "start.py"
            ], cwd=BACKEND_DIR, 
               stdout=subprocess.PIPE, 
               stderr=subprocess.PIPE,
               text=True)
            
            # 启动后台线程读取输出
            backend_thread = threading.Thread(
                target=self._read_backend_output,
                daemon=True
            )
            backend_thread.start()
            
            # 等待后端服务启动
            time.sleep(3)
            
            if self.backend_process.poll() is not None:
                print("❌ 后端服务启动失败")
                return False
            
            print("✅ 后端服务启动成功")
            return True
            
        except Exception as e:
            print(f"❌ 后端服务启动错误: {e}")
            return False
    
    def start_frontend(self):
        """启动前端开发服务器"""
        print("🚀 启动 VabHub 前端服务...")
        
        # 检查前端目录是否存在
        if not FRONTEND_DIR.exists():
            print(f"❌ 前端目录不存在: {FRONTEND_DIR}")
            return False
        
        # 检查package.json是否存在
        package_file = FRONTEND_DIR / "package.json"
        if not package_file.exists():
            print(f"❌ 前端依赖文件不存在: {package_file}")
            return False
        
        # 安装前端依赖
        print("📦 安装前端依赖...")
        try:
            # 检查是否安装了npm
            subprocess.run(["npm", "--version"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("❌ npm 未安装，请先安装 Node.js")
            return False
        
        try:
            subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ 前端依赖安装失败: {e}")
            return False
        
        # 启动前端开发服务器
        print("🔧 启动前端开发服务器...")
        try:
            self.frontend_process = subprocess.Popen([
                "npm", "run", "dev"
            ], cwd=FRONTEND_DIR,
               stdout=subprocess.PIPE,
               stderr=subprocess.PIPE,
               text=True)
            
            # 启动后台线程读取输出
            frontend_thread = threading.Thread(
                target=self._read_frontend_output,
                daemon=True
            )
            frontend_thread.start()
            
            # 等待前端服务启动
            time.sleep(5)
            
            if self.frontend_process.poll() is not None:
                print("❌ 前端服务启动失败")
                return False
            
            print("✅ 前端服务启动成功")
            return True
            
        except Exception as e:
            print(f"❌ 前端服务启动错误: {e}")
            return False
    
    def _read_backend_output(self):
        """读取后端输出"""
        while self.backend_process and self.backend_process.stdout:
            line = self.backend_process.stdout.readline()
            if line:
                print(f"[后端] {line.strip()}")
    
    def _read_frontend_output(self):
        """读取前端输出"""
        while self.frontend_process and self.frontend_process.stdout:
            line = self.frontend_process.stdout.readline()
            if line:
                print(f"[前端] {line.strip()}")
    
    def start(self):
        """启动开发环境"""
        print("=" * 50)
        print("🎯 VabHub 开发环境启动")
        print("=" * 50)
        
        self.running = True
        
        # 启动后端
        if not self.start_backend():
            self.stop()
            return
        
        # 启动前端
        if not self.start_frontend():
            self.stop()
            return
        
        print("\n" + "=" * 50)
        print("🎉 VabHub 开发环境启动完成!")
        print("📊 后端API: http://localhost:8000")
        print("📊 API文档: http://localhost:8000/docs")
        print("🌐 前端界面: http://localhost:5173")
        print("📋 实时日志: http://localhost:5173/logs")
        print("=" * 50)
        print("\n按 Ctrl+C 停止服务...")
        
        # 等待用户中断
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 正在停止服务...")
            self.stop()
    
    def stop(self):
        """停止所有服务"""
        self.running = False
        
        if self.frontend_process:
            print("🛑 停止前端服务...")
            self.frontend_process.terminate()
            self.frontend_process.wait(timeout=10)
        
        if self.backend_process:
            print("🛑 停止后端服务...")
            self.backend_process.terminate()
            self.backend_process.wait(timeout=10)
        
        print("✅ 所有服务已停止")


def main():
    """主函数"""
    # 检查必要的目录
    if not BACKEND_DIR.exists():
        print(f"❌ 后端目录不存在: {BACKEND_DIR}")
        return
    
    if not FRONTEND_DIR.exists():
        print(f"❌ 前端目录不存在: {FRONTEND_DIR}")
        return
    
    # 创建并启动开发服务器
    server = DevServer()
    
    # 注册信号处理
    def signal_handler(signum, frame):
        print("\n🛑 收到停止信号...")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动服务
    server.start()


if __name__ == "__main__":
    main()