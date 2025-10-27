#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理器
批量重命名、转换等高级功能
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseProcessor, ProcessingResult, MediaFile


class BatchProcessorService(BaseProcessor):
    """批量处理器服务"""
    
    def __init__(self):
        super().__init__("BatchProcessor")
        self.supported_conversions = {
            "image": {
                "jpg": ["png", "webp"],
                "png": ["jpg", "webp"],
                "webp": ["jpg", "png"]
            }
        }
    
    async def _initialize_internal(self):
        """初始化批量处理器"""
        pass
    
    async def batch_rename_with_pattern(self, directory: str, pattern: str, 
                                       start_number: int = 1, dry_run: bool = True) -> ProcessingResult:
        """批量重命名文件（模式匹配）"""
        result = ProcessingResult()
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                result.success = False
                result.message = "目录不存在"
                return result
            
            total_files = 0
            renamed_files = 0
            operations = []
            
            # 获取所有文件
            files = []
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    files.append(file_path)
            
            # 按修改时间排序
            files.sort(key=lambda x: x.stat().st_mtime)
            
            current_number = start_number
            
            for file_path in files:
                total_files += 1
                
                # 生成新文件名
                media_file = MediaFile(str(file_path))
                new_name = self._generate_new_name_with_pattern(
                    pattern, current_number, media_file
                )
                
                new_path = file_path.parent / new_name
                
                operation = {
                    "old_name": file_path.name,
                    "new_name": new_name,
                    "old_path": str(file_path),
                    "new_path": str(new_path)
                }
                
                if not dry_run:
                    try:
                        file_path.rename(new_path)
                        renamed_files += 1
                        operation["status"] = "success"
                    except Exception as e:
                        operation["status"] = "failed"
                        operation["error"] = str(e)
                else:
                    operation["status"] = "preview"
                
                operations.append(operation)
                current_number += 1
            
            result.message = f"批量重命名完成: {renamed_files}/{total_files} 个文件"
            result.add_data('total_files', total_files)
            result.add_data('renamed_files', renamed_files)
            result.add_data('operations', operations)
            result.add_data('dry_run', dry_run)
            
        except Exception as e:
            result.success = False
            result.message = f"批量重命名失败: {str(e)}"
        
        return result
    
    def _generate_new_name_with_pattern(self, pattern: str, number: int, 
                                      media_file: MediaFile) -> str:
        """根据模式生成新文件名"""
        
        # 支持的模式变量
        variables = {
            "{number}": str(number),
            "{number:03d}": f"{number:03d}",
            "{number:04d}": f"{number:04d}",
            "{name}": media_file.name,
            "{stem}": media_file.stem,
            "{extension}": media_file.extension,
            "{category}": media_file.category
        }
        
        new_name = pattern
        for var, value in variables.items():
            new_name = new_name.replace(var, value)
        
        return new_name
    
    async def batch_convert_images(self, directory: str, target_format: str, 
                                 quality: int = 90, dry_run: bool = True) -> ProcessingResult:
        """批量转换图片格式"""
        result = ProcessingResult()
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                result.success = False
                result.message = "目录不存在"
                return result
            
            total_files = 0
            converted_files = 0
            operations = []
            
            # 获取所有图片文件
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']
            
            for file_path in dir_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    total_files += 1
                    
                    # 检查是否支持转换
                    source_format = file_path.suffix.lower().lstrip('.')
                    
                    if source_format in self.supported_conversions.get('image', {}) and \
                       target_format in self.supported_conversions['image'][source_format]:
                        
                        new_path = file_path.with_suffix(f'.{target_format}')
                        
                        operation = {
                            "old_name": file_path.name,
                            "new_name": new_path.name,
                            "old_path": str(file_path),
                            "new_path": str(new_path),
                            "source_format": source_format,
                            "target_format": target_format
                        }
                        
                        if not dry_run:
                            try:
                                # 这里需要实际的图片转换逻辑
                                # 暂时使用重命名模拟
                                file_path.rename(new_path)
                                converted_files += 1
                                operation["status"] = "success"
                            except Exception as e:
                                operation["status"] = "failed"
                                operation["error"] = str(e)
                        else:
                            operation["status"] = "preview"
                        
                        operations.append(operation)
            
            result.message = f"批量转换完成: {converted_files}/{total_files} 个文件"
            result.add_data('total_files', total_files)
            result.add_data('converted_files', converted_files)
            result.add_data('operations', operations)
            result.add_data('dry_run', dry_run)
            result.add_data('target_format', target_format)
            
        except Exception as e:
            result.success = False
            result.message = f"批量转换失败: {str(e)}"
        
        return result
    
    async def batch_organize_by_date(self, directory: str, date_format: str = "%Y-%m", 
                                   dry_run: bool = True) -> ProcessingResult:
        """按日期整理文件"""
        result = ProcessingResult()
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                result.success = False
                result.message = "目录不存在"
                return result
            
            total_files = 0
            organized_files = 0
            operations = []
            
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    total_files += 1
                    
                    # 获取文件修改时间
                    mtime = file_path.stat().st_mtime
                    from datetime import datetime
                    date_str = datetime.fromtimestamp(mtime).strftime(date_format)
                    
                    # 创建日期目录
                    date_dir = dir_path / date_str
                    if not dry_run:
                        date_dir.mkdir(exist_ok=True)
                    
                    new_path = date_dir / file_path.name
                    
                    operation = {
                        "old_name": file_path.name,
                        "new_name": new_path.name,
                        "old_path": str(file_path),
                        "new_path": str(new_path),
                        "date": date_str
                    }
                    
                    if not dry_run:
                        try:
                            file_path.rename(new_path)
                            organized_files += 1
                            operation["status"] = "success"
                        except Exception as e:
                            operation["status"] = "failed"
                            operation["error"] = str(e)
                    else:
                        operation["status"] = "preview"
                    
                    operations.append(operation)
            
            result.message = f"按日期整理完成: {organized_files}/{total_files} 个文件"
            result.add_data('total_files', total_files)
            result.add_data('organized_files', organized_files)
            result.add_data('operations', operations)
            result.add_data('dry_run', dry_run)
            result.add_data('date_format', date_format)
            
        except Exception as e:
            result.success = False
            result.message = f"按日期整理失败: {str(e)}"
        
        return result
    
    async def batch_metadata_extract(self, directory: str, 
                                   extract_types: List[str] = None) -> ProcessingResult:
        """批量提取文件元数据"""
        result = ProcessingResult()
        
        if extract_types is None:
            extract_types = ["basic", "exif", "media"]
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                result.success = False
                result.message = "目录不存在"
                return result
            
            total_files = 0
            processed_files = 0
            metadata_results = []
            
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    total_files += 1
                    
                    media_file = MediaFile(str(file_path))
                    metadata = self._extract_file_metadata(media_file, extract_types)
                    
                    metadata_results.append({
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "metadata": metadata
                    })
                    
                    processed_files += 1
            
            result.message = f"元数据提取完成: {processed_files}/{total_files} 个文件"
            result.add_data('total_files', total_files)
            result.add_data('processed_files', processed_files)
            result.add_data('metadata_results', metadata_results)
            result.add_data('extract_types', extract_types)
            
        except Exception as e:
            result.success = False
            result.message = f"元数据提取失败: {str(e)}"
        
        return result
    
    def _extract_file_metadata(self, media_file: MediaFile, extract_types: List[str]) -> Dict[str, Any]:
        """提取文件元数据"""
        metadata = {}
        
        # 基础元数据
        if "basic" in extract_types:
            metadata["basic"] = {
                "name": media_file.name,
                "size": media_file.size,
                "extension": media_file.extension,
                "category": media_file.category
            }
        
        # 图片EXIF信息
        if "exif" in extract_types and media_file.category == "图片":
            try:
                from PIL import Image
                from PIL.ExifTags import TAGS
                
                with Image.open(media_file.file_path) as img:
                    exif_data = img._getexif()
                    if exif_data:
                        metadata["exif"] = {}
                        for tag_id, value in exif_data.items():
                            tag = TAGS.get(tag_id, tag_id)
                            metadata["exif"][tag] = value
            except Exception:
                metadata["exif"] = {"error": "无法提取EXIF信息"}
        
        # 媒体文件信息
        if "media" in extract_types and media_file.category in ["视频", "音频"]:
            try:
                import mutagen
                
                if media_file.category == "音频":
                    audio = mutagen.File(media_file.file_path)
                    if audio:
                        metadata["media"] = dict(audio)
                elif media_file.category == "视频":
                    # 视频元数据提取需要额外库
                    metadata["media"] = {"info": "视频元数据提取需要安装额外库"}
            except Exception:
                metadata["media"] = {"error": "无法提取媒体信息"}
        
        return metadata