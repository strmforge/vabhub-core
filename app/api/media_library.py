"""
VabHub 媒体库API接口
基于MoviePilot基准优化的媒体管理API
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import asyncio

from ...core.media_scanner import MediaScanner
from ...core.metadata_scraper import MetadataScraper
from ...core.download_manager import DownloadManager
from ...core.subscription_manager import SubscriptionManager
from ...core.user_manager import UserManager

router = APIRouter(prefix="/api/media", tags=["media"])

# 依赖注入
async def get_media_scanner():
    return MediaScanner()

async def get_metadata_scraper():
    return MetadataScraper()

async def get_download_manager():
    return DownloadManager()

async def get_subscription_manager():
    return SubscriptionManager()

async def get_user_manager():
    return UserManager()

# 请求/响应模型
class MediaItem(BaseModel):
    id: str
    title: str
    type: str  # movie, tv, anime, music
    year: Optional[int]
    path: str
    size: int
    duration: Optional[int]
    quality: Optional[str]
    metadata: Optional[Dict[str, Any]]
    status: str  # available, downloading, processing

class ScanRequest(BaseModel):
    paths: List[str]
    recursive: bool = True
    force_rescan: bool = False

class ScanResponse(BaseModel):
    task_id: str
    status: str
    scanned_count: int
    new_items: int
    updated_items: int

class MetadataRequest(BaseModel):
    item_ids: List[str]
    providers: List[str] = ["tmdb", "douban"]
    force_refresh: bool = False

class DownloadRequest(BaseModel):
    item_id: str
    downloader: str = "qbittorrent"
    category: str = "vabhub"
    save_path: Optional[str]

class SubscriptionRule(BaseModel):
    name: str
    type: str  # movie, tv, music
    keywords: List[str]
    exclude_keywords: List[str]
    quality: Optional[str]
    size_min: Optional[str]
    size_max: Optional[str]
    enabled: bool = True

# API端点
@router.get("/library", response_model=List[MediaItem])
async def get_media_library(
    type: Optional[str] = Query(None, description="媒体类型: movie, tv, anime, music"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    scanner: MediaScanner = Depends(get_media_scanner)
):
    """获取媒体库列表"""
    try:
        items = await scanner.get_media_items(
            media_type=type,
            limit=limit,
            offset=offset
        )
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取媒体库失败: {str(e)}")

@router.post("/scan", response_model=ScanResponse)
async def scan_media_library(
    request: ScanRequest,
    scanner: MediaScanner = Depends(get_media_scanner)
):
    """扫描媒体库"""
    try:
        result = await scanner.scan_paths(
            paths=request.paths,
            recursive=request.recursive,
            force_rescan=request.force_rescan
        )
        return ScanResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"扫描媒体库失败: {str(e)}")

@router.get("/item/{item_id}", response_model=MediaItem)
async def get_media_item(
    item_id: str,
    scanner: MediaScanner = Depends(get_media_scanner)
):
    """获取单个媒体项详情"""
    try:
        item = await scanner.get_media_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="媒体项不存在")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取媒体项失败: {str(e)}")

@router.post("/metadata/refresh")
async def refresh_metadata(
    request: MetadataRequest,
    scraper: MetadataScraper = Depends(get_metadata_scraper),
    scanner: MediaScanner = Depends(get_media_scanner)
):
    """刷新元数据"""
    try:
        # 获取媒体项
        items = []
        for item_id in request.item_ids:
            item = await scanner.get_media_item(item_id)
            if item:
                items.append(item)
        
        if not items:
            raise HTTPException(status_code=404, detail="未找到指定的媒体项")
        
        # 刷新元数据
        results = []
        for item in items:
            metadata = await scraper.scrape_metadata(
                title=item.title,
                media_type=item.type,
                year=item.year,
                providers=request.providers,
                force_refresh=request.force_refresh
            )
            
            # 更新媒体项
            await scanner.update_media_item(item.id, {"metadata": metadata})
            results.append({"item_id": item.id, "metadata": metadata})
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新元数据失败: {str(e)}")

@router.post("/download")
async def download_media(
    request: DownloadRequest,
    download_manager: DownloadManager = Depends(get_download_manager),
    scanner: MediaScanner = Depends(get_media_scanner)
):
    """下载媒体文件"""
    try:
        # 获取媒体项
        item = await scanner.get_media_item(request.item_id)
        if not item:
            raise HTTPException(status_code=404, detail="媒体项不存在")
        
        # 创建下载任务
        task_id = await download_manager.create_download_task(
            item=item,
            downloader=request.downloader,
            category=request.category,
            save_path=request.save_path
        )
        
        return {"task_id": task_id, "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载媒体失败: {str(e)}")

@router.get("/downloads")
async def get_download_tasks(
    status: Optional[str] = Query(None, description="任务状态: active, completed, error"),
    download_manager: DownloadManager = Depends(get_download_manager)
):
    """获取下载任务列表"""
    try:
        tasks = await download_manager.get_download_tasks(status=status)
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取下载任务失败: {str(e)}")

@router.post("/subscription/rules")
async def create_subscription_rule(
    rule: SubscriptionRule,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    """创建订阅规则"""
    try:
        rule_id = await subscription_manager.create_rule(rule.dict())
        return {"rule_id": rule_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订阅规则失败: {str(e)}")

@router.get("/subscription/rules")
async def get_subscription_rules(
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    """获取订阅规则列表"""
    try:
        rules = await subscription_manager.get_rules()
        return {"rules": rules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订阅规则失败: {str(e)}")

@router.post("/subscription/run")
async def run_subscription_check(
    rule_ids: Optional[List[str]] = None,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    """运行订阅检查"""
    try:
        results = await subscription_manager.run_check(rule_ids=rule_ids)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"运行订阅检查失败: {str(e)}")

@router.get("/stats")
async def get_media_stats(
    scanner: MediaScanner = Depends(get_media_scanner)
):
    """获取媒体库统计信息"""
    try:
        stats = await scanner.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

# 健康检查端点
@router.get("/health")
async def health_check():
    """媒体库健康检查"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0"
    }

# 搜索端点
@router.get("/search")
async def search_media(
    query: str,
    media_type: Optional[str] = None,
    year: Optional[int] = None,
    scanner: MediaScanner = Depends(get_media_scanner)
):
    """搜索媒体库"""
    try:
        results = await scanner.search_media(
            query=query,
            media_type=media_type,
            year=year
        )
        return {"results": results, "query": query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索媒体库失败: {str(e)}")