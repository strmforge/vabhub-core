#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化后的媒体处理器
现代化异步媒体文件处理核心模块
"""

import os
import time
import asyncio
from typing import List, Dict, Any, Optional, Protocol, TypedDict
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor

from core.config import settings
from utils.file_utils import scan_directory, safe_rename
from utils.metadata_utils import MetadataExtractor, TitleQuery


# 类型定义
class ProcessingStrategy(Enum):
    AUTO = "auto"
    SKIP = "skip"
    REPLACE = "replace"
    KEEP_BOTH = "keep_both"


class MediaType(Enum):
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    MUSIC = "music"
    EBOOK = "ebook"
    OTHER = "other"


class ProcessResult(TypedDict):
    file: str
    success: bool
    new_path: Optional[str]
    metadata: Optional[Dict[str, Any]]
    chinese_title: Optional[str]
    error: Optional[str]
    processing_time: float


@dataclass
class ProcessingStats:
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def processing_time(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return 0.0
    
    @property
    def files_per_second(self) -> float:
        if self.processing_time > 0:
            return self.processed_files / self.processing_time
        return 0.0
    
    @property
    def success_rate(self) -> float:
        if self.processed_files > 0:
            return self.successful_files / self.processed_files
        return 0.0


class MediaProcessorInterface(Protocol):
    """媒体处理器接口"""
    
    async def process_file(self, file_path: str, strategy: ProcessingStrategy) -> ProcessResult:
        """处理单个文件"""
        ...
    
    async def process_batch(self, files: List[str], strategy: ProcessingStrategy) -> List[ProcessResult]:
        """批量处理文件"""
        ...


class OptimizedMediaProcessor:
    """优化后的媒体处理器"""
    
    def __init__(self, max_workers: int = 4, max_concurrent: int = 10):
        self.max_workers = max_workers
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        self.stats = ProcessingStats()
        self.is_processing = False
        
        # 初始化组件
        self.metadata_extractor = MetadataExtractor()
        self.title_query = TitleQuery()
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    async def cleanup(self):
        """清理资源"""
        if self.executor:
            self.executor.shutdown(wait=True)
    
    def get_status(self) -> Dict[str, Any]:
        """获取处理状态"""
        return {
            "is_processing": self.is_processing,
            "stats": {
                "total_files": self.stats.total_files,
                "processed_files": self.stats.processed_files,
                "successful_files": self.stats.successful_files,
                "failed_files": self.stats.failed_files,
                "processing_time": self.stats.processing_time,
                "files_per_second": self.stats.files_per_second,
                "success_rate": self.stats.success_rate
            }
        }
    
    async def scan_files_async(self, scan_path: Optional[str] = None) -> List[str]:
        """异步扫描文件"""
        scan_path = scan_path or settings.scan_path
        
        if not scan_path or not os.path.exists(scan_path):
            raise ValueError(f"扫描路径不存在: {scan_path}")
        
        self.logger.info(f"开始扫描文件: {scan_path}")
        
        # 在线程池中执行扫描
        loop = asyncio.get_event_loop()
        files = await loop.run_in_executor(
            self.executor, 
            scan_directory, 
            scan_path
        )
        
        self.logger.info(f"扫描完成，找到 {len(files)} 个文件")
        return files
    
    async def process_file(self, file_path: str, strategy: ProcessingStrategy = ProcessingStrategy.AUTO) -> ProcessResult:
        """异步处理单个文件"""
        start_time = time.time()
        
        async with self.semaphore:
            try:
                # 检查文件是否存在
                if not os.path.exists(file_path):
                    return ProcessResult(
                        file=file_path,
                        success=False,
                        new_path=None,
                        metadata=None,
                        chinese_title=None,
                        error="文件不存在",
                        processing_time=time.time() - start_time
                    )
                
                # 在线程池中执行CPU密集型操作
                loop = asyncio.get_event_loop()
                
                # 提取元数据
                metadata = await loop.run_in_executor(
                    self.executor,
                    self.metadata_extractor.extract_from_filename,
                    file_path
                )
                
                # 获取中文标题
                chinese_title = await loop.run_in_executor(
                    self.executor,
                    self.title_query.get_chinese_title,
                    file_path,
                    metadata
                )
                
                # 确定目标路径
                target_path = await self._determine_target_path_async(file_path, metadata, chinese_title)
                
                # 处理文件冲突
                if os.path.exists(target_path):
                    target_path = await self._handle_conflict_async(file_path, target_path, strategy)
                
                # 重命名文件
                if file_path != target_path:
                    await loop.run_in_executor(
                        self.executor,
                        safe_rename,
                        file_path,
                        target_path
                    )
                    
                    return ProcessResult(
                        file=file_path,
                        success=True,
                        new_path=target_path,
                        metadata=metadata,
                        chinese_title=chinese_title,
                        error=None,
                        processing_time=time.time() - start_time
                    )
                else:
                    return ProcessResult(
                        file=file_path,
                        success=True,
                        new_path=None,
                        metadata=metadata,
                        chinese_title=chinese_title,
                        error="文件无需重命名",
                        processing_time=time.time() - start_time
                    )
                    
            except Exception as e:
                self.logger.error(f"处理文件失败 {file_path}: {str(e)}")
                return ProcessResult(
                    file=file_path,
                    success=False,
                    new_path=None,
                    metadata=None,
                    chinese_title=None,
                    error=str(e),
                    processing_time=time.time() - start_time
                )
    
    async def process_batch(self, files: List[str], strategy: ProcessingStrategy = ProcessingStrategy.AUTO) -> List[ProcessResult]:
        """异步批量处理文件"""
        if self.is_processing:
            raise RuntimeError("已有处理任务正在进行中")
        
        self.is_processing = True
        self.stats = ProcessingStats(
            total_files=len(files),
            start_time=time.time()
        )
        
        try:
            self.logger.info(f"开始批量处理 {len(files)} 个文件")
            
            # 创建处理任务
            tasks = [self.process_file(file_path, strategy) for file_path in files]
            
            # 执行批量处理，使用进度回调
            results = []
            for i, task in enumerate(asyncio.as_completed(tasks)):
                result = await task
                results.append(result)
                
                # 更新统计信息
                self.stats.processed_files += 1
                if result['success']:
                    self.stats.successful_files += 1
                else:
                    self.stats.failed_files += 1
                
                # 打印进度
                if (i + 1) % 10 == 0 or (i + 1) == len(files):
                    progress = (i + 1) / len(files) * 100
                    self.logger.info(
                        f"处理进度: {i + 1}/{len(files)} ({progress:.1f}%) "
                        f"成功率: {self.stats.success_rate:.1%}"
                    )
            
            # 按原始顺序排序结果
            file_to_result = {result['file']: result for result in results}
            ordered_results = [file_to_result[file_path] for file_path in files]
            
            self.stats.end_time = time.time()
            self.logger.info(
                f"批量处理完成: {self.stats.successful_files}/{self.stats.total_files} 成功, "
                f"耗时: {self.stats.processing_time:.2f}秒, "
                f"速度: {self.stats.files_per_second:.2f} 文件/秒"
            )
            
            return ordered_results
            
        finally:
            self.is_processing = False
    
    async def _determine_target_path_async(self, file_path: str, metadata: Dict[str, Any], chinese_title: str) -> str:
        """异步确定目标路径"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._determine_target_path_sync,
            file_path,
            metadata,
            chinese_title
        )
    
    def _determine_target_path_sync(self, file_path: str, metadata: Dict[str, Any], chinese_title: str) -> str:
        """同步确定目标路径"""
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1]
        
        # 根据元数据确定媒体类型和路径
        media_type = MediaType(metadata.get("type", "other"))
        
        if media_type == MediaType.MOVIE:
            base_dir = settings.movie_output_path
            year = metadata.get('year', '')
            new_name = f"{chinese_title} ({year})" if year else chinese_title
            target_dir = os.path.join(base_dir, new_name)
            target_file = f"{new_name}{file_ext}"
        elif media_type == MediaType.TV_SHOW:
            base_dir = settings.tv_output_path
            season = metadata.get("season", 1)
            episode = metadata.get("episode", 1)
            season_dir = f"Season {season:02d}"
            target_dir = os.path.join(base_dir, chinese_title, season_dir)
            target_file = f"{chinese_title} S{season:02d}E{episode:02d}{file_ext}"
        else:
            # 其他类型文件保持原有结构
            return file_path
        
        # 确保目录存在
        os.makedirs(target_dir, exist_ok=True)
        
        return os.path.join(target_dir, target_file)
    
    async def _handle_conflict_async(self, file_path: str, target_path: str, strategy: ProcessingStrategy) -> str:
        """异步处理文件冲突"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._handle_conflict_sync,
            file_path,
            target_path,
            strategy
        )
    
    def _handle_conflict_sync(self, file_path: str, target_path: str, strategy: ProcessingStrategy) -> str:
        """同步处理文件冲突"""
        if strategy == ProcessingStrategy.SKIP:
            return file_path  # 不重命名
        elif strategy == ProcessingStrategy.REPLACE:
            if os.path.exists(target_path):
                os.remove(target_path)
            return target_path
        elif strategy == ProcessingStrategy.KEEP_BOTH:
            base, ext = os.path.splitext(target_path)
            counter = 1
            while os.path.exists(target_path):
                target_path = f"{base}_{counter}{ext}"
                counter += 1
            return target_path
        else:  # AUTO
            if os.path.exists(target_path):
                current_size = os.path.getsize(file_path)
                existing_size = os.path.getsize(target_path)
                
                if current_size > existing_size:
                    os.remove(target_path)
                    return target_path
                else:
                    return file_path
            return target_path


# 工厂函数
def create_optimized_processor(max_workers: int = 4, max_concurrent: int = 10) -> OptimizedMediaProcessor:
    """创建优化的媒体处理器实例"""
    return OptimizedMediaProcessor(max_workers=max_workers, max_concurrent=max_concurrent)


# 全局优化处理器实例
optimized_processor = create_optimized_processor()
