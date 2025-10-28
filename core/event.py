#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 事件系统
参照MoviePilot的事件系统设计，提供完善的事件驱动架构
"""

import asyncio
import importlib
import inspect
import random
import threading
import time
import traceback
import uuid
from queue import Empty, PriorityQueue
from typing import Callable, Dict, List, Optional, Tuple, Union, Any

from fastapi.concurrency import run_in_threadpool

from .log import logger
from .singleton import Singleton

DEFAULT_EVENT_PRIORITY = 10  # 事件的默认优先级
MIN_EVENT_CONSUMER_THREADS = 1  # 最小事件消费者线程数
INITIAL_EVENT_QUEUE_IDLE_TIMEOUT_SECONDS = 1  # 事件队列空闲时的初始超时时间（秒）
MAX_EVENT_QUEUE_IDLE_TIMEOUT_SECONDS = 5  # 事件队列空闲时的最大超时时间（秒）


class EventType:
    """事件类型枚举（对标MoviePilot）"""
    # 系统事件
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIG_CHANGED = "config.changed"
    
    # 媒体事件
    MEDIA_ADDED = "media.added"
    MEDIA_UPDATED = "media.updated"
    MEDIA_DELETED = "media.deleted"
    MEDIA_SCAN_STARTED = "media.scan.started"
    MEDIA_SCAN_COMPLETED = "media.scan.completed"
    
    # 下载事件
    DOWNLOAD_STARTED = "download.started"
    DOWNLOAD_COMPLETED = "download.completed"
    DOWNLOAD_FAILED = "download.failed"
    
    # 订阅事件
    SUBSCRIPTION_ADDED = "subscription.added"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_DELETED = "subscription.deleted"
    
    # 插件事件
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    PLUGIN_ERROR = "plugin.error"
    
    # 工作流事件
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_ERROR = "workflow.error"


class Event:
    """事件类，封装事件的基本信息"""

    def __init__(self, event_type: Union[EventType, str],
                 event_data: Optional[Dict] = None,
                 priority: Optional[int] = DEFAULT_EVENT_PRIORITY):
        """
        :param event_type: 事件的类型
        :param event_data: 可选，事件携带的数据，默认为空字典
        :param priority: 可选，事件的优先级，默认为 10
        """
        self.event_id = str(uuid.uuid4())  # 事件ID
        self.event_type = event_type  # 事件类型
        self.event_data = event_data or {}  # 事件数据
        self.priority = priority  # 事件优先级
        self.timestamp = time.time()  # 事件时间戳

    def __repr__(self) -> str:
        """
        重写 __repr__ 方法，用于返回事件的详细信息
        """
        return f"<Event: {self.event_type}, ID: {self.event_id}, Priority: {self.priority}>"


class EventManager(metaclass=Singleton):
    """事件管理器（单例模式）"""

    def __init__(self):
        self._event_queue = PriorityQueue()  # 事件优先级队列
        self._event_handlers: Dict[str, List[Callable]] = {}  # 事件处理器字典
        self._consumer_threads: List[threading.Thread] = []  # 消费者线程列表
        self._running = False  # 运行状态
        self._consumer_count = MIN_EVENT_CONSUMER_THREADS  # 消费者线程数量

    def register_handler(self, event_type: Union[EventType, str], handler: Callable):
        """注册事件处理器"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        
        if handler not in self._event_handlers[event_type]:
            self._event_handlers[event_type].append(handler)
            logger.info(f"注册事件处理器: {event_type} -> {handler.__name__}")

    def unregister_handler(self, event_type: Union[EventType, str], handler: Callable):
        """注销事件处理器"""
        if event_type in self._event_handlers:
            if handler in self._event_handlers[event_type]:
                self._event_handlers[event_type].remove(handler)
                logger.info(f"注销事件处理器: {event_type} -> {handler.__name__}")

    def send_event(self, event: Event):
        """发送事件（同步）"""
        if not self._running:
            logger.warning("事件管理器未启动，事件将被忽略")
            return
        
        # 将事件放入优先级队列
        self._event_queue.put((event.priority, event))
        logger.debug(f"发送事件: {event}")

    async def send_event_async(self, event: Event):
        """异步发送事件"""
        if not self._running:
            logger.warning("事件管理器未启动，事件将被忽略")
            return
        
        # 在后台线程中处理事件
        await run_in_threadpool(self.send_event, event)

    def _process_event(self, event: Event):
        """处理单个事件"""
        try:
            # 查找对应的事件处理器
            handlers = self._event_handlers.get(event.event_type, [])
            
            if not handlers:
                logger.debug(f"没有找到事件 {event.event_type} 的处理器")
                return
            
            # 执行所有处理器
            for handler in handlers:
                try:
                    # 检查处理器是否需要异步执行
                    if inspect.iscoroutinefunction(handler):
                        # 异步处理器，在事件循环中执行
                        asyncio.create_task(handler(event))
                    else:
                        # 同步处理器，直接调用
                        handler(event)
                except Exception as e:
                    logger.error(f"事件处理器执行失败: {handler.__name__}, 错误: {e}")
                    
        except Exception as e:
            logger.error(f"处理事件失败: {event}, 错误: {e}")

    def _event_consumer(self):
        """事件消费者线程"""
        idle_timeout = INITIAL_EVENT_QUEUE_IDLE_TIMEOUT_SECONDS
        
        while self._running:
            try:
                # 从队列中获取事件，支持超时
                _, event = self._event_queue.get(timeout=idle_timeout)
                
                # 重置空闲超时时间
                idle_timeout = INITIAL_EVENT_QUEUE_IDLE_TIMEOUT_SECONDS
                
                # 处理事件
                self._process_event(event)
                
                # 标记任务完成
                self._event_queue.task_done()
                
            except Empty:
                # 队列为空，增加空闲超时时间
                idle_timeout = min(idle_timeout * 2, MAX_EVENT_QUEUE_IDLE_TIMEOUT_SECONDS)
                
            except Exception as e:
                logger.error(f"事件消费者线程异常: {e}")
                time.sleep(1)  # 避免频繁错误

    def start(self):
        """启动事件管理器"""
        if self._running:
            logger.warning("事件管理器已经在运行")
            return
        
        self._running = True
        
        # 创建消费者线程
        for i in range(self._consumer_count):
            thread = threading.Thread(
                target=self._event_consumer,
                name=f"EventConsumer-{i}",
                daemon=True
            )
            thread.start()
            self._consumer_threads.append(thread)
        
        logger.info(f"事件管理器已启动，消费者线程数: {self._consumer_count}")

    def stop(self):
        """停止事件管理器"""
        if not self._running:
            return
        
        self._running = False
        
        # 等待队列中的事件处理完成
        self._event_queue.join()
        
        # 等待消费者线程结束
        for thread in self._consumer_threads:
            thread.join(timeout=5)
        
        self._consumer_threads.clear()
        logger.info("事件管理器已停止")

    def set_consumer_count(self, count: int):
        """设置消费者线程数量"""
        if count < MIN_EVENT_CONSUMER_THREADS:
            count = MIN_EVENT_CONSUMER_THREADS
        
        self._consumer_count = count
        
        # 如果正在运行，需要重启以应用新的线程数
        if self._running:
            self.stop()
            self.start()


# 全局事件管理器实例
event_manager = EventManager()


def event_handler(event_type: Union[EventType, str]):
    """事件处理器装饰器"""
    def decorator(func):
        event_manager.register_handler(event_type, func)
        return func
    return decorator


# 常用事件发送函数
def send_system_startup():
    """发送系统启动事件"""
    event = Event(EventType.SYSTEM_STARTUP, {"timestamp": time.time()})
    event_manager.send_event(event)


def send_media_added(media_info: Dict):
    """发送媒体添加事件"""
    event = Event(EventType.MEDIA_ADDED, {"media": media_info})
    event_manager.send_event(event)


def send_download_completed(download_info: Dict):
    """发送下载完成事件"""
    event = Event(EventType.DOWNLOAD_COMPLETED, {"download": download_info})
    event_manager.send_event(event)


def send_plugin_loaded(plugin_info: Dict):
    """发送插件加载事件"""
    event = Event(EventType.PLUGIN_LOADED, {"plugin": plugin_info})
    event_manager.send_event(event)


# 测试事件处理器
@event_handler(EventType.SYSTEM_STARTUP)
def handle_system_startup(event: Event):
    """处理系统启动事件"""
    logger.info("系统启动事件处理完成")


@event_handler(EventType.MEDIA_ADDED)
def handle_media_added(event: Event):
    """处理媒体添加事件"""
    media_info = event.event_data.get("media", {})
    logger.info(f"处理新添加的媒体: {media_info.get('title', 'Unknown')}")


# 全局事件管理器实例
event_manager = EventManager()