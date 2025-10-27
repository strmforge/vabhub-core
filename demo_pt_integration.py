#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT功能集成演示脚本
展示media-renamer功能集成到VabHub后的使用
"""

import asyncio
import json
import yaml
from pathlib import Path

from core.pt_integration import get_pt_integration


async def demo_pt_integration():
    """演示PT功能集成"""
    print("🚀 VabHub PT功能集成演示")
    print("=" * 50)
    
    # 加载配置
    config_path = Path("config/pt_config.yaml")
    if not config_path.exists():
        print("❌ 配置文件不存在，请先创建 config/pt_config.yaml")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 获取PT集成实例
    pt_integration = await get_pt_integration(config)
    if not pt_integration:
        print("❌ PT功能集成初始化失败")
        return
    
    print("✅ PT功能集成初始化成功")
    
    try:
        # 演示1: 搜索种子
        print("\n📋 演示1: 搜索种子")
        print("-" * 30)
        
        keywords = ["Avengers Endgame 2019 4K", "Game of Thrones S01"]
        results = await pt_integration.search_torrents(keywords)
        
        print(f"🔍 搜索关键词: {keywords}")
        print(f"📊 找到 {len(results)} 个种子")
        
        for i, result in enumerate(results[:3]):  # 显示前3个结果
            print(f"\n{i+1}. {result.get('title')}")
            print(f"   站点: {result.get('site')}")
            print(f"   大小: {result.get('size', 0) / (1024**3):.2f} GB")
            print(f"   做种: {result.get('seeds', 0)}")
            print(f"   下载: {result.get('leechers', 0)}")
            print(f"   匹配度: {result.get('match_score', 0)}%")
        
        # 演示2: 获取下载状态
        print("\n📊 演示2: 下载状态")
        print("-" * 30)
        
        status = await pt_integration.get_download_status()
        if status.get('connected'):
            print(f"✅ 下载器: {status.get('downloader')}")
            print(f"📥 下载速度: {status.get('download_speed', 0) / 1024:.2f} KB/s")
            print(f"📤 上传速度: {status.get('upload_speed', 0) / 1024:.2f} KB/s")
            print(f"📦 活跃任务: {status.get('active_torrents', 0)}")
            print(f"📋 总任务数: {status.get('total_torrents', 0)}")
        else:
            print("❌ 下载器未连接")
        
        # 演示3: 智能识别
        print("\n🤖 演示3: 智能识别")
        print("-" * 30)
        
        test_files = [
            "Avengers.Endgame.2019.IMAX.2160p.BluRay.REMUX.HEVC.DTS-HD.MA.TrueHD.7.1.Atmos-FRDS.mkv",
            "Game.of.Thrones.S01E01.Winter.Is.Coming.1080p.BluRay.x264-DIMENSION.mkv",
            "The.Matrix.1999.4K.HDR.DV.2160p.BluRay.REMUX.HEVC.DTS-HD.MA.5.1-EVO.mkv"
        ]
        
        for filename in test_files:
            parsed_info = pt_integration.recognizer.parse_filename(filename)
            print(f"\n📁 文件名: {filename}")
            print(f"   解析结果: {json.dumps(parsed_info, ensure_ascii=False, indent=2)}")
        
        # 演示4: PT站点状态
        print("\n🌐 演示4: PT站点状态")
        print("-" * 30)
        
        pt_status = status.get('pt_sites', {})
        for site_name, site_info in pt_status.items():
            print(f"\n{site_name}:")
            print(f"   状态: {'✅ 在线' if site_info.get('online') else '❌ 离线'}")
            print(f"   用户名: {site_info.get('username', 'N/A')}")
            print(f"   上传量: {site_info.get('uploaded', 0) / (1024**3):.2f} GB")
            print(f"   下载量: {site_info.get('downloaded', 0) / (1024**3):.2f} GB")
            print(f"   分享率: {site_info.get('ratio', 0):.2f}")
        
        # 演示5: 自动下载规则检查
        print("\n⚙️ 演示5: 自动下载规则")
        print("-" * 30)
        
        auto_rules = config.get('auto_download_rules', {})
        print("电影下载规则:")
        print(f"  最小大小: {auto_rules.get('movie', {}).get('min_size', 'N/A')}")
        print(f"  最大大小: {auto_rules.get('movie', {}).get('max_size', 'N/A')}")
        print(f"  质量要求: {auto_rules.get('movie', {}).get('quality', [])}")
        
        print("\n电视剧下载规则:")
        print(f"  最小大小: {auto_rules.get('tv', {}).get('min_size', 'N/A')}")
        print(f"  最大大小: {auto_rules.get('tv', {}).get('max_size', 'N/A')}")
        print(f"  质量要求: {auto_rules.get('tv', {}).get('quality', [])}")
        
        print("\n🎉 演示完成!")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
    
    finally:
        # 关闭连接
        await pt_integration.close()
        print("\n🔚 已关闭所有连接")


async def demo_enhanced_features():
    """演示增强功能"""
    print("\n🚀 VabHub 增强功能演示")
    print("=" * 50)
    
    # 演示智能识别器的强大功能
    from core.smart_recognizer import SmartRecognizer
    
    recognizer = SmartRecognizer()
    
    # 测试复杂的文件名识别
    test_cases = [
        "The.Shawshank.Redemption.1994.BluRay.1080p.x264.DTS-CNXP",
        "Interstellar.2014.IMAX.2160p.UHD.BluRay.x265.10bit.HDR.DTS-HD.MA.5.1-SWTYBLZ",
        "Breaking.Bad.S05E14.Ozymandias.1080p.BluRay.x264-REWARD",
        "【CHD】The.Dark.Knight.2008.2160p.UHD.Blu-ray.HEVC.TrueHD.7.1-ADC"
    ]
    
    print("🤖 智能识别演示:")
    for filename in test_cases:
        result = recognizer.parse_filename(filename)
        print(f"\n📁 {filename}")
        print(f"   标题: {result.get('title', 'N/A')}")
        print(f"   年份: {result.get('year', 'N/A')}")
        print(f"   质量: {result.get('quality', 'N/A')}")
        print(f"   编码: {result.get('video_codec', 'N/A')}")
        print(f"   音频: {result.get('audio_codec', 'N/A')}")
        print(f"   发布组: {result.get('release_group', 'N/A')}")
        print(f"   季数: {result.get('season', 'N/A')}")
        print(f"   集数: {result.get('episode', 'N/A')}")
    
    # 演示PT站点适配器
    from core.enhanced_pt_manager import PTManager
    
    print("\n🌐 PT站点适配器演示:")
    
    # 创建模拟配置
    mock_config = {
        'nexusphp': [
            {
                'name': 'demo-site',
                'url': 'https://demo.pt.site',
                'cookie': 'demo_cookie',
                'user_agent': 'Mozilla/5.0 Demo'
            }
        ]
    }
    
    pt_manager = PTManager(mock_config)
    
    # 演示站点适配器类型
    print("支持的站点类型:")
    for site_type, adapters in pt_manager.site_adapters.items():
        print(f"  {site_type}: {len(adapters)} 个适配器")
    
    print("\n🎉 增强功能演示完成!")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_pt_integration())
    asyncio.run(demo_enhanced_features())