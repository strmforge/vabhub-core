"""
音乐订阅API接口
基于VabHub架构的音乐订阅管理API
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ...core.music_manager import MusicManager
from ...core.config import ConfigManager
from ...core.auth import get_current_user

router = APIRouter(prefix="/api/music", tags=["music"])


# 请求/响应模型
class SubscriptionCreate(BaseModel):
    name: str
    query: str
    mode: str = "torznab"
    endpoint: str
    rules: Dict[str, Any]
    enabled: bool = True
    auto_add: bool = False
    max_add: int = 3


class SubscriptionResponse(BaseModel):
    id: str
    name: str
    query: str
    mode: str
    status: str
    last_run: Optional[str]
    result_count: int
    results: List[Dict[str, Any]]


class ChartSubscriptionRequest(BaseModel):
    data_file: str
    top_artists: int = 50
    sources: List[str] = ["apple_music", "spotify"]


class MetadataEnrichRequest(BaseModel):
    artist: str
    title: str


class MetadataEnrichResponse(BaseModel):
    artist: str
    title: str
    metadata: Dict[str, Any]
    enriched_at: str


# 依赖注入
async def get_music_manager() -> MusicManager:
    """获取音乐管理器实例"""
    config = ConfigManager()
    manager = MusicManager(config)
    await manager.initialize()
    return manager


@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    manager: MusicManager = Depends(get_music_manager),
    current_user: dict = Depends(get_current_user)
):
    """获取所有音乐订阅"""
    try:
        # 这里应该从数据库获取订阅列表
        # 简化实现，返回示例数据
        subscriptions = [
            {
                "id": "1",
                "name": "Taylor Swift FLAC",
                "query": "Taylor Swift",
                "mode": "torznab",
                "status": "running",
                "last_run": "2024-01-01T10:00:00",
                "result_count": 5,
                "results": []
            }
        ]
        return subscriptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订阅失败: {str(e)}")


@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    subscription: SubscriptionCreate,
    manager: MusicManager = Depends(get_music_manager),
    current_user: dict = Depends(get_current_user)
):
    """创建新的音乐订阅"""
    try:
        # 实现订阅创建逻辑
        # 这里应该保存到数据库
        
        response = SubscriptionResponse(
            id="new_subscription_id",
            name=subscription.name,
            query=subscription.query,
            mode=subscription.mode,
            status="created",
            last_run=None,
            result_count=0,
            results=[]
        )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订阅失败: {str(e)}")


@router.put("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    subscription: SubscriptionCreate,
    manager: MusicManager = Depends(get_music_manager),
    current_user: dict = Depends(get_current_user)
):
    """更新音乐订阅"""
    try:
        # 实现订阅更新逻辑
        
        response = SubscriptionResponse(
            id=subscription_id,
            name=subscription.name,
            query=subscription.query,
            mode=subscription.mode,
            status="updated",
            last_run=None,
            result_count=0,
            results=[]
        )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新订阅失败: {str(e)}")


@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    manager: MusicManager = Depends(get_music_manager),
    current_user: dict = Depends(get_current_user)
):
    """删除音乐订阅"""
    try:
        # 实现订阅删除逻辑
        return {"message": "订阅删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除订阅失败: {str(e)}")


@router.post("/subscriptions/{subscription_id}/run")
async def run_subscription(
    subscription_id: str,
    manager: MusicManager = Depends(get_music_manager),
    current_user: dict = Depends(get_current_user)
):
    """立即运行音乐订阅"""
    try:
        # 实现立即运行逻辑
        return {"message": "订阅运行成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"运行订阅失败: {str(e)}")


@router.post("/subscriptions/generate-from-charts")
async def generate_subscriptions_from_charts(
    request: ChartSubscriptionRequest,
    manager: MusicManager = Depends(get_music_manager),
    current_user: dict = Depends(get_current_user)
):
    """从榜单生成音乐订阅"""
    try:
        # 加载榜单数据
        chart_data = await _load_chart_data(request.data_file, request.sources)
        
        # 生成订阅
        subscriptions = await manager.generate_chart_subscriptions(
            chart_data, request.top_artists
        )
        
        return {
            "message": "订阅生成成功",
            "generated_count": len(subscriptions),
            "subscriptions": subscriptions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成订阅失败: {str(e)}")


@router.post("/metadata/enrich", response_model=MetadataEnrichResponse)
async def enrich_metadata(
    request: MetadataEnrichRequest,
    manager: MusicManager = Depends(get_music_manager),
    current_user: dict = Depends(get_current_user)
):
    """丰富音乐元数据"""
    try:
        metadata = await manager.enrich_metadata(request.artist, request.title)
        
        response = MetadataEnrichResponse(
            artist=request.artist,
            title=request.title,
            metadata=metadata,
            enriched_at=metadata.get('enriched_at', '')
        )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"元数据丰富失败: {str(e)}")


@router.get("/metadata/{artist}/{title}")
async def get_metadata(
    artist: str,
    title: str,
    manager: MusicManager = Depends(get_music_manager),
    current_user: dict = Depends(get_current_user)
):
    """获取音乐元数据"""
    try:
        # 这里应该从数据库获取缓存的元数据
        # 如果没有缓存，则调用enrich接口
        
        metadata = {
            "artist": artist,
            "title": title,
            "cover_url": "",
            "lyrics": "",
            "musicbrainz_id": ""
        }
        
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取元数据失败: {str(e)}")


@router.get("/status")
async def get_music_status(
    manager: MusicManager = Depends(get_music_manager),
    current_user: dict = Depends(get_current_user)
):
    """获取音乐系统状态"""
    try:
        status = {
            "subscription_count": 0,
            "active_subscriptions": 0,
            "total_results": 0,
            "last_updated": "2024-01-01T10:00:00",
            "metadata_cache_size": 0
        }
        
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


async def _load_chart_data(file_path: str, sources: List[str]) -> List[Dict[str, Any]]:
    """加载榜单数据"""
    # 实现榜单数据加载逻辑
    # 这里应该从文件加载JSONL数据
    
    chart_data = []
    # 示例数据
    if "apple_music" in sources:
        chart_data.extend([
            {"source": "apple_music", "artist_or_show": "Taylor Swift", "title": "Anti-Hero"},
            {"source": "apple_music", "artist_or_show": "Ed Sheeran", "title": "Shape of You"}
        ])
    
    if "spotify" in sources:
        chart_data.extend([
            {"source": "spotify", "artist_or_show": "The Weeknd", "title": "Blinding Lights"},
            {"source": "spotify", "artist_or_show": "Dua Lipa", "title": "Levitating"}
        ])
    
    return chart_data