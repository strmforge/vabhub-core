#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元数据工具模块
提供媒体文件元数据提取和查询功能
"""

import os
import re
import json
from functools import lru_cache
from typing import Dict, Any, Optional

from core.config import settings


class MetadataExtractor:
    """元数据提取器"""
    
    @staticmethod
    def extract_from_filename(filename):
        """从文件名提取基本信息"""
        # 移除扩展名
        name = os.path.splitext(os.path.basename(filename))[0]
        
        # 常见媒体文件命名模式
        patterns = [
            # 电影模式: 电影名 (年份) [质量]
            r'^(.*?)\s*\((\d{4})\)\s*(?:\[(.*?)\])?$',
            # 电视剧模式: 剧名 S01E01 或 剧名 第01集
            r'^(.*?)\s*[Ss](\d{1,2})[Ee](\d{1,2})',
            r'^(.*?)\s*第(\d{1,3})集',
            # 简单模式: 直接使用文件名
            r'^(.*?)$'
        ]
        
        metadata = {
            "original_name": name,
            "title": name,
            "year": None,
            "season": None,
            "episode": None,
            "quality": "Unknown",
            "type": "movie"  # 默认为电影
        }
        
        for pattern in patterns:
            match = re.match(pattern, name)
            if match:
                if pattern == patterns[0]:  # 电影模式
                    metadata["title"] = match.group(1).strip()
                    metadata["year"] = int(match.group(2))
                    if match.group(3):
                        metadata["quality"] = match.group(3)
                elif pattern == patterns[1]:  # 电视剧模式 S01E01
                    metadata["title"] = match.group(1).strip()
                    metadata["season"] = int(match.group(2))
                    metadata["episode"] = int(match.group(3))
                    metadata["type"] = "tv"
                elif pattern == patterns[2]:  # 电视剧模式 第01集
                    metadata["title"] = match.group(1).strip()
                    metadata["episode"] = int(match.group(2))
                    metadata["type"] = "tv"
                break
        
        # 自动检测质量
        quality_indicators = [
            ("4K", ["4k", "uhd", "2160p"]),
            ("1080P", ["1080p", "fhd"]),
            ("720P", ["720p", "hd"]),
            ("480P", ["480p", "sd"])
        ]
        
        name_lower = name.lower()
        for quality, indicators in quality_indicators:
            if any(indicator in name_lower for indicator in indicators):
                metadata["quality"] = quality
                break
        
        return metadata


class TitleQuery:
    """标题查询类"""
    
    def __init__(self):
        self.cache = {}
    
    @lru_cache(maxsize=1000)
    def query_douban(self, title, year=None):
        """查询豆瓣（优先）"""
        if not settings.douban_cookie:
            return None
        
        # 这里可以实现豆瓣API查询
        # 暂时返回模拟数据
        return {
            "title": title,
            "chinese_title": title,  # 假设中文标题相同
            "year": year,
            "rating": 8.5,
            "source": "douban"
        }
    
    @lru_cache(maxsize=1000)
    def query_tmdb(self, title, year=None):
        """查询TMDB"""
        if not settings.tmdb_api_key:
            return None
        
        # 这里可以实现TMDB API查询
        # 暂时返回模拟数据
        return {
            "title": title,
            "original_title": title,
            "year": year,
            "rating": 7.8,
            "source": "tmdb"
        }
    
    def get_chinese_title(self, filename, metadata=None):
        """获取中文标题"""
        if metadata is None:
            metadata = MetadataExtractor.extract_from_filename(filename)
        
        title = metadata.get("title", "")
        year = metadata.get("year")
        
        # 优先查询豆瓣
        result = self.query_douban(title, year)
        if result and result.get("chinese_title"):
            return result["chinese_title"]
        
        # 其次查询TMDB
        result = self.query_tmdb(title, year)
        if result and result.get("title"):
            return result["title"]
        
        # 返回原始标题
        return title


class QualityScorer:
    """质量评分器"""
    
    @staticmethod
    def calculate_score(metadata):
        """计算文件质量评分"""
        score = 0
        
        # 分辨率评分
        quality_scores = {
            "4K": 100,
            "1080P": 80,
            "720P": 60,
            "480P": 40,
            "Unknown": 20
        }
        
        score += quality_scores.get(metadata.get("quality", "Unknown"), 20)
        
        # 年份评分（越新越好）
        year = metadata.get("year")
        if year:
            current_year = 2024  # 假设当前年份
            if year >= current_year - 5:
                score += 30
            elif year >= current_year - 10:
                score += 20
            elif year >= current_year - 20:
                score += 10
        
        return score
    
    @staticmethod
    def compare_files(file1_info, file2_info):
        """比较两个文件的质量"""
        score1 = QualityScorer.calculate_score(file1_info)
        score2 = QualityScorer.calculate_score(file2_info)
        
        if score1 > score2:
            return 1  # file1更好
        elif score1 < score2:
            return -1  # file2更好
        else:
            return 0  # 质量相同


# 工具函数
def validate_metadata(metadata):
    """验证元数据完整性"""
    required_fields = ["title", "type"]
    
    for field in required_fields:
        if field not in metadata or not metadata[field]:
            return False
    
    return True


def format_metadata_for_display(metadata):
    """格式化元数据用于显示"""
    display_info = {
        "标题": metadata.get("title", "未知"),
        "类型": "电影" if metadata.get("type") == "movie" else "电视剧",
        "年份": metadata.get("year", "未知"),
        "质量": metadata.get("quality", "未知")
    }
    
    if metadata.get("type") == "tv":
        display_info["季"] = metadata.get("season", "未知")
        display_info["集"] = metadata.get("episode", "未知")
    
    return display_info