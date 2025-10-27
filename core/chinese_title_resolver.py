#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文标题解析器
智能解析中文影视标题，提取关键信息
"""

import re
import json
from .chinese_number import convert_season_info

class ChineseTitleResolver:
    """中文标题解析器"""
    
    def __init__(self):
        # 常见发布组映射
        self.release_groups = {
            # PTsbao系列
            'PTsbao', 'OPS', 'FFans', 'FFansAIeNcE', 'FFansBD', 'FFansDVD', 
            'FFansDIY', 'FFansTV', 'FFansWEB', 'FHDMv', 'SGXT',
            
            # 其他站点
            'TTG', 'WiKi', 'NGB', 'DoA', 'HHWEB', 'FRDS', 'HDArea', 'HDSky', 
            'HDHome', 'Hares', 'CMCT', 'DreamTV', 'beAst', 'Audies', 'TLF', 
            'DGB', 'PuTao', 'BeiTai', 'TJUPT', 'PiGo', 'Btschool', 'CarPT', 
            'Shark', 'FROG', 'UBits'
        }
        
        # 常见视频编码
        self.video_codecs = ['x264', 'x265', 'HEVC', 'AVC', 'H.264', 'H.265']
        
        # 常见音频编码
        self.audio_codecs = ['AAC', 'DTS', 'AC3', 'Atmos', 'TrueHD', 'FLAC']
        
        # 常见来源
        self.sources = ['BluRay', 'WEB-DL', 'HDTV', 'DVD', 'Remux']
        
        # 分辨率
        self.resolutions = ['720p', '1080p', '2160p', '4K', '8K']
    
    def parse_title(self, filename):
        """
        解析文件名，提取影视信息
        
        Args:
            filename: 文件名
            
        Returns:
            dict: 解析结果
        """
        if not filename:
            return {}
        
        # 移除文件扩展名
        name_only = re.sub(r'\.[^.]+$', '', filename)
        
        # 转换中文数字
        processed_name = convert_season_info(name_only)
        
        result = {
            'original_title': filename,
            'processed_title': processed_name,
            'title': '',
            'year': None,
            'season': None,
            'episode': None,
            'resolution': '',
            'source': '',
            'video_codec': '',
            'audio_codec': '',
            'release_group': '',
            'quality_score': 0.0
        }
        
        # 提取年份
        year_match = re.search(r'(19|20)\d{2}', processed_name)
        if year_match:
            result['year'] = int(year_match.group(0))
        
        # 提取分辨率
        for res in self.resolutions:
            if res.lower() in processed_name.lower():
                result['resolution'] = res
                break
        
        # 提取来源
        for source in self.sources:
            if source.lower() in processed_name.lower():
                result['source'] = source
                break
        
        # 提取视频编码
        for codec in self.video_codecs:
            if codec.lower() in processed_name.lower():
                result['video_codec'] = codec
                break
        
        # 提取音频编码
        for codec in self.audio_codecs:
            if codec.lower() in processed_name.lower():
                result['audio_codec'] = codec
                break
        
        # 提取发布组
        for group in self.release_groups:
            if group in processed_name:
                result['release_group'] = group
                break
        
        # 提取季集信息
        season_match = re.search(r'[Ss](\d+)', processed_name)
        episode_match = re.search(r'[Ee](\d+)', processed_name)
        
        if season_match:
            result['season'] = int(season_match.group(1))
        if episode_match:
            result['episode'] = int(episode_match.group(1))
        
        # 计算质量分数
        result['quality_score'] = self._calculate_quality_score(result)
        
        # 提取标题（移除技术信息后的纯净标题）
        result['title'] = self._extract_clean_title(processed_name, result)
        
        return result
    
    def _calculate_quality_score(self, info):
        """计算质量分数"""
        score = 0.0
        
        # 分辨率权重
        resolution_weights = {
            '720p': 0.6, '1080p': 0.8, '2160p': 0.9, '4K': 0.95, '8K': 1.0
        }
        if info['resolution'] in resolution_weights:
            score += resolution_weights[info['resolution']] * 0.4
        
        # 来源权重
        source_weights = {
            'BluRay': 0.9, 'Remux': 0.95, 'WEB-DL': 0.8, 'HDTV': 0.7, 'DVD': 0.5
        }
        if info['source'] in source_weights:
            score += source_weights[info['source']] * 0.3
        
        # 编码权重
        if info['video_codec'] in ['x265', 'HEVC', 'H.265']:
            score += 0.2
        elif info['video_codec']:
            score += 0.1
        
        # 音频权重
        if info['audio_codec'] in ['Atmos', 'TrueHD', 'DTS']:
            score += 0.1
        
        return min(score, 1.0)
    
    def _extract_clean_title(self, processed_name, info):
        """提取纯净标题"""
        # 移除技术信息
        patterns_to_remove = [
            r'[Ss]\d+[Ee]\d+',  # S01E01
            r'[Ss]\d+',         # S01
            r'[Ee]\d+',         # E01
            r'(19|20)\d{2}',    # 年份
            r'\d+p',            # 720p等
        ]
        
        clean_title = processed_name
        for pattern in patterns_to_remove:
            clean_title = re.sub(pattern, '', clean_title)
        
        # 移除发布组和技术标记
        tech_marks = list(self.release_groups) + self.video_codecs + \
                     self.audio_codecs + self.sources
        
        for mark in tech_marks:
            clean_title = clean_title.replace(mark, '')
        
        # 清理多余字符
        clean_title = re.sub(r'[\[\]\(\)\-_\.]+', ' ', clean_title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        return clean_title

# 测试函数
def test_parser():
    """测试解析器"""
    resolver = ChineseTitleResolver()
    
    test_files = [
        "权力的游戏.S01E01.1080p.BluRay.x264-FFans.mkv",
        "流浪地球.2019.4K.WEB-DL.HEVC.Atmos-FFansBD.mkv",
        "测试文件.第一季.第五集.720p.HDTV.x264.mkv"
    ]
    
    print("中文标题解析测试:")
    for filename in test_files:
        result = resolver.parse_title(filename)
        print(f"\n文件名: {filename}")
        print(f"解析结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    test_parser()