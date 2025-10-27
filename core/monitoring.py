#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控和性能追踪系统
"""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import structlog

logger = structlog.get_logger()


@dataclass
class Metric:
    """指标数据"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics: Dict[str, list] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, list] = defaultdict(list)
    
    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """增加计数器"""
        key = self._get_key(name, tags)
        self.counters[key] += value
        
        metric = Metric(
            name=name,
            value=self.counters[key],
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.metrics[name].append(metric)
    
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """设置仪表值"""
        key = self._get_key(name, tags)
        self.gauges[key] = value
        
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.metrics[name].append(metric)
    
    def timer(self, name: str):
        """计时器装饰器"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self._record_timer(name, duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self._record_timer(name, duration, {"error": str(e)})
                    raise
            return wrapper
        return decorator
    
    def _record_timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """记录计时器结果"""
        key = self._get_key(name, tags)
        self.timers[key].append(duration)
        
        # 只保留最近100个计时记录
        if len(self.timers[key]) > 100:
            self.timers[key] = self.timers[key][-100:]
    
    def _get_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """生成指标键"""
        if not tags:
            return name
        
        tag_str = ":".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}:{tag_str}"
    
    def get_metrics(self, name: str, since: Optional[datetime] = None) -> list:
        """获取指定指标"""
        metrics = self.metrics.get(name, [])
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        return metrics
    
    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """获取计数器值"""
        key = self._get_key(name, tags)
        return self.counters.get(key, 0)
    
    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """获取仪表值"""
        key = self._get_key(name, tags)
        return self.gauges.get(key, 0.0)
    
    def get_timer_stats(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """获取计时器统计信息"""
        key = self._get_key(name, tags)
        values = self.timers.get(key, [])
        
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "p95": sorted(values)[int(len(values) * 0.95)],
            "p99": sorted(values)[int(len(values) * 0.99)]
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.start_time = time.time()
    
    async def monitor_system_resources(self):
        """监控系统资源"""
        import psutil
        
        while True:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics.gauge("system.cpu.usage", cpu_percent)
                
                # 内存使用
                memory = psutil.virtual_memory()
                self.metrics.gauge("system.memory.usage", memory.percent)
                self.metrics.gauge("system.memory.used", memory.used / 1024 / 1024)  # MB
                
                # 磁盘使用
                disk = psutil.disk_usage('/')
                self.metrics.gauge("system.disk.usage", disk.percent)
                
                logger.debug("系统资源监控", cpu=cpu_percent, memory=memory.percent, disk=disk.percent)
                
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error("系统资源监控失败", error=str(e))
                await asyncio.sleep(300)  # 出错时等待5分钟


# 全局指标收集器
metrics_collector = MetricsCollector()


async def setup_monitoring():
    """设置监控系统"""
    try:
        # 启动系统资源监控
        monitor = PerformanceMonitor(metrics_collector)
        asyncio.create_task(monitor.monitor_system_resources())
        
        logger.info("监控系统已启动")
        
    except ImportError:
        logger.warning("psutil未安装，系统资源监控不可用")
    except Exception as e:
        logger.error("监控系统启动失败", error=str(e))


def get_metrics() -> Dict[str, Any]:
    """获取所有指标数据"""
    return {
        "counters": dict(metrics_collector.counters),
        "gauges": dict(metrics_collector.gauges),
        "uptime": time.time() - metrics_collector.start_time
    }