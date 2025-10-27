#!/usr/bin/env python3
"""
MoviePilot PT站点管理器演示脚本
展示基于MoviePilot的PT站点管理功能
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.moviepilot_pt_manager import MoviePilotPTManager, SiteSchema


class MoviePilotPTDemo:
    """MoviePilot PT站点管理器演示类"""
    
    def __init__(self):
        self.pt_manager = MoviePilotPTManager()
        self.setup_demo_sites()
    
    def setup_demo_sites(self):
        """设置演示站点配置"""
        
        # 演示站点配置（实际使用时需要替换为真实的Cookie）
        demo_sites = [
            {
                'name': 'M-Team (演示)',
                'url': 'https://tp.m-team.cc',
                'schema': SiteSchema.NexusPhp,
                'cookie': 'your_mteam_cookie_here',
                'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            {
                'name': 'HDBits (演示)',
                'url': 'https://hdbits.org',
                'schema': SiteSchema.Gazelle,
                'cookie': 'your_hdbits_cookie_here',
                'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            {
                'name': 'Blutopia (演示)',
                'url': 'https://blutopia.xyz',
                'schema': SiteSchema.Unit3d,
                'cookie': 'your_blutopia_cookie_here',
                'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        ]
        
        for site in demo_sites:
            self.pt_manager.add_site(
                name=site['name'],
                url=site['url'],
                schema=site['schema'],
                cookie=site['cookie'],
                ua=site['ua']
            )
    
    def display_user_data(self, site_name: str, user_data):
        """显示用户数据"""
        print(f"\n=== {site_name} 用户数据 ===")
        
        if user_data is None:
            print("❌ 无法获取用户数据")
            return
        
        if user_data.err_msg:
            print(f"❌ 错误: {user_data.err_msg}")
            return
        
        print(f"👤 用户名: {user_data.username or '未知'}")
        print(f"🆔 用户ID: {user_data.userid or '未知'}")
        print(f"⭐ 用户等级: {user_data.user_level or '未知'}")
        print(f"📊 上传量: {self.format_filesize(user_data.upload)}")
        print(f"📥 下载量: {self.format_filesize(user_data.download)}")
        print(f"⚖️  分享率: {user_data.ratio:.3f}")
        print(f"🌱 做种数: {user_data.seeding}")
        print(f"💬 未读消息: {user_data.message_unread}")
        
        # 分享率警告
        if user_data.ratio < 1.0 and user_data.download > 0:
            print("⚠️  警告: 分享率低于1.0，请注意保种！")
    
    def format_filesize(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
    
    def demo_single_site(self):
        """演示单个站点数据获取"""
        print("🚀 开始演示单个站点数据获取...")
        
        # 获取第一个站点的数据
        site_name = list(self.pt_manager.sites.keys())[0]
        user_data = self.pt_manager.get_user_data(site_name)
        
        self.display_user_data(site_name, user_data)
    
    async def demo_async_refresh(self):
        """演示异步刷新所有站点"""
        print("\n🚀 开始演示异步刷新所有站点...")
        
        start_time = datetime.now()
        results = await self.pt_manager.refresh_all_sites()
        end_time = datetime.now()
        
        print(f"⏱️  异步刷新完成，耗时: {(end_time - start_time).total_seconds():.2f}秒")
        
        for site_name, user_data in results.items():
            self.display_user_data(site_name, user_data)
    
    def demo_statistics(self):
        """演示站点统计信息"""
        print("\n📊 开始演示站点统计信息...")
        
        stats = self.pt_manager.get_site_statistics()
        
        if not stats:
            print("❌ 没有可用的统计信息")
            return
        
        print("\n=== 站点统计汇总 ===")
        
        total_upload = 0
        total_download = 0
        total_seeding = 0
        
        for site_name, stat in stats.items():
            print(f"\n📋 {site_name}:")
            print(f"   上传: {self.format_filesize(stat['upload'])}")
            print(f"   下载: {self.format_filesize(stat['download'])}")
            print(f"   分享率: {stat['ratio']:.3f}")
            print(f"   做种数: {stat['seeding']}")
            
            total_upload += stat['upload']
            total_download += stat['download']
            total_seeding += stat['seeding']
        
        print(f"\n📈 总计:")
        print(f"   总上传: {self.format_filesize(total_upload)}")
        print(f"   总下载: {self.format_filesize(total_download)}")
        print(f"   总做种数: {total_seeding}")
        
        if total_download > 0:
            overall_ratio = total_upload / total_download
            print(f"   综合分享率: {overall_ratio:.3f}")
    
    def demo_supported_schemas(self):
        """演示支持的站点框架"""
        print("\n🏗️  支持的站点框架:")
        
        schemas = [
            (SiteSchema.NexusPhp, "NexusPHP框架 - 支持M-Team, TTG, PTHome等"),
            (SiteSchema.Gazelle, "Gazelle框架 - 支持HDBits, PTP, BTN等"),
            (SiteSchema.Unit3d, "Unit3D框架 - 支持Blutopia, Anthelion等"),
            (SiteSchema.DiscuzX, "Discuz框架 - 支持部分国内站点"),
            (SiteSchema.TorrentLeech, "TorrentLeech专用"),
            (SiteSchema.FileList, "FileList专用")
        ]
        
        for schema, description in schemas:
            print(f"  • {schema.value}: {description}")
    
    def run_demo(self):
        """运行完整演示"""
        print("🎬 MoviePilot PT站点管理器演示")
        print("=" * 50)
        
        # 演示支持的框架
        self.demo_supported_schemas()
        
        # 演示单个站点
        self.demo_single_site()
        
        # 演示异步刷新
        asyncio.run(self.demo_async_refresh())
        
        # 演示统计信息
        self.demo_statistics()
        
        print("\n" + "=" * 50)
        print("✅ 演示完成！")
        print("\n💡 使用提示:")
        print("  1. 在配置文件中设置真实的站点Cookie")
        print("  2. 根据需要调整刷新间隔和并发设置")
        print("  3. 启用通知功能获取实时状态更新")


def main():
    """主函数"""
    try:
        demo = MoviePilotPTDemo()
        demo.run_demo()
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        print("💡 请检查依赖是否安装正确:")
        print("  pip install -r requirements.txt")


if __name__ == "__main__":
    main()