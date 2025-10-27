#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强下载器管理系统
集成media-renamer中的下载器功能，支持多种下载器
"""

import asyncio
import aiohttp
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TorrentInfo:
    """种子信息"""
    hash: str
    name: str
    size: int
    progress: float
    download_speed: int
    upload_speed: int
    state: str
    eta: int
    ratio: float
    save_path: str


@dataclass
class DownloaderStats:
    """下载器统计信息"""
    download_speed: int
    upload_speed: int
    total_downloaded: int
    total_uploaded: int
    active_torrents: int
    total_torrents: int


class DownloaderPlugin(ABC):
    """下载器插件基类"""
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.connected = False
        self.session = None
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    async def connect(self) -> bool:
        """连接下载器"""
        try:
            self.session = aiohttp.ClientSession()
            success = await self._perform_connect()
            
            if success:
                self.connected = True
                self.logger.info(f"✅ {self.name} 连接成功")
            else:
                self.logger.error(f"❌ {self.name} 连接失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ {self.name} 连接异常: {e}")
            return False
    
    @abstractmethod
    async def _perform_connect(self) -> bool:
        """具体的连接实现"""
        pass
    
    async def add_torrent(self, torrent_file: str, save_path: str, 
                         category: str = None, paused: bool = False) -> bool:
        """添加下载任务"""
        if not self.connected:
            raise Exception("请先连接下载器")
        
        try:
            success = await self._add_torrent(torrent_file, save_path, category, paused)
            if success:
                self.logger.info(f"✅ {self.name} 添加任务成功: {torrent_file}")
            return success
        except Exception as e:
            self.logger.error(f"❌ {self.name} 添加任务失败: {e}")
            return False
    
    @abstractmethod
    async def _add_torrent(self, torrent_file: str, save_path: str, 
                          category: str, paused: bool) -> bool:
        """具体的添加任务实现"""
        pass
    
    async def get_torrents(self, status_filter: str = None) -> List[TorrentInfo]:
        """获取下载列表"""
        if not self.connected:
            raise Exception("请先连接下载器")
        
        try:
            torrents = await self._get_torrents(status_filter)
            return torrents
        except Exception as e:
            self.logger.error(f"❌ {self.name} 获取任务列表失败: {e}")
            return []
    
    @abstractmethod
    async def _get_torrents(self, status_filter: str) -> List[TorrentInfo]:
        """具体的获取任务列表实现"""
        pass
    
    async def set_speed_limit(self, download_limit: int, upload_limit: int) -> bool:
        """设置速度限制"""
        if not self.connected:
            raise Exception("请先连接下载器")
        
        try:
            success = await self._set_speed_limit(download_limit, upload_limit)
            if success:
                self.logger.info(f"✅ {self.name} 速度限制设置成功: DL={download_limit}, UL={upload_limit}")
            return success
        except Exception as e:
            self.logger.error(f"❌ {self.name} 设置速度限制失败: {e}")
            return False
    
    @abstractmethod
    async def _set_speed_limit(self, download_limit: int, upload_limit: int) -> bool:
        """具体的速度限制设置实现"""
        pass
    
    async def get_stats(self) -> DownloaderStats:
        """获取下载器统计信息"""
        if not self.connected:
            raise Exception("请先连接下载器")
        
        try:
            stats = await self._get_stats()
            return stats
        except Exception as e:
            self.logger.error(f"❌ {self.name} 获取统计信息失败: {e}")
            return DownloaderStats(0, 0, 0, 0, 0, 0)
    
    @abstractmethod
    async def _get_stats(self) -> DownloaderStats:
        """具体的统计信息获取实现"""
        pass
    
    async def delete_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """删除种子"""
        if not self.connected:
            raise Exception("请先连接下载器")
        
        try:
            success = await self._delete_torrent(torrent_hash, delete_files)
            if success:
                self.logger.info(f"✅ {self.name} 删除种子成功: {torrent_hash}")
            return success
        except Exception as e:
            self.logger.error(f"❌ {self.name} 删除种子失败: {e}")
            return False
    
    @abstractmethod
    async def _delete_torrent(self, torrent_hash: str, delete_files: bool) -> bool:
        """具体的删除种子实现"""
        pass
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None
            self.connected = False


class QBittorrentPlugin(DownloaderPlugin):
    """qBittorrent下载器插件"""
    
    def __init__(self, config: Dict):
        super().__init__("qBittorrent", config)
        self.api_url = f"http://{config['host']}:{config['port']}/api/v2"
    
    async def _perform_connect(self) -> bool:
        """连接qBittorrent"""
        login_data = {
            'username': self.config.get('username', ''),
            'password': self.config.get('password', '')
        }
        
        async with self.session.post(
            f"{self.api_url}/auth/login",
            data=login_data
        ) as response:
            return response.status == 200
    
    async def _add_torrent(self, torrent_file: str, save_path: str, 
                          category: str, paused: bool) -> bool:
        """添加qBittorrent任务"""
        with open(torrent_file, 'rb') as f:
            torrent_data = f.read()
        
        form_data = aiohttp.FormData()
        form_data.add_field('torrents', torrent_data, 
                          filename='torrent.torrent',
                          content_type='application/x-bittorrent')
        
        if save_path:
            form_data.add_field('savepath', save_path)
        
        if category:
            form_data.add_field('category', category)
        
        if paused:
            form_data.add_field('paused', 'true')
        
        async with self.session.post(
            f"{self.api_url}/torrents/add",
            data=form_data
        ) as response:
            return response.status == 200
    
    async def _get_torrents(self, status_filter: str) -> List[TorrentInfo]:
        """获取qBittorrent任务列表"""
        params = {}
        if status_filter:
            params['filter'] = status_filter
        
        async with self.session.get(
            f"{self.api_url}/torrents/info",
            params=params
        ) as response:
            if response.status == 200:
                data = await response.json()
                
                torrents = []
                for item in data:
                    torrent = TorrentInfo(
                        hash=item['hash'],
                        name=item['name'],
                        size=item['size'],
                        progress=item['progress'],
                        download_speed=item['dlspeed'],
                        upload_speed=item['upspeed'],
                        state=item['state'],
                        eta=item['eta'],
                        ratio=item['ratio'],
                        save_path=item['save_path']
                    )
                    torrents.append(torrent)
                
                return torrents
            return []
    
    async def _set_speed_limit(self, download_limit: int, upload_limit: int) -> bool:
        """设置qBittorrent速度限制"""
        data = {
            'alt_dl_limit': download_limit,
            'alt_up_limit': upload_limit,
            'alt_speed_enabled': True if download_limit > 0 or upload_limit > 0 else False
        }
        
        async with self.session.post(
            f"{self.api_url}/transfer/setSpeedLimitsMode",
            data=data
        ) as response:
            return response.status == 200
    
    async def _get_stats(self) -> DownloaderStats:
        """获取qBittorrent统计信息"""
        async with self.session.get(f"{self.api_url}/transfer/info") as response:
            if response.status == 200:
                data = await response.json()
                
                return DownloaderStats(
                    download_speed=data['dl_info_speed'],
                    upload_speed=data['up_info_speed'],
                    total_downloaded=data['dl_info_data'],
                    total_uploaded=data['up_info_data'],
                    active_torrents=len([t for t in await self.get_torrents() 
                                        if t.state in ['downloading', 'uploading']]),
                    total_torrents=len(await self.get_torrents())
                )
            return DownloaderStats(0, 0, 0, 0, 0, 0)
    
    async def _delete_torrent(self, torrent_hash: str, delete_files: bool) -> bool:
        """删除qBittorrent种子"""
        data = {
            'hashes': torrent_hash,
            'deleteFiles': delete_files
        }
        
        async with self.session.post(
            f"{self.api_url}/torrents/delete",
            data=data
        ) as response:
            return response.status == 200


class TransmissionPlugin(DownloaderPlugin):
    """Transmission下载器插件"""
    
    def __init__(self, config: Dict):
        super().__init__("Transmission", config)
        self.api_url = f"http://{config['host']}:{config['port']}/transmission/rpc"
    
    async def _perform_connect(self) -> bool:
        """连接Transmission"""
        async with self.session.get(self.api_url) as response:
            if response.status == 409:
                session_id = response.headers.get('X-Transmission-Session-Id')
                if session_id:
                    self.session.headers.update({
                        'X-Transmission-Session-Id': session_id
                    })
                    return True
            return response.status == 200
    
    async def _add_torrent(self, torrent_file: str, save_path: str, 
                          category: str, paused: bool) -> bool:
        """添加Transmission任务"""
        import base64
        with open(torrent_file, 'rb') as f:
            torrent_data = base64.b64encode(f.read()).decode()
        
        data = {
            'method': 'torrent-add',
            'arguments': {
                'metainfo': torrent_data,
                'download-dir': save_path,
                'paused': paused
            }
        }
        
        async with self.session.post(self.api_url, json=data) as response:
            return response.status == 200
    
    async def _get_torrents(self, status_filter: str) -> List[TorrentInfo]:
        """获取Transmission任务列表"""
        data = {
            'method': 'torrent-get',
            'arguments': {
                'fields': ['id', 'name', 'totalSize', 'percentDone', 
                          'rateDownload', 'rateUpload', 'status', 'eta', 
                          'uploadRatio', 'downloadDir']
            }
        }
        
        async with self.session.post(self.api_url, json=data) as response:
            if response.status == 200:
                result = await response.json()
                torrents = []
                
                for item in result['arguments']['torrents']:
                    torrent = TorrentInfo(
                        hash=str(item['id']),
                        name=item['name'],
                        size=item['totalSize'],
                        progress=item['percentDone'] * 100,
                        download_speed=item['rateDownload'],
                        upload_speed=item['rateUpload'],
                        state=self._get_state_name(item['status']),
                        eta=item['eta'],
                        ratio=item['uploadRatio'],
                        save_path=item['downloadDir']
                    )
                    torrents.append(torrent)
                
                return torrents
            return []
    
    def _get_state_name(self, status_code: int) -> str:
        """转换状态码为状态名称"""
        states = {
            0: 'stopped',
            1: 'check_wait',
            2: 'checking',
            3: 'download_wait',
            4: 'downloading',
            5: 'seed_wait',
            6: 'seeding'
        }
        return states.get(status_code, 'unknown')
    
    async def _set_speed_limit(self, download_limit: int, upload_limit: int) -> bool:
        """设置Transmission速度限制"""
        data = {
            'method': 'session-set',
            'arguments': {
                'speed-limit-down': download_limit,
                'speed-limit-down-enabled': download_limit > 0,
                'speed-limit-up': upload_limit,
                'speed-limit-up-enabled': upload_limit > 0
            }
        }
        
        async with self.session.post(self.api_url, json=data) as response:
            return response.status == 200
    
    async def _get_stats(self) -> DownloaderStats:
        """获取Transmission统计信息"""
        data = {
            'method': 'session-stats',
            'arguments': {}
        }
        
        async with self.session.post(self.api_url, json=data) as response:
            if response.status == 200:
                result = await response.json()
                args = result['arguments']
                
                return DownloaderStats(
                    download_speed=args['downloadSpeed'],
                    upload_speed=args['uploadSpeed'],
                    total_downloaded=args['downloadedBytes'],
                    total_uploaded=args['uploadedBytes'],
                    active_torrents=args['activeTorrentCount'],
                    total_torrents=args['torrentCount']
                )
            return DownloaderStats(0, 0, 0, 0, 0, 0)
    
    async def _delete_torrent(self, torrent_hash: str, delete_files: bool) -> bool:
        """删除Transmission种子"""
        data = {
            'method': 'torrent-remove',
            'arguments': {
                'ids': [int(torrent_hash)],
                'delete-local-data': delete_files
            }
        }
        
        async with self.session.post(self.api_url, json=data) as response:
            return response.status == 200


class DownloaderManager:
    """下载器管理器"""
    
    def __init__(self):
        self.downloaders = {}
        self.active_downloader = None
        self._register_downloaders()
    
    def _register_downloaders(self):
        """注册所有下载器插件"""
        self.downloaders = {
            'qbittorrent': QBittorrentPlugin,
            'transmission': TransmissionPlugin,
        }
    
    def get_downloader(self, downloader_key: str, config: Dict) -> Optional[DownloaderPlugin]:
        """获取指定下载器插件"""
        if downloader_key in self.downloaders:
            return self.downloaders[downloader_key](config)
        return None
    
    def get_available_downloaders(self) -> List[str]:
        """获取所有可用的下载器"""
        return list(self.downloaders.keys())
    
    async def add_downloader(self, name: str, downloader_type: str, config: Dict) -> bool:
        """添加下载器"""
        downloader = self.get_downloader(downloader_type, config)
        if not downloader:
            logger.error(f"不支持的下载器类型: {downloader_type}")
            return False
        
        success = await downloader.connect()
        if success:
            self.downloaders[name] = downloader
            if not self.active_downloader:
                self.active_downloader = name
            logger.info(f"成功添加下载器: {name}")
        
        return success
    
    def set_active_downloader(self, name: str) -> bool:
        """设置活跃下载器"""
        if name not in self.downloaders:
            logger.error(f"下载器不存在: {name}")
            return False
        
        self.active_downloader = name
        logger.info(f"设置活跃下载器: {name}")
        return True
    
    async def download_torrent(self, torrent_file: str, save_path: str = None, 
                              category: str = None, paused: bool = False) -> bool:
        """下载种子"""
        if not self.active_downloader:
            logger.error("没有活跃的下载器")
            return False
        
        downloader = self.downloaders[self.active_downloader]
        return await downloader.add_torrent(torrent_file, save_path, category, paused)
    
    async def get_download_status(self) -> Dict[str, Any]:
        """获取下载状态"""
        if not self.active_downloader:
            return {'connected': False}
        
        downloader = self.downloaders[self.active_downloader]
        stats = await downloader.get_stats()
        
        return {
            'connected': True,
            'downloader': self.active_downloader,
            'download_speed': stats.download_speed,
            'upload_speed': stats.upload_speed,
            'total_downloaded': stats.total_downloaded,
            'total_uploaded': stats.total_uploaded,
            'active_torrents': stats.active_torrents,
            'total_torrents': stats.total_torrents
        }
    
    async def close_all(self):
        """关闭所有下载器连接"""
        for name, downloader in self.downloaders.items():
            await downloader.close()
            logger.info(f"已关闭下载器: {name}")


# 全局下载管理器实例
download_manager = DownloaderManager()