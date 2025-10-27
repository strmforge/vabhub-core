#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体处理器
现代化媒体文件处理核心模块
"""

import os
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio

from core.config import settings
from utils.file_utils import scan_directory, safe_rename
from utils.metadata_utils import MetadataExtractor, TitleQuery


class MediaProcessor:
    """媒体处理器"""
    
    def __init__(self):
        self.is_processing = False
        self.processed_files = 0
        self.total_files = 0
        self.start_time = None
        self.metadata_extractor = MetadataExtractor()
        self.title_query = TitleQuery()

    def get_status(self) -> Dict[str, Any]:
        """获取处理状态"""
        return {
            "is_processing": self.is_processing,
            "processed_files": self.processed_files,
            "total_files": self.total_files,
            "start_time": self.start_time,
            "elapsed_time": time.time() - self.start_time if self.start_time else 0
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取处理指标"""
        return {
            "processed_files": self.processed_files,
            "total_files": self.total_files,
            "processing_time": time.time() - self.start_time if self.start_time else 0,
            "files_per_second": self.processed_files / (time.time() - self.start_time) if self.start_time and self.processed_files > 0 else 0
        }
    
    def scan_files(self, scan_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """扫描文件"""
        scan_path = scan_path or settings.scan_path
        
        if not scan_path or not os.path.exists(scan_path):
            raise ValueError(f"扫描路径不存在: {scan_path}")
        
        print(f"开始扫描文件: {scan_path}")
        
        # 扫描目录
        files = scan_directory(scan_path)
        
        print(f"扫描完成，找到 {len(files)} 个文件")
        return files

    def process_files(self, files: List[str], strategy: str = "auto") -> List[Dict[str, Any]]:
        """处理文件"""
        if self.is_processing:
            raise RuntimeError("已有处理任务正在进行中")
        
        self.is_processing = True
        self.start_time = time.time()
        self.processed_files = 0
        self.total_files = len(files)
        
        results = []
        
        try:
            for i, file_path in enumerate(files):
                if not os.path.exists(file_path):
                    results.append({
                        "file": file_path,
                        "success": False,
                        "error": "文件不存在"
                    })
                    continue
                
                try:
                    # 提取元数据
                    metadata = self.metadata_extractor.extract_from_filename(file_path)
                    
                    # 获取中文标题
                    chinese_title = self.title_query.get_chinese_title(file_path, metadata)
                    
                    # 确定目标路径
                    target_path = self._determine_target_path(file_path, metadata, chinese_title)
                    
                    # 处理文件冲突
                    if os.path.exists(target_path):
                        target_path = self._handle_conflict(file_path, target_path, strategy)
                    
                    # 重命名文件
                    if file_path != target_path:
                        safe_rename(file_path, target_path)
                        
                        results.append({
                            "file": file_path,
                            "success": True,
                            "new_path": target_path,
                            "metadata": metadata,
                            "chinese_title": chinese_title
                        })
                    else:
                        results.append({
                            "file": file_path,
                            "success": True,
                            "message": "文件无需重命名",
                            "metadata": metadata
                        })
                    
                    self.processed_files += 1
                    
                    # 打印进度
                    if (i + 1) % 10 == 0:
                        progress = (i + 1) / len(files) * 100
                        print(f"处理进度: {i + 1}/{len(files)} ({progress:.1f}%)")
                        
                except Exception as e:
                    results.append({
                        "file": file_path,
                        "success": False,
                        "error": str(e)
                    })
            
            print(f"文件处理完成: {self.processed_files}/{self.total_files} 成功")
            
        finally:
            self.is_processing = False
        
        return results

    def _determine_target_path(self, file_path: str, metadata: Dict[str, Any], chinese_title: str) -> str:
        """确定目标路径"""
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1]
        
        # 根据元数据确定是电影还是电视剧
        if metadata.get("type") == "movie":
            base_dir = settings.movie_output_path
            # 电影命名格式: 中文标题 (年份)/中文标题 (年份).扩展名
            new_name = f"{chinese_title} ({metadata.get('year', '')})"
        else:
            base_dir = settings.tv_output_path
            # 电视剧命名格式: 中文标题/Season 剧季/中文标题 SxxExx.扩展名
            season = metadata.get("season", 1)
            episode = metadata.get("episode", 1)
            new_name = f"{chinese_title}/Season {season:02d}/{chinese_title} S{season:02d}E{episode:02d}"
        
        # 确保目录存在
        target_dir = os.path.join(base_dir, os.path.dirname(new_name))
        os.makedirs(target_dir, exist_ok=True)
        
        return os.path.join(target_dir, os.path.basename(new_name) + file_ext)

    def _handle_conflict(self, file_path: str, target_path: str, strategy: str) -> str:
        """处理文件冲突"""
        if strategy == "skip":
            # 跳过已存在文件
            return file_path  # 不重命名
        elif strategy == "replace":
            # 替换已存在文件
            if os.path.exists(target_path):
                os.remove(target_path)
            return target_path
        elif strategy == "keep_both":
            # 保留两个文件
            base, ext = os.path.splitext(target_path)
            counter = 1
            while os.path.exists(target_path):
                target_path = f"{base}_{counter}{ext}"
                counter += 1
            return target_path
        else:  # auto
            # 自动处理：比较文件大小，保留较大的文件
            if os.path.exists(target_path):
                current_size = os.path.getsize(file_path)
                existing_size = os.path.getsize(target_path)
                
                if current_size > existing_size:
                    # 当前文件更大，替换
                    os.remove(target_path)
                    return target_path
                else:
                    # 已存在文件更大，跳过
                    return file_path
            return target_path


# 全局处理器实例
processor = MediaProcessor()