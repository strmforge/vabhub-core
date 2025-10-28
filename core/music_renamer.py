"""
音乐重命名系统
基于MoviePilot的重命名架构，专门为音乐文件设计
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime

from .storage_schemas import MediaInfo, RenameRequest, RenameResult


class MusicRenamer:
    """音乐文件重命名器"""
    
    def __init__(self):
        self.logger = logging.getLogger("music_renamer")
        
        # 音乐文件扩展名
        self.music_extensions = {
            '.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', 
            '.wma', '.ape', '.opus', '.dsf', '.dff'
        }
        
        # 音乐元数据字段映射
        self.metadata_fields = {
            'title': ['title', '歌曲名', '歌名'],
            'artist': ['artist', '歌手', '演唱者'],
            'album': ['album', '专辑', '专辑名'],
            'year': ['year', '年份', '发行年份'],
            'track': ['track', '音轨', '曲目'],
            'disc': ['disc', '碟片', '光盘'],
            'genre': ['genre', '流派', '风格'],
            'composer': ['composer', '作曲', '作曲家'],
            'lyricist': ['lyricist', '作词', '作词家'],
            'bpm': ['bpm', '速度', '节拍'],
            'bitrate': ['bitrate', '比特率', '码率'],
            'sample_rate': ['sample_rate', '采样率', '采样频率']
        }
        
        # 音乐重命名模板
        self.rename_templates = {
            'standard': "{artist} - {title}",
            'album': "{artist} - {album} - {track:02d} - {title}",
            'detailed': "{artist} - {album} ({year}) - {track:02d} - {title}",
            'simple': "{track:02d} - {title}",
            'classical': "{composer} - {title} - {artist}"
        }
    
    def detect_music_type(self, file_path: str) -> Optional[str]:
        """检测音乐文件类型"""
        try:
            ext = Path(file_path).suffix.lower()
            if ext in self.music_extensions:
                return "music"
            return None
        except:
            return None
    
    def extract_music_info(self, file_path: str) -> Optional[MediaInfo]:
        """提取音乐文件信息"""
        try:
            # 这里可以集成音乐元数据提取库，如mutagen
            # 简化实现：从文件名提取基本信息
            file_name = Path(file_path).stem
            
            # 常见的音乐文件名模式
            patterns = [
                # 艺术家 - 歌曲名
                r'^(?P<artist>[^\-]+)\s*-\s*(?P<title>.+)$',
                # 艺术家 - 专辑 - 音轨 - 歌曲名
                r'^(?P<artist>[^\-]+)\s*-\s*(?P<album>[^\-]+)\s*-\s*(?P<track>\d+)\s*-\s*(?P<title>.+)$',
                # 音轨 - 歌曲名
                r'^(?P<track>\d+)\s*-\s*(?P<title>.+)$',
                # 艺术家 - 歌曲名 (年份)
                r'^(?P<artist>[^\-]+)\s*-\s*(?P<title>[^\(]+)\s*\((?P<year>\d{4})\)$'
            ]
            
            info = {}
            for pattern in patterns:
                match = re.match(pattern, file_name)
                if match:
                    info.update(match.groupdict())
                    break
            
            if info:
                return MediaInfo(
                    media_type="music",
                    title=info.get('title', file_name),
                    artist=info.get('artist', ''),
                    album=info.get('album', ''),
                    year=int(info.get('year', 0)) if info.get('year') else 0,
                    track=int(info.get('track', 0)) if info.get('track') else 0,
                    file_path=file_path
                )
            
            return MediaInfo(
                media_type="music",
                title=file_name,
                file_path=file_path
            )
            
        except Exception as e:
            self.logger.error(f"提取音乐信息失败: {e}")
            return None
    
    def generate_music_name(self, media_info: MediaInfo, template: str = "standard") -> str:
        """生成音乐文件名"""
        try:
            # 获取模板
            name_template = self.rename_templates.get(template, self.rename_templates['standard'])
            
            # 准备替换数据
            data = {
                'title': media_info.title or 'Unknown Title',
                'artist': media_info.artist or 'Unknown Artist',
                'album': media_info.album or 'Unknown Album',
                'year': media_info.year or datetime.now().year,
                'track': media_info.track or 1,
                'composer': media_info.composer or 'Unknown Composer',
                'genre': media_info.genre or 'Unknown Genre'
            }
            
            # 应用模板
            file_name = name_template.format(**data)
            
            # 清理文件名中的非法字符
            file_name = self._sanitize_filename(file_name)
            
            return file_name
            
        except Exception as e:
            self.logger.error(f"生成音乐文件名失败: {e}")
            return media_info.title or 'Unknown Title'
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # Windows非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '_', filename)
        
        # 去除首尾空格和点
        filename = filename.strip().strip('.')
        
        # 限制文件名长度
        if len(filename) > 255:
            filename = filename[:255]
        
        return filename
    
    def get_music_directory_structure(self, media_info: MediaInfo, 
                                    structure_type: str = "artist_album") -> str:
        """生成音乐目录结构"""
        try:
            artist = media_info.artist or 'Unknown Artist'
            album = media_info.album or 'Unknown Album'
            year = media_info.year or datetime.now().year
            
            structures = {
                "artist_album": f"{artist}/{album} ({year})",
                "genre_artist": f"{media_info.genre or 'Unknown Genre'}/{artist}/{album}",
                "year_artist": f"{year}/{artist}/{album}",
                "simple": f"{artist}/{album}",
                "flat": ""  # 平铺结构
            }
            
            structure = structures.get(structure_type, structures['artist_album'])
            return self._sanitize_filename(structure)
            
        except Exception as e:
            self.logger.error(f"生成目录结构失败: {e}")
            return "Unknown/Unknown"
    
    def rename_music_file(self, request: RenameRequest) -> RenameResult:
        """重命名音乐文件"""
        try:
            # 提取音乐信息
            media_info = self.extract_music_info(request.source_path)
            if not media_info:
                return RenameResult(success=False, message="无法提取音乐信息")
            
            # 生成新文件名
            new_file_name = self.generate_music_name(media_info, request.template)
            
            # 生成目录结构
            directory_structure = self.get_music_directory_structure(
                media_info, request.structure_type
            )
            
            # 构建完整路径
            if directory_structure:
                new_path = Path(request.target_dir) / directory_structure / f"{new_file_name}{Path(request.source_path).suffix}"
            else:
                new_path = Path(request.target_dir) / f"{new_file_name}{Path(request.source_path).suffix}"
            
            # 确保目录存在
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 执行重命名/移动操作
            if request.operation == "rename":
                Path(request.source_path).rename(new_path)
            elif request.operation == "copy":
                import shutil
                shutil.copy2(request.source_path, new_path)
            elif request.operation == "move":
                import shutil
                shutil.move(request.source_path, new_path)
            else:
                return RenameResult(success=False, message=f"不支持的操作: {request.operation}")
            
            return RenameResult(
                success=True,
                message="重命名成功",
                old_path=request.source_path,
                new_path=str(new_path),
                media_info=media_info
            )
            
        except Exception as e:
            self.logger.error(f"重命名音乐文件失败: {e}")
            return RenameResult(success=False, message=f"重命名失败: {e}")
    
    def batch_rename_music_files(self, requests: List[RenameRequest]) -> List[RenameResult]:
        """批量重命名音乐文件"""
        results = []
        
        for request in requests:
            result = self.rename_music_file(request)
            results.append(result)
        
        return results
    
    def validate_music_file(self, file_path: str) -> Dict[str, Any]:
        """验证音乐文件"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {"valid": False, "error": "文件不存在"}
            
            if path.suffix.lower() not in self.music_extensions:
                return {"valid": False, "error": "不支持的音乐格式"}
            
            # 检查文件大小
            file_size = path.stat().st_size
            if file_size == 0:
                return {"valid": False, "error": "文件为空"}
            
            # 检查文件权限
            if not os.access(file_path, os.R_OK):
                return {"valid": False, "error": "文件不可读"}
            
            return {
                "valid": True,
                "file_size": file_size,
                "file_extension": path.suffix.lower(),
                "file_name": path.name
            }
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的音乐格式"""
        return sorted(list(self.music_extensions))
    
    def get_rename_templates(self) -> Dict[str, str]:
        """获取重命名模板"""
        return self.rename_templates.copy()
    
    def add_custom_template(self, name: str, template: str) -> bool:
        """添加自定义模板"""
        try:
            # 验证模板格式
            test_data = {
                'title': 'Test Title',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'year': 2024,
                'track': 1
            }
            
            # 测试模板是否有效
            template.format(**test_data)
            
            self.rename_templates[name] = template
            return True
            
        except Exception as e:
            self.logger.error(f"添加自定义模板失败: {e}")
            return False


# 全局实例
music_renamer = MusicRenamer()