#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMDB ID提取模块
从文件名和元数据中提取TMDB ID，支持多种识别模式
"""

import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TMDBExtractor:
    """TMDB ID提取器"""
    
    def __init__(self):
        # TMDB ID模式
        self.tmdb_patterns = [
            # 标准TMDB ID格式
            r'tmdb[\-\_]?(\d+)',
            r'tmdbid[\-\_]?(\d+)',
            r'tmdb\-id[\-\_]?(\d+)',
            # 在文件名中的TMDB ID
            r'\[(?:tmdb|TMDB)[\-\_]?(\d+)\]',
            r'\((?:tmdb|TMDB)[\-\_]?(\d+)\)',
            r'\{(?:tmdb|TMDB)[\-\_]?(\d+)\}',
            # 纯数字ID（需要上下文验证）
            r'\b(\d{5,8})\b',  # TMDB ID通常是5-8位数字
        ]
        
        # 排除的常见数字模式（避免误识别）
        self.exclude_patterns = [
            r'\d{4}',  # 年份
            r'\d{1,2}x\d{1,3}',  # 分辨率模式
            r's\d{1,2}e\d{1,3}',  # 季集模式
            r'\d{3,4}p',  # 分辨率
            r'\d+\.\d+',  # 版本号
        ]
    
    def extract_tmdb_id(self, filename: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        从文件名和元数据中提取TMDB ID
        
        Args:
            filename: 文件名
            metadata: 可选的元数据字典
            
        Returns:
            Optional[int]: TMDB ID，如果未找到则返回None
        """
        # 优先从元数据中提取
        if metadata and 'tmdb_id' in metadata:
            try:
                return int(metadata['tmdb_id'])
            except (ValueError, TypeError):
                pass
        
        # 从文件名中提取
        for pattern in self.tmdb_patterns:
            matches = re.findall(pattern, filename, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]  # 获取第一个捕获组
                
                # 验证是否为有效的TMDB ID
                if self._is_valid_tmdb_id(match, filename):
                    try:
                        return int(match)
                    except (ValueError, TypeError):
                        continue
        
        return None
    
    def _is_valid_tmdb_id(self, candidate: str, filename: str) -> bool:
        """验证是否为有效的TMDB ID"""
        # 检查是否为排除模式
        for exclude_pattern in self.exclude_patterns:
            if re.search(exclude_pattern, candidate):
                return False
        
        # 检查数字长度
        if not (5 <= len(candidate) <= 8):
            return False
        
        # 检查是否为纯数字
        if not candidate.isdigit():
            return False
        
        # 检查上下文（避免误识别年份等）
        if self._is_context_invalid(candidate, filename):
            return False
        
        return True
    
    def _is_context_invalid(self, candidate: str, filename: str) -> bool:
        """检查上下文是否无效"""
        # 检查是否在年份附近
        year_patterns = [
            r'\b(19|20)\d{2}\b',  # 年份模式
            r'\b\d{4}\b',  # 任意4位数字
        ]
        
        for pattern in year_patterns:
            if re.search(pattern, filename):
                # 如果候选ID在年份附近，可能是误识别
                context = re.sub(r'[^\w\s]', ' ', filename).split()
                for i, word in enumerate(context):
                    if word == candidate:
                        # 检查前后单词
                        if i > 0 and re.match(r'\d{4}', context[i-1]):
                            return True
                        if i < len(context) - 1 and re.match(r'\d{4}', context[i+1]):
                            return True
        
        return False
    
    def extract_with_metadata(self, filename: str, title: str, year: Optional[int] = None) -> Dict[str, Any]:
        """
        结合元数据提取TMDB相关信息
        
        Args:
            filename: 文件名
            title: 标题
            year: 年份（可选）
            
        Returns:
            Dict[str, Any]: 包含TMDB相关信息的字典
        """
        result = {
            'tmdb_id': None,
            'title': title,
            'year': year,
            'confidence': 0.0,
            'source': 'filename'
        }
        
        # 提取TMDB ID
        tmdb_id = self.extract_tmdb_id(filename)
        if tmdb_id:
            result['tmdb_id'] = tmdb_id
            result['confidence'] = 0.8
            result['source'] = 'tmdb_id'
        
        # 如果有标题和年份，增加置信度
        if title and year:
            result['confidence'] = max(result['confidence'], 0.6)
        
        return result


# 全局TMDB提取器实例
tmdb_extractor = TMDBExtractor()