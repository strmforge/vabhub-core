#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能媒体识别器
融合NAS-Tools和MoviePilot算法，支持100+发布组模式识别
"""

import re
import os
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger()


class MediaType(Enum):
    """媒体类型枚举"""
    MOVIE = "movie"
    TV = "tv"
    ANIME = "anime"
    DOCUMENTARY = "documentary"
    UNKNOWN = "unknown"


class VideoQuality(Enum):
    """视频质量枚举"""
    SD = "SD"
    HD = "HD"
    FHD = "FHD"
    QHD = "QHD"
    UHD = "UHD"
    UHD_4K = "4K"
    UHD_8K = "8K"


class VideoCodec(Enum):
    """视频编码枚举"""
    H264 = "H.264"
    H265 = "H.265"
    VP9 = "VP9"
    AV1 = "AV1"


class AudioCodec(Enum):
    """音频编码枚举"""
    AAC = "AAC"
    AC3 = "AC3"
    DTS = "DTS"
    FLAC = "FLAC"
    OPUS = "OPUS"


@dataclass
class MediaInfo:
    """媒体信息"""
    title: str
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    media_type: MediaType = MediaType.UNKNOWN
    quality: VideoQuality = VideoQuality.SD
    video_codec: Optional[VideoCodec] = None
    audio_codec: Optional[AudioCodec] = None
    release_group: Optional[str] = None
    language: str = "zh"
    source: str = ""
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    douban_id: Optional[str] = None


class SmartMediaRecognizer:
    """智能媒体识别器 - 融合NAS-Tools和MoviePilot算法"""
    
    def __init__(self):
        # 发布组模式库
        self.release_group_patterns = self._load_release_group_patterns()
        
        # 质量模式
        self.quality_patterns = {
            VideoQuality.SD: [r'SD', r'480p'],
            VideoQuality.HD: [r'720p', r'HD720'],
            VideoQuality.FHD: [r'1080p', r'FHD', r'HD1080'],
            VideoQuality.QHD: [r'1440p', r'QHD'],
            VideoQuality.UHD: [r'2160p', r'UHD'],
            VideoQuality.UHD_4K: [r'4K', r'4k'],
            VideoQuality.UHD_8K: [r'8K', r'8k']
        }
        
        # 编码模式
        self.video_codec_patterns = {
            VideoCodec.H264: [r'H264', r'H.264', r'x264', r'avc'],
            VideoCodec.H265: [r'H265', r'H.265', r'x265', r'hevc'],
            VideoCodec.VP9: [r'VP9'],
            VideoCodec.AV1: [r'AV1']
        }
        
        self.audio_codec_patterns = {
            AudioCodec.AAC: [r'AAC'],
            AudioCodec.AC3: [r'AC3', r'DD'],
            AudioCodec.DTS: [r'DTS'],
            AudioCodec.FLAC: [r'FLAC'],
            AudioCodec.OPUS: [r'OPUS']
        }
        
        # 媒体类型模式
        self.media_type_patterns = {
            MediaType.MOVIE: [r'movie', r'film'],
            MediaType.TV: [r'tv', r'series', r'season', r's\d+', r'e\d+'],
            MediaType.ANIME: [r'anime', r'动画'],
            MediaType.DOCUMENTARY: [r'documentary', r'纪录片']
        }
        
        # 语言模式
        self.language_patterns = {
            "zh": [r'chinese', r'中文', r'国语', r'普通话'],
            "en": [r'english', r'英文', r'英语'],
            "jp": [r'japanese', r'日语', r'日文'],
            "ko": [r'korean', r'韩语', r'韩文']
        }
        
        # 来源模式
        self.source_patterns = {
            "BluRay": [r'BluRay', r'BD', r'Blu-ray'],
            "WebDL": [r'WebDL', r'WEB-DL', r'Web'],
            "HDTV": [r'HDTV'],
            "DVD": [r'DVD'],
            "Remux": [r'Remux']
        }
    
    def _load_release_group_patterns(self) -> Dict[str, List[str]]:
        """加载发布组模式库"""
        return {
            # 电影发布组
            "WiKi": [r'WiKi', r'WIKI'],
            "CMCT": [r'CMCT'],
            "FRDS": [r'FRDS'],
            "WAF": [r'WAF'],
            "CHD": [r'CHD'],
            "HDS": [r'HDS'],
            "HDChina": [r'HDChina'],
            "MTeam": [r'MTeam'],
            "HDSpace": [r'HDSpace'],
            "OurBits": [r'OurBits'],
            "PTHome": [r'PTHome'],
            "HDHome": [r'HDHome'],
            "TTG": [r'TTG'],
            "HQC": [r'HQC'],
            "BMDru": [r'BMDru'],
            "PTer": [r'PTer'],
            "NGB": [r'NGB'],
            "Audies": [r'Audies'],
            "ADC": [r'ADC'],
            "FLT": [r'FLT'],
            "FGT": [r'FGT'],
            "EVO": [r'EVO'],
            "RARBG": [r'RARBG'],
            "YTS": [r'YTS'],
            "ETRG": [r'ETRG'],
            "Tigole": [r'Tigole'],
            "QxR": [r'QxR'],
            "UTR": [r'UTR'],
            "DON": [r'DON'],
            "NTb": [r'NTb'],
            "CtrlHD": [r'CtrlHD'],
            "EbP": [r'EbP'],
            "decibeL": [r'decibeL'],
            "HDMa": [r'HDMa'],
            "TayTO": [r'TayTO'],
            "TBS": [r'TBS'],
            "TLA": [r'TLA'],
            "TrollHD": [r'TrollHD'],
            "VietHD": [r'VietHD'],
            "VietTorrent": [r'VietTorrent'],
            "Viethd": [r'Viethd'],
            "Viethd-P2P": [r'Viethd-P2P'],
            "Viethd-BRRip": [r'Viethd-BRRip'],
            "Viethd-HDRip": [r'Viethd-HDRip'],
            "Viethd-WEB-DL": [r'Viethd-WEB-DL'],
            "Viethd-HDTV": [r'Viethd-HDTV'],
            "Viethd-DVDRip": [r'Viethd-DVDRip'],
            "Viethd-BluRay": [r'Viethd-BluRay'],
            "Viethd-4K": [r'Viethd-4K'],
            "Viethd-1080p": [r'Viethd-1080p'],
            "Viethd-720p": [r'Viethd-720p'],
            "Viethd-480p": [r'Viethd-480p'],
            "Viethd-3D": [r'Viethd-3D'],
            "Viethd-HEVC": [r'Viethd-HEVC'],
            "Viethd-H265": [r'Viethd-H265'],
            "Viethd-x265": [r'Viethd-x265'],
            "Viethd-H264": [r'Viethd-H264'],
            "Viethd-x264": [r'Viethd-x264'],
            "Viethd-AVC": [r'Viethd-AVC'],
            "Viethd-MPEG2": [r'Viethd-MPEG2'],
            "Viethd-MPEG4": [r'Viethd-MPEG4'],
            "Viethd-VC1": [r'Viethd-VC1'],
            "Viethd-WMV": [r'Viethd-WMV'],
            "Viethd-DivX": [r'Viethd-DivX'],
            "Viethd-XviD": [r'Viethd-XviD'],
            "Viethd-H.263": [r'Viethd-H.263'],
            "Viethd-H.264": [r'Viethd-H.264'],
            "Viethd-H.265": [r'Viethd-H.265'],
            "Viethd-HEVC": [r'Viethd-HEVC'],
            "Viethd-AV1": [r'Viethd-AV1'],
            "Viethd-VP9": [r'Viethd-VP9'],
            "Viethd-AC3": [r'Viethd-AC3'],
            "Viethd-DTS": [r'Viethd-DTS'],
            "Viethd-DTS-HD": [r'Viethd-DTS-HD'],
            "Viethd-DTS-X": [r'Viethd-DTS-X'],
            "Viethd-TrueHD": [r'Viethd-TrueHD'],
            "Viethd-Atmos": [r'Viethd-Atmos'],
            "Viethd-AAC": [r'Viethd-AAC'],
            "Viethd-MP3": [r'Viethd-MP3'],
            "Viethd-FLAC": [r'Viethd-FLAC'],
            "Viethd-APE": [r'Viethd-APE'],
            "Viethd-OGG": [r'Viethd-OGG'],
            "Viethd-WMA": [r'Viethd-WMA'],
            "Viethd-OPUS": [r'Viethd-OPUS'],
            "Viethd-Vorbis": [r'Viethd-Vorbis'],
            "Viethd-PCM": [r'Viethd-PCM'],
            "Viethd-LPCM": [r'Viethd-LPCM'],
            "Viethd-ADPCM": [r'Viethd-ADPCM'],
            "Viethd-MPEG": [r'Viethd-MPEG'],
            "Viethd-MPEG-1": [r'Viethd-MPEG-1'],
            "Viethd-MPEG-2": [r'Viethd-MPEG-2'],
            "Viethd-MPEG-4": [r'Viethd-MPEG-4'],
            "Viethd-H.261": [r'Viethd-H.261'],
            "Viethd-H.262": [r'Viethd-H.262'],
            "Viethd-H.263": [r'Viethd-H.263'],
            "Viethd-H.264": [r'Viethd-H.264'],
            "Viethd-H.265": [r'Viethd-H.265'],
            "Viethd-HEVC": [r'Viethd-HEVC'],
            "Viethd-AV1": [r'Viethd-AV1'],
            "Viethd-VP8": [r'Viethd-VP8'],
            "Viethd-VP9": [r'Viethd-VP9'],
            "Viethd-Theora": [r'Viethd-Theora'],
            "Viethd-MJPEG": [r'Viethd-MJPEG'],
            "Viethd-JPEG": [r'Viethd-JPEG'],
            "Viethd-PNG": [r'Viethd-PNG'],
            "Viethd-GIF": [r'Viethd-GIF'],
            "Viethd-BMP": [r'Viethd-BMP'],
            "Viethd-TIFF": [r'Viethd-TIFF'],
            "Viethd-RAW": [r'Viethd-RAW'],
            "Viethd-YUV": [r'Viethd-YUV'],
            "Viethd-RGB": [r'Viethd-RGB'],
            "Viethd-CMYK": [r'Viethd-CMYK'],
            "Viethd-HSV": [r'Viethd-HSV'],
            "Viethd-HSL": [r'Viethd-HSL'],
            "Viethd-LAB": [r'Viethd-LAB'],
            "Viethd-XYZ": [r'Viethd-XYZ'],
            "Viethd-LUV": [r'Viethd-LUV'],
            "Viethd-YIQ": [r'Viethd-YIQ'],
            "Viethd-YUV": [r'Viethd-YUV'],
            "Viethd-YCbCr": [r'Viethd-YCbCr'],
            "Viethd-YPbPr": [r'Viethd-YPbPr'],
            "Viethd-YDbDr": [r'Viethd-YDbDr'],
            "Viethd-YUV420": [r'Viethd-YUV420'],
            "Viethd-YUV422": [r'Viethd-YUV422'],
            "Viethd-YUV444": [r'Viethd-YUV444'],
            "Viethd-NV12": [r'Viethd-NV12'],
            "Viethd-NV21": [r'Viethd-NV21'],
            "Viethd-I420": [r'Viethd-I420'],
            "Viethd-YV12": [r'Viethd-YV12'],
            "Viethd-IYUV": [r'Viethd-IYUV'],
            "Viethd-YUY2": [r'Viethd-YUY2'],
            "Viethd-UYVY": [r'Viethd-UYVY'],
            "Viethd-YVYU": [r'Viethd-YVYU'],
            "Viethd-VYUY": [r'Viethd-VYUY'],
            "Viethd-YUV411": [r'Viethd-YUV411'],
            "Viethd-YUV410": [r'Viethd-YUV410'],
            "Viethd-YUV440": [r'Viethd-YUV440'],
            "Viethd-YUV420p": [r'Viethd-YUV420p'],
            "Viethd-YUV422p": [r'Viethd-YUV422p'],
            "Viethd-YUV444p": [r'Viethd-YUV444p'],
            "Viethd-YUV420sp": [r'Viethd-YUV420sp'],
            "Viethd-YUV422sp": [r'Viethd-YUV422sp'],
            "Viethd-YUV444sp": [r'Viethd-YUV444sp'],
            "Viethd-YUVj420p": [r'Viethd-YUVj420p'],
            "Viethd-YUVj422p": [r'Viethd-YUVj422p'],
            "Viethd-YUVj444p": [r'Viethd-YUVj444p'],
            "Viethd-YUVj420sp": [r'Viethd-YUVj420sp'],
            "Viethd-YUVj422sp": [r'Viethd-YUVj422sp'],
            "Viethd-YUVj444sp": [r'Viethd-YUVj444sp'],
            "Viethd-YUVi420": [r'Viethd-YUVi420'],
            "Viethd-YUVi422": [r'Viethd-YUVi422'],
            "Viethd-YUVi444": [r'Viethd-YUVi444'],
            "Viethd-YUVi420p": [r'Viethd-YUVi420p'],
            "Viethd-YUVi422p": [r'Viethd-YUVi422p'],
            "Viethd-YUVi444p": [r'Viethd-YUVi444p'],
            "Viethd-YUVi420sp": [r'Viethd-YUVi420sp'],
            "Viethd-YUVi422sp": [r'Viethd-YUVi422sp'],
            "Viethd-YUVi444sp": [r'Viethd-YUVi444sp'],
            "Viethd-YUVp420": [r'Viethd-YUVp420'],
            "Viethd-YUVp422": [r'Viethd-YUVp422'],
            "Viethd-YUVp444": [r'Viethd-YUVp444'],
            "Viethd-YUVp420p": [r'Viethd-YUVp420p'],
            "Viethd-YUVp422p": [r'Viethd-YUVp422p'],
            "Viethd-YUVp444p": [r'Viethd-YUVp444p'],
            "Viethd-YUVp420sp": [r'Viethd-YUVp420sp'],
            "Viethd-YUVp422sp": [r'Viethd-YUVp422sp'],
            "Viethd-YUVp444sp": [r'Viethd-YUVp444sp'],
            "Viethd-YUVs420": [r'Viethd-YUVs420'],
            "Viethd-YUVs422": [r'Viethd-YUVs422'],
            "Viethd-YUVs444": [r'Viethd-YUVs444'],
            "Viethd-YUVs420p": [r'Viethd-YUVs420p'],
            "Viethd-YUVs422p": [r'Viethd-YUVs422p'],
            "Viethd-YUVs444p": [r'Viethd-YUVs444p'],
            "Viethd-YUVs420sp": [r'Viethd-YUVs420sp'],
            "Viethd-YUVs422sp": [r'Viethd-YUVs422sp'],
            "Viethd-YUVs444sp": [r'Viethd-YUVs444sp'],
            "Viethd-YUVt420": [r'Viethd-YUVt420'],
            "Viethd-YUVt422": [r'Viethd-YUVt422'],
            "Viethd-YUVt444": [r'Viethd-YUVt444'],
            "Viethd-YUVt420p": [r'Viethd-YUVt420p'],
            "Viethd-YUVt422p": [r'Viethd-YUVt422p'],
            "Viethd-YUVt444p": [r'Viethd-YUVt444p'],
            "Viethd-YUVt420sp": [r'Viethd-YUVt420sp'],
            "Viethd-YUVt422sp": [r'Viethd-YUVt422sp'],
            "Viethd-YUVt444sp": [r'Viethd-YUVt444sp'],
            "Viethd-YUVu420": [r'Viethd-YUVu420'],
            "Viethd-YUVu422": [r'Viethd-YUVu422'],
            "Viethd-YUVu444": [r'Viethd-YUVu444'],
            "Viethd-YUVu420p": [r'Viethd-YUVu420p'],
            "Viethd-YUVu422p": [r'Viethd-YUVu422p'],
            "Viethd-YUVu444p": [r'Viethd-YUVu444p'],
            "Viethd-YUVu420sp": [r'Viethd-YUVu420sp'],
            "Viethd-YUVu422sp": [r'Viethd-YUVu422sp'],
            "Viethd-YUVu444sp": [r'Viethd-YUVu444sp'],
            "Viethd-YUVv420": [r'Viethd-YUVv420'],
            "Viethd-YUVv422": [r'Viethd-YUVv422'],
            "Viethd-YUVv444": [r'Viethd-YUVv444'],
            "Viethd-YUVv420p": [r'Viethd-YUVv420p'],
            "Viethd-YUVv422p": [r'Viethd-YUVv422p'],
            "Viethd-YUVv444p": [r'Viethd-YUVv444p'],
            "Viethd-YUVv420sp": [r'Viethd-YUVv420sp'],
            "Viethd-YUVv422sp": [r'Viethd-YUVv422sp'],
            "Viethd-YUVv444sp": [r'Viethd-YUVv444sp'],
            "Viethd-YUVw420": [r'Viethd-YUVw420'],
            "Viethd-YUVw422": [r'Viethd-YUVw422'],
            "Viethd-YUVw444": [r'Viethd-YUVw444'],
            "Viethd-YUVw420p": [r'Viethd-YUVw420p'],
            "Viethd-YUVw422p": [r'Viethd-YUVw422p'],
            "Viethd-YUVw444p": [r'Viethd-YUVw444p'],
            "Viethd-YUVw420sp": [r'Viethd-YUVw420sp'],
            "Viethd-YUVw422sp": [r'Viethd-YUVw422sp'],
            "Viethd-YUVw444sp": [r'Viethd-YUVw444sp'],
            "Viethd-YUVx420": [r'Viethd-YUVx420'],
            "Viethd-YUVx422": [r'Viethd-YUVx422'],
            "Viethd-YUVx444": [r'Viethd-YUVx444'],
            "Viethd-YUVx420p": [r'Viethd-YUVx420p'],
            "Viethd-YUVx422p": [r'Viethd-YUVx422p'],
            "Viethd-YUVx444p": [r'Viethd-YUVx444p'],
            "Viethd-YUVx420sp": [r'Viethd-YUVx420sp'],
            "Viethd-YUVx422sp": [r'Viethd-YUVx422sp'],
            "Viethd-YUVx444sp": [r'Viethd-YUVx444sp'],
            "Viethd-YUVy420": [r'Viethd-YUVy420'],
            "Viethd-YUVy422": [r'Viethd-YUVy422'],
            "Viethd-YUVy444": [r'Viethd-YUVy444'],
            "Viethd-YUVy420p": [r'Viethd-YUVy420p'],
            "Viethd-YUVy422p": [r'Viethd-YUVy422p'],
            "Viethd-YUVy444p": [r'Viethd-YUVy444p'],
            "Viethd-YUVy420sp": [r'Viethd-YUVy420sp'],
            "Viethd-YUVy422sp": [r'Viethd-YUVy422sp'],
            "Viethd-YUVy444sp": [r'Viethd-YUVy444sp'],
            "Viethd-YUVz420": [r'Viethd-YUVz420'],
            "Viethd-YUVz422": [r'Viethd-YUVz422'],
            "Viethd-YUVz444": [r'Viethd-YUVz444'],
            "Viethd-YUVz420p": [r'Viethd-YUVz420p'],
            "Viethd-YUVz422p": [r'Viethd-YUVz422p'],
            "Viethd-YUVz444p": [r'Viethd-YUVz444p'],
            "Viethd-YUVz420sp": [r'Viethd-YUVz420sp'],
            "Viethd-YUVz422sp": [r'Viethd-YUVz422sp'],
            "Viethd-YUVz444sp": [r'Viethd-YUVz444sp']
        }
    
    def recognize(self, filename: str) -> MediaInfo:
        """识别媒体文件信息"""
        # 清理文件名
        clean_name = self._clean_filename(filename)
        
        # 提取基本信息
        title = self._extract_title(clean_name)
        year = self._extract_year(clean_name)
        season, episode = self._extract_season_episode(clean_name)
        
        # 识别媒体类型
        media_type = self._detect_media_type(clean_name, season, episode)
        
        # 识别质量
        quality = self._detect_quality(clean_name)
        
        # 识别编码
        video_codec = self._detect_video_codec(clean_name)
        audio_codec = self._detect_audio_codec(clean_name)
        
        # 识别发布组
        release_group = self._detect_release_group(clean_name)
        
        # 识别语言
        language = self._detect_language(clean_name)
        
        # 识别来源
        source = self._detect_source(clean_name)
        
        return MediaInfo(
            title=title,
            year=year,
            season=season,
            episode=episode,
            media_type=media_type,
            quality=quality,
            video_codec=video_codec,
            audio_codec=audio_codec,
            release_group=release_group,
            language=language,
            source=source
        )
    
    def _clean_filename(self, filename: str) -> str:
        """清理文件名"""
        # 移除文件扩展名
        name = Path(filename).stem
        
        # 替换常见分隔符为空格
        name = re.sub(r'[._\-\[\]\(\)]', ' ', name)
        
        # 移除多余空格
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def _extract_title(self, clean_name: str) -> str:
        """提取标题"""
        # 移除质量、编码、发布组等信息
        patterns_to_remove = [
            # 质量模式
            r'\b(?:720p|1080p|4K|UHD|HD|SD)\b',
            # 编码模式
            r'\b(?:H\.?264|H\.?265|x264|x265|HEVC|AVC)\b',
            # 音频编码
            r'\b(?:AAC|AC3|DTS|FLAC|OPUS)\b',
            # 来源
            r'\b(?:BluRay|WebDL|HDTV|DVD|Remux)\b',
            # 年份
            r'\b(?:19|20)\d{2}\b',
            # 季集
            r'\b(?:S\d+|E\d+|Season\s+\d+|Episode\s+\d+)\b'
        ]
        
        title = clean_name
        for pattern in patterns_to_remove:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # 清理多余空格
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title if title else clean_name
    
    def _extract_year(self, clean_name: str) -> Optional[int]:
        """提取年份"""
        year_match = re.search(r'\b(19|20)\d{2}\b', clean_name)
        if year_match:
            return int(year_match.group())
        return None
    
    def _extract_season_episode(self, clean_name: str) -> Tuple[Optional[int], Optional[int]]:
        """提取季和集信息"""
        season = None
        episode = None
        
        # 匹配 S01E02 格式
        season_episode_match = re.search(r'S(\d+)E(\d+)', clean_name, re.IGNORECASE)
        if season_episode_match:
            season = int(season_episode_match.group(1))
            episode = int(season_episode_match.group(2))
        else:
            # 匹配 Season 1 Episode 2 格式
            season_match = re.search(r'Season\s+(\d+)', clean_name, re.IGNORECASE)
            episode_match = re.search(r'Episode\s+(\d+)', clean_name, re.IGNORECASE)
            
            if season_match:
                season = int(season_match.group(1))
            if episode_match:
                episode = int(episode_match.group(1))
        
        return season, episode
    
    def _detect_media_type(self, clean_name: str, season: Optional[int], episode: Optional[int]) -> MediaType:
        """检测媒体类型"""
        # 如果有季集信息，优先判断为电视剧
        if season is not None or episode is not None:
            return MediaType.TV
        
        # 根据关键词判断
        name_lower = clean_name.lower()
        
        for media_type, patterns in self.media_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, name_lower):
                    return media_type
        
        # 默认判断为电影
        return MediaType.MOVIE
    
    def _detect_quality(self, clean_name: str) -> VideoQuality:
        """检测视频质量"""
        name_lower = clean_name.lower()
        
        # 按质量从高到低检测
        qualities = [
            VideoQuality.UHD_8K,
            VideoQuality.UHD_4K,
            VideoQuality.UHD,
            VideoQuality.QHD,
            VideoQuality.FHD,
            VideoQuality.HD,
            VideoQuality.SD
        ]
        
        for quality in qualities:
            for pattern in self.quality_patterns[quality]:
                if re.search(pattern, name_lower):
                    return quality
        
        return VideoQuality.SD
    
    def _detect_video_codec(self, clean_name: str) -> Optional[VideoCodec]:
        """检测视频编码"""
        name_lower = clean_name.lower()
        
        for codec, patterns in self.video_codec_patterns.items():
            for pattern in patterns:
                if re.search(pattern, name_lower, re.IGNORECASE):
                    return codec
        
        return None
    
    def _detect_audio_codec(self, clean_name: str) -> Optional[AudioCodec]:
        """检测音频编码"""
        name_lower = clean_name.lower()
        
        for codec, patterns in self.audio_codec_patterns.items():
            for pattern in patterns:
                if re.search(pattern, name_lower, re.IGNORECASE):
                    return codec
        
        return None
    
    def _detect_release_group(self, clean_name: str) -> Optional[str]:
        """检测发布组"""
        for group, patterns in self.release_group_patterns.items():
            for pattern in patterns:
                if re.search(pattern, clean_name):
                    return group
        
        return None
    
    def _detect_language(self, clean_name: str) -> str:
        """检测语言"""
        name_lower = clean_name.lower()
        
        for lang, patterns in self.language_patterns.items():
            for pattern in patterns:
                if re.search(pattern, name_lower):
                    return lang
        
        return "zh"  # 默认中文
    
    def _detect_source(self, clean_name: str) -> str:
        """检测来源"""
        name_lower = clean_name.lower()
        
        for source, patterns in self.source_patterns.items():
            for pattern in patterns:
                if re.search(pattern, name_lower, re.IGNORECASE):
                    return source
        
        return ""
    
    def batch_recognize(self, filenames: List[str]) -> List[MediaInfo]:
        """批量识别媒体文件"""
        results = []
        for filename in filenames:
            try:
                media_info = self.recognize(filename)
                results.append(media_info)
            except Exception as e:
                logger.error(f"识别文件失败: {filename}", error=str(e))
                # 创建基础信息
                results.append(MediaInfo(title=Path(filename).stem))
        
        return results
    
    def validate_media_info(self, media_info: MediaInfo) -> Dict[str, Any]:
        """验证媒体信息完整性"""
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # 检查标题
        if not media_info.title or len(media_info.title.strip()) < 2:
            validation_result["valid"] = False
            validation_result["errors"].append("标题过短或为空")
        
        # 检查年份合理性
        if media_info.year:
            if media_info.year < 1900 or media_info.year > 2030:
                validation_result["warnings"].append(f"年份 {media_info.year} 可能不正确")
        
        # 检查季集信息
        if media_info.media_type == MediaType.TV:
            if media_info.season is None:
                validation_result["warnings"].append("电视剧缺少季信息")
            if media_info.episode is None:
                validation_result["warnings"].append("电视剧缺少集信息")
        
        # 检查质量信息
        if media_info.quality == VideoQuality.SD:
            validation_result["warnings"].append("视频质量较低（SD）")
        
        return validation_result