"""
VabHub 性能监控器

提供性能监控、指标收集、性能分析和优化建议功能
"""

import asyncio
import time
import psutil
import logging
from dataclasses import dataclass
from collections import deque, defaultdict
from typing import Any, Optional, Union, Dict, List, List
from enum import Enum


class MetricType(Enum):
    """性能指标类型"""

    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    RESPONSE_TIME = "response_time"
    REQUEST_COUNT = "request_count"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"


@dataclass
class PerformanceMetric:
    """性能指标数据点"""

    timestamp: float
    metric_type: MetricType
    value: float
    tags: Optional[Dict[str, str]] = None


@dataclass
class PerformanceStats:
    """性能统计信息"""

    metric_type: MetricType
    count: int = 0
    min_value: float = float("inf")
    max_value: float = float("-inf")
    sum_value: float = 0.0
    avg_value: float = 0.0
    last_value: float = 0.0

    def update(self, value: float):
        """更新统计信息"""
        self.count += 1
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
        self.sum_value += value
        self.avg_value = self.sum_value / self.count
        self.last_value = value


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, history_size: int = 1000):
        self.history_size: int = history_size
        self.metrics_history: dict[MetricType, deque[PerformanceMetric]] = defaultdict(
            lambda: deque(maxlen=history_size)
        )
        self.stats: dict[MetricType, PerformanceStats] = {}
        self.logger: logging.Logger = logging.getLogger(__name__)

        # 初始化统计信息
        for metric_type in MetricType:
            self.stats[metric_type] = PerformanceStats(metric_type)

    async def start_monitoring(self, interval: float = 5.0):
        """开始性能监控"""
        while True:
            try:
                await self.collect_system_metrics()
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(interval)

    async def collect_system_metrics(self):
        """收集系统性能指标"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        await self.record_metric(MetricType.CPU_USAGE, cpu_percent)

        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        await self.record_metric(MetricType.MEMORY_USAGE, memory_percent)

        # 磁盘IO
        disk_io = psutil.disk_io_counters()
        if disk_io:
            disk_usage = (disk_io.read_bytes + disk_io.write_bytes) / 1024 / 1024  # MB
            await self.record_metric(MetricType.DISK_IO, disk_usage)

        # 网络IO
        net_io = psutil.net_io_counters()
        if net_io:
            net_usage = (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024  # MB
            await self.record_metric(MetricType.NETWORK_IO, net_usage)

    async def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ):
        """记录性能指标"""
        timestamp = time.time()
        metric = PerformanceMetric(timestamp, metric_type, value, tags)

        # 添加到历史记录
        if metric_type in self.metrics_history:
            self.metrics_history[metric_type].append(metric)

        # 更新统计信息
        if metric_type in self.stats:
            self.stats[metric_type].update(value)

    async def record_response_time(
        self, endpoint: str, response_time: float, status_code: int
    ):
        """记录API响应时间"""
        tags = {"endpoint": endpoint, "status_code": str(status_code)}
        await self.record_metric(MetricType.RESPONSE_TIME, response_time, tags)

        # 记录请求计数
        await self.record_metric(MetricType.REQUEST_COUNT, 1, tags)

        # 记录错误率
        if status_code >= 400:
            await self.record_metric(MetricType.ERROR_RATE, 1, tags)

    async def record_cache_metrics(self, hits: int, misses: int):
        """记录缓存指标"""
        total = hits + misses
        if total > 0:
            hit_rate = hits / total * 100
            await self.record_metric(MetricType.CACHE_HIT_RATE, hit_rate)

    async def get_metrics_history(
        self, metric_type: MetricType, limit: Optional[int] = None
    ) -> List[PerformanceMetric]:
        """获取指标历史记录"""
        if metric_type not in self.metrics_history:
            return []
        history = list(self.metrics_history[metric_type])
        if limit:
            return history[-limit:]
        return history

    async def get_stats(self, metric_type: MetricType) -> PerformanceStats:
        """获取性能统计信息"""
        return self.stats[metric_type]

    async def get_all_stats(self) -> dict[MetricType, PerformanceStats]:
        """获取所有性能统计信息"""
        return self.stats.copy()

    async def analyze_performance(self) -> dict[str, Any]:
        """性能分析"""
        analysis: dict[str, Any] = {
            "recommendations": [],
            "warnings": [],
            "metrics_summary": {},
        }

        # 分析各项指标
        for metric_type, stats in self.stats.items():
            if metric_type in self.stats:
                analysis["metrics_summary"][metric_type.value] = {
                    "min": stats.min_value,
                    "max": stats.max_value,
                    "avg": stats.avg_value,
                    "count": stats.count,
                }

            # 根据指标类型提供建议
            if metric_type == MetricType.CPU_USAGE:
                if stats.avg_value > 80:
                    analysis["warnings"].append(
                        "CPU使用率过高，建议优化代码或增加计算资源"
                    )
                elif stats.avg_value > 60:
                    analysis["recommendations"].append(
                        "CPU使用率较高，建议监控并优化性能"
                    )

            elif metric_type == MetricType.MEMORY_USAGE:
                if stats.avg_value > 85:
                    analysis["warnings"].append("内存使用率过高，可能导致系统不稳定")
                elif stats.avg_value > 70:
                    analysis["recommendations"].append(
                        "内存使用率较高，建议优化内存使用"
                    )

            elif metric_type == MetricType.CACHE_HIT_RATE:
                if stats.avg_value < 70:
                    analysis["recommendations"].append(
                        "缓存命中率较低，建议优化缓存策略"
                    )

            elif metric_type == MetricType.RESPONSE_TIME:
                if stats.avg_value > 1000:  # 1秒
                    analysis["warnings"].append("API响应时间过长，建议优化接口性能")
                elif stats.avg_value > 500:  # 0.5秒
                    analysis["recommendations"].append("API响应时间较长，建议监控性能")

        return analysis


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()
