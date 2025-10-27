#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 核心服务模块
统一的服务架构设计
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import shutil

from .base import BaseService, BaseProcessor, MediaFile, ProcessingResult, BatchTask
from .config import get_config
from .file_cleaner import FileCleanerService
from .batch_processor import BatchProcessorService


class FileOrganizerService(BaseProcessor):
    """文件整理服务"""
    
    def __init__(self):
        super().__init__("FileOrganizer")
        self.config = get_config()
    
    async def _initialize_internal(self):
        """初始化文件整理服务"""
        # 创建必要的目录
        upload_dir = Path(self.config.media.upload_dir)
        upload_dir.mkdir(exist_ok=True)
        
        media_library = Path(self.config.media.media_library)
        media_library.mkdir(exist_ok=True)
        
        temp_dir = Path(self.config.media.temp_dir)
        temp_dir.mkdir(exist_ok=True)
    
    async def organize_files(self, source_dir: str, target_dir: str, 
                           move_files: bool = False) -> ProcessingResult:
        """整理文件"""
        result = ProcessingResult()
        
        try:
            source_path = Path(source_dir)
            target_path = Path(target_dir)
            
            if not source_path.exists():
                result.success = False
                result.message = "源目录不存在"
                return result
            
            # 创建目标目录
            target_path.mkdir(exist_ok=True)
            
            organized_files = 0
            total_files = 0
            
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    total_files += 1
                    
                    # 确定文件类别
                    media_file = MediaFile(str(file_path))
                    category_dir = target_path / media_file.category
                    category_dir.mkdir(exist_ok=True)
                    
                    # 移动或复制文件
                    target_file = category_dir / file_path.name
                    
                    if move_files:
                        shutil.move(str(file_path), str(target_file))
                    else:
                        shutil.copy2(str(file_path), str(target_file))
                    
                    organized_files += 1
                    
                    # 更新进度
                    progress = (organized_files / total_files) * 100 if total_files > 0 else 0
                    self._notify_progress(progress, f"正在整理: {file_path.name}")
            
            result.message = f"成功整理 {organized_files}/{total_files} 个文件"
            result.add_data('organized_files', organized_files)
            result.add_data('total_files', total_files)
            
        except Exception as e:
            result.success = False
            result.message = f"文件整理失败: {str(e)}"
        
        return result


class DuplicateFinderService(BaseProcessor):
    """重复文件检测服务"""
    
    def __init__(self):
        super().__init__("DuplicateFinder")
        self.hash_cache = {}
    
    async def _initialize_internal(self):
        """初始化重复检测服务"""
        pass
    
    async def find_duplicates(self, directory: str, method: str = "hash") -> ProcessingResult:
        """查找重复文件"""
        result = ProcessingResult()
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                result.success = False
                result.message = "目录不存在"
                return result
            
            file_groups = {}
            total_files = 0
            
            for file_path in dir_path.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    total_files += 1
                    
                    if method == "size_name":
                        key = f"{file_path.name}_{file_path.stat().st_size}"
                    else:
                        key = self._calculate_file_hash(file_path)
                    
                    if key in file_groups:
                        file_groups[key].append(str(file_path))
                    else:
                        file_groups[key] = [str(file_path)]
            
            # 找出重复文件组
            duplicate_groups = []
            for key, files in file_groups.items():
                if len(files) > 1:
                    duplicate_groups.append({
                        'key': key,
                        'files': files,
                        'count': len(files)
                    })
            
            result.message = f"发现 {len(duplicate_groups)} 组重复文件"
            result.add_data('duplicate_groups', duplicate_groups)
            result.add_data('total_files', total_files)
            
        except Exception as e:
            result.success = False
            result.message = f"重复文件检测失败: {str(e)}"
        
        return result
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        import hashlib
        
        if str(file_path) in self.hash_cache:
            return self.hash_cache[str(file_path)]
        
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            # 只读取文件的部分内容来加速
            file_size = file_path.stat().st_size
            chunk_size = 8192
            
            if file_size <= chunk_size * 2:
                hasher.update(f.read())
            else:
                f.seek(0)
                hasher.update(f.read(chunk_size))
                f.seek(-chunk_size, 2)
                hasher.update(f.read(chunk_size))
        
        hash_value = hasher.hexdigest()
        self.hash_cache[str(file_path)] = hash_value
        return hash_value


class SmartRenameService(BaseProcessor):
    """智能重命名服务"""
    
    def __init__(self):
        super().__init__("SmartRename")
        self.config = get_config()
    
    async def _initialize_internal(self):
        """初始化重命名服务"""
        pass
    
    async def rename_file(self, file_path: str, strategy: str = None) -> ProcessingResult:
        """重命名单个文件"""
        result = ProcessingResult()
        
        try:
            if strategy is None:
                strategy = self.config.rename.strategy
            
            media_file = MediaFile(file_path)
            new_name = self._generate_new_name(media_file, strategy)
            
            # 执行重命名
            new_path = Path(file_path).parent / new_name
            Path(file_path).rename(new_path)
            
            result.message = f"重命名成功: {Path(file_path).name} -> {new_name}"
            result.add_data('old_name', Path(file_path).name)
            result.add_data('new_name', new_name)
            result.add_data('strategy', strategy)
            
        except Exception as e:
            result.success = False
            result.message = f"重命名失败: {str(e)}"
        
        return result
    
    def _generate_new_name(self, media_file: MediaFile, strategy: str) -> str:
        """生成新文件名"""
        import re
        
        # 提取元数据
        metadata = self._extract_metadata(media_file.name)
        
        if strategy == "moviepilot":
            if metadata.get('media_type') == 'movie':
                return f"{metadata['title']} ({metadata.get('year', '')})/{metadata['title']} ({metadata.get('year', '')}) [{metadata.get('quality', '')}]"
            else:
                return f"{metadata['title']}/Season {metadata.get('season', 1):02d}/{metadata['title']} S{metadata.get('season', 1):02d}E{metadata.get('episode', 1):02d} [{metadata.get('quality', '')}]"
        else:
            # 标准重命名策略
            return metadata['title'] + media_file.extension
    
    def _extract_metadata(self, filename: str) -> Dict[str, Any]:
        """提取文件元数据"""
        import re
        
        metadata = {
            'original_name': filename,
            'title': Path(filename).stem,
            'media_type': 'unknown'
        }
        
        # 电影模式识别
        movie_patterns = [
            r'(.*?)[\.\s]\((\d{4})\)',  # 电影名 (年份)
            r'(.*?)[\.\s](\d{4})',       # 电影名 年份
        ]
        
        # 电视剧模式识别
        tv_patterns = [
            r'(.*?)[\.\s][Ss](\d{1,2})[Ee](\d{1,2})',  # 剧集 S01E01
            r'(.*?)[\.\s](\d{1,2})x(\d{1,2})',         # 剧集 1x01
        ]
        
        for pattern in movie_patterns:
            match = re.search(pattern, filename)
            if match:
                metadata['media_type'] = 'movie'
                metadata['title'] = match.group(1).replace('.', ' ').strip()
                if len(match.groups()) > 1:
                    metadata['year'] = match.group(2)
                break
        
        for pattern in tv_patterns:
            match = re.search(pattern, filename)
            if match:
                metadata['media_type'] = 'tv_show'
                metadata['title'] = match.group(1).replace('.', ' ').strip()
                if len(match.groups()) > 1:
                    metadata['season'] = int(match.group(2))
                if len(match.groups()) > 2:
                    metadata['episode'] = int(match.group(3))
                break
        
        # 检测质量信息
        qualities = ['BluRay', 'WEB-DL', 'HDTV', 'DVD', 'CAM']
        for quality in qualities:
            if quality.lower() in filename.lower():
                metadata['quality'] = quality
                break
        
        return metadata


class ServiceManager(BaseManager):
    """服务管理器"""
    
    def __init__(self):
        super().__init__("ServiceManager")
        
        # 注册所有服务
        self.file_organizer = FileOrganizerService()
        self.duplicate_finder = DuplicateFinderService()
        self.smart_renamer = SmartRenameService()
        self.file_cleaner = FileCleanerService()
        self.batch_processor = BatchProcessorService()
        
        self.register_service("file_organizer", self.file_organizer)
        self.register_service("duplicate_finder", self.duplicate_finder)
        self.register_service("smart_renamer", self.smart_renamer)
        self.register_service("file_cleaner", self.file_cleaner)
        self.register_service("batch_processor", self.batch_processor)
    
    async def _initialize_internal(self):
        """初始化所有服务"""
        await self.initialize_all()
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = {}
        for name, service in self._services.items():
            status[name] = {
                'ready': service.is_ready(),
                'name': service.service_name
            }
        return status


# 全局服务管理器实例
service_manager = ServiceManager()