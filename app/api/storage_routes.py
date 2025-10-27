#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多存储管理API路由
支持115网盘、阿里云盘、RClone、OpenList等存储的统一管理
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from core.file_manager import FileManager, MediaClassifier
from core.transfer_processor import TransferProcessor, SyncManager, AutoOrganizer

router = APIRouter(prefix="/api/storage", tags=["storage"])

# 依赖注入
file_manager = FileManager()
transfer_processor = TransferProcessor()
sync_manager = SyncManager()
organizer = AutoOrganizer()


class StorageInfo(BaseModel):
    """存储信息"""
    type: str
    name: str
    available: bool
    usage: Optional[Dict[str, Any]] = None


class FileItemResponse(BaseModel):
    """文件项响应"""
    name: str
    path: str
    type: str
    size: int
    modify_time: float
    is_dir: bool
    parent: Optional[str] = None


class TransferTaskRequest(BaseModel):
    """传输任务请求"""
    operation: str  # copy, move, upload, download
    source_storage: str
    source_path: str
    target_storage: str
    target_path: str
    new_name: Optional[str] = None


class TransferTaskResponse(BaseModel):
    """传输任务响应"""
    task_id: str
    status: str
    progress: int
    error_message: Optional[str] = None


class SyncRuleRequest(BaseModel):
    """同步规则请求"""
    name: str
    source_storage: str
    source_path: str
    target_storage: str
    target_path: str
    pattern: str = "*"
    recursive: bool = True
    operation: str = "copy"


class OrganizeRuleRequest(BaseModel):
    """整理规则请求"""
    name: str
    storage: str
    source_path: str
    target_base_path: str
    pattern: str = "*"
    recursive: bool = True


@router.get("/storages", response_model=List[StorageInfo])
async def list_storages():
    """列出所有可用的存储"""
    storages = []
    
    for storage_type in file_manager.list_storages():
        available = file_manager.check_storage(storage_type)
        storage_info = StorageInfo(
            type=storage_type,
            name=storage_type.capitalize(),
            available=available
        )
        
        # 获取存储使用情况
        if available:
            storage = file_manager.get_storage(storage_type)
            if storage:
                usage = storage.usage()
                if usage:
                    storage_info.usage = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free
                    }
        
        storages.append(storage_info)
    
    return storages


@router.get("/{storage_type}/files", response_model=List[FileItemResponse])
async def list_files(
    storage_type: str,
    path: str = Query("", description="目录路径")
):
    """浏览存储文件"""
    if not file_manager.check_storage(storage_type):
        raise HTTPException(status_code=400, detail=f"存储 {storage_type} 不可用")
    
    files = file_manager.list_files(storage_type, path)
    
    return [
        FileItemResponse(
            name=file.name,
            path=file.path,
            type=file.type,
            size=file.size,
            modify_time=file.modify_time,
            is_dir=file.is_dir,
            parent=file.parent
        )
        for file in files
    ]


@router.post("/{storage_type}/folder")
async def create_folder(
    storage_type: str,
    path: str = Query("", description="父目录路径"),
    name: str = Query(..., description="新目录名称")
):
    """创建目录"""
    if not file_manager.check_storage(storage_type):
        raise HTTPException(status_code=400, detail=f"存储 {storage_type} 不可用")
    
    folder = file_manager.create_folder(storage_type, path, name)
    
    if not folder:
        raise HTTPException(status_code=500, detail="创建目录失败")
    
    return {"message": "目录创建成功", "folder": folder.name}


@router.post("/transfer")
async def create_transfer_task(request: TransferTaskRequest):
    """创建传输任务"""
    try:
        task_id = transfer_processor.add_transfer_task(
            operation=request.operation,
            source_storage=request.source_storage,
            source_path=request.source_path,
            target_storage=request.target_storage,
            target_path=request.target_path,
            new_name=request.new_name
        )
        
        return {"task_id": task_id, "message": "传输任务已创建"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transfer/{task_id}", response_model=TransferTaskResponse)
async def get_transfer_task(task_id: str):
    """获取传输任务状态"""
    task = transfer_processor.get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TransferTaskResponse(
        task_id=task.task_id,
        status=task.status.value,
        progress=task.progress,
        error_message=task.error_message
    )


@router.delete("/transfer/{task_id}")
async def cancel_transfer_task(task_id: str):
    """取消传输任务"""
    if transfer_processor.cancel_task(task_id):
        return {"message": "任务已取消"}
    else:
        raise HTTPException(status_code=404, detail="任务不存在或无法取消")


@router.get("/transfer")
async def list_transfer_tasks():
    """列出所有传输任务"""
    tasks = transfer_processor.list_tasks()
    
    return [
        {
            "task_id": task.task_id,
            "operation": task.operation.value,
            "source_storage": task.source_storage,
            "source_path": task.source_path,
            "target_storage": task.target_storage,
            "target_path": task.target_path,
            "status": task.status.value,
            "progress": task.progress,
            "start_time": task.start_time,
            "end_time": task.end_time
        }
        for task in tasks
    ]


@router.post("/sync/rules")
async def add_sync_rule(request: SyncRuleRequest):
    """添加同步规则"""
    sync_manager.add_sync_rule(
        name=request.name,
        source_storage=request.source_storage,
        source_path=request.source_path,
        target_storage=request.target_storage,
        target_path=request.target_path,
        pattern=request.pattern,
        recursive=request.recursive,
        operation=request.operation
    )
    
    return {"message": "同步规则已添加"}


@router.delete("/sync/rules/{rule_name}")
async def remove_sync_rule(rule_name: str):
    """移除同步规则"""
    sync_manager.remove_sync_rule(rule_name)
    
    return {"message": "同步规则已移除"}


@router.post("/sync/execute")
async def execute_sync(rule_name: Optional[str] = None):
    """执行同步"""
    try:
        results = sync_manager.execute_sync(rule_name)
        
        return {
            "message": "同步任务已启动",
            "task_ids": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/organize/rules")
async def add_organize_rule(request: OrganizeRuleRequest):
    """添加整理规则"""
    organizer.add_organize_rule(
        name=request.name,
        storage=request.storage,
        source_path=request.source_path,
        target_base_path=request.target_base_path,
        pattern=request.pattern,
        recursive=request.recursive
    )
    
    return {"message": "整理规则已添加"}


@router.post("/organize/execute")
async def execute_organize(rule_name: Optional[str] = None):
    """执行整理"""
    try:
        results = organizer.execute_organize(rule_name)
        
        return {
            "message": "整理任务已启动",
            "task_ids": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify")
async def classify_file(filename: str):
    """分类文件"""
    classifier = MediaClassifier()
    file_type = classifier.classify_file(filename)
    target_folder = classifier.get_target_folder(filename)
    
    return {
        "filename": filename,
        "type": file_type,
        "target_folder": target_folder
    }


@router.get("/{storage_type}/usage")
async def get_storage_usage(storage_type: str):
    """获取存储使用情况"""
    if not file_manager.check_storage(storage_type):
        raise HTTPException(status_code=400, detail=f"存储 {storage_type} 不可用")
    
    storage = file_manager.get_storage(storage_type)
    if not storage:
        raise HTTPException(status_code=500, detail="无法获取存储实例")
    
    usage = storage.usage()
    if not usage:
        raise HTTPException(status_code=500, detail="无法获取使用情况")
    
    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "used_percentage": round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0
    }