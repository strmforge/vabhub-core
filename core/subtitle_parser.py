#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
副标题解析模块
从文件名和元数据中提取副标题信息，支持多种语言和格式
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class SubtitleParser:
    """副标题解析器"""
    
    def __init__(self):
        # 副标题语言标识
        self.language_indicators = {
            'chinese': ['chs', 'cht', 'sc', 'tc', 'zh', 'zh-cn', 'zh-tw', '中文', '简体', '繁体'],
            'english': ['eng', 'en', 'english', '英文'],
            'japanese': ['jpn', 'jp', 'japanese', '日语', '日文'],
            'korean': ['kor', 'kr', 'korean', '韩语', '韩文'],
            'french': ['fre', 'fr', 'french', '法语'],
            'german': ['ger', 'de', 'german', '德语'],
            'spanish': ['spa', 'es', 'spanish', '西班牙语'],
            'russian': ['rus', 'ru', 'russian', '俄语'],
            'arabic': ['ara', 'ar', 'arabic', '阿拉伯语'],
            'italian': ['ita', 'it', 'italian', '意大利语'],
            'portuguese': ['por', 'pt', 'portuguese', '葡萄牙语'],
            'dutch': ['dut', 'nl', 'dutch', '荷兰语'],
            'polish': ['pol', 'pl', 'polish', '波兰语'],
            'turkish': ['tur', 'tr', 'turkish', '土耳其语'],
            'thai': ['tha', 'th', 'thai', '泰语'],
            'vietnamese': ['vie', 'vi', 'vietnamese', '越南语'],
            'hindi': ['hin', 'hi', 'hindi', '印地语'],
            'multi': ['multi', '多语言', '多字幕']
        }
        
        # 字幕格式标识
        self.format_indicators = {
            'srt': ['srt'],
            'ass': ['ass', 'ssa'],
            'sub': ['sub'],
            'vtt': ['vtt', 'webvtt'],
            'idx': ['idx'],
            'sup': ['sup'],
            'pgs': ['pgs']
        }
        
        # 字幕质量标识
        self.quality_indicators = {
            'high': ['hi', 'high', '高质量', '高清'],
            'standard': ['std', 'standard', '标准'],
            'low': ['low', '低质量']
        }
        
        # 字幕类型标识
        self.type_indicators = {
            'forced': ['forced', '强制', '硬字幕'],
            'sdh': ['sdh', '听障', '听力障碍'],
            'commentary': ['commentary', '评论', '解说']
        }
    
    def parse_subtitle_info(self, filename: str) -> Dict[str, Any]:
        """
        解析副标题信息
        
        Args:
            filename: 文件名
            
        Returns:
            Dict[str, Any]: 包含副标题信息的字典
        """
        result = {
            'languages': [],
            'formats': [],
            'quality': None,
            'types': [],
            'confidence': 0.0
        }
        
        # 提取语言信息
        result['languages'] = self._extract_languages(filename)
        
        # 提取格式信息
        result['formats'] = self._extract_formats(filename)
        
        # 提取质量信息
        result['quality'] = self._extract_quality(filename)
        
        # 提取类型信息
        result['types'] = self._extract_types(filename)
        
        # 计算置信度
        result['confidence'] = self._calculate_confidence(result)
        
        return result
    
    def _extract_languages(self, filename: str) -> List[str]:
        """提取语言信息"""
        languages = []
        filename_lower = filename.lower()
        
        for lang, indicators in self.language_indicators.items():
            for indicator in indicators:
                if indicator.lower() in filename_lower:
                    if lang not in languages:
                        languages.append(lang)
                    break
        
        return languages
    
    def _extract_formats(self, filename: str) -> List[str]:
        """提取格式信息"""
        formats = []
        filename_lower = filename.lower()
        
        for fmt, indicators in self.format_indicators.items():
            for indicator in indicators:
                if indicator.lower() in filename_lower:
                    if fmt not in formats:
                        formats.append(fmt)
                    break
        
        return formats
    
    def _extract_quality(self, filename: str) -> Optional[str]:
        """提取质量信息"""
        filename_lower = filename.lower()
        
        for quality, indicators in self.quality_indicators.items():
            for indicator in indicators:
                if indicator.lower() in filename_lower:
                    return quality
        
        return None
    
    def _extract_types(self, filename: str) -> List[str]:
        """提取类型信息"""
        types = []
        filename_lower = filename.lower()
        
        for type_name, indicators in self.type_indicators.items():
            for indicator in indicators:
                if indicator.lower() in filename_lower:
                    if type_name not in types:
                        types.append(type_name)
                    break
        
        return types
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """计算置信度"""
        confidence = 0.0
        
        # 语言信息加分
        if result['languages']:
            confidence += 0.4
        
        # 格式信息加分
        if result['formats']:
            confidence += 0.3
        
        # 质量信息加分
        if result['quality']:
            confidence += 0.2
        
        # 类型信息加分
        if result['types']:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def is_subtitle_file(self, filename: str) -> bool:
        """判断是否为字幕文件"""
        subtitle_extensions = ['.srt', '.ass', '.ssa', '.sub', '.vtt', '.idx', '.sup', '.pgs']
        
        file_ext = filename.lower()[-4:]
        return file_ext in subtitle_extensions
    
    def get_subtitle_language_pairs(self, media_filename: str, subtitle_filenames: List[str]) -> List[Dict[str, Any]]:
        """
        获取媒体文件与字幕文件的配对信息
        
        Args:
            media_filename: 媒体文件名
            subtitle_filenames: 字幕文件名列表
            
        Returns:
            List[Dict[str, Any]]: 配对信息列表
        """
        pairs = []
        
        # 提取媒体文件的基础信息
        media_base = self._get_filename_base(media_filename)
        
        for subtitle_file in subtitle_filenames:
            if self.is_subtitle_file(subtitle_file):
                # 检查文件名匹配度
                subtitle_base = self._get_filename_base(subtitle_file)
                match_score = self._calculate_filename_match(media_base, subtitle_base)
                
                # 解析字幕信息
                subtitle_info = self.parse_subtitle_info(subtitle_file)
                
                pair_info = {
                    'media_file': media_filename,
                    'subtitle_file': subtitle_file,
                    'match_score': match_score,
                    'subtitle_info': subtitle_info,
                    'is_matched': match_score >= 0.7  # 匹配阈值
                }
                
                pairs.append(pair_info)
        
        # 按匹配度排序
        pairs.sort(key=lambda x: x['match_score'], reverse=True)
        
        return pairs
    
    def _get_filename_base(self, filename: str) -> str:
        """获取文件名基础部分（移除扩展名和路径）"""
        import os
        base_name = os.path.basename(filename)
        return os.path.splitext(base_name)[0]
    
    def _calculate_filename_match(self, media_base: str, subtitle_base: str) -> float:
        """计算文件名匹配度"""
        # 简单的字符串相似度计算
        if media_base == subtitle_base:
            return 1.0
        
        # 检查是否包含关系
        if media_base in subtitle_base or subtitle_base in media_base:
            return 0.8
        
        # 计算公共前缀长度
        min_len = min(len(media_base), len(subtitle_base))
        common_prefix = 0
        for i in range(min_len):
            if media_base[i] == subtitle_base[i]:
                common_prefix += 1
            else:
                break
        
        return common_prefix / max(len(media_base), len(subtitle_base))


# 全局副标题解析器实例
subtitle_parser = SubtitleParser()