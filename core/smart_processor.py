#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能媒体处理器
集成AI技术的智能媒体文件处理
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

from core.config import settings
from core.ai_processor import ai_processor
from utils.file_utils import safe_rename, scan_directory
from utils.metadata_utils import MetadataExtractor, TitleQuery


class SmartMediaProcessor:
    """智能媒体处理器"""
    
    def __init__(self):
        self.ai_processor = ai_processor
        self.metadata_extractor = MetadataExtractor()
        self.title_query = TitleQuery()
        self.processing_stats = {
            "total_files": 0,
            "processed_files": 0,
            "ai_analyzed": 0,
            "smart_renamed": 0,
            "errors": 0
        }
    
    async def smart_process_files(self, file_paths: List[str], use_ai: bool = True) -> List[Dict[str, Any]]:
        """智能处理文件"""
        self.processing_stats["total_files"] = len(file_paths)
        results = []
        
        for i, file_path in enumerate(file_paths):
            try:
                print(f"处理文件 {i+1}/{len(file_paths)}: {Path(file_path).name}")
                
                # 基础元数据提取
                metadata = self.metadata_extractor.extract_from_filename(file_path)
                
                # AI智能分析（如果启用）
                ai_analysis = None
                if use_ai:
                    ai_analysis = await self.ai_processor.analyze_video_content(file_path)
                    self.processing_stats["ai_analyzed"] += 1
                
                # 智能重命名
                result = await self._smart_rename_file(file_path, metadata, ai_analysis)
                
                if result["success"]:
                    self.processing_stats["smart_renamed"] += 1
                
                results.append(result)
                self.processing_stats["processed_files"] += 1
                
                # 显示进度
                progress = (i + 1) / len(file_paths) * 100
                print(f"进度: {progress:.1f}% - {result.get('message', '完成')}")
                
            except Exception as e:
                error_result = {
                    "file_path": file_path,
                    "success": False,
                    "error": str(e),
                    "message": f"处理失败: {e}"
                }
                results.append(error_result)
                self.processing_stats["errors"] += 1
                print(f"处理失败: {file_path} - {e}")
        
        return results
    
    async def _smart_rename_file(self, file_path: str, metadata: Dict[str, Any], 
                                ai_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """智能重命名文件"""
        try:
            # 确定目标路径
            target_path = await self._determine_smart_target_path(file_path, metadata, ai_analysis)
            
            # 如果目标路径与原始路径相同，跳过重命名
            if file_path == target_path:
                return {
                    "file_path": file_path,
                    "success": True,
                    "message": "文件无需重命名",
                    "original_name": Path(file_path).name,
                    "new_name": Path(file_path).name,
                    "metadata": metadata,
                    "ai_analysis": ai_analysis
                }
            
            # 执行重命名
            new_path = safe_rename(file_path, target_path)
            
            return {
                "file_path": file_path,
                "success": True,
                "message": "智能重命名成功",
                "original_name": Path(file_path).name,
                "new_name": Path(new_path).name,
                "new_path": new_path,
                "metadata": metadata,
                "ai_analysis": ai_analysis
            }
            
        except Exception as e:
            return {
                "file_path": file_path,
                "success": False,
                "error": str(e),
                "message": f"智能重命名失败: {e}",
                "metadata": metadata,
                "ai_analysis": ai_analysis
            }
    
    async def _determine_smart_target_path(self, file_path: str, metadata: Dict[str, Any], 
                                          ai_analysis: Optional[Dict[str, Any]]) -> str:
        """确定智能目标路径"""
        file_name = Path(file_path).name
        file_ext = Path(file_path).suffix
        
        # 获取中文标题
        chinese_title = self.title_query.get_chinese_title(file_path, metadata)
        
        # 使用AI分析结果（如果可用）
        if ai_analysis and ai_analysis.get("ai_confidence", 0) > 0.5:
            media_type = ai_analysis.get("media_type", "unknown")
            categories = ai_analysis.get("content_categories", ["general"])
            quality = ai_analysis.get("quality_assessment", {})
        else:
            # 使用传统方法
            media_type = metadata.get("type", "movie")
            categories = ["general"]
            quality = {"resolution": metadata.get("quality", "Unknown")}
        
        # 确定基础目录
        if media_type == "movie" or media_type == "unknown":
            base_dir = settings.movie_output_path
        elif media_type == "tv_series":
            base_dir = settings.tv_output_path
        else:
            base_dir = settings.scan_path  # 默认使用扫描路径
        
        # 生成智能文件名
        if ai_analysis and ai_analysis.get("ai_confidence", 0) > 0.7:
            # 使用AI生成的智能文件名
            smart_name = await self.ai_processor.generate_smart_filename(ai_analysis)
            new_file_name = smart_name
        else:
            # 使用传统命名规则
            new_file_name = self._generate_traditional_filename(chinese_title, metadata, media_type)
        
        # 构建完整路径
        target_dir = os.path.join(base_dir, self._get_category_subdir(categories, media_type))
        os.makedirs(target_dir, exist_ok=True)
        
        return os.path.join(target_dir, new_file_name)
    
    def _generate_traditional_filename(self, chinese_title: str, metadata: Dict[str, Any], 
                                     media_type: str) -> str:
        """生成传统文件名"""
        year = metadata.get("year", "")
        quality = metadata.get("quality", "Unknown")
        
        if media_type == "movie":
            if year:
                return f"{chinese_title} ({year}) [{quality}].mp4"
            else:
                return f"{chinese_title} [{quality}].mp4"
        elif media_type == "tv_series":
            season = metadata.get("season", 1)
            episode = metadata.get("episode", 1)
            return f"{chinese_title} S{season:02d}E{episode:02d} [{quality}].mp4"
        else:
            return f"{chinese_title} [{quality}].mp4"
    
    def _get_category_subdir(self, categories: List[str], media_type: str) -> str:
        """获取分类子目录"""
        if not categories or categories == ["general"]:
            return ""
        
        # 使用主要分类作为子目录
        primary_category = categories[0]
        
        # 分类目录映射
        category_mapping = {
            "action": "动作",
            "comedy": "喜剧", 
            "drama": "剧情",
            "sci-fi": "科幻",
            "horror": "恐怖",
            "romance": "爱情",
            "adventure": "冒险",
            "fantasy": "奇幻",
            "crime": "犯罪",
            "thriller": "惊悚",
            "documentary": "纪录片",
            "animation": "动画"
        }
        
        return category_mapping.get(primary_category, primary_category)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        return {
            "total_files": self.processing_stats["total_files"],
            "processed_files": self.processing_stats["processed_files"],
            "ai_analyzed": self.processing_stats["ai_analyzed"],
            "smart_renamed": self.processing_stats["smart_renamed"],
            "errors": self.processing_stats["errors"],
            "success_rate": (self.processing_stats["processed_files"] - self.processing_stats["errors"]) / max(1, self.processing_stats["processed_files"])
        }
    
    def reset_stats(self):
        """重置统计"""
        self.processing_stats = {
            "total_files": 0,
            "processed_files": 0,
            "ai_analyzed": 0,
            "smart_renamed": 0,
            "errors": 0
        }


# 全局智能处理器实例
smart_processor = SmartMediaProcessor()