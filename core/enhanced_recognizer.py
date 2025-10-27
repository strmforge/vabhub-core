"""
增强的媒体识别引擎
集成NASTool的智能识别精华功能
"""

import re
import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RecognitionResult:
    """识别结果数据类"""
    title: str
    original_title: Optional[str]
    year: Optional[int]
    season: Optional[int]
    episode: Optional[int]
    media_type: str  # movie, tv, anime
    quality: Optional[str]
    source: Optional[str]
    group: Optional[str]
    language: Optional[str]
    confidence: float  # 置信度 0-1
    raw_name: str
    normalized_name: str


class EnhancedRecognizer:
    """增强的媒体识别引擎"""
    
    def __init__(self):
        # 媒体类型模式
        self.media_patterns = {
            "movie": self._parse_movie_pattern,
            "tv": self._parse_tv_pattern,
            "anime": self._parse_anime_pattern
        }
        
        # 质量标识
        self.quality_indicators = {
            "4k": ["4k", "2160p", "uhd"],
            "1080p": ["1080p", "fullhd"],
            "720p": ["720p", "hd"],
            "480p": ["480p", "sd"],
            "bluray": ["bluray", "bdrip", "brrip"],
            "webdl": ["webdl", "web-dl", "webrip"],
            "hdtv": ["hdtv", "hdrip"]
        }
        
        # 来源标识
        self.source_indicators = {
            "bluray": ["bluray", "bd"],
            "web": ["webdl", "web-dl", "webrip"],
            "hdtv": ["hdtv"],
            "dvd": ["dvd", "dvdrip"],
            "cam": ["cam", "ts", "tc"]
        }
        
        # 语言标识
        self.language_indicators = {
            "chinese": ["chinese", "ch", "cn", "zh", "zh-cn", "zh-tw"],
            "english": ["english", "en", "eng"],
            "japanese": ["japanese", "jp", "jpn"],
            "korean": ["korean", "kr", "kor"]
        }
        
        # 增强版发布组列表（100+ 发布组）
        self.release_groups = [
            # CHD系列 (12个)
            "CHD", "CHDBits", "CHDPAD", "CHDTV", "CHDWEB", "CHDStudio",
            "CHDbits", "CHDpad", "CHDtv", "CHDweb", "CHD", "CHDTeam",
            
            # HDChina系列 (6个)
            "HDC", "HDChina", "HDCTV", "HDCWeb", "HDCStudio", "HDC",
            
            # LemonHD系列 (9个)
            "LeagueCD", "LeagueHD", "LeagueTV", "LemonHD", "LemonStudio",
            "LemonTV", "LemonWEB", "Lemon", "LHD",
            
            # MTeam系列 (4个)
            "MTeam", "MTeamTV", "MPAD", "MT",
            
            # OurBits系列 (8个)
            "OurBits", "OurTV", "FLTTH", "OurBitsTV", "OurBitsWEB",
            "OurBitsStudio", "OurBits", "OB",
            
            # PTer系列 (6个)
            "PTer", "PTerDIY", "PTerTV", "PTerWEB", "PTer", "PTerClub",
            
            # PTHome系列 (7个)
            "PTH", "PTHAudio", "PTHome", "PTHTV", "PTHWEB", "PTH", "PTHome",
            
            # PTsbao系列 (11个)
            "PTsbao", "OPS", "FFans", "FFansAIeNcE", "FFansBD", "FFansDVD",
            "FFansDIY", "FFansTV", "FFansWEB", "FHDMv", "SGXT",
            
            # 动漫字幕组 (20+)
            "ANi", "HYSUB", "KTXP", "LoliHouse", "VCB-Studio", "UHA-WINGS",
            "DMG", "DHR", "FLsnow", "FZSD", "HKG", "KTKJ", "LKSUB", "Mabors",
            "Moe", "NEO", "Pussub", "Sakurato", "SweetSub", "YUI-7",
            
            # 国际组 (20+)
            "BMDru", "BeyondHD", "BTN", "EVO", "FLUX", "FraMeSToR", "Grym",
            "HONE", "iFT", "KiNGS", "NTb", "PSA", "RARBG", "RARtv", "RZeroX",
            "SPARKS", "TBS", "Tigole", "ViSiON", "YIFY", "YTS",
            
            # 其他常见组
            "rarbg", "yts", "ettv", "eztv", "lol", "dimension", "amzn",
            "ntb", "fgt", "cmpt", "flux", "tbs", "cocain", "evolve",
            "fov", "hazmat", "kings", "mteam", "nbs", "ptp", "rarbg",
            "rartv", "sartre", "sva", "tastetv", "tvp", "vxt", "yify"
        ]
        
    def recognize(self, filename: str, filepath: Optional[str] = None) -> RecognitionResult:
        """识别媒体文件"""
        try:
            # 预处理文件名
            normalized_name = self._normalize_filename(filename)
            
            # 尝试不同的识别模式
            results = []
            for media_type, parser in self.media_patterns.items():
                result = parser(normalized_name, filepath)
                if result:
                    results.append(result)
            
            # 选择最佳结果
            if results:
                best_result = max(results, key=lambda x: x.confidence)
                return best_result
            else:
                # 返回基础识别结果
                return self._create_base_result(filename, normalized_name)
                
        except Exception as e:
            logger.error(f"识别媒体文件失败: {str(e)}")
            return self._create_base_result(filename, filename)
            
    def _parse_movie_pattern(self, filename: str, filepath: Optional[str]) -> Optional[RecognitionResult]:
        """解析电影模式"""
        # 电影模式: 标题 (年份) [质量] [来源] [语言] [发布组]
        patterns = [
            # 标准电影模式
            r'^(.*?)[\s\.]\((\d{4})\)[\s\.].*$',
            r'^(.*?)[\s\.](\d{4})[\s\.].*$',
            r'^(.*?)[\s\.]\[(\d{4})\][\s\.].*$',
            # 中文电影模式
            r'^(.*?)[\s\.]（(\d{4})）[\s\.].*$',
            r'^(.*?)[\s\.](\d{4})[\s\.].*$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                title = match.group(1).replace('.', ' ').strip()
                year = int(match.group(2)) if match.group(2) else None
                
                # 提取其他信息
                quality = self._extract_quality(filename)
                source = self._extract_source(filename)
                language = self._extract_language(filename)
                group = self._extract_group(filename)
                
                confidence = self._calculate_confidence(title, year, quality)
                
                return RecognitionResult(
                    title=title,
                    original_title=None,
                    year=year,
                    season=None,
                    episode=None,
                    media_type="movie",
                    quality=quality,
                    source=source,
                    group=group,
                    language=language,
                    confidence=confidence,
                    raw_name=filename,
                    normalized_name=filename
                )
        
        return None
        
    def _parse_tv_pattern(self, filename: str, filepath: Optional[str]) -> Optional[RecognitionResult]:
        """解析电视剧模式"""
        # 电视剧模式: 标题 S01E01 或 标题 第1季 第1集
        patterns = [
            # 标准季集模式
            r'^(.*?)[\s\.][Ss](\d{1,2})[Ee](\d{1,3})[\s\.].*$',
            r'^(.*?)[\s\.]Season[\s\.]?(\d{1,2})[\s\.]Episode[\s\.]?(\d{1,3})[\s\.].*$',
            r'^(.*?)[\s\.](\d{1,2})x(\d{1,3})[\s\.].*$',
            # 中文季集模式
            r'^(.*?)[\s\.]第(\d{1,2})季[\s\.]第(\d{1,3})集[\s\.].*$',
            r'^(.*?)[\s\.]S(\d{1,2})E(\d{1,3})[\s\.].*$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                title = match.group(1).replace('.', ' ').strip()
                season = int(match.group(2)) if match.group(2) else None
                episode = int(match.group(3)) if match.group(3) else None
                
                # 尝试提取年份（从标题中）
                year_match = re.search(r'\((\d{4})\)', title)
                year = int(year_match.group(1)) if year_match else None
                
                if year:
                    title = re.sub(r'\s*\(\d{4}\)\s*', ' ', title).strip()
                
                # 提取其他信息
                quality = self._extract_quality(filename)
                source = self._extract_source(filename)
                language = self._extract_language(filename)
                group = self._extract_group(filename)
                
                confidence = self._calculate_confidence(title, year, quality, season, episode)
                
                return RecognitionResult(
                    title=title,
                    original_title=None,
                    year=year,
                    season=season,
                    episode=episode,
                    media_type="tv",
                    quality=quality,
                    source=source,
                    group=group,
                    language=language,
                    confidence=confidence,
                    raw_name=filename,
                    normalized_name=filename
                )
        
        return None
        
    def _parse_anime_pattern(self, filename: str, filepath: Optional[str]) -> Optional[RecognitionResult]:
        """解析动漫模式"""
        # 动漫模式: [发布组] 标题 [集数] [质量]
        patterns = [
            # 标准动漫模式
            r'^\[(.*?)\][\s\.](.*?)[\s\.]\[(\d{1,3})\][\s\.].*$',
            r'^(.*?)[\s\.]-[\s\.](\d{1,3})[\s\.].*$',
            r'^(.*?)[\s\.]第(\d{1,3})话[\s\.].*$',
            r'^(.*?)[\s\.]Episode[\s\.]?(\d{1,3})[\s\.].*$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                if len(match.groups()) == 3:
                    group = match.group(1)
                    title = match.group(2).replace('.', ' ').strip()
                    episode = int(match.group(3)) if match.group(3) else None
                else:
                    group = None
                    title = match.group(1).replace('.', ' ').strip()
                    episode = int(match.group(2)) if len(match.groups()) >= 2 else None
                
                # 提取其他信息
                quality = self._extract_quality(filename)
                source = self._extract_source(filename)
                language = self._extract_language(filename)
                
                # 动漫通常没有明确的年份
                year = None
                
                confidence = self._calculate_confidence(title, year, quality, None, episode)
                
                return RecognitionResult(
                    title=title,
                    original_title=None,
                    year=year,
                    season=None,
                    episode=episode,
                    media_type="anime",
                    quality=quality,
                    source=source,
                    group=group,
                    language=language,
                    confidence=confidence,
                    raw_name=filename,
                    normalized_name=filename
                )
        
        return None
        
    def _extract_quality(self, filename: str) -> Optional[str]:
        """提取质量信息"""
        filename_lower = filename.lower()
        
        for quality, indicators in self.quality_indicators.items():
            for indicator in indicators:
                if indicator in filename_lower:
                    return quality
        
        return None
        
    def _extract_source(self, filename: str) -> Optional[str]:
        """提取来源信息"""
        filename_lower = filename.lower()
        
        for source, indicators in self.source_indicators.items():
            for indicator in indicators:
                if indicator in filename_lower:
                    return source
        
        return None
        
    def _extract_language(self, filename: str) -> Optional[str]:
        """提取语言信息"""
        filename_lower = filename.lower()
        
        for language, indicators in self.language_indicators.items():
            for indicator in indicators:
                if indicator in filename_lower:
                    return language
        
        return None
        
    def _extract_group(self, filename: str) -> Optional[str]:
        """提取发布组信息"""
        filename_lower = filename.lower()
        
        for group in self.release_groups:
            if group in filename_lower:
                return group
        
        # 尝试从方括号中提取发布组
        bracket_match = re.search(r'\[(.*?)\]', filename)
        if bracket_match:
            potential_group = bracket_match.group(1).lower()
            # 检查是否是已知的发布组格式
            if len(potential_group) <= 20 and not re.search(r'\d', potential_group):
                return potential_group
        
        return None
        
    def _calculate_confidence(self, title: str, year: Optional[int], quality: Optional[str], 
                            season: Optional[int] = None, episode: Optional[int] = None) -> float:
        """计算识别置信度"""
        confidence = 0.5  # 基础置信度
        
        # 标题长度影响
        if len(title) >= 3:
            confidence += 0.2
        
        # 年份影响
        if year and 1900 <= year <= 2030:
            confidence += 0.1
        
        # 质量信息影响
        if quality:
            confidence += 0.1
        
        # 季集信息影响（电视剧/动漫）
        if season is not None and episode is not None:
            confidence += 0.1
        
        # 限制在0-1之间
        return min(1.0, max(0.0, confidence))
        
    def _normalize_filename(self, filename: str) -> str:
        """标准化文件名"""
        # 移除文件扩展名
        name_without_ext = os.path.splitext(filename)[0]
        
        # 替换常见分隔符为空格
        normalized = re.sub(r'[\._\-]+', ' ', name_without_ext)
        
        # 移除多余空格
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
        
    def _create_base_result(self, filename: str, normalized_name: str) -> RecognitionResult:
        """创建基础识别结果"""
        return RecognitionResult(
            title=normalized_name,
            original_title=None,
            year=None,
            season=None,
            episode=None,
            media_type="unknown",
            quality=None,
            source=None,
            group=None,
            language=None,
            confidence=0.1,
            raw_name=filename,
            normalized_name=normalized_name
        )
        
    def batch_recognize(self, filenames: List[str]) -> Dict[str, RecognitionResult]:
        """批量识别媒体文件"""
        results = {}
        
        for filename in filenames:
            result = self.recognize(filename)
            results[filename] = result
            
        return results
        
    def get_recognizer_info(self) -> Dict[str, Any]:
        """获取识别器信息"""
        return {
            "version": "2.0.0",
            "supported_media_types": list(self.media_patterns.keys()),
            "quality_indicators": list(self.quality_indicators.keys()),
            "source_indicators": list(self.source_indicators.keys()),
            "language_indicators": list(self.language_indicators.keys()),
            "release_groups_count": len(self.release_groups)
        }