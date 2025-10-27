"""
订阅管理API路由
集成MoviePilot的精华订阅功能
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

from core.subscription_manager import SubscriptionManager

router = APIRouter(prefix="/subscription", tags=["subscription"])

# 全局订阅管理器实例
subscription_manager = SubscriptionManager()


class RSSFeedCreate(BaseModel):
    """RSS订阅源创建模型"""
    name: str = Field(..., description="订阅源名称")
    url: str = Field(..., description="RSS订阅URL")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤器配置")


class DownloaderCreate(BaseModel):
    """下载器配置模型"""
    name: str = Field(..., description="下载器名称")
    type: str = Field(..., description="下载器类型: qbittorrent, aria2")
    host: str = Field(..., description="下载器主机地址")
    port: int = Field(..., description="下载器端口")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    download_path: Optional[str] = Field(None, description="下载路径")


class SubscriptionResponse(BaseModel):
    """订阅响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@router.on_event("startup")
async def startup_event():
    """应用启动时初始化订阅管理器"""
    await subscription_manager.initialize()


@router.get("/status", response_model=SubscriptionResponse)
async def get_subscription_status():
    """获取订阅系统状态"""
    try:
        status = subscription_manager.get_status()
        return SubscriptionResponse(
            success=True,
            message="订阅系统状态获取成功",
            data=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/feeds", response_model=SubscriptionResponse)
async def create_feed(feed_data: RSSFeedCreate):
    """创建RSS订阅源"""
    try:
        success = subscription_manager.add_feed(
            name=feed_data.name,
            url=feed_data.url,
            filters=feed_data.filters or {}
        )
        
        if success:
            return SubscriptionResponse(
                success=True,
                message=f"订阅源 {feed_data.name} 创建成功",
                data={"feed_name": feed_data.name}
            )
        else:
            return SubscriptionResponse(
                success=False,
                message=f"订阅源 {feed_data.name} 已存在",
                data={"feed_name": feed_data.name}
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订阅源失败: {str(e)}")


@router.get("/feeds", response_model=SubscriptionResponse)
async def list_feeds():
    """获取所有订阅源列表"""
    try:
        feeds = subscription_manager.list_feeds()
        return SubscriptionResponse(
            success=True,
            message="订阅源列表获取成功",
            data={"feeds": feeds}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订阅源列表失败: {str(e)}")


@router.delete("/feeds/{feed_name}", response_model=SubscriptionResponse)
async def delete_feed(feed_name: str):
    """删除订阅源"""
    try:
        success = subscription_manager.remove_feed(feed_name)
        if success:
            return SubscriptionResponse(
                success=True,
                message=f"订阅源 {feed_name} 删除成功"
            )
        else:
            return SubscriptionResponse(
                success=False,
                message=f"订阅源 {feed_name} 不存在"
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除订阅源失败: {str(e)}")


@router.post("/downloaders", response_model=SubscriptionResponse)
async def create_downloader(downloader_data: DownloaderCreate):
    """添加下载器配置"""
    try:
        config = {
            "host": downloader_data.host,
            "port": downloader_data.port,
            "username": downloader_data.username,
            "password": downloader_data.password,
            "download_path": downloader_data.download_path
        }
        
        success = subscription_manager.add_downloader(
            name=downloader_data.name,
            downloader_type=downloader_data.type,
            config=config
        )
        
        if success:
            return SubscriptionResponse(
                success=True,
                message=f"下载器 {downloader_data.name} 添加成功",
                data={"downloader_name": downloader_data.name}
            )
        else:
            return SubscriptionResponse(
                success=False,
                message=f"下载器 {downloader_data.name} 添加失败",
                data={"downloader_name": downloader_data.name}
            )
    
    except ValueError:
        raise HTTPException(status_code=400, detail="不支持的下载器类型")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加下载器失败: {str(e)}")


@router.get("/downloaders", response_model=SubscriptionResponse)
async def list_downloaders():
    """获取所有下载器列表"""
    try:
        downloaders = subscription_manager.list_downloaders()
        return SubscriptionResponse(
            success=True,
            message="下载器列表获取成功",
            data={"downloaders": downloaders}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取下载器列表失败: {str(e)}")


@router.post("/monitoring/start", response_model=SubscriptionResponse)
async def start_monitoring(background_tasks: BackgroundTasks):
    """启动订阅监控"""
    try:
        background_tasks.add_task(subscription_manager.start_monitoring)
        return SubscriptionResponse(
            success=True,
            message="订阅监控已启动"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动监控失败: {str(e)}")


@router.post("/monitoring/stop", response_model=SubscriptionResponse)
async def stop_monitoring():
    """停止订阅监控"""
    try:
        subscription_manager.stop_monitoring()
        return SubscriptionResponse(
            success=True,
            message="订阅监控已停止"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止监控失败: {str(e)}")


@router.get("/tasks", response_model=SubscriptionResponse)
async def get_tasks():
    """获取当前下载任务列表"""
    try:
        tasks = subscription_manager.get_tasks()
        return SubscriptionResponse(
            success=True,
            message="任务列表获取成功",
            data={"tasks": tasks}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.post("/tasks/{task_id}/pause", response_model=SubscriptionResponse)
async def pause_task(task_id: str):
    """暂停下载任务"""
    try:
        success = subscription_manager.pause_task(task_id)
        if success:
            return SubscriptionResponse(
                success=True,
                message=f"任务 {task_id} 已暂停"
            )
        else:
            return SubscriptionResponse(
                success=False,
                message=f"任务 {task_id} 暂停失败"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停任务失败: {str(e)}")


@router.post("/tasks/{task_id}/resume", response_model=SubscriptionResponse)
async def resume_task(task_id: str):
    """恢复下载任务"""
    try:
        success = subscription_manager.resume_task(task_id)
        if success:
            return SubscriptionResponse(
                success=True,
                message=f"任务 {task_id} 已恢复"
            )
        else:
            return SubscriptionResponse(
                success=False,
                message=f"任务 {task_id} 恢复失败"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复任务失败: {str(e)}")


@router.delete("/tasks/{task_id}", response_model=SubscriptionResponse)
async def delete_task(task_id: str):
    """删除下载任务"""
    try:
        success = subscription_manager.delete_task(task_id)
        if success:
            return SubscriptionResponse(
                success=True,
                message=f"任务 {task_id} 已删除"
            )
        else:
            return SubscriptionResponse(
                success=False,
                message=f"任务 {task_id} 删除失败"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")