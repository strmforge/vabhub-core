#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版仪表盘API路由
集成系统监控、下载器监控、媒体服务器集成等专业功能
参考MoviePilot的仪表盘架构设计
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import json

from core.system_monitor import system_monitor
from core.ai_dashboard import ai_dashboard

router = APIRouter(prefix="/api/v2/dashboard", tags=["增强版仪表盘"])

# 模拟数据 - 在实际应用中应该从数据库获取
MOCK_DOWNLOADERS = [
    {
        "id": "qbittorrent",
        "name": "qBittorrent",
        "type": "torrent",
        "status": "connected",
        "download_speed": 2.5,  # MB/s
        "upload_speed": 0.8,    # MB/s
        "active_torrents": 3,
        "total_torrents": 15,
        "free_space": 1024,    # GB
        "last_update": datetime.now().isoformat()
    },
    {
        "id": "aria2",
        "name": "Aria2",
        "type": "http",
        "status": "connected",
        "download_speed": 1.2,  # MB/s
        "upload_speed": 0.0,
        "active_tasks": 2,
        "total_tasks": 8,
        "last_update": datetime.now().isoformat()
    }
]

MOCK_MEDIA_SERVERS = [
    {
        "id": "plex",
        "name": "Plex Media Server",
        "type": "plex",
        "status": "connected",
        "version": "1.32.8",
        "libraries": [
            {"name": "电影", "type": "movie", "count": 856},
            {"name": "电视剧", "type": "tv", "count": 312},
            {"name": "音乐", "type": "music", "count": 0}
        ],
        "active_streams": 2,
        "last_sync": datetime.now().isoformat()
    },
    {
        "id": "jellyfin",
        "name": "Jellyfin",
        "type": "jellyfin",
        "status": "connected",
        "version": "10.9.0",
        "libraries": [
            {"name": "电影", "type": "movie", "count": 423},
            {"name": "电视剧", "type": "tv", "count": 189}
        ],
        "active_streams": 1,
        "last_sync": datetime.now().isoformat()
    }
]

MOCK_SCHEDULED_TASKS = [
    {
        "id": "media_scan",
        "name": "媒体库扫描",
        "description": "扫描媒体库新增文件",
        "status": "enabled",
        "last_run": "2024-01-15T10:00:00",
        "next_run": "2024-01-15T12:00:00",
        "interval": "2小时"
    },
    {
        "id": "subscription_check",
        "name": "订阅检查",
        "description": "检查RSS订阅更新",
        "status": "enabled",
        "last_run": "2024-01-15T09:30:00",
        "next_run": "2024-01-15T10:30:00",
        "interval": "1小时"
    },
    {
        "id": "backup",
        "name": "系统备份",
        "description": "备份系统配置和数据",
        "status": "disabled",
        "last_run": "2024-01-14T02:00:00",
        "next_run": "2024-01-16T02:00:00",
        "interval": "每天"
    }
]

@router.on_event("startup")
async def startup_event():
    """启动时初始化系统监控"""
    system_monitor.start_monitoring()

@router.get("/overview", summary="获取仪表盘概览")
async def get_dashboard_overview():
    """获取仪表盘概览数据"""
    try:
        # 并行获取各种数据
        system_overview = system_monitor.get_system_overview()
        ai_overview = ai_dashboard.get_dashboard_overview()
        
        return {
            "success": True,
            "data": {
                "system": {
                    "cpu_usage": system_overview["cpu"]["total"],
                    "memory_usage": system_overview["memory"]["percent"],
                    "disk_usage": system_overview["disk"]["percent"],
                    "uptime": system_overview["uptime"],
                    "status": "healthy" if system_overview["cpu"]["total"] < 90 else "warning"
                },
                "media": {
                    "total_files": ai_overview.get("total_analyses", 0),
                    "movies": 856,
                    "tv_shows": 312,
                    "music": 0,
                    "last_scan": "2024-01-15T10:00:00"
                },
                "downloads": {
                    "active": 5,
                    "completed_today": 12,
                    "total_speed": 3.7,  # MB/s
                    "status": "active"
                },
                "services": {
                    "media_servers": len([s for s in MOCK_MEDIA_SERVERS if s["status"] == "connected"]),
                    "downloaders": len([d for d in MOCK_DOWNLOADERS if d["status"] == "connected"]),
                    "scheduled_tasks": len([t for t in MOCK_SCHEDULED_TASKS if t["status"] == "enabled"])
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概览失败: {str(e)}")

@router.get("/system/monitor", summary="获取系统监控数据")
async def get_system_monitor(
    metric: str = Query("all", description="监控指标: cpu, memory, disk, network, all"),
    time_range: str = Query("1h", description="时间范围: 1h, 6h, 24h")
):
    """获取系统监控数据"""
    try:
        data = {}
        
        if metric in ["all", "cpu"]:
            data["cpu"] = {
                "current": system_monitor.get_cpu_usage(),
                "history": system_monitor.get_history_data("cpu", time_range)
            }
        
        if metric in ["all", "memory"]:
            data["memory"] = {
                "current": system_monitor.get_memory_usage(),
                "history": system_monitor.get_history_data("memory", time_range)
            }
        
        if metric in ["all", "disk"]:
            data["disk"] = {
                "current": system_monitor.get_disk_usage(),
                "history": system_monitor.get_history_data("disk", time_range)
            }
        
        if metric in ["all", "network"]:
            data["network"] = {
                "current": system_monitor.get_network_usage(),
                "history": system_monitor.get_history_data("network", time_range)
            }
        
        if metric == "all":
            data["trends"] = system_monitor.get_trend_analysis()
            data["processes"] = system_monitor.get_process_info()
        
        return {
            "success": True,
            "data": data,
            "time_range": time_range,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统监控数据失败: {str(e)}")

@router.get("/downloaders", summary="获取下载器状态")
async def get_downloaders_status():
    """获取下载器状态信息"""
    try:
        return {
            "success": True,
            "data": {
                "downloaders": MOCK_DOWNLOADERS,
                "summary": {
                    "total_downloaders": len(MOCK_DOWNLOADERS),
                    "connected_downloaders": len([d for d in MOCK_DOWNLOADERS if d["status"] == "connected"]),
                    "total_speed": sum(d.get("download_speed", 0) for d in MOCK_DOWNLOADERS),
                    "active_tasks": sum(d.get("active_torrents", 0) for d in MOCK_DOWNLOADERS)
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取下载器状态失败: {str(e)}")

@router.get("/media-servers", summary="获取媒体服务器状态")
async def get_media_servers_status():
    """获取媒体服务器状态信息"""
    try:
        return {
            "success": True,
            "data": {
                "servers": MOCK_MEDIA_SERVERS,
                "summary": {
                    "total_servers": len(MOCK_MEDIA_SERVERS),
                    "connected_servers": len([s for s in MOCK_MEDIA_SERVERS if s["status"] == "connected"]),
                    "total_libraries": sum(len(s.get("libraries", [])) for s in MOCK_MEDIA_SERVERS),
                    "total_media": sum(
                        sum(lib.get("count", 0) for lib in s.get("libraries", []))
                        for s in MOCK_MEDIA_SERVERS
                    ),
                    "active_streams": sum(s.get("active_streams", 0) for s in MOCK_MEDIA_SERVERS)
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取媒体服务器状态失败: {str(e)}")

@router.get("/scheduled-tasks", summary="获取定时任务状态")
async def get_scheduled_tasks():
    """获取定时任务状态信息"""
    try:
        enabled_tasks = [t for t in MOCK_SCHEDULED_TASKS if t["status"] == "enabled"]
        
        return {
            "success": True,
            "data": {
                "tasks": MOCK_SCHEDULED_TASKS,
                "summary": {
                    "total_tasks": len(MOCK_SCHEDULED_TASKS),
                    "enabled_tasks": len(enabled_tasks),
                    "disabled_tasks": len(MOCK_SCHEDULED_TASKS) - len(enabled_tasks),
                    "next_run": min(
                        (t["next_run"] for t in enabled_tasks if t.get("next_run")),
                        default=None
                    )
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取定时任务状态失败: {str(e)}")

@router.get("/ai-analytics", summary="获取AI分析数据")
async def get_ai_analytics(
    time_range: str = Query("24h", description="时间范围: 24h, 7d, 30d")
):
    """获取AI分析数据"""
    try:
        overview = ai_dashboard.get_dashboard_overview()
        trends = ai_dashboard.get_trend_analysis(time_range)
        service_comparison = ai_dashboard.get_service_comparison()
        
        return {
            "success": True,
            "data": {
                "overview": overview,
                "trends": trends,
                "service_comparison": service_comparison,
                "performance": ai_dashboard.get_recommendation_performance()
            },
            "time_range": time_range,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取AI分析数据失败: {str(e)}")

@router.get("/alerts", summary="获取系统警报")
async def get_system_alerts():
    """获取系统警报信息"""
    try:
        # 模拟警报数据
        alerts = []
        
        system_overview = system_monitor.get_system_overview()
        
        # CPU警报
        if system_overview["cpu"]["total"] > 80:
            alerts.append({
                "id": "cpu_high",
                "type": "cpu",
                "level": "warning",
                "message": f"CPU使用率过高: {system_overview['cpu']['total']}%",
                "timestamp": datetime.now().isoformat()
            })
        
        # 内存警报
        if system_overview["memory"]["percent"] > 85:
            alerts.append({
                "id": "memory_high",
                "type": "memory",
                "level": "warning",
                "message": f"内存使用率过高: {system_overview['memory']['percent']}%",
                "timestamp": datetime.now().isoformat()
            })
        
        # 磁盘警报
        if system_overview["disk"]["percent"] > 90:
            alerts.append({
                "id": "disk_low",
                "type": "disk",
                "level": "critical",
                "message": f"磁盘空间不足: 仅剩{100 - system_overview['disk']['percent']}%",
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "success": True,
            "data": {
                "alerts": alerts,
                "total_alerts": len(alerts),
                "critical_alerts": len([a for a in alerts if a["level"] == "critical"]),
                "warning_alerts": len([a for a in alerts if a["level"] == "warning"])
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统警报失败: {str(e)}")

@router.get("/health", summary="系统健康检查")
async def get_system_health():
    """获取系统健康状态"""
    try:
        system_overview = system_monitor.get_system_overview()
        ai_health = ai_dashboard.get_health_status()
        
        # 计算整体健康分数
        health_score = 100
        
        # CPU健康度
        cpu_health = max(0, 100 - system_overview["cpu"]["total"])
        health_score = min(health_score, cpu_health)
        
        # 内存健康度
        memory_health = max(0, 100 - system_overview["memory"]["percent"])
        health_score = min(health_score, memory_health)
        
        # 磁盘健康度
        disk_health = max(0, 100 - system_overview["disk"]["percent"])
        health_score = min(health_score, disk_health)
        
        # AI健康度
        ai_health_score = ai_health.get("health_score", 100)
        health_score = min(health_score, ai_health_score)
        
        # 确定健康状态
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "success": True,
            "data": {
                "overall_score": health_score,
                "status": status,
                "components": {
                    "cpu": {
                        "score": cpu_health,
                        "status": "healthy" if cpu_health >= 80 else "degraded" if cpu_health >= 60 else "unhealthy"
                    },
                    "memory": {
                        "score": memory_health,
                        "status": "healthy" if memory_health >= 80 else "degraded" if memory_health >= 60 else "unhealthy"
                    },
                    "disk": {
                        "score": disk_health,
                        "status": "healthy" if disk_health >= 80 else "degraded" if disk_health >= 60 else "unhealthy"
                    },
                    "ai": {
                        "score": ai_health_score,
                        "status": ai_health.get("status", "unknown")
                    }
                },
                "recommendations": ai_health.get("recommendations", [])
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统健康状态失败: {str(e)}")

@router.post("/refresh", summary="手动刷新数据")
async def refresh_dashboard_data(background_tasks: BackgroundTasks):
    """手动刷新仪表盘数据"""
    try:
        # 在后台刷新数据
        background_tasks.add_task(_refresh_data)
        
        return {
            "success": True,
            "message": "数据刷新任务已启动",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新数据失败: {str(e)}")

async def _refresh_data():
    """后台刷新数据"""
    # 这里可以添加数据刷新逻辑
    await asyncio.sleep(1)
    print("仪表盘数据已刷新")

@router.get("/widgets", summary="获取可用的仪表盘组件")
async def get_available_widgets():
    """获取可用的仪表盘组件列表"""
    try:
        widgets = [
            {
                "id": "system_monitor",
                "name": "系统监控",
                "description": "实时监控CPU、内存、磁盘、网络使用情况",
                "type": "chart",
                "default_position": {"x": 0, "y": 0, "w": 6, "h": 4},
                "configurable": True
            },
            {
                "id": "download_status",
                "name": "下载状态",
                "description": "显示当前下载任务和速度",
                "type": "list",
                "default_position": {"x": 6, "y": 0, "w": 6, "h": 3},
                "configurable": True
            },
            {
                "id": "media_library",
                "name": "媒体库概览",
                "description": "显示媒体库统计信息",
                "type": "stats",
                "default_position": {"x": 0, "y": 4, "w": 4, "h": 2},
                "configurable": True
            },
            {
                "id": "ai_analytics",
                "name": "AI分析",
                "description": "显示AI分析结果和趋势",
                "type": "chart",
                "default_position": {"x": 4, "y": 4, "w": 8, "h": 3},
                "configurable": True
            },
            {
                "id": "scheduled_tasks",
                "name": "定时任务",
                "description": "显示定时任务状态",
                "type": "list",
                "default_position": {"x": 0, "y": 6, "w": 6, "h": 3},
                "configurable": True
            },
            {
                "id": "system_alerts",
                "name": "系统警报",
                "description": "显示系统警报信息",
                "type": "alert",
                "default_position": {"x": 6, "y": 3, "w": 6, "h": 3},
                "configurable": True
            }
        ]
        
        return {
            "success": True,
            "data": {
                "widgets": widgets,
                "total_widgets": len(widgets)
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取组件列表失败: {str(e)}")

@router.get("/layout", summary="获取默认布局配置")
async def get_default_layout():
    """获取默认仪表盘布局配置"""
    try:
        layout = {
            "breakpoint": "lg",
            "cols": 12,
            "rowHeight": 100,
            "margin": [10, 10],
            "layouts": {
                "lg": [
                    {"i": "system_monitor", "x": 0, "y": 0, "w": 6, "h": 4},
                    {"i": "download_status", "x": 6, "y": 0, "w": 6, "h": 3},
                    {"i": "media_library", "x": 0, "y": 4, "w": 4, "h": 2},
                    {"i": "ai_analytics", "x": 4, "y": 4, "w": 8, "h": 3},
                    {"i": "scheduled_tasks", "x": 0, "y": 6, "w": 6, "h": 3},
                    {"i": "system_alerts", "x": 6, "y": 3, "w": 6, "h": 3}
                ]
            }
        }
        
        return {
            "success": True,
            "data": layout,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取布局配置失败: {str(e)}")