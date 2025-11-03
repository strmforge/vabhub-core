"""
性能监控初始化脚本

在应用启动时初始化缓存系统和性能监控
"""

import asyncio
import logging
from pathlib import Path

from .cache_manager import cache_manager, CacheLevel, MemoryCacheBackend, DiskCacheBackend
from .performance_monitor import performance_monitor
from .websocket_manager import websocket_manager


logger = logging.getLogger(__name__)


async def initialize_performance_system():
    """初始化性能监控和缓存系统"""
    try:
        # 初始化缓存后端
        memory_cache = MemoryCacheBackend(max_size=1000)
        disk_cache = DiskCacheBackend(cache_dir=Path(".cache"))
        
        cache_manager.add_backend(CacheLevel.MEMORY, memory_cache)
        cache_manager.add_backend(CacheLevel.DISK, disk_cache)
        
        logger.info("缓存系统初始化完成")
        
        # 启动性能监控
        asyncio.create_task(performance_monitor.start_monitoring())
        
        # 启动系统状态广播任务
        asyncio.create_task(broadcast_system_status())
        
        logger.info("性能监控系统启动完成")
        
        return True
    
    except Exception as e:
        logger.error(f"性能系统初始化失败: {e}")
        return False


async def broadcast_system_status():
    """定期广播系统状态"""
    while True:
        try:
            # 获取系统性能统计
            stats = await performance_monitor.get_all_stats()
            
            # 获取连接统计
            connection_stats = websocket_manager.get_connection_stats()
            
            # 构建系统状态
            system_status = {
                'performance': {
                    metric_type.value: {
                        'min': stats[metric_type].min_value,
                        'max': stats[metric_type].max_value,
                        'avg': stats[metric_type].avg_value,
                        'count': stats[metric_type].count,
                        'last': stats[metric_type].last_value
                    }
                    for metric_type in stats
                },
                'connections': connection_stats,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            # 广播系统状态
            await websocket_manager.broadcast_system_status(system_status)
            
            # 每10秒广播一次
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"广播系统状态失败: {e}")
            await asyncio.sleep(10)  # 出错后继续尝试


async def log_performance_metrics():
    """记录性能指标到日志系统"""
    while True:
        try:
            # 获取性能分析
            analysis = await performance_monitor.analyze_performance()
            
            # 记录警告和建议
            for warning in analysis['warnings']:
                await websocket_manager.broadcast_log('warning', 'performance_monitor', warning)
            
            for recommendation in analysis['recommendations']:
                await websocket_manager.broadcast_log('info', 'performance_monitor', recommendation)
            
            # 每30秒记录一次
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")
            await asyncio.sleep(30)


# 在应用启动时调用
async def start_performance_system():
    """启动性能系统"""
    await initialize_performance_system()