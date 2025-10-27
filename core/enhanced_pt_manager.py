#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强PT站点管理器
整合PT-Plugin-Plus的站点管理和下载器功能
"""

import asyncio
import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog
from app.utils.commons import SingletonMeta

from .event import EventType, Event, event_manager

logger = structlog.get_logger()


class PTSiteStatus(Enum):
    """PT站点状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class PTSiteConfig:
    """PT站点配置"""
    name: str
    url: str
    username: str
    password: str
    cookie: Optional[str] = None
    api_key: Optional[str] = None
    enabled: bool = True
    priority: int = 1
    max_downloads: int = 5
    download_path: Optional[str] = None


@dataclass
class TorrentInfo:
    """种子信息"""
    site_name: str
    title: str
    url: str
    size: int
    seeders: int
    leechers: int
    upload_time: datetime
    category: str
    free_status: str = "normal"
    download_url: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class DownloadTask:
    """下载任务"""
    task_id: str
    torrent_info: TorrentInfo
    download_path: str
    status: DownloadStatus
    progress: float = 0.0
    speed: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None


class PTSiteAdapter(ABC):
    """PT站点适配器基类"""
    
    @abstractmethod
    async def login(self, config: PTSiteConfig) -> bool:
        """登录站点"""
        pass
    
    @abstractmethod
    async def search(self, keyword: str, category: str = "") -> List[TorrentInfo]:
        """搜索种子"""
        pass
    
    @abstractmethod
    async def download_torrent(self, torrent_info: TorrentInfo) -> Optional[str]:
        """下载种子文件"""
        pass
    
    @abstractmethod
    def get_status(self) -> PTSiteStatus:
        """获取站点状态"""
        pass


class DownloaderAdapter(ABC):
    """下载器适配器基类"""
    
    @abstractmethod
    async def add_torrent(self, torrent_file: str, download_path: str) -> str:
        """添加种子到下载器"""
        pass
    
    @abstractmethod
    async def get_task_status(self, task_id: str) -> DownloadTask:
        """获取下载任务状态"""
        pass
    
    @abstractmethod
    async def pause_task(self, task_id: str) -> bool:
        """暂停下载任务"""
        pass
    
    @abstractmethod
    async def resume_task(self, task_id: str) -> bool:
        """恢复下载任务"""
        pass


class EnhancedPTManager(metaclass=SingletonMeta):
    """增强PT站点管理器 - 整合PT-Plugin-Plus功能"""
    
    def __init__(self):
        # 站点配置和适配器
        self.site_configs: Dict[str, PTSiteConfig] = {}
        self.site_adapters: Dict[str, PTSiteAdapter] = {}
        
        # 下载器适配器
        self.downloader_adapters: Dict[str, DownloaderAdapter] = {}
        self.active_downloader: Optional[str] = None
        
        # 下载任务管理
        self.download_tasks: Dict[str, DownloadTask] = {}
        self.task_queue = asyncio.Queue()
        
        # 监控任务
        self._monitor_task = None
        self._active = False
        
        # 注册内置适配器
        self._register_builtin_adapters()
    
    def _register_builtin_adapters(self):
        """注册内置适配器"""
        # 注册PT站点适配器
        self.register_site_adapter("nexusphp", NexusPHPAdapter())
        self.register_site_adapter("gazelle", GazelleAdapter())
        self.register_site_adapter("unit3d", Unit3DAdapter())
        
        # 注册下载器适配器
        self.register_downloader_adapter("qbittorrent", QBittorrentAdapter())
        self.register_downloader_adapter("transmission", TransmissionAdapter())
        self.register_downloader_adapter("aria2", Aria2Adapter())
    
    def register_site_adapter(self, site_type: str, adapter: PTSiteAdapter):
        """注册站点适配器"""
        self.site_adapters[site_type] = adapter
        logger.info("PT站点适配器已注册", site_type=site_type)
    
    def register_downloader_adapter(self, downloader_type: str, adapter: DownloaderAdapter):
        """注册下载器适配器"""
        self.downloader_adapters[downloader_type] = adapter
        logger.info("下载器适配器已注册", downloader_type=downloader_type)
    
    async def add_site(self, config: PTSiteConfig, site_type: str) -> bool:
        """添加PT站点"""
        if site_type not in self.site_adapters:
            logger.error("不支持的站点类型", site_type=site_type)
            return False
        
        # 测试登录
        adapter = self.site_adapters[site_type]
        login_success = await adapter.login(config)
        
        if not login_success:
            logger.error("PT站点登录失败", site_name=config.name)
            return False
        
        self.site_configs[config.name] = config
        
        # 发布站点添加事件
        event = Event(
            event_type=EventType.PT_SITE_ADDED,
            data={
                "site_name": config.name,
                "site_type": site_type,
                "url": config.url
            }
        )
        event_manager.publish(event)
        
        logger.info("PT站点已添加", site_name=config.name, site_type=site_type)
        return True
    
    async def search_all_sites(self, keyword: str, category: str = "") -> List[TorrentInfo]:
        """在所有站点搜索种子"""
        all_results = []
        
        # 并行搜索所有启用的站点
        search_tasks = []
        for config in self.site_configs.values():
            if config.enabled:
                # 根据站点URL推断站点类型
                site_type = self._detect_site_type(config.url)
                if site_type in self.site_adapters:
                    search_tasks.append(
                        self._search_site(config, site_type, keyword, category)
                    )
        
        # 等待所有搜索完成
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
        
        # 按种子数排序
        all_results.sort(key=lambda x: x.seeders, reverse=True)
        
        logger.info("多站点搜索完成", keyword=keyword, results_count=len(all_results))
        return all_results
    
    async def _search_site(self, config: PTSiteConfig, site_type: str, keyword: str, category: str) -> List[TorrentInfo]:
        """在单个站点搜索"""
        try:
            adapter = self.site_adapters[site_type]
            results = await adapter.search(keyword, category)
            
            # 为结果添加站点信息
            for result in results:
                result.site_name = config.name
            
            return results
        except Exception as e:
            logger.error("站点搜索失败", site_name=config.name, error=str(e))
            return []
    
    async def download_torrent(self, torrent_info: TorrentInfo, download_path: str) -> str:
        """下载种子"""
        if not self.active_downloader:
            raise ValueError("未设置活动下载器")
        
        # 获取下载器适配器
        downloader_adapter = self.downloader_adapters[self.active_downloader]
        
        # 下载种子文件
        torrent_file = await self._download_torrent_file(torrent_info)
        if not torrent_file:
            raise Exception("种子文件下载失败")
        
        # 添加到下载器
        task_id = await downloader_adapter.add_torrent(torrent_file, download_path)
        
        # 创建下载任务记录
        download_task = DownloadTask(
            task_id=task_id,
            torrent_info=torrent_info,
            download_path=download_path,
            status=DownloadStatus.PENDING,
            start_time=datetime.now()
        )
        
        self.download_tasks[task_id] = download_task
        
        # 发布下载开始事件
        event = Event(
            event_type=EventType.DOWNLOAD_STARTED,
            data={
                "task_id": task_id,
                "torrent_title": torrent_info.title,
                "site_name": torrent_info.site_name
            }
        )
        event_manager.publish(event)
        
        logger.info("种子下载任务已创建", task_id=task_id, title=torrent_info.title)
        return task_id
    
    async def _download_torrent_file(self, torrent_info: TorrentInfo) -> Optional[str]:
        """下载种子文件"""
        # 根据站点名称获取配置和适配器
        config = self.site_configs.get(torrent_info.site_name)
        if not config:
            return None
        
        site_type = self._detect_site_type(config.url)
        adapter = self.site_adapters.get(site_type)
        
        if not adapter:
            return None
        
        try:
            torrent_file = await adapter.download_torrent(torrent_info)
            return torrent_file
        except Exception as e:
            logger.error("种子文件下载失败", title=torrent_info.title, error=str(e))
            return None
    
    def set_active_downloader(self, downloader_type: str):
        """设置活动下载器"""
        if downloader_type not in self.downloader_adapters:
            raise ValueError(f"不支持的下载器类型: {downloader_type}")
        
        self.active_downloader = downloader_type
        logger.info("活动下载器已设置", downloader_type=downloader_type)
    
    def start_monitoring(self):
        """启动监控"""
        if self._active:
            return
        
        self._active = True
        self._monitor_task = asyncio.create_task(self._monitor_downloads())
        
        logger.info("PT站点监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self._active:
            return
        
        self._active = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
        
        logger.info("PT站点监控已停止")
    
    async def _monitor_downloads(self):
        """监控下载任务"""
        while self._active:
            try:
                # 更新所有下载任务状态
                for task_id, task in list(self.download_tasks.items()):
                    if task.status in [DownloadStatus.PENDING, DownloadStatus.DOWNLOADING]:
                        await self._update_task_status(task_id)
                
                await asyncio.sleep(10)  # 每10秒更新一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("下载监控异常", error=str(e))
                await asyncio.sleep(30)
    
    async def _update_task_status(self, task_id: str):
        """更新任务状态"""
        task = self.download_tasks.get(task_id)
        if not task or not self.active_downloader:
            return
        
        downloader_adapter = self.downloader_adapters[self.active_downloader]
        
        try:
            updated_task = await downloader_adapter.get_task_status(task_id)
            
            # 更新任务状态
            task.status = updated_task.status
            task.progress = updated_task.progress
            task.speed = updated_task.speed
            
            # 检查状态变化
            if updated_task.status == DownloadStatus.COMPLETED and task.status != DownloadStatus.COMPLETED:
                task.end_time = datetime.now()
                
                # 发布下载完成事件
                event = Event(
                    event_type=EventType.DOWNLOAD_COMPLETED,
                    data={
                        "task_id": task_id,
                        "torrent_title": task.torrent_info.title,
                        "download_path": task.download_path
                    }
                )
                event_manager.publish(event)
                
                logger.info("下载任务已完成", task_id=task_id, title=task.torrent_info.title)
            
            elif updated_task.status == DownloadStatus.FAILED and task.status != DownloadStatus.FAILED:
                task.error_message = updated_task.error_message
                task.end_time = datetime.now()
                
                # 发布下载失败事件
                event = Event(
                    event_type=EventType.DOWNLOAD_FAILED,
                    data={
                        "task_id": task_id,
                        "torrent_title": task.torrent_info.title,
                        "error": task.error_message
                    }
                )
                event_manager.publish(event)
                
                logger.error("下载任务失败", task_id=task_id, title=task.torrent_info.title, error=task.error_message)
                
        except Exception as e:
            logger.error("任务状态更新失败", task_id=task_id, error=str(e))
    
    def _detect_site_type(self, url: str) -> str:
        """根据URL检测站点类型"""
        # 简单的URL模式匹配
        if "nexusphp" in url.lower():
            return "nexusphp"
        elif "gazelle" in url.lower():
            return "gazelle"
        elif "unit3d" in url.lower():
            return "unit3d"
        else:
            return "nexusphp"  # 默认类型
    
    def get_site_status(self, site_name: str) -> Optional[PTSiteStatus]:
        """获取站点状态"""
        config = self.site_configs.get(site_name)
        if not config:
            return None
        
        site_type = self._detect_site_type(config.url)
        adapter = self.site_adapters.get(site_type)
        
        if adapter:
            return adapter.get_status()
        
        return PTSiteStatus.OFFLINE
    
    def list_sites(self) -> List[Dict[str, Any]]:
        """列出所有站点"""
        sites = []
        for config in self.site_configs.values():
            status = self.get_site_status(config.name)
            sites.append({
                "name": config.name,
                "url": config.url,
                "enabled": config.enabled,
                "status": status.value if status else "unknown",
                "priority": config.priority
            })
        
        return sorted(sites, key=lambda x: x["priority"])


# 内置适配器实现
class NexusPHPAdapter(PTSiteAdapter):
    """NexusPHP站点适配器"""
    
    def __init__(self):
        self.logged_in = False
        self.session = None
        self.config = None
    
    async def login(self, config: PTSiteConfig) -> bool:
        """登录NexusPHP站点"""
        try:
            import aiohttp
            
            # 保存配置
            self.config = config
            
            # 创建会话
            self.session = aiohttp.ClientSession()
            
            # 登录数据
            login_data = {
                "username": config.username,
                "password": config.password
            }
            
            # 发送登录请求
            async with self.session.post(
                f"{config.url}/login.php",
                data=login_data
            ) as response:
                if response.status == 200:
                    self.logged_in = True
                    logger.info("NexusPHP站点登录成功", site_name=config.name)
                    return True
                else:
                    logger.error("NexusPHP站点登录失败", site_name=config.name, status=response.status)
                    return False
                    
        except Exception as e:
            logger.error("NexusPHP站点登录异常", site_name=config.name, error=str(e))
            return False
    
    async def search(self, keyword: str, category: str = "") -> List[TorrentInfo]:
        """搜索种子"""
        if not self.logged_in:
            raise Exception("请先登录站点")
        
        try:
            # 构建搜索URL
            search_url = f"{self.config.url}/torrents.php"
            params = {
                "search": keyword,
                "cat": category
            }
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    content = await response.text()
                    return self._parse_search_results(content)
                else:
                    logger.error("搜索请求失败", status=response.status)
                    return []
                    
        except Exception as e:
            logger.error("搜索异常", error=str(e))
            return []
    
    def _parse_search_results(self, html_content: str) -> List[TorrentInfo]:
        """解析搜索结果"""
        # 简化的解析逻辑，实际实现需要根据具体站点HTML结构调整
        torrents = []
        
        # 使用正则表达式匹配种子信息
        # 这里需要根据具体站点的HTML结构编写解析逻辑
        
        return torrents
    
    async def download_torrent(self, torrent_info: TorrentInfo) -> Optional[str]:
        """下载种子文件"""
        if not self.logged_in:
            raise Exception("请先登录站点")
        
        try:
            # 下载种子文件
            async with self.session.get(torrent_info.download_url) as response:
                if response.status == 200:
                    content = await response.read()
                    # 保存种子文件
                    filename = f"{torrent_info.title}.torrent"
                    with open(filename, 'wb') as f:
                        f.write(content)
                    return filename
                else:
                    logger.error("种子下载失败", status=response.status)
                    return None
                    
        except Exception as e:
            logger.error("种子下载异常", error=str(e))
            return None
    
    def get_status(self) -> PTSiteStatus:
        """获取站点状态"""
        if not self.logged_in:
            return PTSiteStatus.OFFLINE
        
        # 简化的状态检测，实际实现需要更复杂的逻辑
        return PTSiteStatus.ONLINE


class GazelleAdapter(PTSiteAdapter):
    """Gazelle站点适配器"""
    
    def __init__(self):
        self.logged_in = False
        self.session = None
        self.config = None
    
    async def login(self, config: PTSiteConfig) -> bool:
        """登录Gazelle站点"""
        # Gazelle站点通常使用API密钥认证
        try:
            import aiohttp
            
            self.config = config
            self.session = aiohttp.ClientSession()
            
            # 测试API连接
            test_url = f"{config.url}/ajax.php"
            params = {
                "action": "index",
                "apikey": config.api_key
            }
            
            async with self.session.get(test_url, params=params) as response:
                if response.status == 200:
                    self.logged_in = True
                    logger.info("Gazelle站点登录成功", site_name=config.name)
                    return True
                else:
                    logger.error("Gazelle站点登录失败", site_name=config.name, status=response.status)
                    return False
                    
        except Exception as e:
            logger.error("Gazelle站点登录异常", site_name=config.name, error=str(e))
            return False
    
    async def search(self, keyword: str, category: str = "") -> List[TorrentInfo]:
        """搜索种子"""
        if not self.logged_in:
            raise Exception("请先登录站点")
        
        try:
            search_url = f"{self.config.url}/ajax.php"
            params = {
                "action": "browse",
                "searchstr": keyword,
                "apikey": self.config.api_key
            }
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_api_response(data)
                else:
                    logger.error("搜索请求失败", status=response.status)
                    return []
                    
        except Exception as e:
            logger.error("搜索异常", error=str(e))
            return []
    
    def _parse_api_response(self, data: Dict) -> List[TorrentInfo]:
        """解析API响应"""
        torrents = []
        # 根据Gazelle API结构解析数据
        return torrents
    
    async def download_torrent(self, torrent_info: TorrentInfo) -> Optional[str]:
        """下载种子文件"""
        if not self.logged_in:
            raise Exception("请先登录站点")
        
        try:
            download_url = f"{self.config.url}/torrents.php"
            params = {
                "action": "download",
                "id": torrent_info.details.get("id"),
                "authkey": self.config.api_key
            }
            
            async with self.session.get(download_url, params=params) as response:
                if response.status == 200:
                    content = await response.read()
                    filename = f"{torrent_info.title}.torrent"
                    with open(filename, 'wb') as f:
                        f.write(content)
                    return filename
                else:
                    logger.error("种子下载失败", status=response.status)
                    return None
                    
        except Exception as e:
            logger.error("种子下载异常", error=str(e))
            return None
    
    def get_status(self) -> PTSiteStatus:
        """获取站点状态"""
        if not self.logged_in:
            return PTSiteStatus.OFFLINE
        return PTSiteStatus.ONLINE


class Unit3DAdapter(PTSiteAdapter):
    """Unit3D站点适配器"""
    
    def __init__(self):
        self.logged_in = False
        self.session = None
        self.config = None
    
    async def login(self, config: PTSiteConfig) -> bool:
        """登录Unit3D站点"""
        try:
            import aiohttp
            
            self.config = config
            self.session = aiohttp.ClientSession()
            
            # Unit3D通常使用用户名密码登录
            login_data = {
                "username": config.username,
                "password": config.password
            }
            
            async with self.session.post(f"{config.url}/login", data=login_data) as response:
                if response.status == 200:
                    self.logged_in = True
                    logger.info("Unit3D站点登录成功", site_name=config.name)
                    return True
                else:
                    logger.error("Unit3D站点登录失败", site_name=config.name, status=response.status)
                    return False
                    
        except Exception as e:
            logger.error("Unit3D站点登录异常", site_name=config.name, error=str(e))
            return False
    
    async def search(self, keyword: str, category: str = "") -> List[TorrentInfo]:
        """搜索种子"""
        if not self.logged_in:
            raise Exception("请先登录站点")
        
        try:
            search_url = f"{self.config.url}/torrents"
            params = {
                "name": keyword,
                "categories[]": category
            }
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    content = await response.text()
                    return self._parse_search_results(content)
                else:
                    logger.error("搜索请求失败", status=response.status)
                    return []
                    
        except Exception as e:
            logger.error("搜索异常", error=str(e))
            return []
    
    def _parse_search_results(self, html_content: str) -> List[TorrentInfo]:
        """解析搜索结果"""
        torrents = []
        # 根据Unit3D的HTML结构解析数据
        return torrents
    
    async def download_torrent(self, torrent_info: TorrentInfo) -> Optional[str]:
        """下载种子文件"""
        if not self.logged_in:
            raise Exception("请先登录站点")
        
        try:
            download_url = f"{self.config.url}/torrents/download/{torrent_info.details.get('id')}"
            
            async with self.session.get(download_url) as response:
                if response.status == 200:
                    content = await response.read()
                    filename = f"{torrent_info.title}.torrent"
                    with open(filename, 'wb') as f:
                        f.write(content)
                    return filename
                else:
                    logger.error("种子下载失败", status=response.status)
                    return None
                    
        except Exception as e:
            logger.error("种子下载异常", error=str(e))
            return None
    
    def get_status(self) -> PTSiteStatus:
        """获取站点状态"""
        if not self.logged_in:
            return PTSiteStatus.OFFLINE
        return PTSiteStatus.ONLINE


# 下载器适配器实现
class QBittorrentAdapter(DownloaderAdapter):
    """qBittorrent适配器"""
    
    def __init__(self):
        self.client = None
    
    async def add_torrent(self, torrent_file: str, download_path: str) -> str:
        """添加种子到qBittorrent"""
        try:
            from qbittorrentapi import Client
            
            if not self.client:
                self.client = Client(host='localhost', port=8080)
            
            # 添加种子
            result = self.client.torrents_add(
                torrent_files=torrent_file,
                save_path=download_path
            )
            
            # 返回任务ID
            return result
            
        except Exception as e:
            logger.error("添加种子到qBittorrent失败", error=str(e))
            raise
    
    async def get_task_status(self, task_id: str) -> DownloadTask:
        """获取任务状态"""
        # 简化的状态获取，实际实现需要更复杂的逻辑
        return DownloadTask(
            task_id=task_id,
            torrent_info=TorrentInfo("", "", "", 0, 0, 0, datetime.now(), ""),
            download_path="",
            status=DownloadStatus.DOWNLOADING,
            progress=50.0
        )
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        try:
            self.client.torrents_pause(torrent_hashes=task_id)
            return True
        except Exception as e:
            logger.error("暂停任务失败", error=str(e))
            return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        try:
            self.client.torrents_resume(torrent_hashes=task_id)
            return True
        except Exception as e:
            logger.error("恢复任务失败", error=str(e))
            return False


class TransmissionAdapter(DownloaderAdapter):
    """Transmission适配器"""
    
    def __init__(self):
        self.client = None
    
    async def add_torrent(self, torrent_file: str, download_path: str) -> str:
        """添加种子到Transmission"""
        try:
            import transmission_rpc
            
            if not self.client:
                self.client = transmission_rpc.Client()
            
            # 添加种子
            result = self.client.add_torrent(
                torrent=torrent_file,
                download_dir=download_path
            )
            
            return result.id
            
        except Exception as e:
            logger.error("添加种子到Transmission失败", error=str(e))
            raise
    
    async def get_task_status(self, task_id: str) -> DownloadTask:
        """获取任务状态"""
        # 简化的状态获取
        return DownloadTask(
            task_id=task_id,
            torrent_info=TorrentInfo("", "", "", 0, 0, 0, datetime.now(), ""),
            download_path="",
            status=DownloadStatus.DOWNLOADING,
            progress=50.0
        )
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        try:
            self.client.stop_torrent(ids=[task_id])
            return True
        except Exception as e:
            logger.error("暂停任务失败", error=str(e))
            return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        try:
            self.client.start_torrent(ids=[task_id])
            return True
        except Exception as e:
            logger.error("恢复任务失败", error=str(e))
            return False


class Aria2Adapter(DownloaderAdapter):
    """Aria2适配器"""
    
    def __init__(self):
        self.client = None
    
    async def add_torrent(self, torrent_file: str, download_path: str) -> str:
        """添加种子到Aria2"""
        try:
            import aria2p
            
            if not self.client:
                self.client = aria2p.API()
            
            # 添加种子
            result = self.client.add_torrent(
                torrent_file_path=torrent_file,
                options={"dir": download_path}
            )
            
            return result.gid
            
        except Exception as e:
            logger.error("添加种子到Aria2失败", error=str(e))
            raise
    
    async def get_task_status(self, task_id: str) -> DownloadTask:
        """获取任务状态"""
        # 简化的状态获取
        return DownloadTask(
            task_id=task_id,
            torrent_info=TorrentInfo("", "", "", 0, 0, 0, datetime.now(), ""),
            download_path="",
            status=DownloadStatus.DOWNLOADING,
            progress=50.0
        )
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        try:
            self.client.pause([task_id])
            return True
        except Exception as e:
            logger.error("暂停任务失败", error=str(e))
            return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        try:
            self.client.unpause([task_id])
            return True
        except Exception as e:
            logger.error("恢复任务失败", error=str(e))
            return False