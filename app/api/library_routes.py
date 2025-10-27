#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 库管理API路由
提供库的CRUD操作和扫描功能
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from core.library_manager import LibraryManager, LibraryConfig, LibraryType

router = APIRouter()
library_manager = LibraryManager()


# 请求/响应模型
class LibraryCreateRequest(BaseModel):
    """创建库请求"""
    library_id: str
    name: str
    type: str
    path: str
    enabled: bool = True
    auto_scan: bool = True
    scan_interval: int = 3600
    rename_rules: Optional[Dict] = None
    metadata_sources: Optional[List[str]] = None
    file_extensions: Optional[List[str]] = None


class LibraryUpdateRequest(BaseModel):
    """更新库请求"""
    name: Optional[str] = None
    path: Optional[str] = None
    enabled: Optional[bool] = None
    auto_scan: Optional[bool] = None
    scan_interval: Optional[int] = None
    rename_rules: Optional[Dict] = None
    metadata_sources: Optional[List[str]] = None
    file_extensions: Optional[List[str]] = None


class LibraryResponse(BaseModel):
    """库响应"""
    library_id: str
    name: str
    type: str
    path: str
    enabled: bool
    auto_scan: bool
    scan_interval: int
    rename_rules: Dict
    metadata_sources: List[str]
    file_extensions: List[str]


class ScanResultResponse(BaseModel):
    """扫描结果响应"""
    library_id: str
    library_name: str
    file_count: int
    total_size: int
    status: str
    media_files: List[Dict]


class LibraryStatsResponse(BaseModel):
    """库统计响应"""
    total_libraries: int
    enabled_libraries: int
    by_type: Dict[str, Dict]
    path_validation: Dict[str, bool]


# API路由
@router.get("/libraries", response_model=Dict[str, LibraryResponse])
async def get_all_libraries():
    """获取所有库"""
    libraries = {}
    for lib_id, lib_config in library_manager.libraries.items():
        libraries[lib_id] = LibraryResponse(
            library_id=lib_id,
            name=lib_config.name,
            type=lib_config.type.value,
            path=lib_config.path,
            enabled=lib_config.enabled,
            auto_scan=lib_config.auto_scan,
            scan_interval=lib_config.scan_interval,
            rename_rules=lib_config.rename_rules or {},
            metadata_sources=lib_config.metadata_sources or [],
            file_extensions=lib_config.file_extensions or []
        )
    return libraries


@router.get("/libraries/{library_id}", response_model=LibraryResponse)
async def get_library(library_id: str):
    """获取指定库"""
    library = library_manager.get_library(library_id)
    if not library:
        raise HTTPException(status_code=404, detail=f"库不存在: {library_id}")
    
    return LibraryResponse(
        library_id=library_id,
        name=library.name,
        type=library.type.value,
        path=library.path,
        enabled=library.enabled,
        auto_scan=library.auto_scan,
        scan_interval=library.scan_interval,
        rename_rules=library.rename_rules or {},
        metadata_sources=library.metadata_sources or [],
        file_extensions=library.file_extensions or []
    )


@router.post("/libraries", response_model=LibraryResponse)
async def create_library(request: LibraryCreateRequest):
    """创建新库"""
    # 验证库类型
    try:
        library_type = LibraryType(request.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的库类型: {request.type}")
    
    # 创建库配置
    library_config = LibraryConfig(
        name=request.name,
        type=library_type,
        path=request.path,
        enabled=request.enabled,
        auto_scan=request.auto_scan,
        scan_interval=request.scan_interval,
        rename_rules=request.rename_rules,
        metadata_sources=request.metadata_sources,
        file_extensions=request.file_extensions
    )
    
    # 添加库
    success = library_manager.add_library(request.library_id, library_config)
    if not success:
        raise HTTPException(status_code=400, detail=f"库已存在: {request.library_id}")
    
    return LibraryResponse(
        library_id=request.library_id,
        name=library_config.name,
        type=library_config.type.value,
        path=library_config.path,
        enabled=library_config.enabled,
        auto_scan=library_config.auto_scan,
        scan_interval=library_config.scan_interval,
        rename_rules=library_config.rename_rules or {},
        metadata_sources=library_config.metadata_sources or [],
        file_extensions=library_config.file_extensions or []
    )


@router.put("/libraries/{library_id}", response_model=LibraryResponse)
async def update_library(library_id: str, request: LibraryUpdateRequest):
    """更新库配置"""
    # 构建更新参数
    update_params = {}
    if request.name is not None:
        update_params["name"] = request.name
    if request.path is not None:
        update_params["path"] = request.path
    if request.enabled is not None:
        update_params["enabled"] = request.enabled
    if request.auto_scan is not None:
        update_params["auto_scan"] = request.auto_scan
    if request.scan_interval is not None:
        update_params["scan_interval"] = request.scan_interval
    if request.rename_rules is not None:
        update_params["rename_rules"] = request.rename_rules
    if request.metadata_sources is not None:
        update_params["metadata_sources"] = request.metadata_sources
    if request.file_extensions is not None:
        update_params["file_extensions"] = request.file_extensions
    
    # 更新库
    success = library_manager.update_library(library_id, **update_params)
    if not success:
        raise HTTPException(status_code=404, detail=f"库不存在: {library_id}")
    
    # 返回更新后的库
    library = library_manager.get_library(library_id)
    return LibraryResponse(
        library_id=library_id,
        name=library.name,
        type=library.type.value,
        path=library.path,
        enabled=library.enabled,
        auto_scan=library.auto_scan,
        scan_interval=library.scan_interval,
        rename_rules=library.rename_rules or {},
        metadata_sources=library.metadata_sources or [],
        file_extensions=library.file_extensions or []
    )


@router.delete("/libraries/{library_id}")
async def delete_library(library_id: str):
    """删除库"""
    success = library_manager.remove_library(library_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"库不存在: {library_id}")
    
    return {"message": f"库已删除: {library_id}"}


@router.post("/libraries/{library_id}/enable")
async def enable_library(library_id: str):
    """启用库"""
    success = library_manager.enable_library(library_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"库不存在: {library_id}")
    
    return {"message": f"库已启用: {library_id}"}


@router.post("/libraries/{library_id}/disable")
async def disable_library(library_id: str):
    """禁用库"""
    success = library_manager.disable_library(library_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"库不存在: {library_id}")
    
    return {"message": f"库已禁用: {library_id}"}


@router.post("/libraries/{library_id}/scan", response_model=ScanResultResponse)
async def scan_library(library_id: str):
    """扫描指定库"""
    result = library_manager.scan_library(library_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return ScanResultResponse(
        library_id=result["library_id"],
        library_name=result["library_name"],
        file_count=result["file_count"],
        total_size=result["total_size"],
        status=result["status"],
        media_files=result["media_files"]
    )


@router.post("/libraries/scan/all")
async def scan_all_libraries():
    """扫描所有启用的库"""
    result = library_manager.scan_all_libraries()
    return result


@router.get("/libraries/stats", response_model=LibraryStatsResponse)
async def get_library_stats():
    """获取库统计信息"""
    stats = library_manager.get_library_stats()
    return LibraryStatsResponse(
        total_libraries=stats["total_libraries"],
        enabled_libraries=stats["enabled_libraries"],
        by_type=stats["by_type"],
        path_validation=stats["path_validation"]
    )


@router.get("/libraries/types")
async def get_library_types():
    """获取支持的库类型"""
    return {
        "types": [
            {
                "value": lib_type.value,
                "label": lib_type.name,
                "description": f"{lib_type.name}库"
            }
            for lib_type in LibraryType
        ]
    }


@router.get("/libraries/validation/paths")
async def validate_library_paths():
    """验证所有库路径"""
    results = library_manager.validate_library_paths()
    return {
        "validation_results": results,
        "valid_count": sum(1 for valid in results.values() if valid),
        "invalid_count": sum(1 for valid in results.values() if not valid)
    }


# 健康检查端点
@router.get("/libraries/health")
async def library_health_check():
    """库服务健康检查"""
    stats = library_manager.get_library_stats()
    
    # 检查是否有启用的库
    enabled_libraries = stats["enabled_libraries"]
    path_validation = stats["path_validation"]
    
    # 检查路径有效性
    valid_paths = sum(1 for valid in path_validation.values() if valid)
    
    health_status = "healthy" if enabled_libraries > 0 and valid_paths > 0 else "degraded"
    
    return {
        "status": health_status,
        "enabled_libraries": enabled_libraries,
        "valid_paths": valid_paths,
        "total_libraries": stats["total_libraries"]
    }