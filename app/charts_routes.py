"""
排行榜数据API路由
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import asyncio

router = APIRouter(prefix="/api/charts", tags=["charts"])


@router.get("/data")
async def get_charts_data(
    source: str = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    获取排行榜数据
    
    Args:
        source: 数据源 (apple_music, spotify_charts, netflix_top10, imdb_datasets)
        limit: 返回数量限制
        offset: 偏移量
    """
    try:
        # 获取插件管理器实例
        from core.plugin_manager import plugin_manager
        
        # 查找排行榜收集器插件
        charts_plugin = None
        for plugin in plugin_manager.get_plugins():
            if hasattr(plugin, 'name') and plugin.name == 'charts_collector':
                charts_plugin = plugin
                break
        
        if not charts_plugin:
            raise HTTPException(status_code=404, detail="排行榜插件未找到")
        
        # 获取数据
        data = await charts_plugin.get_latest_data(limit + offset)
        
        # 过滤数据源
        if source:
            data = [item for item in data if item.get('source') == source]
        
        # 分页
        paginated_data = data[offset:offset + limit]
        
        return {
            "success": True,
            "data": paginated_data,
            "total": len(data),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")


@router.get("/sources")
async def get_available_sources() -> Dict[str, Any]:
    """获取可用的数据源列表"""
    sources = [
        {
            "id": "apple_music",
            "name": "Apple Music",
            "description": "Apple Music / iTunes 热门歌曲排行榜",
            "enabled": True
        },
        {
            "id": "spotify_charts", 
            "name": "Spotify Charts",
            "description": "Spotify 全球/地区排行榜",
            "enabled": True
        },
        {
            "id": "netflix_top10",
            "name": "Netflix Top 10", 
            "description": "Netflix 全球热门影视排行榜",
            "enabled": True
        },
        {
            "id": "imdb_datasets",
            "name": "IMDb Datasets",
            "description": "IMDb 高评分电影排行榜",
            "enabled": True
        }
    ]
    
    return {
        "success": True,
        "sources": sources
    }


@router.post("/collect")
async def trigger_collection() -> Dict[str, Any]:
    """手动触发数据收集"""
    try:
        # 获取插件管理器实例
        from core.plugin_manager import plugin_manager
        
        # 查找排行榜收集器插件
        charts_plugin = None
        for plugin in plugin_manager.get_plugins():
            if hasattr(plugin, 'name') and plugin.name == 'charts_collector':
                charts_plugin = plugin
                break
        
        if not charts_plugin:
            raise HTTPException(status_code=404, detail="排行榜插件未找到")
        
        # 触发数据收集
        await charts_plugin.collect_all_data()
        
        return {
            "success": True,
            "message": "数据收集任务已触发"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发收集失败: {str(e)}")


@router.get("/stats")
async def get_collection_stats() -> Dict[str, Any]:
    """获取数据收集统计信息"""
    try:
        # 获取插件管理器实例
        from core.plugin_manager import plugin_manager
        
        # 查找排行榜收集器插件
        charts_plugin = None
        for plugin in plugin_manager.get_plugins():
            if hasattr(plugin, 'name') and plugin.name == 'charts_collector':
                charts_plugin = plugin
                break
        
        if not charts_plugin:
            raise HTTPException(status_code=404, detail="排行榜插件未找到")
        
        # 获取最新数据
        latest_data = await charts_plugin.get_latest_data(1000)
        
        # 统计各数据源数量
        source_stats = {}
        for item in latest_data:
            source = item.get('source', 'unknown')
            source_stats[source] = source_stats.get(source, 0) + 1
        
        return {
            "success": True,
            "stats": {
                "total_records": len(latest_data),
                "sources": source_stats,
                "last_collection": "2025-10-27T10:00:00"  # 这里需要从插件获取实际时间
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")