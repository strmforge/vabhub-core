#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由定义
媒体文件管理器的核心API接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from core.config import settings
from core.processor import MediaProcessor
from utils.file_utils import scan_directory
from utils.metadata_utils import MetadataExtractor, TitleQuery

# 导入存储路由
from app.api.storage_routes import router as storage_router

# 导入STRM路由
from app.api.strm_routes import strm_router

# 创建API路由器
api_router = APIRouter()


# 请求/响应模型
class ScanRequest(BaseModel):
    path: str
    recursive: bool = True
    file_types: Optional[List[str]] = None


class ProcessRequest(BaseModel):
    files: List[str]
    strategy: str = "auto"


class StatusResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class FileInfo(BaseModel):
    path: str
    name: str
    size: int
    modified_time: float
    type: str


# 全局处理器实例
processor = MediaProcessor()


@api_router.get("/health", response_model=StatusResponse)
async def health_check():
    """健康检查"""
    return StatusResponse(
        status="healthy",
        message="服务运行正常",
        data={
            "app_name": settings.app_name,
            "version": settings.version
        }
    )


@api_router.get("/status", response_model=StatusResponse)
async def get_status():
    """获取处理状态"""
    return StatusResponse(
        status="success",
        message="状态查询成功",
        data=processor.get_status()
    )


@api_router.post("/scan", response_model=StatusResponse)
async def scan_files(request: ScanRequest):
    """扫描文件"""
    try:
        files = scan_directory(
            request.path,
            recursive=request.recursive,
            file_types=request.file_types
        )
        
        return StatusResponse(
            status="success",
            message=f"扫描完成，找到 {len(files)} 个文件",
            data={"files": files}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"扫描失败: {str(e)}")


@api_router.post("/process", response_model=StatusResponse)
async def process_files(request: ProcessRequest, background_tasks: BackgroundTasks):
    """处理文件"""
    try:
        # 验证策略
        valid_strategies = ["auto", "skip", "replace", "keep_both"]
        if request.strategy not in valid_strategies:
            raise HTTPException(
                status_code=400,
                detail=f"无效的处理策略，必须是: {valid_strategies}"
            )
        
        # 在后台处理文件
        background_tasks.add_task(
            processor.process_files,
            request.files,
            request.strategy
        )
        
        return StatusResponse(
            status="success",
            message="文件处理任务已开始",
            data={
                "file_count": len(request.files),
                "strategy": request.strategy
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@api_router.get("/config", response_model=StatusResponse)
async def get_config():
    """获取配置信息"""
    config_data = {
        "app_name": settings.app_name,
        "version": settings.version,
        "scan_path": settings.scan_path,
        "movie_output_path": settings.movie_output_path,
        "tv_output_path": settings.tv_output_path,
        "conflict_strategy": settings.conflict_strategy,
        "network_retry_count": settings.network_retry_count,
        "batch_size": settings.batch_size
    }
    
    return StatusResponse(
        status="success",
        message="配置获取成功",
        data=config_data
    )


@api_router.put("/config", response_model=StatusResponse)
async def update_config(config_data: Dict[str, Any]):
    """更新配置"""
    try:
        # 验证和更新配置
        for key, value in config_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        # 保存配置到文件
        from core.config import save_config_to_file
        save_config_to_file()
        
        return StatusResponse(
            status="success",
            message="配置更新成功",
            data=config_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")


@api_router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """获取应用指标"""
    return processor.get_metrics()


@api_router.post("/validate/path", response_model=StatusResponse)
async def validate_path(path: str):
    """验证路径"""
    try:
        if not path:
            raise HTTPException(status_code=400, detail="路径不能为空")
        
        if not path.startswith("/"):
            raise HTTPException(status_code=400, detail="路径必须是绝对路径")
        
        if not os.path.exists(path):
            raise HTTPException(status_code=400, detail="路径不存在")
        
        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail="路径不是目录")
        
        return StatusResponse(
            status="success",
            message="路径验证成功",
            data={"path": path}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"路径验证失败: {str(e)}")


@api_router.get("/metadata/{file_path:path}", response_model=StatusResponse)
async def get_metadata(file_path: str):
    """获取文件元数据"""
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        extractor = MetadataExtractor()
        metadata = extractor.extract_from_filename(file_path)
        
        return StatusResponse(
            status="success",
            message="元数据获取成功",
            data=metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"元数据获取失败: {str(e)}")


# 包含存储路由
api_router.include_router(storage_router)

# 包含STRM路由
api_router.include_router(strm_router)

# 包含STRM路由
api_router.include_router(strm_router)