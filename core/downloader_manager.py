#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载器管理器
监控和管理各种下载器（qBittorrent、Aria2、Transmission等）
参考MoviePilot的下载器监控功能设计
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class DownloaderType(Enum):
    """下载器类型"""
    QBITTORRENT = "qbittorrent"
    ARIA2 = "aria2"
    TRANSMISSION = "transmission"
    DELUGE = "deluge"


class DownloadStatus(Enum):
    """下载状态"""
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    QUEUED = "queued"
    CHECKING = "checking"


@dataclass
class DownloadTask:
    """下载任务"""
    id: str
    name: str
    status: DownloadStatus
    progress: float  # 0-100
    size: int  # 字节
    downloaded: int  # 已下载字节
    download_speed: int  # 下载速度 bytes/s
    upload_speed: int  # 上传速度 bytes/s
    eta: Optional[int] = None  # 预计剩余时间（秒）
    peers: int = 0
    seeds: int = 0
    ratio: float = 0.0
    added_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None


@dataclass
class DownloaderInfo:
    """下载器信息"""
    id: str
    name: str
    type: DownloaderType
    status: str  # connected, disconnected, error
    version: Optional[str] = None
    free_space: Optional[int] = None  # 剩余空间 bytes
    total_tasks: int = 0
    active_tasks: int = 0
    download_speed: int = 0  # 总下载速度 bytes/s
    upload_speed: int = 0  # 总上传速度 bytes/s
    last_update: Optional[datetime] = None


class DownloaderManager:
    """下载器管理器"""
    
    def __init__(self):
        self.downloaders: Dict[str, DownloaderInfo] = {}
        self.tasks: Dict[str, DownloadTask] = {}
        self.monitoring = False
        self.update_interval = 10  # 更新间隔（秒）
        
    async def add_downloader(self, downloader_config: Dict[str, Any]) -> bool:
        """添加下载器"""
        try:
            downloader_id = downloader_config["id"]
            downloader_type = DownloaderType(downloader_config["type"])
            
            # 测试连接
            if not await self._test_connection(downloader_config):
                return False
            
            # 获取下载器信息
            downloader_info = await self._get_downloader_info(downloader_config)
            if not downloader_info:
                return False
            
            self.downloaders[downloader_id] = downloader_info
            return True
            
        except Exception as e:
            print(f"添加下载器失败: {e}")
            return False
    
    async def remove_downloader(self, downloader_id: str) -> bool:
        """移除下载器"""
        if downloader_id in self.downloaders:
            del self.downloaders[downloader_id]
            # 同时移除该下载器的所有任务
            self.tasks = {task_id: task for task_id, task in self.tasks.items() 
                         if not task_id.startswith(f"{downloader_id}_")}
            return True
        return False
    
    async def update_downloaders_status(self):
        """更新所有下载器状态"""
        for downloader_id, downloader_info in self.downloaders.items():
            try:
                # 获取下载器配置（这里需要从配置中获取）
                config = self._get_downloader_config(downloader_id)
                if not config:
                    continue
                
                # 更新下载器信息
                updated_info = await self._get_downloader_info(config)
                if updated_info:
                    self.downloaders[downloader_id] = updated_info
                
                # 更新任务列表
                await self._update_downloader_tasks(downloader_id, config)
                
            except Exception as e:
                print(f"更新下载器 {downloader_id} 状态失败: {e}")
                # 标记下载器为错误状态
                self.downloaders[downloader_id].status = "error"
    
    async def _test_connection(self, config: Dict[str, Any]) -> bool:
        """测试下载器连接"""
        try:
            downloader_type = DownloaderType(config["type"])
            
            if downloader_type == DownloaderType.QBITTORRENT:
                return await self._test_qbittorrent_connection(config)
            elif downloader_type == DownloaderType.ARIA2:
                return await self._test_aria2_connection(config)
            elif downloader_type == DownloaderType.TRANSMISSION:
                return await self._test_transmission_connection(config)
            
            return False
        except Exception as e:
            print(f"测试连接失败: {e}")
            return False
    
    async def _test_qbittorrent_connection(self, config: Dict[str, Any]) -> bool:
        """测试qBittorrent连接"""
        try:
            base_url = config["url"]
            username = config.get("username")
            password = config.get("password")
            
            async with aiohttp.ClientSession() as session:
                # 登录
                login_data = {
                    "username": username or "",
                    "password": password or ""
                }
                
                async with session.post(f"{base_url}/api/v2/auth/login", data=login_data) as response:
                    if response.status != 200:
                        return False
                
                # 测试API
                async with session.get(f"{base_url}/api/v2/app/version") as response:
                    return response.status == 200
                    
        except Exception as e:
            return False
    
    async def _test_aria2_connection(self, config: Dict[str, Any]) -> bool:
        """测试Aria2连接"""
        try:
            # Aria2使用JSON-RPC over HTTP
            base_url = config["url"]
            secret = config.get("secret")
            
            payload = {
                "jsonrpc": "2.0",
                "id": "test",
                "method": "aria2.getVersion",
                "params": [f"token:{secret}"] if secret else []
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(base_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return "result" in result
                    return False
                    
        except Exception as e:
            return False
    
    async def _test_transmission_connection(self, config: Dict[str, Any]) -> bool:
        """测试Transmission连接"""
        try:
            base_url = config["url"]
            username = config.get("username")
            password = config.get("password")
            
            auth = aiohttp.BasicAuth(username, password) if username and password else None
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "method": "session-stats",
                    "tag": 1
                }
                
                async with session.post(base_url, json=payload, auth=auth) as response:
                    if response.status == 200:
                        result = await response.json()
                        return "result" in result and result["result"] == "success"
                    return False
                    
        except Exception as e:
            return False
    
    async def _get_downloader_info(self, config: Dict[str, Any]) -> Optional[DownloaderInfo]:
        """获取下载器信息"""
        try:
            downloader_type = DownloaderType(config["type"])
            
            if downloader_type == DownloaderType.QBITTORRENT:
                return await self._get_qbittorrent_info(config)
            elif downloader_type == DownloaderType.ARIA2:
                return await self._get_aria2_info(config)
            elif downloader_type == DownloaderType.TRANSMISSION:
                return await self._get_transmission_info(config)
            
            return None
        except Exception as e:
            print(f"获取下载器信息失败: {e}")
            return None
    
    async def _get_qbittorrent_info(self, config: Dict[str, Any]) -> Optional[DownloaderInfo]:
        """获取qBittorrent信息"""
        try:
            base_url = config["url"]
            
            async with aiohttp.ClientSession() as session:
                # 登录
                login_data = {
                    "username": config.get("username", ""),
                    "password": config.get("password", "")
                }
                
                async with session.post(f"{base_url}/api/v2/auth/login", data=login_data) as response:
                    if response.status != 200:
                        return None
                
                # 获取应用信息
                async with session.get(f"{base_url}/api/v2/app/version") as response:
                    if response.status != 200:
                        return None
                    version = await response.text()
                
                # 获取传输信息
                async with session.get(f"{base_url}/api/v2/transfer/info") as response:
                    if response.status != 200:
                        return None
                    transfer_info = await response.json()
                
                return DownloaderInfo(
                    id=config["id"],
                    name=config.get("name", "qBittorrent"),
                    type=DownloaderType.QBITTORRENT,
                    status="connected",
                    version=version,
                    free_space=transfer_info.get("free_space_on_disk"),
                    download_speed=transfer_info.get("dl_info_speed", 0),
                    upload_speed=transfer_info.get("up_info_speed", 0),
                    last_update=datetime.now()
                )
                
        except Exception as e:
            return None
    
    async def _get_aria2_info(self, config: Dict[str, Any]) -> Optional[DownloaderInfo]:
        """获取Aria2信息"""
        try:
            base_url = config["url"]
            secret = config.get("secret")
            
            payload = {
                "jsonrpc": "2.0",
                "id": "info",
                "method": "aria2.getGlobalStat",
                "params": [f"token:{secret}"] if secret else []
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(base_url, json=payload) as response:
                    if response.status != 200:
                        return None
                    
                    result = await response.json()
                    if "result" not in result:
                        return None
                    
                    global_stat = result["result"]
                    
                    return DownloaderInfo(
                        id=config["id"],
                        name=config.get("name", "Aria2"),
                        type=DownloaderType.ARIA2,
                        status="connected",
                        download_speed=int(global_stat.get("downloadSpeed", 0)),
                        upload_speed=int(global_stat.get("uploadSpeed", 0)),
                        last_update=datetime.now()
                    )
                    
        except Exception as e:
            return None
    
    async def _get_transmission_info(self, config: Dict[str, Any]) -> Optional[DownloaderInfo]:
        """获取Transmission信息"""
        try:
            base_url = config["url"]
            username = config.get("username")
            password = config.get("password")
            
            auth = aiohttp.BasicAuth(username, password) if username and password else None
            
            payload = {
                "method": "session-stats",
                "tag": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(base_url, json=payload, auth=auth) as response:
                    if response.status != 200:
                        return None
                    
                    result = await response.json()
                    if result.get("result") != "success":
                        return None
                    
                    stats = result.get("arguments", {})
                    
                    return DownloaderInfo(
                        id=config["id"],
                        name=config.get("name", "Transmission"),
                        type=DownloaderType.TRANSMISSION,
                        status="connected",
                        download_speed=stats.get("downloadSpeed", 0),
                        upload_speed=stats.get("uploadSpeed", 0),
                        last_update=datetime.now()
                    )
                    
        except Exception as e:
            return None
    
    async def _update_downloader_tasks(self, downloader_id: str, config: Dict[str, Any]):
        """更新下载器任务列表"""
        try:
            downloader_type = DownloaderType(config["type"])
            
            if downloader_type == DownloaderType.QBITTORRENT:
                await self._update_qbittorrent_tasks(downloader_id, config)
            elif downloader_type == DownloaderType.ARIA2:
                await self._update_aria2_tasks(downloader_id, config)
            elif downloader_type == DownloaderType.TRANSMISSION:
                await self._update_transmission_tasks(downloader_id, config)
                
        except Exception as e:
            print(f"更新下载器 {downloader_id} 任务失败: {e}")
    
    async def _update_qbittorrent_tasks(self, downloader_id: str, config: Dict[str, Any]):
        """更新qBittorrent任务"""
        try:
            base_url = config["url"]
            
            async with aiohttp.ClientSession() as session:
                # 登录
                login_data = {
                    "username": config.get("username", ""),
                    "password": config.get("password", "")
                }
                
                async with session.post(f"{base_url}/api/v2/auth/login", data=login_data) as response:
                    if response.status != 200:
                        return
                
                # 获取任务列表
                async with session.get(f"{base_url}/api/v2/torrents/info") as response:
                    if response.status != 200:
                        return
                    
                    torrents = await response.json()
                    
                    for torrent in torrents:
                        task_id = f"{downloader_id}_{torrent['hash']}"
                        
                        # 转换状态
                        qb_status = torrent.get("state", "")
                        if qb_status in ["downloading", "stalledDL"]:
                            status = DownloadStatus.DOWNLOADING
                        elif qb_status in ["uploading", "stalledUP"]:
                            status = DownloadStatus.COMPLETED
                        elif qb_status == "pausedDL":
                            status = DownloadStatus.PAUSED
                        elif qb_status == "checking":
                            status = DownloadStatus.CHECKING
                        elif qb_status == "queuedDL":
                            status = DownloadStatus.QUEUED
                        else:
                            status = DownloadStatus.ERROR
                        
                        task = DownloadTask(
                            id=task_id,
                            name=torrent.get("name", "Unknown"),
                            status=status,
                            progress=torrent.get("progress", 0) * 100,
                            size=torrent.get("total_size", 0),
                            downloaded=torrent.get("completed", 0),
                            download_speed=torrent.get("dlspeed", 0),
                            upload_speed=torrent.get("upspeed", 0),
                            ratio=torrent.get("ratio", 0),
                            peers=torrent.get("num_leechs", 0),
                            seeds=torrent.get("num_seeds", 0),
                            added_time=datetime.fromtimestamp(torrent.get("added_on", 0))
                        )
                        
                        self.tasks[task_id] = task
                        
        except Exception as e:
            print(f"更新qBittorrent任务失败: {e}")
    
    async def _update_aria2_tasks(self, downloader_id: str, config: Dict[str, Any]):
        """更新Aria2任务"""
        try:
            base_url = config["url"]
            secret = config.get("secret")
            
            payload = {
                "jsonrpc": "2.0",
                "id": "tasks",
                "method": "aria2.tellActive",
                "params": [f"token:{secret}"] if secret else []
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(base_url, json=payload) as response:
                    if response.status != 200:
                        return
                    
                    result = await response.json()
                    if "result" not in result:
                        return
                    
                    for task_data in result["result"]:
                        task_id = f"{downloader_id}_{task_data['gid']}"
                        
                        task = DownloadTask(
                            id=task_id,
                            name=task_data.get("bittorrent", {}).get("info", {}).get("name", "Unknown"),
                            status=DownloadStatus.DOWNLOADING,
                            progress=float(task_data.get("completedLength", 0)) / float(task_data.get("totalLength", 1)) * 100,
                            size=int(task_data.get("totalLength", 0)),
                            downloaded=int(task_data.get("completedLength", 0)),
                            download_speed=int(task_data.get("downloadSpeed", 0)),
                            upload_speed=int(task_data.get("uploadSpeed", 0)),
                            added_time=datetime.fromtimestamp(int(task_data.get("addedTime", 0)) / 1000)
                        )
                        
                        self.tasks[task_id] = task
                        
        except Exception as e:
            print(f"更新Aria2任务失败: {e}")
    
    async def _update_transmission_tasks(self, downloader_id: str, config: Dict[str, Any]):
        """更新Transmission任务"""
        # 实现类似上面的逻辑
        pass
    
    def _get_downloader_config(self, downloader_id: str) -> Optional[Dict[str, Any]]:
        """获取下载器配置（这里需要从配置文件或数据库获取）"""
        # 这里应该从配置中获取实际的下载器配置
        # 暂时返回模拟配置
        mock_configs = {
            "qbittorrent": {
                "id": "qbittorrent",
                "type": "qbittorrent",
                "name": "qBittorrent",
                "url": "http://localhost:8080",
                "username": "admin",
                "password": "adminadmin"
            },
            "aria2": {
                "id": "aria2",
                "type": "aria2",
                "name": "Aria2",
                "url": "http://localhost:6800/jsonrpc",
                "secret": "secret"
            }
        }
        
        return mock_configs.get(downloader_id)
    
    def get_downloaders_summary(self) -> Dict[str, Any]:
        """获取下载器汇总信息"""
        total_downloaders = len(self.downloaders)
        connected_downloaders = len([d for d in self.downloaders.values() if d.status == "connected"])
        
        total_tasks = len(self.tasks)
        active_tasks = len([t for t in self.tasks.values() if t.status == DownloadStatus.DOWNLOADING])
        
        total_download_speed = sum(d.download_speed for d in self.downloaders.values())
        total_upload_speed = sum(d.upload_speed for d in self.downloaders.values())
        
        return {
            "total_downloaders": total_downloaders,
            "connected_downloaders": connected_downloaders,
            "total_tasks": total_tasks,
            "active_tasks": active_tasks,
            "total_download_speed": total_download_speed,
            "total_upload_speed": total_upload_speed,
            "last_update": datetime.now().isoformat()
        }
    
    async def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        
        # 启动监控循环
        asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                await self.update_downloaders_status()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                print(f"下载器监控循环错误: {e}")
                await asyncio.sleep(self.update_interval)


# 全局下载器管理器实例
downloader_manager = DownloaderManager()