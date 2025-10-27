#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT功能集成模块
将media-renamer的PT功能集成到VabHub中
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .enhanced_pt_manager import PTManager
from .enhanced_downloader import download_manager
from .smart_recognizer import SmartRecognizer

logger = logging.getLogger(__name__)


class PTIntegration:
    """PT功能集成类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pt_manager = None
        self.recognizer = None
        self.initialized = False
    
    async def initialize(self) -> bool:
        """初始化PT功能"""
        try:
            # 初始化PT管理器
            self.pt_manager = PTManager(self.config.get('pt_sites', {}))
            
            # 初始化智能识别器
            self.recognizer = SmartRecognizer()
            
            # 初始化下载器
            downloader_config = self.config.get('downloaders', {})
            for name, config in downloader_config.items():
                if config.get('enabled', False):
                    await download_manager.add_downloader(name, name, config)
            
            self.initialized = True
            logger.info("✅ PT功能集成初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ PT功能集成初始化失败: {e}")
            return False
    
    async def search_torrents(self, keywords: List[str], 
                            categories: List[str] = None,
                            sites: List[str] = None) -> List[Dict[str, Any]]:
        """搜索种子"""
        if not self.initialized:
            raise Exception("请先初始化PT功能")
        
        try:
            results = []
            
            for keyword in keywords:
                # 使用智能识别器解析关键词
                parsed_info = self.recognizer.parse_filename(keyword)
                
                # 在指定站点搜索
                torrents = await self.pt_manager.search_torrents(
                    keyword=keyword,
                    sites=sites or [],
                    categories=categories or []
                )
                
                for torrent in torrents:
                    # 增强种子信息
                    enhanced_torrent = self._enhance_torrent_info(torrent, parsed_info)
                    results.append(enhanced_torrent)
            
            # 按匹配度排序
            results.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            
            logger.info(f"✅ 搜索完成，找到 {len(results)} 个种子")
            return results
            
        except Exception as e:
            logger.error(f"❌ 搜索种子失败: {e}")
            return []
    
    def _enhance_torrent_info(self, torrent: Dict[str, Any], 
                            parsed_info: Dict[str, Any]) -> Dict[str, Any]:
        """增强种子信息"""
        enhanced = torrent.copy()
        
        # 计算匹配度分数
        match_score = 0
        
        # 标题匹配
        title = torrent.get('title', '').lower()
        if parsed_info.get('title'):
            if parsed_info['title'].lower() in title:
                match_score += 30
        
        # 年份匹配
        if parsed_info.get('year') and str(parsed_info['year']) in title:
            match_score += 20
        
        # 质量匹配
        if parsed_info.get('quality'):
            quality = parsed_info['quality'].lower()
            if quality in title:
                match_score += 15
        
        # 编码匹配
        if parsed_info.get('video_codec'):
            codec = parsed_info['video_codec'].lower()
            if codec in title:
                match_score += 10
        
        # 发布组匹配
        if parsed_info.get('release_group'):
            group = parsed_info['release_group'].lower()
            if group in title:
                match_score += 25
        
        enhanced['match_score'] = match_score
        enhanced['parsed_info'] = parsed_info
        
        return enhanced
    
    async def download_torrent(self, torrent_info: Dict[str, Any],
                             save_path: str = None,
                             category: str = None) -> bool:
        """下载种子"""
        if not self.initialized:
            raise Exception("请先初始化PT功能")
        
        try:
            # 下载种子文件
            torrent_file = await self.pt_manager.download_torrent(torrent_info)
            
            if not torrent_file:
                logger.error("❌ 下载种子文件失败")
                return False
            
            # 添加到下载器
            success = await download_manager.download_torrent(
                torrent_file=torrent_file,
                save_path=save_path,
                category=category
            )
            
            if success:
                logger.info(f"✅ 种子下载成功: {torrent_info.get('title')}")
                
                # 记录下载历史
                await self._record_download_history(torrent_info)
                
            return success
            
        except Exception as e:
            logger.error(f"❌ 下载种子失败: {e}")
            return False
    
    async def _record_download_history(self, torrent_info: Dict[str, Any]):
        """记录下载历史"""
        try:
            history_file = Path("download_history.json")
            history = []
            
            if history_file.exists():
                import json
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # 添加新记录
            record = {
                'title': torrent_info.get('title'),
                'site': torrent_info.get('site'),
                'download_time': asyncio.get_event_loop().time(),
                'size': torrent_info.get('size'),
                'seeds': torrent_info.get('seeds'),
                'leechers': torrent_info.get('leechers')
            }
            
            history.append(record)
            
            # 保存历史记录
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"记录下载历史失败: {e}")
    
    async def get_download_status(self) -> Dict[str, Any]:
        """获取下载状态"""
        if not self.initialized:
            return {'connected': False}
        
        try:
            status = await download_manager.get_download_status()
            
            # 添加PT站点状态
            pt_status = await self.pt_manager.get_site_status()
            status['pt_sites'] = pt_status
            
            return status
            
        except Exception as e:
            logger.error(f"获取下载状态失败: {e}")
            return {'connected': False}
    
    async def auto_download(self, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """自动下载"""
        if not self.initialized:
            raise Exception("请先初始化PT功能")
        
        try:
            downloaded = []
            
            # 获取RSS订阅
            rss_feeds = rules.get('rss_feeds', [])
            for feed in rss_feeds:
                torrents = await self.pt_manager.get_rss_feed(feed)
                
                for torrent in torrents:
                    # 检查是否符合下载规则
                    if self._check_download_rule(torrent, rules):
                        # 下载种子
                        success = await self.download_torrent(torrent)
                        if success:
                            downloaded.append(torrent)
            
            logger.info(f"✅ 自动下载完成，成功下载 {len(downloaded)} 个种子")
            return downloaded
            
        except Exception as e:
            logger.error(f"❌ 自动下载失败: {e}")
            return []
    
    def _check_download_rule(self, torrent: Dict[str, Any], 
                           rules: Dict[str, Any]) -> bool:
        """检查是否符合下载规则"""
        # 检查大小限制
        size = torrent.get('size', 0)
        min_size = self._parse_size(rules.get('min_size', '0'))
        max_size = self._parse_size(rules.get('max_size', '100GB'))
        
        if size < min_size or size > max_size:
            return False
        
        # 检查质量要求
        quality = torrent.get('quality', '').lower()
        allowed_qualities = [q.lower() for q in rules.get('quality', [])]
        if allowed_qualities and quality not in allowed_qualities:
            return False
        
        # 检查种子健康度
        seeds = torrent.get('seeds', 0)
        min_seeds = rules.get('min_seeds', 1)
        if seeds < min_seeds:
            return False
        
        return True
    
    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串"""
        size_str = size_str.upper().strip()
        
        multipliers = {
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'TB': 1024 * 1024 * 1024 * 1024
        }
        
        for unit, multiplier in multipliers.items():
            if size_str.endswith(unit):
                num = float(size_str[:-len(unit)])
                return int(num * multiplier)
        
        # 默认字节
        return int(size_str)
    
    async def close(self):
        """关闭连接"""
        if self.pt_manager:
            await self.pt_manager.close()
        
        await download_manager.close_all()
        
        self.initialized = False
        logger.info("✅ PT功能集成已关闭")


# 全局PT集成实例
pt_integration = None


async def get_pt_integration(config: Dict[str, Any] = None) -> PTIntegration:
    """获取PT集成实例"""
    global pt_integration
    
    if pt_integration is None and config:
        pt_integration = PTIntegration(config)
        await pt_integration.initialize()
    
    return pt_integration