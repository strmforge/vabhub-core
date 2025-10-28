"""
媒体库扫描和识别模块
基于现有MediaRecognizer进行增强，支持电影/电视剧/动漫自动识别
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MediaType(Enum):
    """媒体类型枚举"""
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    ANIME = "anime"
    DOCUMENTARY = "documentary"
    VARIETY = "variety"
    UNKNOWN = "unknown"


@dataclass
class MediaFile:
    """媒体文件信息"""
    file_path: Path
    file_name: str
    file_size: int
    media_type: MediaType
    title: str
    year: Optional[int]
    season: Optional[int]
    episode: Optional[int]
    quality: Optional[str]
    language: Optional[str]
    metadata: Dict[str, Any]


class MediaScanner:
    """媒体库扫描器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scan_paths = config.get('scan_paths', [])
        self.supported_extensions = {
            '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
            '.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a'
        }
        
    async def scan_library(self) -> List[MediaFile]:
        """扫描媒体库"""
        logger.info("开始扫描媒体库")
        
        all_media_files = []
        
        for scan_path in self.scan_paths:
            path = Path(scan_path)
            if not path.exists():
                logger.warning(f"扫描路径不存在: {path}")
                continue
                
            media_files = await self._scan_directory(path)
            all_media_files.extend(media_files)
            
        logger.info(f"扫描完成，共找到 {len(all_media_files)} 个媒体文件")
        return all_media_files
    
    async def _scan_directory(self, directory: Path) -> List[MediaFile]:
        """扫描单个目录"""
        media_files = []
        
        try:
            for item in directory.iterdir():
                if item.is_dir():
                    # 递归扫描子目录
                    sub_files = await self._scan_directory(item)
                    media_files.extend(sub_files)
                elif item.is_file() and item.suffix.lower() in self.supported_extensions:
                    # 识别媒体文件
                    media_file = await self._identify_media_file(item)
                    if media_file:
                        media_files.append(media_file)
                        
        except PermissionError:
            logger.warning(f"无权限访问目录: {directory}")
        except Exception as e:
            logger.error(f"扫描目录失败 {directory}: {e}")
            
        return media_files
    
    async def _identify_media_file(self, file_path: Path) -> Optional[MediaFile]:
        """识别单个媒体文件"""
        try:
            # 获取文件基本信息
            file_size = file_path.stat().st_size
            file_name = file_path.name
            
            # 解析文件名获取媒体信息
            media_info = await self._parse_filename(file_name)
            
            # 确定媒体类型
            media_type = self._determine_media_type(file_name, media_info)
            
            # 创建媒体文件对象
            media_file = MediaFile(
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                media_type=media_type,
                title=media_info.get('title', file_name),
                year=media_info.get('year'),
                season=media_info.get('season'),
                episode=media_info.get('episode'),
                quality=media_info.get('quality'),
                language=media_info.get('language'),
                metadata=media_info
            )
            
            return media_file
            
        except Exception as e:
            logger.error(f"识别媒体文件失败 {file_path}: {e}")
            return None
    
    async def _parse_filename(self, filename: str) -> Dict[str, Any]:
        """解析文件名提取媒体信息"""
        import re
        
        # 移除文件扩展名
        name_without_ext = Path(filename).stem
        
        # 常见模式匹配
        patterns = {
            'year': r'(19|20)\d{2}',
            'season': r'[Ss](\d{1,2})',
            'episode': r'[Ee](\d{1,3})',
            'quality': r'(720p|1080p|2160p|4K|HDTV|BluRay|WEB-DL)',
            'language': r'(CHS|CHT|ENG|JPN|KOR)',
        }
        
        info = {}
        
        # 提取年份
        year_match = re.search(patterns['year'], name_without_ext)
        if year_match:
            info['year'] = int(year_match.group())
        
        # 提取季数
        season_match = re.search(patterns['season'], name_without_ext)
        if season_match:
            info['season'] = int(season_match.group(1))
        
        # 提取集数
        episode_match = re.search(patterns['episode'], name_without_ext)
        if episode_match:
            info['episode'] = int(episode_match.group(1))
        
        # 提取质量
        quality_match = re.search(patterns['quality'], name_without_ext)
        if quality_match:
            info['quality'] = quality_match.group()
        
        # 提取语言
        language_match = re.search(patterns['language'], name_without_ext)
        if language_match:
            info['language'] = language_match.group()
        
        # 提取标题（移除所有模式匹配的部分）
        title = name_without_ext
        for pattern in patterns.values():
            title = re.sub(pattern, '', title)
        
        # 清理标题
        title = re.sub(r'[\.\-_\[\]\(\)]', ' ', title).strip()
        info['title'] = title
        
        return info
    
    def _determine_media_type(self, filename: str, media_info: Dict) -> MediaType:
        """根据文件名和信息确定媒体类型"""
        filename_lower = filename.lower()
        
        # 动漫检测
        anime_keywords = ['anime', '动漫', '动画', '番剧', 'ova', 'oad']
        if any(keyword in filename_lower for keyword in anime_keywords):
            return MediaType.ANIME
        
        # 电视剧检测
        if media_info.get('season') is not None or media_info.get('episode') is not None:
            return MediaType.TV_SHOW
        
        # 电影检测
        movie_keywords = ['movie', 'film', '电影', '影片']
        if any(keyword in filename_lower for keyword in movie_keywords):
            return MediaType.MOVIE
        
        # 纪录片检测
        doc_keywords = ['documentary', '纪录片', '纪实']
        if any(keyword in filename_lower for keyword in doc_keywords):
            return MediaType.DOCUMENTARY
        
        # 综艺检测
        variety_keywords = ['variety', '综艺', '真人秀']
        if any(keyword in filename_lower for keyword in variety_keywords):
            return MediaType.VARIETY
        
        return MediaType.UNKNOWN


class MediaLibraryManager:
    """媒体库管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scanner = MediaScanner(config)
        self.media_database = {}  # 实际应该使用数据库
        
    async def scan_and_update_library(self) -> Dict[str, Any]:
        """扫描并更新媒体库"""
        logger.info("开始扫描并更新媒体库")
        
        # 扫描媒体文件
        media_files = await self.scanner.scan_library()
        
        # 更新数据库
        stats = await self._update_database(media_files)
        
        logger.info(f"媒体库更新完成: {stats}")
        return stats
    
    async def _update_database(self, media_files: List[MediaFile]) -> Dict[str, Any]:
        """更新媒体数据库"""
        stats = {
            'total_files': len(media_files),
            'movies': 0,
            'tv_shows': 0,
            'anime': 0,
            'documentaries': 0,
            'variety': 0,
            'unknown': 0,
            'total_size_gb': 0
        }
        
        for media_file in media_files:
            # 统计不同类型
            if media_file.media_type == MediaType.MOVIE:
                stats['movies'] += 1
            elif media_file.media_type == MediaType.TV_SHOW:
                stats['tv_shows'] += 1
            elif media_file.media_type == MediaType.ANIME:
                stats['anime'] += 1
            elif media_file.media_type == MediaType.DOCUMENTARY:
                stats['documentaries'] += 1
            elif media_file.media_type == MediaType.VARIETY:
                stats['variety'] += 1
            else:
                stats['unknown'] += 1
            
            # 统计总大小
            stats['total_size_gb'] += media_file.file_size / (1024**3)
            
            # 更新数据库（这里简化处理）
            self.media_database[str(media_file.file_path)] = {
                'title': media_file.title,
                'year': media_file.year,
                'type': media_file.media_type.value,
                'size_gb': media_file.file_size / (1024**3),
                'quality': media_file.quality,
                'language': media_file.language
            }
        
        stats['total_size_gb'] = round(stats['total_size_gb'], 2)
        return stats
    
    async def search_media(self, query: str, media_type: Optional[MediaType] = None) -> List[MediaFile]:
        """搜索媒体文件"""
        results = []
        
        for file_path, media_info in self.media_database.items():
            # 类型过滤
            if media_type and media_info['type'] != media_type.value:
                continue
            
            # 关键词搜索
            if query.lower() in media_info['title'].lower():
                # 创建简化的MediaFile对象
                results.append(MediaFile(
                    file_path=Path(file_path),
                    file_name=Path(file_path).name,
                    file_size=media_info['size_gb'] * (1024**3),
                    media_type=MediaType(media_info['type']),
                    title=media_info['title'],
                    year=media_info.get('year'),
                    season=None,
                    episode=None,
                    quality=media_info.get('quality'),
                    language=media_info.get('language'),
                    metadata=media_info
                ))
        
        return results


# 使用示例
async def main():
    """使用示例"""
    config = {
        'scan_paths': ['/path/to/media/library'],
        'supported_extensions': ['.mp4', '.mkv', '.avi', '.mp3', '.flac']
    }
    
    manager = MediaLibraryManager(config)
    
    # 扫描媒体库
    stats = await manager.scan_and_update_library()
    print(f"扫描结果: {stats}")
    
    # 搜索媒体
    results = await manager.search_media("复仇者联盟", MediaType.MOVIE)
    print(f"搜索结果: {len(results)} 个文件")


if __name__ == "__main__":
    asyncio.run(main())