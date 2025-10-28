#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐订阅API路由
提供音乐订阅的创建、管理和监控功能
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import asyncio

from core.music_subscription import (
    MusicSubscriptionManager, MusicSubscriptionType, MusicSource,
    music_subscription_manager
)

router = APIRouter(prefix="/music/subscription", tags=["music-subscription"])


class MusicSubscriptionCreate(BaseModel):
    """音乐订阅创建请求"""
    name: str = Field(..., description="订阅名称")
    subscription_type: str = Field(..., description="订阅类型: artist/album/genre/playlist/label")
    target: str = Field(..., description="订阅目标（艺术家名、专辑名、流派等）")
    sources: List[str] = Field(..., description="数据源列表: spotify/apple_music/netease/qq_music")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤器配置")
    check_interval: int = Field(3600, description="检查间隔（秒）")


class MusicSubscriptionResponse(BaseModel):
    """音乐订阅响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class MusicSubscriptionListResponse(BaseModel):
    """音乐订阅列表响应"""
    success: bool
    message: str
    data: Dict[str, Any]


@router.on_event("startup")
async def startup_event():
    """应用启动时启动音乐订阅监控"""
    await music_subscription_manager.start_monitoring()


@router.on_event("shutdown")
async def shutdown_event():
    """应用关闭时停止音乐订阅监控"""
    await music_subscription_manager.stop_monitoring()


@router.post("/", response_model=MusicSubscriptionResponse)
async def create_music_subscription(subscription_data: MusicSubscriptionCreate):
    """创建音乐订阅"""
    try:
        # 验证订阅类型
        try:
            subscription_type = MusicSubscriptionType(subscription_data.subscription_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"不支持的订阅类型: {subscription_data.subscription_type}")
        
        # 验证数据源
        sources = []
        for source_str in subscription_data.sources:
            try:
                source = MusicSource(source_str)
                sources.append(source)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"不支持的数据源: {source_str}")
        
        # 创建订阅
        subscription = await music_subscription_manager.create_subscription(
            name=subscription_data.name,
            subscription_type=subscription_type,
            target=subscription_data.target,
            sources=sources,
            filters=subscription_data.filters
        )
        
        return MusicSubscriptionResponse(
            success=True,
            message="音乐订阅创建成功",
            data=subscription.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建音乐订阅失败: {str(e)}")


@router.post("/artist", response_model=MusicSubscriptionResponse)
async def subscribe_to_artist(
    artist_name: str = Field(..., description="艺术家名称"),
    sources: List[str] = Field(..., description="数据源列表"),
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤器配置")
):
    """订阅艺术家新发布"""
    try:
        # 验证数据源
        music_sources = []
        for source_str in sources:
            try:
                source = MusicSource(source_str)
                music_sources.append(source)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"不支持的数据源: {source_str}")
        
        subscription = await music_subscription_manager.subscribe_to_artist(
            artist_name=artist_name,
            sources=music_sources,
            filters=filters
        )
        
        return MusicSubscriptionResponse(
            success=True,
            message=f"艺术家订阅创建成功: {artist_name}",
            data=subscription.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建艺术家订阅失败: {str(e)}")


@router.post("/album", response_model=MusicSubscriptionResponse)
async def subscribe_to_album(
    album_name: str = Field(..., description="专辑名称"),
    artist_name: str = Field(..., description="艺术家名称"),
    sources: List[str] = Field(..., description="数据源列表"),
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤器配置")
):
    """订阅专辑发布"""
    try:
        # 验证数据源
        music_sources = []
        for source_str in sources:
            try:
                source = MusicSource(source_str)
                music_sources.append(source)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"不支持的数据源: {source_str}")
        
        subscription = await music_subscription_manager.subscribe_to_album(
            album_name=album_name,
            artist_name=artist_name,
            sources=music_sources,
            filters=filters
        )
        
        return MusicSubscriptionResponse(
            success=True,
            message=f"专辑订阅创建成功: {album_name} - {artist_name}",
            data=subscription.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建专辑订阅失败: {str(e)}")


@router.post("/genre", response_model=MusicSubscriptionResponse)
async def subscribe_to_genre(
    genre: str = Field(..., description="音乐流派"),
    sources: List[str] = Field(..., description="数据源列表"),
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤器配置")
):
    """订阅流派新发布"""
    try:
        # 验证数据源
        music_sources = []
        for source_str in sources:
            try:
                source = MusicSource(source_str)
                music_sources.append(source)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"不支持的数据源: {source_str}")
        
        subscription = await music_subscription_manager.subscribe_to_genre(
            genre=genre,
            sources=music_sources,
            filters=filters
        )
        
        return MusicSubscriptionResponse(
            success=True,
            message=f"流派订阅创建成功: {genre}",
            data=subscription.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建流派订阅失败: {str(e)}")


@router.get("/", response_model=MusicSubscriptionListResponse)
async def list_music_subscriptions():
    """获取所有音乐订阅列表"""
    try:
        subscriptions = music_subscription_manager.list_subscriptions()
        statistics = music_subscription_manager.get_statistics()
        
        return MusicSubscriptionListResponse(
            success=True,
            message="音乐订阅列表获取成功",
            data={
                "subscriptions": subscriptions,
                "statistics": statistics
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取音乐订阅列表失败: {str(e)}")


@router.get("/{subscription_id}", response_model=MusicSubscriptionResponse)
async def get_music_subscription(subscription_id: str):
    """获取特定音乐订阅信息"""
    try:
        subscription_data = music_subscription_manager.get_subscription(subscription_id)
        
        if not subscription_data:
            raise HTTPException(status_code=404, detail="音乐订阅不存在")
        
        return MusicSubscriptionResponse(
            success=True,
            message="音乐订阅信息获取成功",
            data=subscription_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取音乐订阅信息失败: {str(e)}")


@router.delete("/{subscription_id}", response_model=MusicSubscriptionResponse)
async def delete_music_subscription(subscription_id: str):
    """删除音乐订阅"""
    try:
        success = await music_subscription_manager.delete_subscription(subscription_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="音乐订阅不存在")
        
        return MusicSubscriptionResponse(
            success=True,
            message="音乐订阅删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除音乐订阅失败: {str(e)}")


@router.post("/{subscription_id}/check", response_model=MusicSubscriptionResponse)
async def check_music_subscription(subscription_id: str):
    """手动检查音乐订阅"""
    try:
        subscription_data = music_subscription_manager.get_subscription(subscription_id)
        
        if not subscription_data:
            raise HTTPException(status_code=404, detail="音乐订阅不存在")
        
        # 这里可以添加手动检查的逻辑
        # 暂时返回成功消息
        
        return MusicSubscriptionResponse(
            success=True,
            message="音乐订阅检查已触发"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查音乐订阅失败: {str(e)}")


@router.get("/statistics", response_model=MusicSubscriptionResponse)
async def get_music_subscription_statistics():
    """获取音乐订阅统计信息"""
    try:
        statistics = music_subscription_manager.get_statistics()
        
        return MusicSubscriptionResponse(
            success=True,
            message="音乐订阅统计信息获取成功",
            data=statistics
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取音乐订阅统计信息失败: {str(e)}")


@router.post("/monitoring/start", response_model=MusicSubscriptionResponse)
async def start_music_subscription_monitoring():
    """启动音乐订阅监控"""
    try:
        await music_subscription_manager.start_monitoring()
        
        return MusicSubscriptionResponse(
            success=True,
            message="音乐订阅监控已启动"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动音乐订阅监控失败: {str(e)}")


@router.post("/monitoring/stop", response_model=MusicSubscriptionResponse)
async def stop_music_subscription_monitoring():
    """停止音乐订阅监控"""
    try:
        await music_subscription_manager.stop_monitoring()
        
        return MusicSubscriptionResponse(
            success=True,
            message="音乐订阅监控已停止"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止音乐订阅监控失败: {str(e)}")