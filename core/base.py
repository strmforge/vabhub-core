#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 基础类定义
参照MoviePilot的架构理念
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
import logging

from .config import get_config


class BaseService(ABC):
    """基础服务类"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = self._setup_logger()
        self.config = get_config()
        self._initialized = False
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger(self.service_name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            await self._initialize_internal()
            self._initialized = True
            self.logger.info(f"{self.service_name} 服务初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"{self.service_name} 服务初始化失败: {e}")
            return False
    
    @abstractmethod
    async def _initialize_internal(self):
        """内部初始化逻辑"""
        pass
    
    def is_ready(self) -> bool:
        """检查服务是否就绪"""
        return self._initialized


class BaseProcessor(BaseService):
    """基础处理器类"""
    
    def __init__(self, processor_name: str):
        super().__init__(processor_name)
        self.progress_callbacks = []
    
    def add_progress_callback(self, callback):
        """添加进度回调"""
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self, progress: float, message: str = ""):
        """通知进度更新"""
        for callback in self.progress_callbacks:
            try:
                callback(progress, message)
            except Exception as e:
                self.logger.warning(f"进度回调执行失败: {e}")


class BaseManager(BaseService):
    """基础管理器类"""
    
    def __init__(self, manager_name: str):
        super().__init__(manager_name)
        self._services = {}
    
    def register_service(self, name: str, service: BaseService):
        """注册服务"""
        self._services[name] = service
    
    def get_service(self, name: str) -> Optional[BaseService]:
        """获取服务"""
        return self._services.get(name)
    
    async def initialize_all(self) -> bool:
        """初始化所有服务"""
        success = True
        for name, service in self._services.items():
            if not await service.initialize():
                self.logger.error(f"服务 {name} 初始化失败")
                success = False
        return success


class MediaFile:
    """媒体文件类"""
    
    def __init__(self, file_path: str):
        self.path = Path(file_path)
        self.name = self.path.name
        self.size = self.path.stat().st_size if self.path.exists() else 0
        self.extension = self.path.suffix.lower()
        self.category = self._determine_category()
        self.metadata = {}
    
    def _determine_category(self) -> str:
        """确定文件类别"""
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        if self.extension in video_extensions:
            return 'video'
        elif self.extension in audio_extensions:
            return 'audio'
        elif self.extension in image_extensions:
            return 'image'
        else:
            return 'other'
    
    def exists(self) -> bool:
        """检查文件是否存在"""
        return self.path.exists()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'path': str(self.path),
            'name': self.name,
            'size': self.size,
            'extension': self.extension,
            'category': self.category,
            'metadata': self.metadata
        }


class ProcessingResult:
    """处理结果类"""
    
    def __init__(self, success: bool = True, message: str = ""):
        self.success = success
        self.message = message
        self.data = {}
        self.timestamp = datetime.now()
    
    def add_data(self, key: str, value: Any):
        """添加数据"""
        self.data[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }


class BatchTask:
    """批量任务类"""
    
    def __init__(self, task_id: str, task_type: str):
        self.task_id = task_id
        self.task_type = task_type
        self.status = 'pending'  # pending, running, completed, failed
        self.progress = 0.0
        self.files = []
        self.results = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_file(self, file_path: str):
        """添加文件"""
        self.files.append(file_path)
    
    def update_progress(self, progress: float):
        """更新进度"""
        self.progress = progress
        self.updated_at = datetime.now()
    
    def add_result(self, result: ProcessingResult):
        """添加结果"""
        self.results.append(result)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'status': self.status,
            'progress': self.progress,
            'file_count': len(self.files),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }