#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 统一API接口
参照MoviePilot的API设计理念
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
from pathlib import Path

from core.config import get_config, config_manager
from core.services import get_service_manager
from core.base import BatchTask, ProcessingResult

# 获取服务管理器实例
service_manager = get_service_manager()

# 获取服务管理器实例
service_manager = get_service_manager()


class APIResponse(BaseModel):
    """统一API响应格式"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success(cls, message: str = "", data: Dict[str, Any] = None):
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error(cls, message: str = ""):
        return cls(success=False, message=message)


class FileOrganizeRequest(BaseModel):
    """文件整理请求"""
    source_dir: str
    target_dir: str
    move_files: bool = False


class DuplicateScanRequest(BaseModel):
    """重复扫描请求"""
    directory: str
    method: str = "hash"


class RenameRequest(BaseModel):
    """重命名请求"""
    file_path: str
    strategy: Optional[str] = None


class BatchRenameRequest(BaseModel):
    """批量重命名请求"""
    files: List[str]
    strategy: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: float
    message: str
    results: Optional[List[Dict[str, Any]]] = None


class VabHubAPI:
    """VabHub API主类"""
    
    def __init__(self):
        self.app = FastAPI(
            title="VabHub API",
            version="5.0.0",
            description="VabHub 统一API接口"
        )
        self.config = get_config()
        self.tasks = {}  # 任务管理器
        self.websocket_connections = []
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """设置中间件"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.api.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.get("/", response_model=APIResponse)
        async def root():
            """根路径"""
            return APIResponse.success("VabHub API 服务运行正常")
        
        @self.app.get("/health", response_model=APIResponse)
        async def health_check():
            """健康检查"""
            service_status = service_manager.get_service_status()
            return APIResponse.success("服务健康", {
                "services": service_status,
                "version": self.config.version
            })
        
        @self.app.get("/config", response_model=APIResponse)
        async def get_configuration():
            """获取配置"""
            return APIResponse.success("配置获取成功", {
                "config": self.config.dict()
            })
        
        @self.app.post("/config/update", response_model=APIResponse)
        async def update_configuration(updates: Dict[str, Any]):
            """更新配置"""
            try:
                config_manager.update_config(**updates)
                return APIResponse.success("配置更新成功")
            except Exception as e:
                return APIResponse.error(f"配置更新失败: {str(e)}")
        
        @self.app.post("/files/organize", response_model=APIResponse)
        async def organize_files(request: FileOrganizeRequest, background_tasks: BackgroundTasks):
            """文件整理"""
            if not config_manager.get_feature_status("file_organizer"):
                return APIResponse.error("文件整理功能未启用")
            
            task_id = self._create_task("file_organize", {
                "source_dir": request.source_dir,
                "target_dir": request.target_dir,
                "move_files": request.move_files
            })
            
            background_tasks.add_task(self._execute_file_organize, task_id)
            
            return APIResponse.success("文件整理任务已启动", {"task_id": task_id})
        
        @self.app.post("/files/duplicate-scan", response_model=APIResponse)
        async def duplicate_scan(request: DuplicateScanRequest, background_tasks: BackgroundTasks):
            """重复文件扫描"""
            if not config_manager.get_feature_status("duplicate_finder"):
                return APIResponse.error("重复文件检测功能未启用")
            
            task_id = self._create_task("duplicate_scan", {
                "directory": request.directory,
                "method": request.method
            })
            
            background_tasks.add_task(self._execute_duplicate_scan, task_id)
            
            return APIResponse.success("重复文件扫描任务已启动", {"task_id": task_id})
        
        @self.app.post("/files/rename", response_model=APIResponse)
        async def rename_file(request: RenameRequest):
            """重命名文件"""
            if not config_manager.get_feature_status("smart_rename"):
                return APIResponse.error("智能重命名功能未启用")
            
            try:
                result = await service_manager.smart_renamer.rename_file(
                    request.file_path, request.strategy
                )
                
                if result.success:
                    return APIResponse.success(result.message, result.data)
                else:
                    return APIResponse.error(result.message)
                    
            except Exception as e:
                return APIResponse.error(f"重命名失败: {str(e)}")
        
        @self.app.post("/files/batch-rename", response_model=APIResponse)
        async def batch_rename(request: BatchRenameRequest, background_tasks: BackgroundTasks):
            """批量重命名"""
            if not config_manager.get_feature_status("smart_rename"):
                return APIResponse.error("智能重命名功能未启用")
            
            task_id = self._create_task("batch_rename", {
                "files": request.files,
                "strategy": request.strategy
            })
            
            background_tasks.add_task(self._execute_batch_rename, task_id)
            
            return APIResponse.success("批量重命名任务已启动", {"task_id": task_id})
        
        @self.app.get("/tasks/{task_id}", response_model=APIResponse)
        async def get_task_status(task_id: str):
            """获取任务状态"""
            if task_id not in self.tasks:
                return APIResponse.error("任务不存在")
            
            task = self.tasks[task_id]
            return APIResponse.success("任务状态获取成功", {
                "task": task.to_dict()
            })
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket端点"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    # 处理客户端消息
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "message": "连接正常"
                    }))
            except Exception:
                self.websocket_connections.remove(websocket)
    
    def _create_task(self, task_type: str, params: Dict[str, Any]) -> str:
        """创建任务"""
        import hashlib
        import time
        
        task_id = hashlib.md5(f"{task_type}{time.time()}".encode()).hexdigest()[:8]
        task = BatchTask(task_id, task_type)
        
        for file_path in params.get('files', []):
            task.add_file(file_path)
        
        self.tasks[task_id] = task
        return task_id
    
    async def _execute_file_organize(self, task_id: str):
        """执行文件整理任务"""
        task = self.tasks[task_id]
        task.status = 'running'
        
        try:
            result = await service_manager.file_organizer.organize_files(
                task.params['source_dir'],
                task.params['target_dir'],
                task.params.get('move_files', False)
            )
            
            task.add_result(result)
            task.status = 'completed'
            task.update_progress(100.0)
            
        except Exception as e:
            task.status = 'failed'
            task.add_result(ProcessingResult(False, str(e)))
    
    async def _execute_duplicate_scan(self, task_id: str):
        """执行重复扫描任务"""
        task = self.tasks[task_id]
        task.status = 'running'
        
        try:
            result = await service_manager.duplicate_finder.find_duplicates(
                task.params['directory'],
                task.params.get('method', 'hash')
            )
            
            task.add_result(result)
            task.status = 'completed'
            task.update_progress(100.0)
            
        except Exception as e:
            task.status = 'failed'
            task.add_result(ProcessingResult(False, str(e)))
    
    async def _execute_batch_rename(self, task_id: str):
        """执行批量重命名任务"""
        task = self.tasks[task_id]
        task.status = 'running'
        
        try:
            total_files = len(task.params['files'])
            processed_files = 0
            
            for file_path in task.params['files']:
                result = await service_manager.smart_renamer.rename_file(
                    file_path, task.params.get('strategy')
                )
                task.add_result(result)
                
                processed_files += 1
                progress = (processed_files / total_files) * 100
                task.update_progress(progress)
            
            task.status = 'completed'
            
        except Exception as e:
            task.status = 'failed'
            task.add_result(ProcessingResult(False, str(e)))
    
    async def _broadcast_message(self, message: Dict[str, Any]):
        """广播消息到所有WebSocket连接"""
        for connection in self.websocket_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.websocket_connections.remove(connection)


# 创建API实例
api = VabHubAPI()
app = api.app