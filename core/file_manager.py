#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理器核心模块
基于MoviePilot的文件管理器架构设计
支持多存储统一管理
"""

import os
import json
import time
import threading
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Callable, Union
from enum import Enum

from core.storage_base import StorageBase, FileItem, StorageUsage, StorageSchema, StorageManager


class FileOperation(Enum):
    """文件操作类型"""
    COPY = "copy"
    MOVE = "move"
    RENAME = "rename"
    DELETE = "delete"
    UPLOAD = "upload"
    DOWNLOAD = "download"


class TransferStatus(Enum):
    """传输状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransferTask:
    """传输任务"""
    
    def __init__(self, 
                 task_id: str,
                 operation: FileOperation,
                 source_storage: str,
                 source_path: str,
                 target_storage: str,
                 target_path: str,
                 file_name: str,
                 size: int = 0):
        self.task_id = task_id
        self.operation = operation
        self.source_storage = source_storage
        self.source_path = source_path
        self.target_storage = target_storage
        self.target_path = target_path
        self.file_name = file_name
        self.size = size
        self.status = TransferStatus.PENDING
        self.progress = 0
        self.start_time = None
        self.end_time = None
        self.error_message = None


class FileManager:
    """文件管理器"""
    
    def __init__(self):
        self.storage_manager = StorageManager()
        self.transfer_tasks = {}
        self.task_lock = threading.Lock()
        self.task_counter = 0
        
    def get_storage(self, storage_type: str) -> Optional[StorageBase]:
        """获取存储适配器"""
        return self.storage_manager.get_storage(storage_type)
    
    def list_storages(self) -> List[str]:
        """列出可用的存储类型"""
        return self.storage_manager.list_available_storages()
    
    def check_storage(self, storage_type: str) -> bool:
        """检查存储是否可用"""
        return self.storage_manager.check_storage_availability(storage_type)
    
    def list_files(self, storage_type: str, path: str = "") -> List[FileItem]:
        """浏览文件列表"""
        storage = self.get_storage(storage_type)
        if not storage:
            return []
        
        fileitem = FileItem(
            name=Path(path).name if path else "",
            path=path,
            type="folder",
            is_dir=True
        )
        
        return storage.list(fileitem)
    
    def create_folder(self, storage_type: str, path: str, name: str) -> Optional[FileItem]:
        """创建目录"""
        storage = self.get_storage(storage_type)
        if not storage:
            return None
        
        fileitem = FileItem(
            name=Path(path).name if path else "",
            path=path,
            type="folder",
            is_dir=True
        )
        
        return storage.create_folder(fileitem, name)
    
    def delete_file(self, storage_type: str, file_path: str) -> bool:
        """删除文件"""
        storage = self.get_storage(storage_type)
        if not storage:
            return False
        
        fileitem = FileItem(
            name=Path(file_path).name,
            path=file_path,
            type="file",
            is_dir=False
        )
        
        return storage.delete(fileitem)
    
    def rename_file(self, storage_type: str, file_path: str, new_name: str) -> bool:
        """重命名文件"""
        storage = self.get_storage(storage_type)
        if not storage:
            return False
        
        fileitem = FileItem(
            name=Path(file_path).name,
            path=file_path,
            type="file",
            is_dir=False
        )
        
        return storage.rename(fileitem, new_name)
    
    def copy_file(self, 
                  source_storage: str, 
                  source_path: str,
                  target_storage: str,
                  target_path: str,
                  new_name: str = None) -> str:
        """复制文件"""
        task_id = self._generate_task_id()
        
        source_file = Path(source_path)
        target_name = new_name or source_file.name
        
        task = TransferTask(
            task_id=task_id,
            operation=FileOperation.COPY,
            source_storage=source_storage,
            source_path=source_path,
            target_storage=target_storage,
            target_path=target_path,
            file_name=target_name
        )
        
        self._add_task(task)
        self._start_transfer_task(task)
        
        return task_id
    
    def move_file(self, 
                  source_storage: str, 
                  source_path: str,
                  target_storage: str,
                  target_path: str,
                  new_name: str = None) -> str:
        """移动文件"""
        task_id = self._generate_task_id()
        
        source_file = Path(source_path)
        target_name = new_name or source_file.name
        
        task = TransferTask(
            task_id=task_id,
            operation=FileOperation.MOVE,
            source_storage=source_storage,
            source_path=source_path,
            target_storage=target_storage,
            target_path=target_path,
            file_name=target_name
        )
        
        self._add_task(task)
        self._start_transfer_task(task)
        
        return task_id
    
    def upload_file(self, 
                    local_path: str,
                    target_storage: str,
                    target_path: str,
                    new_name: str = None) -> str:
        """上传文件"""
        task_id = self._generate_task_id()
        
        local_file = Path(local_path)
        target_name = new_name or local_file.name
        
        task = TransferTask(
            task_id=task_id,
            operation=FileOperation.UPLOAD,
            source_storage="local",
            source_path=local_path,
            target_storage=target_storage,
            target_path=target_path,
            file_name=target_name,
            size=local_file.stat().st_size
        )
        
        self._add_task(task)
        self._start_transfer_task(task)
        
        return task_id
    
    def download_file(self, 
                      source_storage: str,
                      source_path: str,
                      local_path: str,
                      new_name: str = None) -> str:
        """下载文件"""
        task_id = self._generate_task_id()
        
        source_file = Path(source_path)
        local_name = new_name or source_file.name
        local_target = Path(local_path) / local_name
        
        task = TransferTask(
            task_id=task_id,
            operation=FileOperation.DOWNLOAD,
            source_storage=source_storage,
            source_path=source_path,
            target_storage="local",
            target_path=str(local_target.parent),
            file_name=local_name
        )
        
        self._add_task(task)
        self._start_transfer_task(task)
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[TransferTask]:
        """获取任务状态"""
        with self.task_lock:
            return self.transfer_tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.task_lock:
            task = self.transfer_tasks.get(task_id)
            if task and task.status == TransferStatus.RUNNING:
                task.status = TransferStatus.CANCELLED
                task.end_time = time.time()
                return True
        return False
    
    def list_tasks(self) -> List[TransferTask]:
        """列出所有任务"""
        with self.task_lock:
            return list(self.transfer_tasks.values())
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        with self.task_lock:
            self.task_counter += 1
            return f"task_{self.task_counter}_{int(time.time())}"
    
    def _add_task(self, task: TransferTask):
        """添加任务"""
        with self.task_lock:
            self.transfer_tasks[task.task_id] = task
    
    def _start_transfer_task(self, task: TransferTask):
        """启动传输任务"""
        def _run_task():
            task.status = TransferStatus.RUNNING
            task.start_time = time.time()
            
            try:
                if task.operation == FileOperation.COPY:
                    self._execute_copy(task)
                elif task.operation == FileOperation.MOVE:
                    self._execute_move(task)
                elif task.operation == FileOperation.UPLOAD:
                    self._execute_upload(task)
                elif task.operation == FileOperation.DOWNLOAD:
                    self._execute_download(task)
                
                if task.status != TransferStatus.CANCELLED:
                    task.status = TransferStatus.COMPLETED
                    task.progress = 100
                
            except Exception as e:
                task.status = TransferStatus.FAILED
                task.error_message = str(e)
            
            task.end_time = time.time()
        
        # 在后台线程中执行任务
        thread = threading.Thread(target=_run_task)
        thread.daemon = True
        thread.start()
    
    def _execute_copy(self, task: TransferTask):
        """执行复制操作"""
        source_storage = self.get_storage(task.source_storage)
        target_storage = self.get_storage(task.target_storage)
        
        if not source_storage or not target_storage:
            raise Exception("存储不可用")
        
        # 获取源文件信息
        source_file = FileItem(
            name=Path(task.source_path).name,
            path=task.source_path,
            type="file",
            is_dir=False
        )
        
        # 创建目标目录
        target_folder = target_storage.get_folder(Path(task.target_path))
        if not target_folder:
            raise Exception("无法创建目标目录")
        
        # 执行复制
        if not source_storage.copy(source_file, Path(task.target_path), task.file_name):
            raise Exception("复制失败")
    
    def _execute_move(self, task: TransferTask):
        """执行移动操作"""
        source_storage = self.get_storage(task.source_storage)
        target_storage = self.get_storage(task.target_storage)
        
        if not source_storage or not target_storage:
            raise Exception("存储不可用")
        
        # 获取源文件信息
        source_file = FileItem(
            name=Path(task.source_path).name,
            path=task.source_path,
            type="file",
            is_dir=False
        )
        
        # 创建目标目录
        target_folder = target_storage.get_folder(Path(task.target_path))
        if not target_folder:
            raise Exception("无法创建目标目录")
        
        # 执行移动
        if not source_storage.move(source_file, Path(task.target_path), task.file_name):
            raise Exception("移动失败")
    
    def _execute_upload(self, task: TransferTask):
        """执行上传操作"""
        target_storage = self.get_storage(task.target_storage)
        
        if not target_storage:
            raise Exception("目标存储不可用")
        
        # 检查本地文件
        local_path = Path(task.source_path)
        if not local_path.exists():
            raise Exception("本地文件不存在")
        
        # 创建目标目录
        target_folder = target_storage.get_folder(Path(task.target_path))
        if not target_folder:
            raise Exception("无法创建目标目录")
        
        # 执行上传
        uploaded_file = target_storage.upload(target_folder, local_path, task.file_name)
        if not uploaded_file:
            raise Exception("上传失败")
    
    def _execute_download(self, task: TransferTask):
        """执行下载操作"""
        source_storage = self.get_storage(task.source_storage)
        
        if not source_storage:
            raise Exception("源存储不可用")
        
        # 检查目标目录
        local_dir = Path(task.target_path)
        if not local_dir.exists():
            local_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取源文件信息
        source_file = FileItem(
            name=Path(task.source_path).name,
            path=task.source_path,
            type="file",
            is_dir=False
        )
        
        # 执行下载
        local_path = source_storage.download(source_file, local_dir / task.file_name)
        if not local_path:
            raise Exception("下载失败")


class MediaClassifier:
    """媒体文件分类器"""
    
    def __init__(self):
        self.movie_patterns = [
            r'^.*\.(mp4|mkv|avi|mov|wmv|flv|webm|m4v)$',
            r'^.*[Ss]\d+[Ee]\d+.*$'
        ]
        self.tv_patterns = [
            r'^.*[Ss]\d+.*$',
            r'^.*\sSeason\s\d+.*$'
        ]
        self.anime_patterns = [
            r'^.*\[.*\].*$',
            r'^.*\d{2,4}.*$'
        ]
    
    def classify_file(self, file_name: str) -> str:
        """分类文件"""
        import re
        
        # 检查电影模式
        for pattern in self.movie_patterns:
            if re.match(pattern, file_name, re.IGNORECASE):
                return "movie"
        
        # 检查电视剧模式
        for pattern in self.tv_patterns:
            if re.match(pattern, file_name, re.IGNORECASE):
                return "tv"
        
        # 检查动漫模式
        for pattern in self.anime_patterns:
            if re.match(pattern, file_name, re.IGNORECASE):
                return "anime"
        
        return "other"
    
    def get_target_folder(self, file_name: str, base_path: str = "") -> str:
        """获取目标文件夹路径"""
        file_type = self.classify_file(file_name)
        
        if file_type == "movie":
            return f"{base_path}/电影".lstrip('/')
        elif file_type == "tv":
            return f"{base_path}/电视剧".lstrip('/')
        elif file_type == "anime":
            return f"{base_path}/动漫".lstrip('/')
        else:
            return f"{base_path}/其他".lstrip('/')