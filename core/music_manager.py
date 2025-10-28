"""
音乐管理模块 - 集成ptmusic-sub v2功能
基于VabHub架构设计的音乐订阅和元数据管理系统
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .database import DatabaseManager
from .event import EventManager, EventType
from .config import ConfigManager


class MusicManager:
    """音乐管理器 - 核心业务逻辑"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager()
        self.event_manager = EventManager()
        
        # 音乐订阅配置
        self.subscriptions = {}
        self.metadata_providers = {}
        
    async def initialize(self) -> bool:
        """初始化音乐管理器"""
        try:
            # 加载订阅配置
            await self._load_subscriptions()
            
            # 初始化元数据提供者
            await self._init_metadata_providers()
            
            self.logger.info("音乐管理器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"音乐管理器初始化失败: {e}")
            return False
    
    async def _load_subscriptions(self):
        """加载音乐订阅配置"""
        subscriptions_config = self.config.get('music.subscriptions', {})
        
        for sub_name, sub_config in subscriptions_config.items():
            self.subscriptions[sub_name] = MusicSubscription(sub_name, sub_config)
    
    async def _init_metadata_providers(self):
        """初始化元数据提供者"""
        # iTunes封面提供者
        self.metadata_providers['itunes'] = ITunesMetadataProvider()
        
        # MusicBrainz录音信息提供者
        self.metadata_providers['musicbrainz'] = MusicBrainzProvider()
        
        # LRCLIB歌词提供者
        self.metadata_providers['lyrics'] = LRCLibLyricsProvider()
    
    async def search_music(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """搜索音乐 - 集成Torznab和RSS搜索"""
        results = []
        
        # 并行搜索所有订阅源
        tasks = []
        for subscription in self.subscriptions.values():
            task = subscription.search(query, filters)
            tasks.append(task)
        
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in search_results:
            if isinstance(result, Exception):
                self.logger.error(f"搜索失败: {result}")
                continue
            results.extend(result)
        
        # 去重和排序
        results = self._deduplicate_and_sort(results, filters)
        
        # 触发搜索完成事件
        event_data = {
            'query': query,
            'results_count': len(results),
            'filters': filters
        }
        await self.event_manager.trigger_event(EventType.MUSIC_SEARCH_COMPLETED, event_data)
        
        return results
    
    async def enrich_metadata(self, artist: str, title: str) -> Dict[str, Any]:
        """丰富音乐元数据 - 集成ptmusic-sub v2的enrich功能"""
        metadata = {
            'artist': artist,
            'title': title,
            'enriched_at': datetime.now().isoformat()
        }
        
        # 并行获取各种元数据
        tasks = []
        for provider_name, provider in self.metadata_providers.items():
            task = provider.get_metadata(artist, title)
            tasks.append(task)
        
        metadata_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (provider_name, result) in enumerate(zip(self.metadata_providers.keys(), metadata_results)):
            if isinstance(result, Exception):
                self.logger.warning(f"{provider_name} 元数据获取失败: {result}")
                continue
            metadata[provider_name] = result
        
        # 保存到数据库
        await self.db.save_music_metadata(metadata)
        
        return metadata
    
    async def generate_chart_subscriptions(self, chart_data: List[Dict], top_artists: int = 50) -> List[Dict]:
        """从榜单生成订阅 - 集成ptmusic-sub v2的chartslink功能"""
        from collections import Counter
        
        # 统计热门艺人
        artist_counter = Counter()
        for chart_item in chart_data:
            if chart_item.get('source') in ('apple_music', 'spotify'):
                artist = (chart_item.get('artist_or_show') or '').strip()
                if artist:
                    artist_counter[artist] += 1
        
        # 获取前N名艺人
        top_artists_list = [artist for artist, _ in artist_counter.most_common(top_artists)]
        
        # 生成订阅配置
        subscriptions = []
        for artist in top_artists_list:
            subscription = {
                'name': f'charts-{artist}',
                'mode': 'torznab',
                'query': artist,
                'category': 3000,  # 音乐分类
                'auto_add': False,
                'max_add': 3,
                'rules': {
                    'include_keywords': [artist, 'FLAC', 'WEB', 'ALAC'],
                    'exclude_keywords': ['Pack', '合集', 'Karaoke', 'Instrumental'],
                    'require_quality': ['FLAC', 'ALAC'],
                    'prefer_keywords': ['WEB', 'FLAC', '24bit']
                }
            }
            subscriptions.append(subscription)
        
        return subscriptions
    
    def _deduplicate_and_sort(self, results: List[Dict], filters: Dict[str, Any] = None) -> List[Dict]:
        """去重和排序搜索结果"""
        # 基于标题和文件大小去重
        seen = set()
        unique_results = []
        
        for result in results:
            key = (result.get('title', ''), result.get('size', 0))
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        # 根据规则排序
        if filters and 'sort_by' in filters:
            sort_key = filters['sort_by']
            reverse = filters.get('reverse', False)
            unique_results.sort(key=lambda x: x.get(sort_key, 0), reverse=reverse)
        
        return unique_results


class MusicSubscription:
    """音乐订阅管理"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def search(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行搜索"""
        mode = self.config.get('mode', 'torznab')
        
        if mode == 'torznab':
            return await self._search_torznab(query, filters)
        elif mode == 'rss':
            return await self._search_rss(query, filters)
        else:
            self.logger.warning(f"不支持的搜索模式: {mode}")
            return []
    
    async def _search_torznab(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Torznab搜索"""
        # 实现Torznab API调用
        endpoints = self.config.get('endpoints', [])
        results = []
        
        for endpoint in endpoints:
            try:
                # 调用Torznab API
                torznab_results = await self._call_torznab_api(endpoint, query, filters)
                results.extend(torznab_results)
            except Exception as e:
                self.logger.error(f"Torznab搜索失败 {endpoint}: {e}")
        
        return results
    
    async def _search_rss(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """RSS搜索"""
        # 实现RSS订阅解析
        rss_url = self.config.get('url')
        
        try:
            return await self._parse_rss_feed(rss_url, query, filters)
        except Exception as e:
            self.logger.error(f"RSS搜索失败 {rss_url}: {e}")
            return []
    
    async def _call_torznab_api(self, endpoint: str, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """调用Torznab API"""
        # 实现具体的API调用逻辑
        # 这里简化实现，实际应该使用aiohttp等异步HTTP客户端
        return []
    
    async def _parse_rss_feed(self, rss_url: str, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析RSS订阅"""
        # 实现RSS解析逻辑
        return []


class ITunesMetadataProvider:
    """iTunes元数据提供者"""
    
    async def get_metadata(self, artist: str, title: str) -> Dict[str, Any]:
        """获取iTunes封面和元数据"""
        # 实现iTunes API调用
        return {}


class MusicBrainzProvider:
    """MusicBrainz元数据提供者"""
    
    async def get_metadata(self, artist: str, title: str) -> Dict[str, Any]:
        """获取MusicBrainz录音信息"""
        # 实现MusicBrainz API调用
        return {}


class LRCLibLyricsProvider:
    """LRCLIB歌词提供者"""
    
    async def get_metadata(self, artist: str, title: str) -> Dict[str, Any]:
        """获取歌词信息"""
        # 实现LRCLIB API调用
        return {}