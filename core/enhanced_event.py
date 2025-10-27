#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版事件驱动系统
支持PT功能的高级事件管理
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional, Set, Type
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import structlog

from app.utils.commons import SingletonMeta

logger = structlog.get_logger()


class EventType(Enum):
    """增强版事件类型枚举"""
    # PT相关事件
    PT_SITE_ADDED = "pt_site_added"
    PT_SITE_REMOVED = "pt_site_removed"
    PT_SITE_STATUS_CHANGED = "pt_site_status_changed"
    PT_SEARCH_STARTED = "pt_search_started"
    PT_SEARCH_COMPLETED = "pt_search_completed"
    PT_DOWNLOAD_STARTED = "pt_download_started"
    PT_DOWNLOAD_COMPLETED = "pt_download_completed"
    PT_DOWNLOAD_FAILED = "pt_download_failed"
    PT_DOWNLOAD_PAUSED = "pt_download_paused"
    PT_DOWNLOAD_RESUMED = "pt_download_resumed"
    PT_MONITORING_STARTED = "pt_monitoring_started"
    PT_MONITORING_STOPPED = "pt_monitoring_stopped"
    PT_RSS_FEED_UPDATED = "pt_rss_feed_updated"
    PT_AUTO_DOWNLOAD_TRIGGERED = "pt_auto_download_triggered"
    
    # 工作流事件
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_STEP_STARTED = "workflow_step_started"
    WORKFLOW_STEP_COMPLETED = "workflow_step_completed"
    
    # 插件事件
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    PLUGIN_ERROR = "plugin_error"
    
    # AI媒体处理事件
    AI_MEDIA_ANALYSIS_STARTED = "ai_media_analysis_started"
    AI_MEDIA_ANALYSIS_COMPLETED = "ai_media_analysis_completed"
    AI_MEDIA_TAGGING_STARTED = "ai_media_tagging_started"
    AI_MEDIA_TAGGING_COMPLETED = "ai_media_tagging_completed"


@dataclass
class Event:
    """增强版事件基类"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime = None
    source: str = "enhanced_system"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class PTEvent(Event):
    """PT事件基类"""
    site_name: str
    site_type: str
    torrent_title: Optional[str] = None
    torrent_url: Optional[str] = None


@dataclass
class PTSiteEvent(PTEvent):
    """PT站点事件"""
    site_url: str
    site_status: str
    priority: int = 1


@dataclass
class PTDownloadEvent(PTEvent):
    """PT下载事件"""
    task_id: str
    download_path: str
    downloader_type: str
    progress: float = 0.0
    speed: float = 0.0
    error_message: Optional[str] = None


@dataclass
class WorkflowEvent(Event):
    """工作流事件"""
    execution_id: str
    workflow_name: str
    step_name: Optional[str] = None
    step_result: Optional[Dict[str, Any]] = None


class EnhancedEventManager(metaclass=SingletonMeta):
    """增强版事件管理器"""
    
    def __init__(self):
        self._listeners: Dict[EventType, Set[Callable]] = {}
        self._async_listeners: Dict[EventType, Set[Callable]] = {}
        self._event_queue = asyncio.Queue()
        self._processing_task = None
        self._active = False
        
    def start(self):
        """启动事件处理器"""
        if not self._active:
            self._active = True
            self._processing_task = asyncio.create_task(self._process_events())
            logger.info("增强版事件管理器已启动")
    
    def stop(self):
        """停止事件处理器"""
        if self._active:
            self._active = False
            if self._processing_task:
                self._processing_task.cancel()
            logger.info("增强版事件管理器已停止")
    
    def subscribe(self, event_type: EventType, listener: Callable, is_async: bool = False):
        """订阅事件"""
        listeners = self._async_listeners if is_async else self._listeners
        if event_type not in listeners:
            listeners[event_type] = set()
        listeners[event_type].add(listener)
        logger.debug("事件监听器已注册", event_type=event_type.value)
    
    def unsubscribe(self, event_type: EventType, listener: Callable, is_async: bool = False):
        """取消订阅"""
        listeners = self._async_listeners if is_async else self._listeners
        if event_type in listeners:
            listeners[event_type].discard(listener)
        logger.debug("事件监听器已取消注册", event_type=event_type.value)
    
    def publish(self, event: Event):
        """发布事件（同步）"""
        logger.debug("发布增强版事件", event_type=event.event_type.value, source=event.source)
        
        # 处理同步监听器
        if event.event_type in self._listeners:
            for listener in self._listeners[event.event_type]:
                try:
                    listener(event)
                except Exception as e:
                    logger.error("增强版事件监听器执行失败", listener=str(listener), error=str(e))
    
    async def publish_async(self, event: Event):
        """发布事件（异步）"""
        logger.debug("发布增强版异步事件", event_type=event.event_type.value, source=event.source)
        
        # 将事件加入队列进行异步处理
        await self._event_queue.put(event)
    
    async def _process_events(self):
        """异步处理事件队列"""
        while self._active:
            try:
                # 从队列获取事件
                event = await self._event_queue.get()
                
                # 处理异步监听器
                if event.event_type in self._async_listeners:
                    tasks = []
                    for listener in self._async_listeners[event.event_type]:
                        if inspect.iscoroutinefunction(listener):
                            tasks.append(listener(event))
                        else:
                            # 如果是同步函数，在事件循环中运行
                            def sync_wrapper():
                                try:
                                    listener(event)
                                except Exception as e:
                                    logger.error("增强版异步事件监听器执行失败", listener=str(listener), error=str(e))
                            
                            tasks.append(asyncio.get_event_loop().run_in_executor(None, sync_wrapper))
                    
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
                
                # 标记任务完成
                self._event_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("增强版事件处理异常", error=str(e))
    
    def get_event_stats(self) -> Dict[str, Any]:
        """获取事件统计信息"""
        return {
            "active": self._active,
            "queue_size": self._event_queue.qsize(),
            "sync_listeners": {et.value: len(listeners) for et, listeners in self._listeners.items()},
            "async_listeners": {et.value: len(listeners) for et, listeners in self._async_listeners.items()}
        }


# 全局增强版事件管理器实例
enhanced_event_manager = EnhancedEventManager()