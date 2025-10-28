#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 集成测试
测试对标MoviePilot的所有核心模块
"""

import asyncio
import time
from pathlib import Path

from core.config import VabHubConfig
from core.event import EventType, Event, event_manager
from core.scheduler import scheduler
from core.chain import MediaChain, DownloadChain, PluginChain
from core.plugin import PluginManager, PluginBase


class TestPlugin(PluginBase):
    """测试插件"""
    
    plugin_id = "test_plugin"
    plugin_name = "测试插件"
    plugin_desc = "用于集成测试的插件"
    plugin_version = "1.0.0"
    plugin_author = "VabHub Team"
    
    def init(self):
        """初始化插件"""
        print("测试插件初始化完成")
    
    def test_method(self, data: dict) -> dict:
        """测试方法"""
        return {"result": "success", "data": data}


async def test_config_system():
    """测试配置系统"""
    print("=== 测试配置系统 ===")
    
    config = VabHubConfig()
    print(f"应用名称: {config.app_name}")
    print(f"版本号: {config.version}")
    print(f"服务端口: {config.port}")
    print(f"调试模式: {config.debug}")
    
    # 测试系统资源配置
    print(f"缓存种子数量: {config.system_conf.torrents}")
    print(f"线程池大小: {config.system_conf.threadpool}")
    
    print("配置系统测试完成\n")


async def test_event_system():
    """测试事件系统"""
    print("=== 测试事件系统 ===")
    
    # 定义事件处理器
    @event_manager.event_handler(EventType.SYSTEM_STARTUP)
    def handle_startup(event: Event):
        print(f"收到系统启动事件: {event.event_id}")
    
    @event_manager.event_handler(EventType.MEDIA_ADDED)
    def handle_media_added(event: Event):
        media_info = event.event_data.get("media", {})
        print(f"收到媒体添加事件: {media_info.get('title', 'Unknown')}")
    
    # 启动事件管理器
    event_manager.start()
    
    # 发送测试事件
    event_manager.send_event(Event(EventType.SYSTEM_STARTUP))
    event_manager.send_event(Event(EventType.MEDIA_ADDED, {"media": {"title": "Test Movie", "year": 2024}}))
    
    # 等待事件处理完成
    await asyncio.sleep(1)
    
    # 停止事件管理器
    event_manager.stop()
    
    print("事件系统测试完成\n")


async def test_scheduler_system():
    """测试调度器系统"""
    print("=== 测试调度器系统 ===")
    
    # 启动调度器
    scheduler.start()
    
    # 获取任务列表
    jobs = scheduler.get_jobs()
    print(f"当前任务数量: {len(jobs)}")
    for job in jobs:
        print(f"任务: {job['name']}, 触发器: {job['trigger']}")
    
    # 运行一段时间
    await asyncio.sleep(3)
    
    # 停止调度器
    scheduler.stop()
    
    print("调度器系统测试完成\n")


async def test_chain_system():
    """测试业务链系统"""
    print("=== 测试业务链系统 ===")
    
    # 测试媒体链
    media_chain = MediaChain()
    result = media_chain.scan_media_library(Path("/test/media"))
    print(f"媒体库扫描结果: {result}")
    
    # 测试下载链
    download_chain = DownloadChain()
    result = download_chain.download_torrent("http://example.com/torrent", Path("/test/downloads"))
    print(f"种子下载结果: {result}")
    
    print("业务链系统测试完成\n")


async def test_plugin_system():
    """测试插件系统"""
    print("=== 测试插件系统 ===")
    
    plugin_manager = PluginManager()
    
    # 扫描插件
    plugins = plugin_manager.scan_plugins()
    print(f"扫描到的插件数量: {len(plugins)}")
    
    # 加载测试插件
    if plugin_manager.load_plugin("test_plugin"):
        print("测试插件加载成功")
        
        # 执行插件方法
        result = plugin_manager.execute_plugin_method("test_plugin", "test_method", {"test": "data"})
        print(f"插件方法执行结果: {result}")
        
        # 获取运行中的插件
        running_plugins = plugin_manager.get_running_plugins()
        print(f"运行中的插件数量: {len(running_plugins)}")
        
        # 卸载插件
        plugin_manager.unload_plugin("test_plugin")
        print("测试插件已卸载")
    else:
        print("测试插件加载失败")
    
    print("插件系统测试完成\n")


async def main():
    """主测试函数"""
    print("开始VabHub集成测试...\n")
    
    try:
        # 测试配置系统
        await test_config_system()
        
        # 测试事件系统
        await test_event_system()
        
        # 测试调度器系统
        await test_scheduler_system()
        
        # 测试业务链系统
        await test_chain_system()
        
        # 测试插件系统
        await test_plugin_system()
        
        print("所有集成测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())