"""
下载器相关的API接口
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from .download_manager import download_manager
from .download_client import DownloadClientType, TorrentStatus

router = APIRouter(prefix="/api/v1/download", tags=["download"])


class DownloadClientConfigRequest(BaseModel):
    """下载器配置请求"""

    client_id: str
    client_type: DownloadClientType
    host: str
    port: int
    username: str = ""
    password: str = ""
    timeout: int = 30
    set_as_default: bool = False


class TorrentAddRequest(BaseModel):
    """添加种子请求"""

    torrent: str  # 磁力链接或种子URL
    client_id: Optional[str] = None
    save_path: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class TorrentActionRequest(BaseModel):
    """种子操作请求"""

    torrent_hash: str
    client_id: Optional[str] = None


class TorrentRemoveRequest(TorrentActionRequest):
    """删除种子请求"""

    delete_files: bool = False


class TorrentSetCategoryRequest(BaseModel):
    """设置分类请求"""

    torrent_hash: str
    category: str
    client_id: Optional[str] = None


class TorrentSetRatioRequest(BaseModel):
    """设置分享率请求"""

    torrent_hash: str
    ratio: float
    client_id: Optional[str] = None


class TorrentSetSpeedRequest(BaseModel):
    """设置速度请求"""

    torrent_hash: str
    download_limit: int = 0
    upload_limit: int = 0
    client_id: Optional[str] = None


@router.post("/clients")
async def add_download_client(config: DownloadClientConfigRequest):
    """添加下载器客户端"""
    try:
        success = await download_manager.add_client(
            client_id=config.client_id,
            client_type=config.client_type,
            host=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            timeout=config.timeout,
            set_as_default=config.set_as_default,
        )

        if success:
            return {"ok": True, "message": "下载器添加成功"}
        else:
            raise HTTPException(status_code=400, detail="下载器添加失败")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clients/{client_id}")
async def remove_download_client(client_id: str):
    """移除下载器客户端"""
    try:
        success = await download_manager.remove_client(client_id)

        if success:
            return {"ok": True, "message": "下载器移除成功"}
        else:
            raise HTTPException(status_code=404, detail="下载器不存在")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clients/{client_id}/default")
async def set_default_download_client(client_id: str):
    """设置默认下载器"""
    try:
        success = download_manager.set_default_client(client_id)

        if success:
            return {"ok": True, "message": "默认下载器设置成功"}
        else:
            raise HTTPException(status_code=404, detail="下载器不存在")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients")
async def list_download_clients():
    """列出所有下载器客户端"""
    try:
        clients = download_manager.list_clients()
        return {"ok": True, "data": clients}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/torrents")
async def add_torrent(request: TorrentAddRequest):
    """添加种子"""
    try:
        success = await download_manager.add_torrent(
            torrent=request.torrent,
            client_id=request.client_id,
            save_path=request.save_path,
            category=request.category,
            tags=request.tags,
        )

        if success:
            return {"ok": True, "message": "种子添加成功"}
        else:
            raise HTTPException(status_code=400, detail="种子添加失败")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/torrents/{torrent_hash}/pause")
async def pause_torrent(torrent_hash: str, request: TorrentActionRequest):
    """暂停种子"""
    try:
        success = await download_manager.pause_torrent(
            torrent_hash=torrent_hash, client_id=request.client_id
        )

        if success:
            return {"ok": True, "message": "种子暂停成功"}
        else:
            raise HTTPException(status_code=400, detail="种子暂停失败")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/torrents/{torrent_hash}/resume")
async def resume_torrent(torrent_hash: str, request: TorrentActionRequest):
    """恢复种子"""
    try:
        success = await download_manager.resume_torrent(
            torrent_hash=torrent_hash, client_id=request.client_id
        )

        if success:
            return {"ok": True, "message": "种子恢复成功"}
        else:
            raise HTTPException(status_code=400, detail="种子恢复失败")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/torrents/{torrent_hash}")
async def remove_torrent(torrent_hash: str, request: TorrentRemoveRequest):
    """删除种子"""
    try:
        success = await download_manager.remove_torrent(
            torrent_hash=torrent_hash,
            delete_files=request.delete_files,
            client_id=request.client_id,
        )

        if success:
            return {"ok": True, "message": "种子删除成功"}
        else:
            raise HTTPException(status_code=400, detail="种子删除失败")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/torrents")
async def get_torrents(
    client_id: Optional[str] = None,
    status: Optional[TorrentStatus] = None,
    category: Optional[str] = None,
):
    """获取种子列表"""
    try:
        torrents = await download_manager.get_torrents(
            client_id=client_id, status_filter=status, category=category
        )

        # 转换为可序列化的格式
        torrents_data = []
        for torrent in torrents:
            torrents_data.append(
                {
                    "hash": torrent.hash,
                    "name": torrent.name,
                    "size": torrent.size,
                    "progress": torrent.progress,
                    "status": torrent.status.value,
                    "download_speed": torrent.download_speed,
                    "upload_speed": torrent.upload_speed,
                    "ratio": torrent.ratio,
                    "eta": torrent.eta,
                    "save_path": torrent.save_path,
                    "category": torrent.category,
                    "added_on": torrent.added_on,
                }
            )

        return {"ok": True, "data": torrents_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/torrents/{torrent_hash}")
async def get_torrent(torrent_hash: str, client_id: Optional[str] = None):
    """获取单个种子信息"""
    try:
        torrent = await download_manager.get_torrent(torrent_hash, client_id)

        if not torrent:
            raise HTTPException(status_code=404, detail="种子不存在")

        torrent_data = {
            "hash": torrent.hash,
            "name": torrent.name,
            "size": torrent.size,
            "progress": torrent.progress,
            "status": torrent.status.value,
            "download_speed": torrent.download_speed,
            "upload_speed": torrent.upload_speed,
            "ratio": torrent.ratio,
            "eta": torrent.eta,
            "save_path": torrent.save_path,
            "category": torrent.category,
            "added_on": torrent.added_on,
        }

        return {"ok": True, "data": torrent_data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/torrents/{torrent_hash}/category")
async def set_torrent_category(torrent_hash: str, request: TorrentSetCategoryRequest):
    """设置种子分类"""
    try:
        success = await download_manager.set_category(
            torrent_hash=torrent_hash,
            category=request.category,
            client_id=request.client_id,
        )

        if success:
            return {"ok": True, "message": "分类设置成功"}
        else:
            raise HTTPException(status_code=400, detail="分类设置失败")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/torrents/{torrent_hash}/ratio")
async def set_torrent_ratio(torrent_hash: str, request: TorrentSetRatioRequest):
    """设置种子分享率限制"""
    try:
        success = await download_manager.set_ratio_limit(
            torrent_hash=torrent_hash, ratio=request.ratio, client_id=request.client_id
        )

        if success:
            return {"ok": True, "message": "分享率限制设置成功"}
        else:
            raise HTTPException(status_code=400, detail="分享率限制设置失败")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/torrents/{torrent_hash}/speed")
async def set_torrent_speed(torrent_hash: str, request: TorrentSetSpeedRequest):
    """设置种子速度限制"""
    try:
        success = await download_manager.set_speed_limit(
            torrent_hash=torrent_hash,
            download_limit=request.download_limit,
            upload_limit=request.upload_limit,
            client_id=request.client_id,
        )

        if success:
            return {"ok": True, "message": "速度限制设置成功"}
        else:
            raise HTTPException(status_code=400, detail="速度限制设置失败")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_download_stats(client_id: Optional[str] = None):
    """获取下载统计信息"""
    try:
        stats = await download_manager.get_transfer_info(client_id)
        return {"ok": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/{client_id}/test")
async def test_download_client_connection(client_id: str):
    """测试下载器连接"""
    try:
        result = await download_manager.test_connection(client_id)
        return {"ok": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
