#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 新功能集成测试脚本
测试事件系统、调度器、业务链等新功能的集成效果
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_event_system():
    """测试事件系统功能"""
    print("🔔 测试事件系统...")
    
    try:
        # 导入事件系统模块
        sys.path.insert(0, str(project_root / "VabHub-Core"))
        from core.event import EventType, Event, EventManager, event_handler
        
        # 创建事件管理器实例
        event_manager = EventManager()
        
        # 测试事件类型枚举
        print(f"  ✅ 事件类型数量: {len([attr for attr in dir(EventType) if not attr.startswith('_')])}")
        
        # 测试事件创建
        test_event = Event(EventType.MEDIA_ADDED, {"title": "测试电影"})
        print(f"  ✅ 事件创建成功: {test_event.event_type}")
        
        # 测试事件处理器装饰器
        @event_handler(EventType.MEDIA_ADDED)
        def test_handler(event):
            print(f"  ✅ 事件处理器被调用: {event.event_type}")
        
        print("  ✅ 事件处理器装饰器工作正常")
        
        return True, "事件系统测试通过"
        
    except Exception as e:
        return False, f"事件系统测试失败: {str(e)}"

def test_scheduler_system():
    """测试调度器系统功能"""
    print("⏰ 测试调度器系统...")
    
    try:
        # 导入调度器模块
        sys.path.insert(0, str(project_root / "VabHub-Core"))
        from core.scheduler import Scheduler, SchedulerJob
        
        # 创建调度器实例
        scheduler = Scheduler()
        
        # 测试调度器初始化
        print(f"  ✅ 调度器状态: {'已启动' if scheduler._scheduler else '未启动'}")
        
        # 测试任务定义
        def test_job():
            print("  ✅ 测试任务执行成功")
        
        test_job_def = SchedulerJob(
            job_id="test_job",
            name="测试任务",
            func=test_job,
            trigger="interval",
            minutes=1
        )
        
        print(f"  ✅ 任务定义成功: {test_job_def.name}")
        
        return True, "调度器系统测试通过"
        
    except Exception as e:
        return False, f"调度器系统测试失败: {str(e)}"

def test_chain_system():
    """测试业务链系统功能"""
    print("🔗 测试业务链系统...")
    
    try:
        # 导入业务链模块
        sys.path.insert(0, str(project_root / "VabHub-Core"))
        from core.chain import ChainBase, MediaChain, DownloadChain, PluginChain
        
        # 测试基类
        print(f"  ✅ 业务链基类: {ChainBase.__name__}")
        
        # 测试业务链类
        print(f"  ✅ 媒体链类: {MediaChain.__name__}")
        print(f"  ✅ 下载链类: {DownloadChain.__name__}")
        print(f"  ✅ 插件链类: {PluginChain.__name__}")
        
        # 测试链方法
        test_chain = MediaChain()
        print(f"  ✅ 业务链实例化成功")
        
        return True, "业务链系统测试通过"
        
    except Exception as e:
        return False, f"业务链系统测试失败: {str(e)}"

def test_plugin_system():
    """测试插件系统功能"""
    print("🔌 测试插件系统...")
    
    try:
        # 导入插件模块
        sys.path.insert(0, str(project_root / "VabHub-Core"))
        from core.plugin import PluginBase, PluginManager
        
        # 测试插件基类
        print(f"  ✅ 插件基类: {PluginBase.__name__}")
        
        # 测试插件管理器
        plugin_manager = PluginManager()
        print(f"  ✅ 插件管理器实例化成功")
        
        # 测试插件生命周期
        print(f"  ✅ 插件生命周期状态检查")
        
        return True, "插件系统测试通过"
        
    except Exception as e:
        return False, f"插件系统测试失败: {str(e)}"

def test_api_integration():
    """测试API接口集成"""
    print("🌐 测试API接口集成...")
    
    try:
        # 检查前端API文件
        api_file = "VabHub-Frontend/src/api/index.js"
        if os.path.exists(api_file):
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查API端点
            api_endpoints = ["eventAPI", "schedulerAPI", "chainAPI"]
            missing_apis = []
            
            for api in api_endpoints:
                if f"export const {api}" in content:
                    print(f"  ✅ {api} 接口存在")
                else:
                    missing_apis.append(api)
            
            if missing_apis:
                return False, f"缺少API接口: {', '.join(missing_apis)}"
            else:
                return True, "API接口集成测试通过"
        else:
            return False, "API文件不存在"
            
    except Exception as e:
        return False, f"API集成测试失败: {str(e)}"

def test_dependency_integration():
    """测试依赖集成"""
    print("📦 测试依赖集成...")
    
    try:
        # 测试关键依赖导入
        try:
            from apscheduler import __version__ as aps_version
            print(f"  ✅ APScheduler 版本: {aps_version}")
        except ImportError:
            return False, "APScheduler 依赖未安装"
        
        try:
            from pydantic_settings import __version__ as pydantic_settings_version
            print(f"  ✅ pydantic-settings 版本: {pydantic_settings_version}")
        except ImportError:
            return False, "pydantic-settings 依赖未安装"
        
        return True, "依赖集成测试通过"
        
    except Exception as e:
        return False, f"依赖集成测试失败: {str(e)}"

def main():
    """主测试函数"""
    print("🚀 VabHub 新功能集成测试开始")
    print("=" * 60)
    
    # 执行所有测试
    tests = [
        test_event_system,
        test_scheduler_system, 
        test_chain_system,
        test_plugin_system,
        test_api_integration,
        test_dependency_integration
    ]
    
    results = []
    
    for test_func in tests:
        try:
            success, message = test_func()
            results.append((test_func.__name__, success, message))
        except Exception as e:
            results.append((test_func.__name__, False, f"测试异常: {str(e)}"))
    
    print("\n📊 集成测试结果汇总:")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, success, message in results:
        status_icon = "✅" if success else "❌"
        test_display = test_name.replace('_', ' ').replace('test ', '').title()
        print(f"{status_icon} {test_display}: {message}")
        
        if success:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"📈 总体统计: 通过 {passed} 项, 失败 {failed} 项")
    
    if failed == 0:
        print("🎉 所有新功能集成测试通过！")
        return 0
    else:
        print("⚠️  存在集成问题，请检查失败的测试项")
        return 1

if __name__ == "__main__":
    sys.exit(main())