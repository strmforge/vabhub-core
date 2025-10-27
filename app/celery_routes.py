#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Celery任务API路由
异步任务管理接口
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from celery.result import AsyncResult

from core.celery_app import celery_app
from core.tasks import process_files_task, scan_directory_task, cleanup_task, batch_rename_task
from core.auth import User, get_current_active_user
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/tasks", tags=["任务"])


@router.post("/process-files")
async def start_process_files_task(
    files: List[Dict[str, Any]],
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """启动文件处理任务"""
    try:
        task = process_files_task.delay(files, session_id)
        
        logger.info("文件处理任务已启动", 
                   task_id=task.id, 
                   session_id=session_id, 
                   file_count=len(files))
        
        return {
            "task_id": task.id,
            "status": "started",
            "session_id": session_id,
            "file_count": len(files)
        }
    
    except Exception as e:
        logger.error("启动文件处理任务失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"任务启动失败: {str(e)}")


@router.post("/scan-directory")
async def start_scan_directory_task(
    directory: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """启动目录扫描任务"""
    try:
        task = scan_directory_task.delay(directory)
        
        logger.info("目录扫描任务已启动", task_id=task.id, directory=directory)
        
        return {
            "task_id": task.id,
            "status": "started",
            "directory": directory
        }
    
    except Exception as e:
        logger.error("启动目录扫描任务失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"任务启动失败: {str(e)}")


@router.post("/cleanup")
async def start_cleanup_task(
    directory: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """启动清理任务"""
    try:
        task = cleanup_task.delay(directory)
        
        logger.info("清理任务已启动", task_id=task.id, directory=directory)
        
        return {
            "task_id": task.id,
            "status": "started",
            "directory": directory
        }
    
    except Exception as e:
        logger.error("启动清理任务失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"任务启动失败: {str(e)}")


@router.post("/batch-rename")
async def start_batch_rename_task(
    file_mappings: List[Dict[str, str]],
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """启动批量重命名任务"""
    try:
        task = batch_rename_task.delay(file_mappings)
        
        logger.info("批量重命名任务已启动", task_id=task.id, file_count=len(file_mappings))
        
        return {
            "task_id": task.id,
            "status": "started",
            "file_count": len(file_mappings)
        }
    
    except Exception as e:
        logger.error("启动批量重命名任务失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"任务启动失败: {str(e)}")


@router.get("/{task_id}")
async def get_task_status(task_id: str, current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """获取任务状态"""
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        response = {
            "task_id": task_id,
            "status": task_result.status,
            "result": None
        }
        
        if task_result.ready():
            if task_result.successful():
                response["result"] = task_result.result
            else:
                response["error"] = str(task_result.result)
        
        elif task_result.state == 'PROGRESS':
            response["progress"] = task_result.info
        
        return response
    
    except Exception as e:
        logger.error("获取任务状态失败", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.get("/")
async def get_active_tasks(current_user: User = Depends(get_current_active_user)) -> List[Dict[str, Any]]:
    """获取活跃任务列表"""
    try:
        # 获取Celery监控信息
        inspector = celery_app.control.inspect()
        
        active_tasks = []
        
        # 获取活跃任务
        active = inspector.active()
        if active:
            for worker, tasks in active.items():
                for task in tasks:
                    active_tasks.append({
                        "task_id": task['id'],
                        "name": task['name'],
                        "worker": worker,
                        "state": "active",
                        "args": task['args'],
                        "kwargs": task['kwargs']
                    })
        
        # 获取预定任务
        scheduled = inspector.scheduled()
        if scheduled:
            for worker, tasks in scheduled.items():
                for task in tasks:
                    active_tasks.append({
                        "task_id": task['request']['id'],
                        "name": task['request']['name'],
                        "worker": worker,
                        "state": "scheduled",
                        "eta": task['eta']
                    })
        
        return active_tasks
    
    except Exception as e:
        logger.error("获取活跃任务列表失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.delete("/{task_id}")
async def cancel_task(task_id: str, current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """取消任务"""
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result.state in ['PENDING', 'STARTED']:
            task_result.revoke(terminate=True)
            logger.info("任务已取消", task_id=task_id)
            return {"message": "任务已取消", "task_id": task_id}
        
        else:
            raise HTTPException(status_code=400, detail="任务无法取消")
    
    except Exception as e:
        logger.error("取消任务失败", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.get("/stats/summary")
async def get_task_stats_summary(current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """获取任务统计摘要"""
    try:
        # 这里可以实现任务统计逻辑
        # 暂时返回模拟数据
        return {
            "total_tasks": 100,
            "completed_tasks": 85,
            "failed_tasks": 5,
            "active_tasks": 10,
            "average_processing_time": 120.5,
            "success_rate": 0.85
        }
    
    except Exception as e:
        logger.error("获取任务统计失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")