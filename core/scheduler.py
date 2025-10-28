#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 任务调度系统
参照MoviePilot的调度器设计，提供强大的定时任务管理功能
"""

import asyncio
import gc
import inspect
import multiprocessing
import threading
import traceback
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Callable, Any

import pytz
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import VabHubConfig
from .event import EventType, Event, event_manager, event_handler
from .log import logger
from .singleton import Singleton


class SchedulerJob:
    """调度任务定义"""
    
    def __init__(self, 
                 job_id: str,
                 name: str,
                 func: Callable,
                 trigger: str = "interval",
                 minutes: int = 60,
                 cron: str = None,
                 enabled: bool = True):
        self.job_id = job_id
        self.name = name
        self.func = func
        self.trigger = trigger
        self.minutes = minutes
        self.cron = cron
        self.enabled = enabled
        self.last_run = None
        self.next_run = None
        self.error_count = 0


class Scheduler(metaclass=Singleton):
    """
    定时任务管理器（单例模式）
    对标MoviePilot的Scheduler类
    """

    def __init__(self):
        # 定时服务
        self._scheduler = None
        # 退出事件
        self._event = threading.Event()
        # 锁
        self._lock = threading.RLock()
        # 各服务的运行状态
        self._jobs: Dict[str, SchedulerJob] = {}
        # 当前事件循环
        self.loop = asyncio.get_event_loop()
        
        # 初始化默认任务
        self._init_default_jobs()

    def _init_default_jobs(self):
        """初始化默认任务（对标MoviePilot）"""
        self._jobs = {
            "media_scan": {
                "name": "媒体库扫描",
                "func": self._scan_media_library,
                "trigger": "interval",
                "minutes": 60,
                "enabled": True
            },
            "download_cleanup": {
                "name": "下载清理",
                "func": self._cleanup_downloads,
                "trigger": "interval", 
                "minutes": 30,
                "enabled": True
            },
            "plugin_update": {
                "name": "插件更新检查",
                "func": self._check_plugin_updates,
                "trigger": "cron",
                "cron": "0 2 * * *",  # 每天凌晨2点
                "enabled": True
            },
            "data_backup": {
                "name": "数据备份",
                "func": self._backup_data,
                "trigger": "cron",
                "cron": "0 3 * * 0",  # 每周日凌晨3点
                "enabled": True
            },
            "system_health": {
                "name": "系统健康检查",
                "func": self._check_system_health,
                "trigger": "interval",
                "minutes": 10,
                "enabled": True
            }
        }

    @event_handler(EventType.CONFIG_CHANGED)
    def handle_config_changed(self, event: Event):
        """
        处理配置变更事件
        :param event: 事件对象
        """
        if not event:
            return
        
        event_data = event.event_data
        config_key = event_data.get("key", "")
        
        # 需要重新初始化的配置项
        restart_keys = [
            'media_scan_interval',
            'download_cleanup_interval', 
            'plugin_update_interval',
            'data_backup_interval',
            'system_health_interval'
        ]
        
        if config_key in restart_keys:
            logger.info(f"配置项 {config_key} 变更，重新初始化定时服务...")
            self.init()

    def init(self):
        """
        初始化定时服务
        """
        # 停止定时服务
        self.stop()

        # 调试模式不启动定时服务
        config = VabHubConfig()
        if config.debug:
            logger.info("调试模式，不启动定时服务")
            return

        with self._lock:
            # 创建调度器
            self._scheduler = BackgroundScheduler(
                executors={
                    'default': ThreadPoolExecutor(20)
                },
                job_defaults={
                    'coalesce': True,
                    'max_instances': 3,
                    'misfire_grace_time': 60
                }
            )

            # 添加任务
            for job_id, job_config in self._jobs.items():
                if not job_config.get("enabled", True):
                    continue
                    
                try:
                    if job_config["trigger"] == "interval":
                        self._scheduler.add_job(
                            func=job_config["func"],
                            trigger="interval",
                            minutes=job_config["minutes"],
                            id=job_id,
                            name=job_config["name"],
                            replace_existing=True
                        )
                    elif job_config["trigger"] == "cron":
                        self._scheduler.add_job(
                            func=job_config["func"],
                            trigger=CronTrigger.from_crontab(job_config["cron"]),
                            id=job_id,
                            name=job_config["name"],
                            replace_existing=True
                        )
                    
                    logger.info(f"添加定时任务: {job_config['name']}")
                    
                except Exception as e:
                    logger.error(f"添加定时任务失败 {job_config['name']}: {e}")

            # 启动调度器
            self._scheduler.start()
            logger.info("定时服务启动完成")

    def start(self):
        """启动调度器"""
        self.init()

    def stop(self):
        """停止调度器"""
        if self._scheduler:
            self._scheduler.shutdown()
            self._scheduler = None
            logger.info("定时服务已停止")

    def pause(self):
        """暂停调度器"""
        if self._scheduler:
            self._scheduler.pause()
            logger.info("定时服务已暂停")

    def resume(self):
        """恢复调度器"""
        if self._scheduler:
            self._scheduler.resume()
            logger.info("定时服务已恢复")

    def add_job(self, job_id: str, name: str, func: Callable, 
                trigger: str = "interval", minutes: int = 60, 
                cron: str = None, enabled: bool = True):
        """
        添加定时任务
        """
        with self._lock:
            job = SchedulerJob(job_id, name, func, trigger, minutes, cron, enabled)
            self._jobs[job_id] = job
            
            if self._scheduler and enabled:
                try:
                    if trigger == "interval":
                        self._scheduler.add_job(
                            func=func,
                            trigger="interval",
                            minutes=minutes,
                            id=job_id,
                            name=name,
                            replace_existing=True
                        )
                    elif trigger == "cron":
                        self._scheduler.add_job(
                            func=func,
                            trigger=CronTrigger.from_crontab(cron),
                            id=job_id,
                            name=name,
                            replace_existing=True
                        )
                    
                    logger.info(f"动态添加定时任务: {name}")
                    
                except Exception as e:
                    logger.error(f"动态添加定时任务失败 {name}: {e}")

    def remove_job(self, job_id: str):
        """移除定时任务"""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                
                if self._scheduler:
                    try:
                        self._scheduler.remove_job(job_id)
                        logger.info(f"移除定时任务: {job_id}")
                    except JobLookupError:
                        pass

    def get_jobs(self) -> List[Dict]:
        """获取所有任务信息"""
        jobs = []
        for job_id, job_config in self._jobs.items():
            job_info = {
                "id": job_id,
                "name": job_config["name"],
                "trigger": job_config["trigger"],
                "enabled": job_config.get("enabled", True)
            }
            
            if job_config["trigger"] == "interval":
                job_info["interval"] = f"{job_config['minutes']}分钟"
            elif job_config["trigger"] == "cron":
                job_info["cron"] = job_config["cron"]
                
            jobs.append(job_info)
            
        return jobs

    # 默认任务实现
    def _scan_media_library(self):
        """媒体库扫描任务"""
        try:
            logger.info("开始执行媒体库扫描任务")
            # 发送扫描开始事件
            event_manager.send_event(Event(EventType.MEDIA_SCAN_STARTED))
            
            # 这里实现媒体扫描逻辑
            # TODO: 实现具体的媒体扫描功能
            
            # 发送扫描完成事件
            event_manager.send_event(Event(EventType.MEDIA_SCAN_COMPLETED))
            logger.info("媒体库扫描任务完成")
            
        except Exception as e:
            logger.error(f"媒体库扫描任务失败: {e}")
            event_manager.send_event(Event(EventType.MEDIA_SCAN_ERROR, {"error": str(e)}))

    def _cleanup_downloads(self):
        """下载清理任务"""
        try:
            logger.info("开始执行下载清理任务")
            # TODO: 实现下载清理逻辑
            logger.info("下载清理任务完成")
            
        except Exception as e:
            logger.error(f"下载清理任务失败: {e}")

    def _check_plugin_updates(self):
        """插件更新检查任务"""
        try:
            logger.info("开始执行插件更新检查任务")
            # TODO: 实现插件更新检查逻辑
            logger.info("插件更新检查任务完成")
            
        except Exception as e:
            logger.error(f"插件更新检查任务失败: {e}")

    def _backup_data(self):
        """数据备份任务"""
        try:
            logger.info("开始执行数据备份任务")
            # TODO: 实现数据备份逻辑
            logger.info("数据备份任务完成")
            
        except Exception as e:
            logger.error(f"数据备份任务失败: {e}")

    def _check_system_health(self):
        """系统健康检查任务"""
        try:
            logger.info("开始执行系统健康检查任务")
            # TODO: 实现系统健康检查逻辑
            logger.info("系统健康检查任务完成")
            
        except Exception as e:
            logger.error(f"系统健康检查任务失败: {e}")


# 全局调度器实例
scheduler = Scheduler()


def init_scheduler():
    """初始化调度器"""
    scheduler.init()


def start_scheduler():
    """启动调度器"""
    scheduler.start()


def stop_scheduler():
    """停止调度器"""
    scheduler.stop()


if __name__ == "__main__":
    # 测试调度器
    start_scheduler()
    
    try:
        # 运行一段时间
        import time
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        stop_scheduler()