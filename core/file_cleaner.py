#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件清理服务
清理临时文件、空目录等
"""

import os
import fnmatch
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseProcessor, ProcessingResult


class FileCleanerService(BaseProcessor):
    """文件清理服务"""
    
    def __init__(self):
        super().__init__("FileCleaner")
        self.temp_patterns = [
            "*.tmp", "*.temp", "*.bak", "*.log", "~*", "._*",
            "Thumbs.db", ".DS_Store", "desktop.ini"
        ]
    
    async def _initialize_internal(self):
        """初始化清理服务"""
        pass
    
    async def clean_directory(self, directory: str, dry_run: bool = True) -> ProcessingResult:
        """清理目录"""
        result = ProcessingResult()
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                result.success = False
                result.message = "目录不存在"
                return result
            
            cleaned_files = 0
            cleaned_dirs = 0
            total_size = 0
            files_removed = []
            dirs_removed = []
            
            # 清理临时文件
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    if self._is_temp_file(file_path.name):
                        file_size = file_path.stat().st_size
                        
                        if not dry_run:
                            try:
                                file_path.unlink()
                                cleaned_files += 1
                                total_size += file_size
                                files_removed.append(str(file_path))
                            except Exception:
                                pass  # 忽略删除失败的文件
                        else:
                            cleaned_files += 1
                            total_size += file_size
                            files_removed.append(str(file_path))
            
            # 清理空目录（从底层开始）
            if not dry_run:
                for dir_path in sorted(dir_path.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                    if dir_path.is_dir():
                        try:
                            if not any(dir_path.iterdir()):  # 空目录
                                dir_path.rmdir()
                                cleaned_dirs += 1
                                dirs_removed.append(str(dir_path))
                        except Exception:
                            pass  # 忽略删除失败的目录
            
            result.message = f"清理完成: {cleaned_files} 个文件, {cleaned_dirs} 个目录"
            result.add_data('cleaned_files', cleaned_files)
            result.add_data('cleaned_dirs', cleaned_dirs)
            result.add_data('total_size', total_size)
            result.add_data('files_removed', files_removed)
            result.add_data('dirs_removed', dirs_removed)
            result.add_data('dry_run', dry_run)
            
        except Exception as e:
            result.success = False
            result.message = f"目录清理失败: {str(e)}"
        
        return result
    
    def _is_temp_file(self, filename: str) -> bool:
        """检查是否为临时文件"""
        for pattern in self.temp_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False
    
    async def clean_by_size(self, directory: str, max_size_mb: int = 10, 
                           dry_run: bool = True) -> ProcessingResult:
        """按大小清理文件"""
        result = ProcessingResult()
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                result.success = False
                result.message = "目录不存在"
                return result
            
            max_size_bytes = max_size_mb * 1024 * 1024
            cleaned_files = 0
            total_size = 0
            files_removed = []
            
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    
                    if file_size > max_size_bytes:
                        if not dry_run:
                            try:
                                file_path.unlink()
                                cleaned_files += 1
                                total_size += file_size
                                files_removed.append(str(file_path))
                            except Exception:
                                pass
                        else:
                            cleaned_files += 1
                            total_size += file_size
                            files_removed.append(str(file_path))
            
            result.message = f"按大小清理完成: {cleaned_files} 个文件"
            result.add_data('cleaned_files', cleaned_files)
            result.add_data('total_size', total_size)
            result.add_data('files_removed', files_removed)
            result.add_data('dry_run', dry_run)
            result.add_data('max_size_mb', max_size_mb)
            
        except Exception as e:
            result.success = False
            result.message = f"按大小清理失败: {str(e)}"
        
        return result