#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版API路由
整合所有高级功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from core.services import get_service_manager
from core.enhanced_pt_manager import EnhancedPTManager, PTSiteConfig, TorrentInfo, DownloadTask

# 创建增强版API路由器
enhanced_router = APIRouter()

# 获取服务管理器实例（暂时设为None，待实现）
service_manager = None

# 获取PT管理器实例
pt_manager = EnhancedPTManager()


class CleanRequest(BaseModel):
    """清理请求模型"""
    directory: str
    dry_run: bool = True


class CleanBySizeRequest(BaseModel):
    """按大小清理请求模型"""
    directory: str
    max_size_mb: int = 10
    dry_run: bool = True


class BatchRenamePatternRequest(BaseModel):
    """批量重命名模式请求模型"""
    directory: str
    pattern: str = "file_{number:03d}"
    start_number: int = 1
    dry_run: bool = True


class BatchConvertRequest(BaseModel):
    """批量转换请求模型"""
    directory: str
    target_format: str
    quality: int = 90
    dry_run: bool = True


class BatchOrganizeByDateRequest(BaseModel):
    """按日期整理请求模型"""
    directory: str
    date_format: str = "%Y-%m"
    dry_run: bool = True


class BatchMetadataRequest(BaseModel):
    """批量元数据提取请求模型"""
    directory: str
    extract_types: List[str] = ["basic", "exif", "media"]


class CleanResponse(BaseModel):
    """清理响应模型"""
    success: bool
    message: str
    cleaned_files: int
    cleaned_dirs: int
    total_size: int
    files_removed: List[str]
    dirs_removed: List[str]
    dry_run: bool


class BatchRenamePatternResponse(BaseModel):
    """批量重命名响应模型"""
    success: bool
    message: str
    total_files: int
    renamed_files: int
    operations: List[Dict[str, Any]]
    dry_run: bool


class BatchConvertResponse(BaseModel):
    """批量转换响应模型"""
    success: bool
    message: str
    total_files: int
    converted_files: int
    operations: List[Dict[str, Any]]
    dry_run: bool
    target_format: str


class BatchOrganizeByDateResponse(BaseModel):
    """按日期整理响应模型"""
    success: bool
    message: str
    total_files: int
    organized_files: int
    operations: List[Dict[str, Any]]
    dry_run: bool
    date_format: str


class BatchMetadataResponse(BaseModel):
    """批量元数据响应模型"""
    success: bool
    message: str
    total_files: int
    processed_files: int
    metadata_results: List[Dict[str, Any]]
    extract_types: List[str]


@enhanced_router.post("/clean", response_model=CleanResponse)
async def clean_directory(request: CleanRequest):
    """清理目录"""
    try:
        # 检查文件清理功能是否启用
        # 注意：这里需要根据实际配置检查功能状态
        # 暂时跳过功能状态检查
        
        # 直接调用文件清理功能（需要实现实际的清理逻辑）
        # 暂时返回模拟结果
        result = {"success": True, "message": "清理功能暂未实现", "data": {}}
        
        if result['success']:
            return CleanResponse(
                success=True,
                message=result['message'],
                cleaned_files=result['data'].get('cleaned_files', 0),
                cleaned_dirs=result['data'].get('cleaned_dirs', 0),
                total_size=result['data'].get('total_size', 0),
                files_removed=result['data'].get('files_removed', []),
                dirs_removed=result['data'].get('dirs_removed', []),
                dry_run=result['data'].get('dry_run', True)
            )
        else:
            raise HTTPException(status_code=400, detail=result['message'])
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"目录清理失败: {str(e)}")


@enhanced_router.post("/clean/size", response_model=CleanResponse)
async def clean_by_size(request: CleanBySizeRequest):
    """按大小清理文件"""
    try:
        # 功能状态检查暂时跳过
        # if not service_manager.config.get_feature_status("file_cleaner"):
        #     raise HTTPException(status_code=400, detail="文件清理功能未启用")
        
        # 直接调用文件清理功能（需要实现实际的清理逻辑）
        # 暂时返回模拟结果
        result = {"success": True, "message": "按大小清理功能暂未实现", "data": {}}
        
        if result['success']:
            return CleanResponse(
                success=True,
                message=result['message'],
                cleaned_files=result['data'].get('cleaned_files', 0),
                cleaned_dirs=0,  # 按大小清理不涉及目录
                total_size=result['data'].get('total_size', 0),
                files_removed=result['data'].get('files_removed', []),
                dirs_removed=[],
                dry_run=result['data'].get('dry_run', True)
            )
        else:
            raise HTTPException(status_code=400, detail=result['message'])
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"按大小清理失败: {str(e)}")


@enhanced_router.post("/batch/rename-pattern", response_model=BatchRenamePatternResponse)
async def batch_rename_with_pattern(request: BatchRenamePatternRequest):
    """批量重命名文件（模式匹配）"""
    try:
        # 功能状态检查暂时跳过
        # if not service_manager.config.get_feature_status("batch_processor"):
        #     raise HTTPException(status_code=400, detail="批量处理功能未启用")
        
        # 直接调用批量重命名功能（需要实现实际的逻辑）
        # 暂时返回模拟结果
        result = {"success": True, "message": "批量重命名功能暂未实现", "data": {}}
        
        if result['success']:
            return BatchRenamePatternResponse(
                success=True,
                message=result['message'],
                total_files=result['data'].get('total_files', 0),
                renamed_files=result['data'].get('renamed_files', 0),
                operations=result['data'].get('operations', []),
                dry_run=result['data'].get('dry_run', True)
            )
        else:
            raise HTTPException(status_code=400, detail=result['message'])
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量重命名失败: {str(e)}")


@enhanced_router.post("/batch/convert", response_model=BatchConvertResponse)
async def batch_convert_images(request: BatchConvertRequest):
    """批量转换图片格式"""
    try:
        # 功能状态检查暂时跳过
        # if not service_manager.config.get_feature_status("batch_processor"):
        #     raise HTTPException(status_code=400, detail="批量处理功能未启用")
        
        # 直接调用图片转换功能（需要实现实际的逻辑）
        # 暂时返回模拟结果
        result = {"success": True, "message": "图片转换功能暂未实现", "data": {}}
        
        if result['success']:
            return BatchConvertResponse(
                success=True,
                message=result['message'],
                total_files=result['data'].get('total_files', 0),
                converted_files=result['data'].get('converted_files', 0),
                operations=result['data'].get('operations', []),
                dry_run=result['data'].get('dry_run', True),
                target_format=result['data'].get('target_format', '')
            )
        else:
            raise HTTPException(status_code=400, detail=result['message'])
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量转换失败: {str(e)}")


@enhanced_router.post("/batch/organize-date", response_model=BatchOrganizeByDateResponse)
async def batch_organize_by_date(request: BatchOrganizeByDateRequest):
    """按日期整理文件"""
    try:
        # 功能状态检查暂时跳过
        # if not service_manager.config.get_feature_status("batch_processor"):
        #     raise HTTPException(status_code=400, detail="批量处理功能未启用")
        
        # 直接调用按日期整理功能（需要实现实际的逻辑）
        # 暂时返回模拟结果
        result = {"success": True, "message": "按日期整理功能暂未实现", "data": {}}
        
        if result['success']:
            return BatchOrganizeByDateResponse(
                success=True,
                message=result['message'],
                total_files=result['data'].get('total_files', 0),
                organized_files=result['data'].get('organized_files', 0),
                operations=result['data'].get('operations', []),
                dry_run=result['data'].get('dry_run', True),
                date_format=result['data'].get('date_format', '')
            )
        else:
            raise HTTPException(status_code=400, detail=result['message'])
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"按日期整理失败: {str(e)}")


@enhanced_router.post("/batch/metadata", response_model=BatchMetadataResponse)
async def batch_extract_metadata(request: BatchMetadataRequest):
    """批量提取文件元数据"""
    try:
        # 功能状态检查暂时跳过
        # if not service_manager.config.get_feature_status("batch_processor"):
        #     raise HTTPException(status_code=400, detail="批量处理功能未启用")
        
        # 直接调用元数据提取功能（需要实现实际的逻辑）
        # 暂时返回模拟结果
        result = {"success": True, "message": "元数据提取功能暂未实现", "data": {}}
        
        if result['success']:
            return BatchMetadataResponse(
                success=True,
                message=result['message'],
                total_files=result['data'].get('total_files', 0),
                processed_files=result['data'].get('processed_files', 0),
                metadata_results=result['data'].get('metadata_results', []),
                extract_types=result['data'].get('extract_types', [])
            )
        else:
            raise HTTPException(status_code=400, detail=result['message'])
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"元数据提取失败: {str(e)}")


@enhanced_router.get("/features/status")
async def get_features_status():
    """获取功能状态"""
    try:
        features = {
            "file_organizer": "文件整理",
            "duplicate_finder": "重复检测", 
            "smart_rename": "智能重命名",
            "file_cleaner": "文件清理",
            "batch_processor": "批量处理",
            "pt_search": "PT搜索",
            "media_library": "媒体库"
        }
        
        status = {}
        for feature_key, feature_name in features.items():
            status[feature_key] = {
                "name": feature_name,
                "enabled": True,  # 暂时设置为启用
                "service_ready": True  # 暂时设置为就绪
            }
        
        return {
            "success": True,
            "features": status
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取功能状态失败: {str(e)}")


@enhanced_router.get("/health")
async def health_check():
    """健康检查"""
    try:
        service_status = service_manager.get_service_status()
        
        return {
            "status": "healthy",
            "services": service_status,
            "timestamp": "2024-01-01T00:00:00Z"  # 实际应该使用当前时间
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


# PT站点管理相关API
class PTSiteAddRequest(BaseModel):
    """添加PT站点请求模型"""
    name: str
    url: str
    username: str
    password: str
    site_type: str
    api_key: Optional[str] = None
    enabled: bool = True
    priority: int = 1
    max_downloads: int = 5
    download_path: Optional[str] = None


class PTSearchRequest(BaseModel):
    """PT搜索请求模型"""
    keyword: str
    category: str = ""


class PTDownloadRequest(BaseModel):
    """PT下载请求模型"""
    torrent_info: Dict[str, Any]
    download_path: str
    downloader_type: str = "qbittorrent"


class PTSiteStatusResponse(BaseModel):
    """PT站点状态响应模型"""
    name: str
    url: str
    enabled: bool
    status: str
    priority: int


class PTSearchResponse(BaseModel):
    """PT搜索响应模型"""
    success: bool
    message: str
    results: List[Dict[str, Any]]
    total_count: int


class PTDownloadResponse(BaseModel):
    """PT下载响应模型"""
    success: bool
    message: str
    task_id: Optional[str] = None
    download_path: str


@enhanced_router.post("/pt/sites/add", response_model=dict)
async def add_pt_site(request: PTSiteAddRequest):
    """添加PT站点"""
    try:
        # 创建站点配置
        config = PTSiteConfig(
            name=request.name,
            url=request.url,
            username=request.username,
            password=request.password,
            api_key=request.api_key,
            enabled=request.enabled,
            priority=request.priority,
            max_downloads=request.max_downloads,
            download_path=request.download_path
        )
        
        # 添加站点
        success = await pt_manager.add_site(config, request.site_type)
        
        if success:
            return {
                "success": True,
                "message": f"PT站点 {request.name} 添加成功",
                "site_name": request.name
            }
        else:
            raise HTTPException(status_code=400, detail=f"PT站点 {request.name} 添加失败")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加PT站点失败: {str(e)}")


@enhanced_router.get("/pt/sites", response_model=List[PTSiteStatusResponse])
async def list_pt_sites():
    """列出所有PT站点"""
    try:
        sites = pt_manager.list_sites()
        return sites
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取PT站点列表失败: {str(e)}")


@enhanced_router.post("/pt/search", response_model=PTSearchResponse)
async def search_pt_torrents(request: PTSearchRequest):
    """搜索PT种子"""
    try:
        # 在所有站点搜索
        results = await pt_manager.search_all_sites(request.keyword, request.category)
        
        # 转换为字典格式
        torrents_list = []
        for torrent in results:
            torrents_list.append({
                "site_name": torrent.site_name,
                "title": torrent.title,
                "url": torrent.url,
                "size": torrent.size,
                "seeders": torrent.seeders,
                "leechers": torrent.leechers,
                "upload_time": torrent.upload_time.isoformat(),
                "category": torrent.category,
                "free_status": torrent.free_status,
                "download_url": torrent.download_url
            })
        
        return PTSearchResponse(
            success=True,
            message=f"搜索完成，找到 {len(results)} 个结果",
            results=torrents_list,
            total_count=len(results)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PT搜索失败: {str(e)}")


@enhanced_router.post("/pt/download", response_model=PTDownloadResponse)
async def download_pt_torrent(request: PTDownloadRequest):
    """下载PT种子"""
    try:
        # 设置活动下载器
        pt_manager.set_active_downloader(request.downloader_type)
        
        # 创建TorrentInfo对象
        torrent_info = TorrentInfo(
            site_name=request.torrent_info["site_name"],
            title=request.torrent_info["title"],
            url=request.torrent_info["url"],
            size=request.torrent_info["size"],
            seeders=request.torrent_info["seeders"],
            leechers=request.torrent_info["leechers"],
            upload_time=request.torrent_info["upload_time"],
            category=request.torrent_info["category"],
            free_status=request.torrent_info.get("free_status", "normal"),
            download_url=request.torrent_info["download_url"]
        )
        
        # 开始下载
        task_id = await pt_manager.download_torrent(torrent_info, request.download_path)
        
        return PTDownloadResponse(
            success=True,
            message="下载任务已创建",
            task_id=task_id,
            download_path=request.download_path
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PT下载失败: {str(e)}")


@enhanced_router.get("/pt/downloads", response_model=List[Dict[str, Any]])
async def list_download_tasks():
    """列出所有下载任务"""
    try:
        tasks = []
        for task_id, task in pt_manager.download_tasks.items():
            tasks.append({
                "task_id": task_id,
                "title": task.torrent_info.title,
                "site_name": task.torrent_info.site_name,
                "status": task.status.value,
                "progress": task.progress,
                "speed": task.speed,
                "download_path": task.download_path,
                "start_time": task.start_time.isoformat() if task.start_time else None,
                "end_time": task.end_time.isoformat() if task.end_time else None,
                "error_message": task.error_message
            })
        
        return tasks
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取下载任务列表失败: {str(e)}")


@enhanced_router.post("/pt/downloads/{task_id}/pause")
async def pause_download_task(task_id: str):
    """暂停下载任务"""
    try:
        success = await pt_manager.pause_task(task_id)
        
        if success:
            return {"success": True, "message": "任务已暂停"}
        else:
            raise HTTPException(status_code=400, detail="暂停任务失败")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停任务失败: {str(e)}")


@enhanced_router.post("/pt/downloads/{task_id}/resume")
async def resume_download_task(task_id: str):
    """恢复下载任务"""
    try:
        success = await pt_manager.resume_task(task_id)
        
        if success:
            return {"success": True, "message": "任务已恢复"}
        else:
            raise HTTPException(status_code=400, detail="恢复任务失败")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复任务失败: {str(e)}")


@enhanced_router.post("/pt/monitoring/start")
async def start_pt_monitoring():
    """启动PT监控"""
    try:
        pt_manager.start_monitoring()
        return {"success": True, "message": "PT监控已启动"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动PT监控失败: {str(e)}")


@enhanced_router.post("/pt/monitoring/stop")
async def stop_pt_monitoring():
    """停止PT监控"""
    try:
        pt_manager.stop_monitoring()
        return {"success": True, "message": "PT监控已停止"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止PT监控失败: {str(e)}")


@enhanced_router.get("/pt/downloaders")
async def list_downloaders():
    """列出支持的下载器"""
    try:
        downloaders = ["qbittorrent", "transmission", "aria2"]
        return {
            "success": True,
            "downloaders": downloaders,
            "active_downloader": pt_manager.active_downloader
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取下载器列表失败: {str(e)}")