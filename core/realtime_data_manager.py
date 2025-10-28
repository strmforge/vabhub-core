#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时数据管理器
支持WebSocket实时推送和高效数据更新
参考MoviePilot的实时数据架构设计
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict


class DataType(Enum):
    """数据类型"""
    SYSTEM_MONITOR = "system_monitor"
    DOWNLOAD_STATUS = "download_status"
    MEDIA_SERVER = "media_server"
    AI_ANALYTICS = "ai_analytics"
    SCHEDULED_TASKS = "scheduled_tasks"
    SYSTEM_ALERTS = "system_alerts"


class UpdateFrequency(Enum):
    """更新频率"""
    HIGH = 1  # 1秒
    MEDIUM = 5  # 5秒
    LOW = 30  # 30秒
    VERY_LOW = 60  # 60秒


@dataclass
class DataSubscription:
    """数据订阅"""
    client_id: str
    data_types: Set[DataType]
    frequency: UpdateFrequency
    last_update: float = 0
    callback: Optional[Callable] = None


@dataclass
class CachedData:
    """缓存数据"""
    data: Any
    timestamp: float
    ttl: float  # 生存时间（秒）


class RealtimeDataManager:
    """实时数据管理器"""
    
    def __init__(self):
        self.subscriptions: Dict[str, DataSubscription] = {}
        self.data_cache: Dict[DataType, CachedData] = {}
        self.update_handlers: Dict[DataType, Callable] = {}
        self.running = False
        
        # 默认数据TTL
        self.default_ttl = {
            DataType.SYSTEM_MONITOR: 2.0,  # 系统监控数据2秒过期
            DataType.DOWNLOAD_STATUS: 10.0,  # 下载状态10秒过期
            DataType.MEDIA_SERVER: 30.0,  # 媒体服务器30秒过期
            DataType.AI_ANALYTICS: 60.0,  # AI分析60秒过期
            DataType.SCHEDULED_TASKS: 300.0,  # 定时任务5分钟过期
            DataType.SYSTEM_ALERTS: 600.0  # 系统警报10分钟过期
        }
        
        # 注册默认更新处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认更新处理器"""
        # 系统监控处理器
        self.update_handlers[DataType.SYSTEM_MONITOR] = self._update_system_monitor_data
        
        # 下载状态处理器
        self.update_handlers[DataType.DOWNLOAD_STATUS] = self._update_download_status_data
        
        # 媒体服务器处理器
        self.update_handlers[DataType.MEDIA_SERVER] = self._update_media_server_data
        
        # AI分析处理器
        self.update_handlers[DataType.AI_ANALYTICS] = self._update_ai_analytics_data
        
        # 定时任务处理器
        self.update_handlers[DataType.SCHEDULED_TASKS] = self._update_scheduled_tasks_data
        
        # 系统警报处理器
        self.update_handlers[DataType.SYSTEM_ALERTS] = self._update_system_alerts_data
    
    async def subscribe(self, client_id: str, data_types: List[DataType], 
                        frequency: UpdateFrequency = UpdateFrequency.MEDIUM,
                        callback: Optional[Callable] = None) -> bool:
        """订阅数据更新"""
        try:
            subscription = DataSubscription(
                client_id=client_id,
                data_types=set(data_types),
                frequency=frequency,
                callback=callback
            )
            
            self.subscriptions[client_id] = subscription
            
            # 立即发送一次数据
            await self._send_initial_data(client_id, data_types)
            
            return True
            
        except Exception as e:
            print(f"订阅数据失败: {e}")
            return False
    
    async def unsubscribe(self, client_id: str) -> bool:
        """取消订阅"""
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
            return True
        return False
    
    async def update_data(self, data_type: DataType, force: bool = False) -> bool:
        """更新指定类型的数据"""
        try:
            # 检查是否需要更新
            if not force and not self._should_update(data_type):
                return True
            
            # 获取更新处理器
            handler = self.update_handlers.get(data_type)
            if not handler:
                return False
            
            # 执行更新
            data = await handler()
            if data is None:
                return False
            
            # 缓存数据
            ttl = self.default_ttl.get(data_type, 30.0)
            self.data_cache[data_type] = CachedData(
                data=data,
                timestamp=time.time(),
                ttl=ttl
            )
            
            # 通知订阅者
            await self._notify_subscribers(data_type, data)
            
            return True
            
        except Exception as e:
            print(f"更新数据失败 {data_type}: {e}")
            return False
    
    async def update_all_data(self, force: bool = False) -> Dict[DataType, bool]:
        """更新所有类型的数据"""
        results = {}
        
        for data_type in DataType:
            success = await self.update_data(data_type, force)
            results[data_type] = success
        
        return results
    
    def get_cached_data(self, data_type: DataType) -> Optional[Any]:
        """获取缓存数据"""
        cached = self.data_cache.get(data_type)
        if not cached:
            return None
        
        # 检查是否过期
        if time.time() - cached.timestamp > cached.ttl:
            del self.data_cache[data_type]
            return None
        
        return cached.data
    
    def _should_update(self, data_type: DataType) -> bool:
        """检查是否需要更新数据"""
        cached = self.data_cache.get(data_type)
        if not cached:
            return True
        
        # 检查是否过期
        if time.time() - cached.timestamp > cached.ttl:
            return True
        
        # 检查是否有活跃订阅者需要高频更新
        for subscription in self.subscriptions.values():
            if data_type in subscription.data_types:
                # 如果订阅者要求更高频率的更新
                update_interval = subscription.frequency.value
                if time.time() - cached.timestamp > update_interval:
                    return True
        
        return False
    
    async def _send_initial_data(self, client_id: str, data_types: List[DataType]):
        """发送初始数据"""
        for data_type in data_types:
            data = self.get_cached_data(data_type)
            if data is None:
                # 如果没有缓存数据，立即更新
                await self.update_data(data_type, force=True)
                data = self.get_cached_data(data_type)
            
            if data is not None:
                await self._send_to_client(client_id, data_type, data)
    
    async def _notify_subscribers(self, data_type: DataType, data: Any):
        """通知订阅者"""
        current_time = time.time()
        
        for subscription in self.subscriptions.values():
            if data_type not in subscription.data_types:
                continue
            
            # 检查更新频率
            update_interval = subscription.frequency.value
            if current_time - subscription.last_update < update_interval:
                continue
            
            # 发送数据
            await self._send_to_client(subscription.client_id, data_type, data)
            subscription.last_update = current_time
    
    async def _send_to_client(self, client_id: str, data_type: DataType, data: Any):
        """发送数据到客户端"""
        subscription = self.subscriptions.get(client_id)
        if not subscription or not subscription.callback:
            return
        
        try:
            message = {
                "type": "data_update",
                "data_type": data_type.value,
                "data": data,
                "timestamp": time.time()
            }
            
            await subscription.callback(message)
            
        except Exception as e:
            print(f"发送数据到客户端失败 {client_id}: {e}")
    
    async def _update_system_monitor_data(self) -> Optional[Dict[str, Any]]:
        """更新系统监控数据"""
        try:
            # 这里应该调用实际的系统监控API
            # 暂时返回模拟数据
            return {
                "cpu": {
                    "usage": 25.5,
                    "cores": 8,
                    "temperature": 45.0
                },
                "memory": {
                    "total": 16384,
                    "used": 8192,
                    "percent": 50.0
                },
                "disk": {
                    "total": 1000000,
                    "used": 500000,
                    "percent": 50.0
                },
                "network": {
                    "upload": 1024,
                    "download": 2048,
                    "connections": 150
                }
            }
        except Exception as e:
            print(f"更新系统监控数据失败: {e}")
            return None
    
    async def _update_download_status_data(self) -> Optional[Dict[str, Any]]:
        """更新下载状态数据"""
        try:
            # 这里应该调用实际的下载器API
            # 暂时返回模拟数据
            return {
                "active_tasks": 3,
                "total_speed": 3.7,
                "tasks": [
                    {
                        "name": "movie_sample.mkv",
                        "progress": 75.5,
                        "speed": 2.5,
                        "size": 2048,
                        "eta": 120
                    },
                    {
                        "name": "tv_show_s01e01.mkv",
                        "progress": 45.2,
                        "speed": 1.2,
                        "size": 1024,
                        "eta": 300
                    }
                ]
            }
        except Exception as e:
            print(f"更新下载状态数据失败: {e}")
            return None
    
    async def _update_media_server_data(self) -> Optional[Dict[str, Any]]:
        """更新媒体服务器数据"""
        try:
            # 这里应该调用实际的媒体服务器API
            # 暂时返回模拟数据
            return {
                "servers": [
                    {
                        "name": "Plex",
                        "status": "online",
                        "libraries": 3,
                        "active_streams": 2
                    },
                    {
                        "name": "Jellyfin",
                        "status": "online",
                        "libraries": 2,
                        "active_streams": 1
                    }
                ],
                "total_media": 1168,
                "active_streams": 3
            }
        except Exception as e:
            print(f"更新媒体服务器数据失败: {e}")
            return None
    
    async def _update_ai_analytics_data(self) -> Optional[Dict[str, Any]]:
        """更新AI分析数据"""
        try:
            # 这里应该调用实际的AI分析API
            # 暂时返回模拟数据
            return {
                "total_analyses": 1284,
                "average_confidence": 92.5,
                "success_rate": 98.2,
                "recent_analyses": [
                    {
                        "file": "movie_sample.mkv",
                        "confidence": 96.2,
                        "time": 2.3
                    },
                    {
                        "file": "music_album.flac",
                        "confidence": 88.7,
                        "time": 1.8
                    }
                ]
            }
        except Exception as e:
            print(f"更新AI分析数据失败: {e}")
            return None
    
    async def _update_scheduled_tasks_data(self) -> Optional[Dict[str, Any]]:
        """更新定时任务数据"""
        try:
            # 这里应该调用实际的定时任务API
            # 暂时返回模拟数据
            return {
                "tasks": [
                    {
                        "name": "媒体库扫描",
                        "status": "enabled",
                        "last_run": "2024-01-15T10:00:00",
                        "next_run": "2024-01-15T12:00:00"
                    },
                    {
                        "name": "订阅检查",
                        "status": "enabled",
                        "last_run": "2024-01-15T09:30:00",
                        "next_run": "2024-01-15T10:30:00"
                    }
                ]
            }
        except Exception as e:
            print(f"更新定时任务数据失败: {e}")
            return None
    
    async def _update_system_alerts_data(self) -> Optional[Dict[str, Any]]:
        """更新系统警报数据"""
        try:
            # 这里应该调用实际的警报系统API
            # 暂时返回模拟数据
            return {
                "alerts": [
                    {
                        "level": "warning",
                        "message": "CPU使用率超过80%",
                        "timestamp": "2024-01-15T10:15:00"
                    },
                    {
                        "level": "info",
                        "message": "媒体库扫描完成",
                        "timestamp": "2024-01-15T10:00:00"
                    }
                ],
                "total_alerts": 2
            }
        except Exception as e:
            print(f"更新系统警报数据失败: {e}")
            return None
    
    async def start(self):
        """启动实时数据管理器"""
        if self.running:
            return
        
        self.running = True
        
        # 启动更新循环
        asyncio.create_task(self._update_loop())
    
    async def stop(self):
        """停止实时数据管理器"""
        self.running = False
    
    async def _update_loop(self):
        """更新循环"""
        while self.running:
            try:
                # 更新所有需要更新的数据
                await self.update_all_data()
                
                # 等待一段时间
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"实时数据更新循环错误: {e}")
                await asyncio.sleep(1)


# 全局实时数据管理器实例
realtime_data_manager = RealtimeDataManager()