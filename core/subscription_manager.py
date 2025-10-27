#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订阅管理系统
集成 MoviePilot 的自动化订阅管理精华功能
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import aiohttp
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SubscriptionStatus(Enum):
    """订阅状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


class DownloaderType(Enum):
    """下载器类型"""
    QBITTORRENT = "qbittorrent"
    TRANSMISSION = "transmission"
    ARIA2 = "aria2"


@dataclass
class RSSFeed:
    """RSS订阅源配置"""
    name: str
    url: str
    filters: Dict[str, Any] = field(default_factory=dict)
    last_check: Optional[datetime] = None
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'url': self.url,
            'filters': self.filters,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'status': self.status.value
        }


@dataclass
class SubscriptionItem:
    """订阅项"""
    title: str
    link: str
    description: str = ""
    pub_date: Optional[datetime] = None
    size: Optional[int] = None
    seeders: Optional[int] = None
    leechers: Optional[int] = None
    category: str = ""
    matched_filters: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'link': self.link,
            'description': self.description,
            'pub_date': self.pub_date.isoformat() if self.pub_date else None,
            'size': self.size,
            'seeders': self.seeders,
            'leechers': self.leechers,
            'category': self.category,
            'matched_filters': self.matched_filters
        }


@dataclass
class DownloaderConfig:
    """下载器配置"""
    type: DownloaderType
    host: str
    port: int
    username: str = ""
    password: str = ""
    download_path: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'download_path': self.download_path
        }


class SubscriptionManager:
    """订阅管理器 - MoviePilot风格"""
    
    def __init__(self):
        self.feeds: Dict[str, RSSFeed] = {}
        self.downloaders: Dict[str, DownloaderConfig] = {}
        self.filters: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
        self.check_interval = 300  # 5分钟检查一次
        
        # 内置过滤器
        self._setup_default_filters()
    
    def _setup_default_filters(self):
        """设置默认过滤器"""
        self.filters = {
            'movie_1080p': {
                'type': 'movie',
                'quality': ['1080p', 'BluRay'],
                'min_size': 2000,  # 2GB
                'max_size': 15000,  # 15GB
                'keywords': [],
                'exclude_keywords': ['CAM', 'TS', 'TC']
            },
            'tv_show_720p': {
                'type': 'tv',
                'quality': ['720p', 'HDTV'],
                'min_size': 500,   # 500MB
                'max_size': 5000,  # 5GB
                'keywords': [],
                'exclude_keywords': ['CAM', 'TS']
            },
            '4k_movie': {
                'type': 'movie',
                'quality': ['4K', '2160p', 'UHD'],
                'min_size': 10000,  # 10GB
                'max_size': 50000,  # 50GB
                'keywords': [],
                'exclude_keywords': ['CAM', 'TS', 'TC']
            }
        }
    
    async def add_feed(self, name: str, url: str, filters: Dict[str, Any] = None) -> bool:
        """添加RSS订阅源"""
        if name in self.feeds:
            logger.warning(f"订阅源 '{name}' 已存在")
            return False
        
        feed = RSSFeed(name=name, url=url, filters=filters or {})
        self.feeds[name] = feed
        logger.info(f"添加订阅源: {name}")
        return True
    
    async def remove_feed(self, name: str) -> bool:
        """移除订阅源"""
        if name in self.feeds:
            del self.feeds[name]
            logger.info(f"移除订阅源: {name}")
            return True
        return False
    
    async def add_downloader(self, name: str, config: DownloaderConfig) -> bool:
        """添加下载器"""
        # 测试下载器连接
        if not await self._test_downloader_connection(config):
            logger.error(f"下载器连接测试失败: {name}")
            return False
        
        self.downloaders[name] = config
        logger.info(f"添加下载器: {name}")
        return True
    
    async def _test_downloader_connection(self, config: DownloaderConfig) -> bool:
        """测试下载器连接"""
        try:
            if config.type == DownloaderType.QBITTORRENT:
                return await self._test_qbittorrent_connection(config)
            elif config.type == DownloaderType.TRANSMISSION:
                return await self._test_transmission_connection(config)
            elif config.type == DownloaderType.ARIA2:
                return await self._test_aria2_connection(config)
        except Exception as e:
            logger.error(f"下载器连接测试失败: {e}")
            return False
        return False
    
    async def _test_qbittorrent_connection(self, config: DownloaderConfig) -> bool:
        """测试qBittorrent连接"""
        try:
            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(config.username, config.password)
                url = f"http://{config.host}:{config.port}/api/v2/app/version"
                
                async with session.get(url, auth=auth) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def _test_transmission_connection(self, config: DownloaderConfig) -> bool:
        """测试Transmission连接"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{config.host}:{config.port}/transmission/rpc"
                
                # 获取session ID
                async with session.post(url) as response:
                    if response.status == 409:  # 需要session ID
                        return True
                    return response.status == 200
        except Exception:
            return False
    
    async def _test_aria2_connection(self, config: DownloaderConfig) -> bool:
        """测试Aria2连接"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{config.host}:{config.port}/jsonrpc"
                data = {
                    'jsonrpc': '2.0',
                    'method': 'aria2.getVersion',
                    'id': 'test'
                }
                
                async with session.post(url, json=data) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def start_monitoring(self):
        """开始监控订阅"""
        if self.is_running:
            logger.warning("订阅监控已在运行中")
            return
        
        self.is_running = True
        logger.info("开始订阅监控")
        
        while self.is_running:
            try:
                await self._check_feeds()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"订阅监控错误: {e}")
                await asyncio.sleep(60)  # 错误后等待1分钟
    
    async def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        logger.info("停止订阅监控")
    
    async def _check_feeds(self):
        """检查所有订阅源"""
        for feed_name, feed in self.feeds.items():
            if feed.status != SubscriptionStatus.ACTIVE:
                continue
            
            try:
                items = await self._parse_feed(feed)
                matched_items = await self._filter_items(items, feed.filters)
                
                if matched_items:
                    logger.info(f"订阅源 '{feed_name}' 发现 {len(matched_items)} 个匹配项")
                    await self._process_matched_items(matched_items, feed_name)
                
                feed.last_check = datetime.now()
                
            except Exception as e:
                logger.error(f"检查订阅源 '{feed_name}' 失败: {e}")
                feed.status = SubscriptionStatus.ERROR
    
    async def _parse_feed(self, feed: RSSFeed) -> List[SubscriptionItem]:
        """解析RSS订阅源"""
        items = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(feed.url) as response:
                    if response.status == 200:
                        content = await response.text()
                        parsed = feedparser.parse(content)
                        
                        for entry in parsed.entries:
                            item = SubscriptionItem(
                                title=entry.get('title', ''),
                                link=entry.get('link', ''),
                                description=entry.get('description', ''),
                            )
                            
                            # 解析发布时间
                            if 'published' in entry:
                                try:
                                    item.pub_date = datetime.fromisoformat(entry.published)
                                except:
                                    pass
                            
                            # 解析大小、种子数等信息
                            item = await self._parse_item_details(item)
                            items.append(item)
        
        except Exception as e:
            logger.error(f"解析RSS订阅源失败: {e}")
        
        return items
    
    async def _parse_item_details(self, item: SubscriptionItem) -> SubscriptionItem:
        """解析订阅项详细信息"""
        # 从标题中提取信息
        title_lower = item.title.lower()
        
        # 提取大小信息
        size_match = self._extract_size(item.title)
        if size_match:
            item.size = size_match
        
        # 提取种子和下载者数量
        seeders_match = re.search(r'(\d+)[\s]*[Ss]eeder', item.title)
        leechers_match = re.search(r'(\d+)[\s]*[Ll]eecher', item.title)
        
        if seeders_match:
            item.seeders = int(seeders_match.group(1))
        if leechers_match:
            item.leechers = int(leechers_match.group(1))
        
        # 分类识别
        if any(keyword in title_lower for keyword in ['movie', 'film', '电影']):
            item.category = 'movie'
        elif any(keyword in title_lower for keyword in ['tv', 'season', 'episode', '电视剧', '剧集']):
            item.category = 'tv'
        elif any(keyword in title_lower for keyword in ['anime', '动漫']):
            item.category = 'anime'
        
        return item
    
    def _extract_size(self, title: str) -> Optional[int]:
        """从标题中提取文件大小（MB）"""
        # 匹配各种大小格式
        patterns = [
            r'(\d+\.?\d*)[\s]*(GB|Gb)',  # GB格式
            r'(\d+\.?\d*)[\s]*(MB|Mb)',  # MB格式
            r'(\d+)[\s]*GB',  # 简单GB
            r'(\d+)[\s]*MB',  # 简单MB
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                size = float(match.group(1))
                unit = match.group(2).lower() if len(match.groups()) > 1 else ''
                
                if 'gb' in unit or not unit:
                    return int(size * 1024)  # GB转MB
                elif 'mb' in unit:
                    return int(size)
        
        return None
    
    async def _filter_items(self, items: List[SubscriptionItem], filters: Dict[str, Any]) -> List[SubscriptionItem]:
        """过滤订阅项"""
        matched_items = []
        
        for item in items:
            matched_filters = []
            
            # 应用内置过滤器
            for filter_name, filter_config in self.filters.items():
                if await self._match_filter(item, filter_config):
                    matched_filters.append(filter_name)
            
            # 应用自定义过滤器
            for key, value in filters.items():
                if key.startswith('include_') and value:
                    if not any(keyword.lower() in item.title.lower() for keyword in value):
                        continue
                elif key.startswith('exclude_') and value:
                    if any(keyword.lower() in item.title.lower() for keyword in value):
                        continue
            
            if matched_filters:
                item.matched_filters = matched_filters
                matched_items.append(item)
        
        return matched_items
    
    async def _match_filter(self, item: SubscriptionItem, filter_config: Dict[str, Any]) -> bool:
        """匹配单个过滤器"""
        # 类型匹配
        if filter_config.get('type') and item.category != filter_config['type']:
            return False
        
        # 质量匹配
        if filter_config.get('quality'):
            title_lower = item.title.lower()
            quality_matched = any(q.lower() in title_lower for q in filter_config['quality'])
            if not quality_matched:
                return False
        
        # 大小范围匹配
        if item.size:
            min_size = filter_config.get('min_size', 0)
            max_size = filter_config.get('max_size', float('inf'))
            if not (min_size <= item.size <= max_size):
                return False
        
        # 关键词排除
        if filter_config.get('exclude_keywords'):
            title_lower = item.title.lower()
            if any(kw.lower() in title_lower for kw in filter_config['exclude_keywords']):
                return False
        
        # 种子数要求
        if filter_config.get('min_seeders') and item.seeders:
            if item.seeders < filter_config['min_seeders']:
                return False
        
        return True
    
    async def _process_matched_items(self, items: List[SubscriptionItem], feed_name: str):
        """处理匹配的订阅项"""
        if not self.downloaders:
            logger.warning("没有可用的下载器，跳过下载")
            return
        
        # 按种子数排序，优先下载种子多的
        items.sort(key=lambda x: x.seeders or 0, reverse=True)
        
        for item in items:
            try:
                # 选择第一个可用的下载器
                downloader_name, downloader_config = next(iter(self.downloaders.items()))
                
                success = await self._add_to_downloader(item, downloader_config)
                if success:
                    logger.info(f"成功添加下载: {item.title}")
                else:
                    logger.error(f"添加下载失败: {item.title}")
                
                # 避免过快连续下载
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"处理订阅项失败: {e}")
    
    async def _add_to_downloader(self, item: SubscriptionItem, config: DownloaderConfig) -> bool:
        """添加任务到下载器"""
        try:
            if config.type == DownloaderType.QBITTORRENT:
                return await self._add_to_qbittorrent(item, config)
            elif config.type == DownloaderType.TRANSMISSION:
                return await self._add_to_transmission(item, config)
            elif config.type == DownloaderType.ARIA2:
                return await self._add_to_aria2(item, config)
        except Exception as e:
            logger.error(f"添加下载任务失败: {e}")
            return False
        
        return False
    
    async def _add_to_qbittorrent(self, item: SubscriptionItem, config: DownloaderConfig) -> bool:
        """添加到qBittorrent"""
        try:
            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(config.username, config.password)
                url = f"http://{config.host}:{config.port}/api/v2/torrents/add"
                
                # 下载种子文件或使用磁力链接
                if item.link.startswith('magnet:'):
                    data = {'urls': item.link}
                else:
                    # 下载种子文件
                    async with session.get(item.link) as response:
                        if response.status == 200:
                            torrent_data = await response.read()
                            data = {'torrents': torrent_data}
                        else:
                            return False
                
                # 设置下载路径
                if config.download_path:
                    data['savepath'] = config.download_path
                
                async with session.post(url, data=data, auth=auth) as response:
                    return response.status == 200
        
        except Exception:
            return False
    
    async def _add_to_transmission(self, item: SubscriptionItem, config: DownloaderConfig) -> bool:
        """添加到Transmission"""
        # 简化实现，实际需要处理session ID等
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{config.host}:{config.port}/transmission/rpc"
                
                # 获取session ID
                async with session.post(url) as response:
                    if response.status == 409:
                        session_id = response.headers.get('X-Transmission-Session-Id')
                    else:
                        return False
                
                # 添加下载任务
                data = {
                    'method': 'torrent-add',
                    'arguments': {
                        'filename': item.link
                    }
                }
                
                headers = {'X-Transmission-Session-Id': session_id}
                async with session.post(url, json=data, headers=headers) as response:
                    return response.status == 200
        
        except Exception:
            return False
    
    async def _add_to_aria2(self, item: SubscriptionItem, config: DownloaderConfig) -> bool:
        """添加到Aria2"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{config.host}:{config.port}/jsonrpc"
                
                data = {
                    'jsonrpc': '2.0',
                    'method': 'aria2.addUri',
                    'id': 'add_download',
                    'params': [[item.link]]
                }
                
                async with session.post(url, json=data) as response:
                    return response.status == 200
        
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取订阅管理器状态"""
        return {
            'is_running': self.is_running,
            'feed_count': len(self.feeds),
            'downloader_count': len(self.downloaders),
            'feeds': {name: feed.to_dict() for name, feed in self.feeds.items()},
            'downloaders': {name: config.to_dict() for name, config in self.downloaders.items()},
            'filters': self.filters
        }


# 使用示例
async def demo():
    """演示使用方法"""
    manager = SubscriptionManager()
    
    # 添加RSS订阅源
    await manager.add_feed(
        name="电影RSS",
        url="https://example.com/movies.rss",
        filters={'include_keywords': ['1080p', 'BluRay']}
    )
    
    # 添加下载器
    qbt_config = DownloaderConfig(
        type=DownloaderType.QBITTORRENT,
        host="localhost",
        port=8080,
        username="admin",
        password="adminadmin",
        download_path="/downloads"
    )
    
    await manager.add_downloader("qbt_main", qbt_config)
    
    # 开始监控
    import asyncio
    task = asyncio.create_task(manager.start_monitoring())
    
    # 运行一段时间后停止
    await asyncio.sleep(60)
    await manager.stop_monitoring()
    await task


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())