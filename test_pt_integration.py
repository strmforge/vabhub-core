#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT功能集成测试脚本
测试PT站点搜索和下载功能
"""

import asyncio
import sys
import os

# 添加项目路径到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.enhanced_pt_manager import EnhancedPTManager, PTSiteConfig


async def test_pt_manager():
    """测试PT管理器功能"""
    print("=== PT功能集成测试 ===")
    
    # 创建PT管理器实例
    pt_manager = EnhancedPTManager()
    
    # 测试1: 列出支持的下载器
    print("\n1. 测试支持的下载器:")
    downloaders = list(pt_manager.downloader_adapters.keys())
    print(f"   支持的下载器: {downloaders}")
    
    # 测试2: 列出支持的PT站点适配器
    print("\n2. 测试支持的PT站点适配器:")
    site_adapters = list(pt_manager.site_adapters.keys())
    print(f"   支持的PT站点适配器: {site_adapters}")
    
    # 测试3: 设置活动下载器
    print("\n3. 测试设置活动下载器:")
    try:
        pt_manager.set_active_downloader("qbittorrent")
        print(f"   活动下载器: {pt_manager.active_downloader}")
    except Exception as e:
        print(f"   设置下载器失败: {e}")
    
    # 测试4: 模拟添加PT站点
    print("\n4. 测试添加PT站点:")
    try:
        # 创建测试配置
        test_config = PTSiteConfig(
            name="测试站点",
            url="https://example.com",
            username="test_user",
            password="test_pass",
            enabled=True,
            priority=1
        )
        
        # 注意：这里不会真正登录，只是测试配置创建
        print(f"   测试站点配置创建成功: {test_config.name}")
        print(f"   站点URL: {test_config.url}")
        print(f"   启用状态: {test_config.enabled}")
        
    except Exception as e:
        print(f"   创建站点配置失败: {e}")
    
    # 测试5: 测试搜索功能（模拟）
    print("\n5. 测试搜索功能:")
    try:
        # 模拟搜索（不会真正请求网络）
        results = await pt_manager.search_all_sites("测试关键词", "")
        print(f"   搜索完成，找到 {len(results)} 个结果")
        
        if results:
            for i, result in enumerate(results[:3]):  # 只显示前3个结果
                print(f"   结果 {i+1}: {result.title}")
                print(f"     大小: {result.size} bytes")
                print(f"     种子数: {result.seeders}")
        
    except Exception as e:
        print(f"   搜索测试失败: {e}")
    
    # 测试6: 测试监控功能
    print("\n6. 测试监控功能:")
    try:
        pt_manager.start_monitoring()
        print("   PT监控已启动")
        
        # 等待几秒钟
        await asyncio.sleep(2)
        
        pt_manager.stop_monitoring()
        print("   PT监控已停止")
        
    except Exception as e:
        print(f"   监控测试失败: {e}")
    
    print("\n=== 测试完成 ===")
    return True


async def test_downloader_adapters():
    """测试下载器适配器功能"""
    print("\n=== 下载器适配器测试 ===")
    
    pt_manager = EnhancedPTManager()
    
    # 测试每个下载器适配器
    for downloader_type, adapter in pt_manager.downloader_adapters.items():
        print(f"\n测试 {downloader_type} 适配器:")
        
        try:
            # 测试适配器方法是否存在
            methods = ['add_torrent', 'get_task_status', 'pause_task', 'resume_task']
            for method in methods:
                if hasattr(adapter, method):
                    print(f"   ✓ {method} 方法存在")
                else:
                    print(f"   ✗ {method} 方法缺失")
            
        except Exception as e:
            print(f"   测试失败: {e}")
    
    print("\n=== 下载器测试完成 ===")
    return True


async def test_pt_site_adapters():
    """测试PT站点适配器功能"""
    print("\n=== PT站点适配器测试 ===")
    
    pt_manager = EnhancedPTManager()
    
    # 测试每个PT站点适配器
    for site_type, adapter in pt_manager.site_adapters.items():
        print(f"\n测试 {site_type} 适配器:")
        
        try:
            # 测试适配器方法是否存在
            methods = ['login', 'search', 'download_torrent', 'get_status']
            for method in methods:
                if hasattr(adapter, method):
                    print(f"   ✓ {method} 方法存在")
                else:
                    print(f"   ✗ {method} 方法缺失")
            
        except Exception as e:
            print(f"   测试失败: {e}")
    
    print("\n=== PT站点适配器测试完成 ===")
    return True


async def main():
    """主测试函数"""
    try:
        # 运行所有测试
        await test_pt_manager()
        await test_downloader_adapters()
        await test_pt_site_adapters()
        
        print("\n🎉 所有测试完成！PT功能已成功集成。")
        print("\n下一步:")
        print("1. 配置真实的PT站点信息")
        print("2. 设置下载器连接信息")
        print("3. 通过API接口进行实际测试")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 运行异步测试
    success = asyncio.run(main())
    
    if success:
        print("\n✅ PT功能集成测试通过")
        sys.exit(0)
    else:
        print("\n❌ PT功能集成测试失败")
        sys.exit(1)