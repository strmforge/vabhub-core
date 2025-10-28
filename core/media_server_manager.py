#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体服务器管理器
集成Plex、Jellyfin、Emby等媒体服务器
参考MoviePilot的媒体服务器集成功能设计
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class MediaServerType(Enum):
    """媒体服务器类型"""
    PLEX = "plex"
    JELLYFIN = "jellyfin"
    EMBY = "emby"


class MediaType(Enum):
    """媒体类型"""
    MOVIE = "movie"
    TV_SHOW = "tvshow"
    EPISODE = "episode"
    MUSIC = "music"
    PHOTO = "photo"


@dataclass
class LibraryInfo:
    """媒体库信息"""
    id: str
    name: str
    type: MediaType
    content_count: int
    last_scan: Optional[datetime] = None
    size: Optional[int] = None  # 字节


@dataclass
class ActiveStream:
    """活跃流信息"""
    id: str
    user: str
    title: str
    type: MediaType
    progress: float  # 0-100
    duration: int  # 秒
    quality: str
    client: str
    start_time: datetime


@dataclass
class MediaServerInfo:
    """媒体服务器信息"""
    id: str
    name: str
    type: MediaServerType
    status: str  # connected, disconnected, error
    version: Optional[str] = None
    url: Optional[str] = None
    libraries: List[LibraryInfo] = None
    active_streams: List[ActiveStream] = None
    total_users: int = 0
    online_users: int = 0
    last_sync: Optional[datetime] = None
    
    def __post_init__(self):
        if self.libraries is None:
            self.libraries = []
        if self.active_streams is None:
            self.active_streams = []


class MediaServerManager:
    """媒体服务器管理器"""
    
    def __init__(self):
        self.servers: Dict[str, MediaServerInfo] = {}
        self.monitoring = False
        self.update_interval = 30  # 更新间隔（秒）
        
    async def add_server(self, server_config: Dict[str, Any]) -> bool:
        """添加媒体服务器"""
        try:
            server_id = server_config["id"]
            server_type = MediaServerType(server_config["type"])
            
            # 测试连接
            if not await self._test_connection(server_config):
                return False
            
            # 获取服务器信息
            server_info = await self._get_server_info(server_config)
            if not server_info:
                return False
            
            self.servers[server_id] = server_info
            return True
            
        except Exception as e:
            print(f"添加媒体服务器失败: {e}")
            return False
    
    async def remove_server(self, server_id: str) -> bool:
        """移除媒体服务器"""
        if server_id in self.servers:
            del self.servers[server_id]
            return True
        return False
    
    async def update_servers_status(self):
        """更新所有媒体服务器状态"""
        for server_id, server_info in self.servers.items():
            try:
                # 获取服务器配置
                config = self._get_server_config(server_id)
                if not config:
                    continue
                
                # 更新服务器信息
                updated_info = await self._get_server_info(config)
                if updated_info:
                    self.servers[server_id] = updated_info
                
            except Exception as e:
                print(f"更新媒体服务器 {server_id} 状态失败: {e}")
                # 标记服务器为错误状态
                self.servers[server_id].status = "error"
    
    async def _test_connection(self, config: Dict[str, Any]) -> bool:
        """测试媒体服务器连接"""
        try:
            server_type = MediaServerType(config["type"])
            
            if server_type == MediaServerType.PLEX:
                return await self._test_plex_connection(config)
            elif server_type == MediaServerType.JELLYFIN:
                return await self._test_jellyfin_connection(config)
            elif server_type == MediaServerType.EMBY:
                return await self._test_emby_connection(config)
            
            return False
        except Exception as e:
            print(f"测试连接失败: {e}")
            return False
    
    async def _test_plex_connection(self, config: Dict[str, Any]) -> bool:
        """测试Plex连接"""
        try:
            base_url = config["url"]
            token = config.get("token")
            
            headers = {
                "X-Plex-Token": token,
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/status/sessions", headers=headers) as response:
                    return response.status == 200
                    
        except Exception as e:
            return False
    
    async def _test_jellyfin_connection(self, config: Dict[str, Any]) -> bool:
        """测试Jellyfin连接"""
        try:
            base_url = config["url"]
            api_key = config.get("api_key")
            
            headers = {
                "X-Emby-Token": api_key,
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/System/Info", headers=headers) as response:
                    return response.status == 200
                    
        except Exception as e:
            return False
    
    async def _test_emby_connection(self, config: Dict[str, Any]) -> bool:
        """测试Emby连接"""
        try:
            base_url = config["url"]
            api_key = config.get("api_key")
            
            headers = {
                "X-Emby-Token": api_key,
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/System/Info", headers=headers) as response:
                    return response.status == 200
                    
        except Exception as e:
            return False
    
    async def _get_server_info(self, config: Dict[str, Any]) -> Optional[MediaServerInfo]:
        """获取媒体服务器信息"""
        try:
            server_type = MediaServerType(config["type"])
            
            if server_type == MediaServerType.PLEX:
                return await self._get_plex_info(config)
            elif server_type == MediaServerType.JELLYFIN:
                return await self._get_jellyfin_info(config)
            elif server_type == MediaServerType.EMBY:
                return await self._get_emby_info(config)
            
            return None
        except Exception as e:
            print(f"获取媒体服务器信息失败: {e}")
            return None
    
    async def _get_plex_info(self, config: Dict[str, Any]) -> Optional[MediaServerInfo]:
        """获取Plex信息"""
        try:
            base_url = config["url"]
            token = config.get("token")
            
            headers = {
                "X-Plex-Token": token,
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # 获取服务器信息
                async with session.get(f"{base_url}", headers=headers) as response:
                    if response.status != 200:
                        return None
                    
                    # Plex返回XML，这里简化处理
                    # 实际应该解析XML获取详细信息
                    
                # 获取活跃会话
                async with session.get(f"{base_url}/status/sessions", headers=headers) as response:
                    if response.status != 200:
                        active_streams = []
                    else:
                        # 解析活跃会话
                        active_streams = await self._parse_plex_sessions(await response.text())
                
                # 获取媒体库信息
                async with session.get(f"{base_url}/library/sections", headers=headers) as response:
                    if response.status != 200:
                        libraries = []
                    else:
                        # 解析媒体库
                        libraries = await self._parse_plex_libraries(await response.text())
                
                return MediaServerInfo(
                    id=config["id"],
                    name=config.get("name", "Plex Media Server"),
                    type=MediaServerType.PLEX,
                    status="connected",
                    url=base_url,
                    libraries=libraries,
                    active_streams=active_streams,
                    last_sync=datetime.now()
                )
                
        except Exception as e:
            return None
    
    async def _get_jellyfin_info(self, config: Dict[str, Any]) -> Optional[MediaServerInfo]:
        """获取Jellyfin信息"""
        try:
            base_url = config["url"]
            api_key = config.get("api_key")
            
            headers = {
                "X-Emby-Token": api_key,
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # 获取系统信息
                async with session.get(f"{base_url}/System/Info", headers=headers) as response:
                    if response.status != 200:
                        return None
                    
                    system_info = await response.json()
                
                # 获取活跃会话
                async with session.get(f"{base_url}/Sessions", headers=headers) as response:
                    if response.status != 200:
                        active_streams = []
                    else:
                        sessions_data = await response.json()
                        active_streams = self._parse_jellyfin_sessions(sessions_data)
                
                # 获取媒体库信息
                async with session.get(f"{base_url}/Library/VirtualFolders", headers=headers) as response:
                    if response.status != 200:
                        libraries = []
                    else:
                        libraries_data = await response.json()
                        libraries = self._parse_jellyfin_libraries(libraries_data)
                
                return MediaServerInfo(
                    id=config["id"],
                    name=config.get("name", system_info.get("ServerName", "Jellyfin")),
                    type=MediaServerType.JELLYFIN,
                    status="connected",
                    version=system_info.get("Version"),
                    url=base_url,
                    libraries=libraries,
                    active_streams=active_streams,
                    total_users=system_info.get("TotalUsers", 0),
                    online_users=len(active_streams),
                    last_sync=datetime.now()
                )
                
        except Exception as e:
            return None
    
    async def _get_emby_info(self, config: Dict[str, Any]) -> Optional[MediaServerInfo]:
        """获取Emby信息"""
        # 实现类似Jellyfin的逻辑
        try:
            base_url = config["url"]
            api_key = config.get("api_key")
            
            headers = {
                "X-Emby-Token": api_key,
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # 获取系统信息
                async with session.get(f"{base_url}/System/Info", headers=headers) as response:
                    if response.status != 200:
                        return None
                    
                    system_info = await response.json()
                
                # 获取活跃会话
                async with session.get(f"{base_url}/Sessions", headers=headers) as response:
                    if response.status != 200:
                        active_streams = []
                    else:
                        sessions_data = await response.json()
                        active_streams = self._parse_emby_sessions(sessions_data)
                
                # 获取媒体库信息
                async with session.get(f"{base_url}/Library/VirtualFolders", headers=headers) as response:
                    if response.status != 200:
                        libraries = []
                    else:
                        libraries_data = await response.json()
                        libraries = self._parse_emby_libraries(libraries_data)
                
                return MediaServerInfo(
                    id=config["id"],
                    name=config.get("name", system_info.get("ServerName", "Emby")),
                    type=MediaServerType.EMBY,
                    status="connected",
                    version=system_info.get("Version"),
                    url=base_url,
                    libraries=libraries,
                    active_streams=active_streams,
                    total_users=system_info.get("TotalUsers", 0),
                    online_users=len(active_streams),
                    last_sync=datetime.now()
                )
                
        except Exception as e:
            return None
    
    async def _parse_plex_sessions(self, xml_data: str) -> List[ActiveStream]:
        """解析Plex活跃会话"""
        # 简化实现，实际应该解析XML
        return []
    
    async def _parse_plex_libraries(self, xml_data: str) -> List[LibraryInfo]:
        """解析Plex媒体库"""
        # 简化实现，实际应该解析XML
        return [
            LibraryInfo(
                id="1",
                name="电影",
                type=MediaType.MOVIE,
                content_count=856
            ),
            LibraryInfo(
                id="2",
                name="电视剧",
                type=MediaType.TV_SHOW,
                content_count=312
            )
        ]
    
    def _parse_jellyfin_sessions(self, sessions_data: List[Dict]) -> List[ActiveStream]:
        """解析Jellyfin活跃会话"""
        active_streams = []
        
        for session in sessions_data:
            if session.get("NowPlayingItem"):
                item = session["NowPlayingItem"]
                
                # 确定媒体类型
                media_type = self._get_media_type_from_jellyfin(item.get("Type"))
                
                # 计算进度
                if item.get("RunTimeTicks") and session.get("PlayState", {}).get("PositionTicks"):
                    progress = (session["PlayState"]["PositionTicks"] / item["RunTimeTicks"]) * 100
                else:
                    progress = 0
                
                stream = ActiveStream(
                    id=session.get("Id"),
                    user=session.get("UserName", "Unknown"),
                    title=item.get("Name", "Unknown"),
                    type=media_type,
                    progress=progress,
                    duration=item.get("RunTimeTicks", 0) // 10000000 if item.get("RunTimeTicks") else 0,
                    quality=item.get("MediaStreams", [{}])[0].get("DisplayTitle", "Unknown"),
                    client=session.get("Client", "Unknown"),
                    start_time=datetime.fromisoformat(session.get("LastActivityDate", datetime.now().isoformat()))
                )
                
                active_streams.append(stream)
        
        return active_streams
    
    def _parse_jellyfin_libraries(self, libraries_data: List[Dict]) -> List[LibraryInfo]:
        """解析Jellyfin媒体库"""
        libraries = []
        
        for lib in libraries_data:
            # 确定媒体类型
            media_type = self._get_media_type_from_jellyfin(lib.get("CollectionType"))
            
            library = LibraryInfo(
                id=lib.get("ItemId"),
                name=lib.get("Name", "Unknown"),
                type=media_type,
                content_count=lib.get("LibraryOptions", {}).get("TotalRecordCount", 0)
            )
            
            libraries.append(library)
        
        return libraries
    
    def _parse_emby_sessions(self, sessions_data: List[Dict]) -> List[ActiveStream]:
        """解析Emby活跃会话"""
        # 实现类似Jellyfin的逻辑
        return self._parse_jellyfin_sessions(sessions_data)
    
    def _parse_emby_libraries(self, libraries_data: List[Dict]) -> List[LibraryInfo]:
        """解析Emby媒体库"""
        # 实现类似Jellyfin的逻辑
        return self._parse_jellyfin_libraries(libraries_data)
    
    def _get_media_type_from_jellyfin(self, type_str: str) -> MediaType:
        """从Jellyfin类型字符串获取媒体类型"""
        type_map = {
            "Movie": MediaType.MOVIE,
            "Series": MediaType.TV_SHOW,
            "Episode": MediaType.EPISODE,
            "Audio": MediaType.MUSIC,
            "Photo": MediaType.PHOTO
        }
        return type_map.get(type_str, MediaType.MOVIE)
    
    def _get_server_config(self, server_id: str) -> Optional[Dict[str, Any]]:
        """获取媒体服务器配置"""
        # 这里应该从配置中获取实际的服务器配置
        # 暂时返回模拟配置
        mock_configs = {
            "plex": {
                "id": "plex",
                "type": "plex",
                "name": "Plex Media Server",
                "url": "http://localhost:32400",
                "token": "your_plex_token"
            },
            "jellyfin": {
                "id": "jellyfin",
                "type": "jellyfin",
                "name": "Jellyfin",
                "url": "http://localhost:8096",
                "api_key": "your_jellyfin_api_key"
            }
        }
        
        return mock_configs.get(server_id)
    
    def get_servers_summary(self) -> Dict[str, Any]:
        """获取媒体服务器汇总信息"""
        total_servers = len(self.servers)
        connected_servers = len([s for s in self.servers.values() if s.status == "connected"])
        
        total_libraries = sum(len(s.libraries) for s in self.servers.values())
        total_media = sum(
            sum(lib.content_count for lib in s.libraries)
            for s in self.servers.values()
        )
        
        active_streams = sum(len(s.active_streams) for s in self.servers.values())
        total_users = sum(s.total_users for s in self.servers.values())
        online_users = sum(s.online_users for s in self.servers.values())
        
        return {
            "total_servers": total_servers,
            "connected_servers": connected_servers,
            "total_libraries": total_libraries,
            "total_media": total_media,
            "active_streams": active_streams,
            "total_users": total_users,
            "online_users": online_users,
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
                await self.update_servers_status()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                print(f"媒体服务器监控循环错误: {e}")
                await asyncio.sleep(self.update_interval)


# 全局媒体服务器管理器实例
media_server_manager = MediaServerManager()