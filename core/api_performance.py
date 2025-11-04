"""
性能监控API路由

提供性能指标查询、性能分析和优化建议功能
"""

import time
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from .performance_monitor import performance_monitor, MetricType
from .cache_manager import cache_manager, CacheLevel


class PerformanceStatsResponse(BaseModel):
    """性能统计响应模型"""

    metric_type: str
    count: int
    min_value: float
    max_value: float
    avg_value: float
    last_value: float


class PerformanceAnalysisResponse(BaseModel):
    """性能分析响应模型"""

    recommendations: List[str]
    warnings: List[str]
    metrics_summary: Dict[str, Dict[str, float]]


class CacheStatsResponse(BaseModel):
    """缓存统计响应模型"""

    level: str
    hits: int
    misses: int
    size: int
    max_size: int
    hit_rate: float


router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/metrics", response_model=Dict[str, PerformanceStatsResponse])
async def get_performance_metrics():
    """获取所有性能指标统计"""
    try:
        all_stats = await performance_monitor.get_all_stats()

        response = {}
        for metric_type, stats in all_stats.items():
            response[metric_type.value] = PerformanceStatsResponse(
                metric_type=metric_type.value,
                count=stats.count,
                min_value=stats.min_value,
                max_value=stats.max_value,
                avg_value=stats.avg_value,
                last_value=stats.last_value,
            )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/analysis", response_model=PerformanceAnalysisResponse)
async def analyze_performance():
    """分析性能并生成优化建议"""
    try:
        analysis = await performance_monitor.analyze_performance()

        return PerformanceAnalysisResponse(**analysis)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze performance: {str(e)}"
        )


@router.get("/cache/stats", response_model=Dict[str, CacheStatsResponse])
async def get_cache_stats():
    """获取缓存统计信息"""
    try:
        cache_stats = await cache_manager.get_stats()

        response = {}
        for level, stats in cache_stats.items():
            response[level.value] = CacheStatsResponse(
                level=level.value,
                hits=stats.hits,
                misses=stats.misses,
                size=stats.size,
                max_size=stats.max_size,
                hit_rate=stats.hit_rate,
            )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache stats: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_cache(level: Optional[str] = Query(None)):
    """清空缓存"""
    try:
        cache_level = None
        if level:
            try:
                cache_level = CacheLevel(level)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid cache level: {level}"
                )

        success = await cache_manager.clear(cache_level)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear cache")

        return {"ok": True, "message": "Cache cleared successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/system/info")
async def get_system_info():
    """获取系统信息"""
    try:
        import psutil

        # CPU信息
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)

        # 内存信息
        memory = psutil.virtual_memory()
        memory_total = memory.total / 1024 / 1024 / 1024  # GB
        memory_used = memory.used / 1024 / 1024 / 1024  # GB
        memory_percent = memory.percent

        # 磁盘信息
        disk = psutil.disk_usage("/")
        disk_total = disk.total / 1024 / 1024 / 1024  # GB
        disk_used = disk.used / 1024 / 1024 / 1024  # GB
        disk_percent = disk.percent

        return {
            "cpu": {"count": cpu_count, "usage_percent": cpu_percent},
            "memory": {
                "total_gb": round(memory_total, 2),
                "used_gb": round(memory_used, 2),
                "usage_percent": memory_percent,
            },
            "disk": {
                "total_gb": round(disk_total, 2),
                "used_gb": round(disk_used, 2),
                "usage_percent": disk_percent,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get system info: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        import psutil

        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent

        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "system": {"cpu_usage": cpu_usage, "memory_usage": memory_usage},
            "services": {"api": "running", "cache": "running", "monitoring": "running"},
        }

        if cpu_usage > 90:
            health_status["warnings"] = ["CPU使用率过高"]
        if memory_usage > 90:
            health_status["warnings"] = health_status.get("warnings", []) + [
                "内存使用率过高"
            ]

        return health_status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
