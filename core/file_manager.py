"""
文件管理器主模块
基于MoviePilot的最佳实践，实现智能重命名和媒体整理功能
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Callable, Any
import logging

from .storage_base import StorageBase
from .storage_schemas import (
    FileItem, StorageUsage, TransferInfo, TransferDirectoryConf,
    MediaInfo, MetaInfo, ExistMediaInfo, TmdbEpisode, MediaType
)


class FileManager:
    """
    文件管理器
    负责媒体文件的智能重命名和整理
    """
    
    def __init__(self):
        self.logger = logging.getLogger("file_manager")
        
        # 媒体文件扩展名
        self.media_extensions = [
            '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
            '.m4v', '.ts', '.m2ts', '.mpg', '.mpeg', '.vob', '.iso'
        ]
        
        # 字幕文件扩展名
        self.subtitle_extensions = [
            '.srt', '.ass', '.ssa', '.sub', '.vtt', '.smi'
        ]
        
        # 音频轨道扩展名
        self.audio_extensions = [
            '.ac3', '.dts', '.aac', '.mp3', '.flac', '.wav', '.ogg'
        ]
        
        # 重命名模板
        self.rename_templates = {
            MediaType.MOVIE: "{title} ({year})/{title} ({year}){quality}",
            MediaType.TV: "{title} ({year})/Season {season:02d}/{title} - S{season:02d}E{episode:02d} - {episode_name}{quality}",
            MediaType.ANIME: "{title} ({year})/Season {season:02d}/{title} - S{season:02d}E{episode:02d} - {episode_name}{quality}",
            MediaType.DOCUMENTARY: "{title} ({year})/{title} ({year}){quality}",
            MediaType.VARIETY: "{title} ({year})/Season {season:02d}/{title} - S{season:02d}E{episode:02d}{quality}"
        }
    
    def recommend_name(self, meta: MetaInfo, mediainfo: MediaInfo) -> Optional[str]:
        """
        获取重命名后的名称
        :param meta: 元数据
        :param mediainfo: 媒体信息
        :return: 重命名后的名称（含目录）
        """
        try:
            # 获取重命名模板
            template = self.rename_templates.get(mediainfo.type, self.rename_templates[MediaType.MOVIE])
            
            # 构建重命名字典
            rename_dict = self._get_naming_dict(meta, mediainfo)
            
            # 应用模板
            renamed_path = template.format(**rename_dict)
            
            # 清理路径中的非法字符
            renamed_path = self._clean_path(renamed_path)
            
            return renamed_path
            
        except Exception as e:
            self.logger.error(f"生成重命名路径失败: {e}")
            return None
    
    def _get_naming_dict(self, meta: MetaInfo, mediainfo: MediaInfo) -> Dict[str, Any]:
        """
        获取重命名字典
        """
        # 基础信息
        naming_dict = {
            "title": mediainfo.title or meta.title,
            "year": mediainfo.year or meta.year or "",
            "season": mediainfo.season or meta.season or 1,
            "episode": mediainfo.episode or meta.episode or 1,
            "episode_name": "",  # 需要从TMDB获取
            "quality": "",  # 需要从文件名识别
            "video_codec": "",
            "audio_codec": "",
            "group": ""
        }
        
        # 处理年份
        if naming_dict["year"]:
            naming_dict["year"] = f"({naming_dict['year']})"
        
        # 处理季集格式
        if mediainfo.type in [MediaType.TV, MediaType.ANIME, MediaType.VARIETY]:
            naming_dict["season"] = int(naming_dict["season"])
            naming_dict["episode"] = int(naming_dict["episode"])
        
        return naming_dict
    
    def _clean_path(self, path: str) -> str:
        """
        清理路径中的非法字符
        """
        # Windows非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        path = re.sub(illegal_chars, '_', path)
        
        # 清理连续的下划线
        path = re.sub(r'_+', '_', path)
        
        # 清理开头和结尾的下划线
        path = path.strip('_')
        
        return path
    
    def transfer_media(
        self,
        fileitem: FileItem,
        meta: MetaInfo,
        mediainfo: MediaInfo,
        target_directory: TransferDirectoryConf,
        target_storage: Optional[str] = None,
        target_path: Optional[Path] = None,
        transfer_type: Optional[str] = None,
        scrape: Optional[bool] = None,
        library_type_folder: Optional[bool] = None,
        library_category_folder: Optional[bool] = None,
        episodes_info: List[TmdbEpisode] = None,
        source_oper: Callable = None,
        target_oper: Callable = None
    ) -> TransferInfo:
        """
        文件整理
        :param fileitem: 文件信息
        :param meta: 预识别的元数据
        :param mediainfo: 识别的媒体信息
        :param target_directory: 目标目录配置
        :param target_storage: 目标存储
        :param target_path: 目标路径
        :param transfer_type: 转移模式
        :param scrape: 是否刮削元数据
        :param library_type_folder: 是否按媒体类型创建目录
        :param library_category_folder: 是否按媒体类别创建目录
        :param episodes_info: 当前季的全部集信息
        :param source_oper: 源存储操作对象
        :param target_oper: 目标存储操作对象
        :return: 传输信息
        """
        try:
            # 检查源文件
            if fileitem.storage == "local" and not Path(fileitem.path).exists():
                return TransferInfo(
                    success=False,
                    message=f"{fileitem.path} 不存在",
                    fileitem=fileitem
                )
            
            # 获取目标路径
            if target_directory:
                # 检查目标目录配置
                if not target_directory.library_path:
                    return TransferInfo(
                        success=False,
                        message="目标媒体库目录未设置",
                        fileitem=fileitem
                    )
                
                # 设置传输类型
                if not transfer_type:
                    transfer_type = target_directory.transfer_type
                
                # 设置目标存储
                if not target_storage:
                    target_storage = target_directory.library_storage
                
                # 构建目标路径
                target_path = self._get_dest_path(
                    mediainfo=mediainfo,
                    target_dir=target_directory,
                    need_type_folder=library_type_folder,
                    need_category_folder=library_category_folder
                )
            
            elif target_path:
                # 手动整理模式
                if not transfer_type:
                    transfer_type = "move"
                
                if not target_storage:
                    target_storage = fileitem.storage
                
                target_path = self._get_dest_path(
                    mediainfo=mediainfo,
                    target_path=target_path,
                    need_type_folder=library_type_folder,
                    need_category_folder=library_category_folder
                )
            
            else:
                return TransferInfo(
                    success=False,
                    message="未找到有效的媒体库目录",
                    fileitem=fileitem
                )
            
            # 检查传输类型支持
            if not self._check_transfer_type_support(fileitem.storage, target_storage, transfer_type):
                return TransferInfo(
                    success=False,
                    message=f"不支持的传输类型: {transfer_type}",
                    fileitem=fileitem
                )
            
            # 执行文件传输
            return self._execute_transfer(
                fileitem=fileitem,
                target_storage=target_storage,
                target_path=target_path,
                transfer_type=transfer_type,
                source_oper=source_oper,
                target_oper=target_oper
            )
            
        except Exception as e:
            self.logger.error(f"文件整理失败: {e}")
            return TransferInfo(
                success=False,
                message=str(e),
                fileitem=fileitem
            )
    
    def _get_dest_path(
        self,
        mediainfo: MediaInfo,
        target_dir: Optional[TransferDirectoryConf] = None,
        target_path: Optional[Path] = None,
        need_type_folder: Optional[bool] = None,
        need_category_folder: Optional[bool] = None
    ) -> Path:
        """
        获取目标路径
        """
        if target_dir:
            # 基于目录配置构建路径
            base_path = Path(target_dir.library_path)
            
            # 按媒体类型创建目录
            if need_type_folder or target_dir.renaming:
                base_path = base_path / mediainfo.type.value
            
            # 按分类创建目录（需要额外的分类信息）
            if need_category_folder and mediainfo.type == MediaType.TV:
                # 这里可以根据剧集类型进一步分类
                base_path = base_path / "TV Shows"
            elif need_category_folder and mediainfo.type == MediaType.MOVIE:
                base_path = base_path / "Movies"
            
            # 应用重命名
            if target_dir.renaming:
                renamed_name = self.recommend_name(MetaInfo(title=mediainfo.title), mediainfo)
                if renamed_name:
                    base_path = base_path / renamed_name
            
            return base_path
        
        elif target_path:
            # 直接使用提供的路径
            return target_path
        
        else:
            raise ValueError("必须提供目标目录配置或目标路径")
    
    def _check_transfer_type_support(self, source_storage: str, target_storage: str, transfer_type: str) -> bool:
        """
        检查传输类型是否支持
        """
        # 本地到本地：支持所有传输类型
        if source_storage == "local" and target_storage == "local":
            return transfer_type in ["copy", "move", "link", "softlink"]
        
        # 本地到网盘或网盘到本地：只支持复制和移动
        elif source_storage == "local" and target_storage != "local":
            return transfer_type in ["copy", "move"]
        
        # 网盘到网盘：只支持复制和移动
        elif source_storage != "local" and target_storage != "local":
            return transfer_type in ["copy", "move"]
        
        # 网盘到本地：只支持复制和移动
        else:
            return transfer_type in ["copy", "move"]
    
    def _execute_transfer(
        self,
        fileitem: FileItem,
        target_storage: str,
        target_path: Path,
        transfer_type: str,
        source_oper: Callable,
        target_oper: Callable
    ) -> TransferInfo:
        """
        执行文件传输
        """
        try:
            # 获取源操作对象
            if not source_oper:
                source_oper = self._get_storage_oper(fileitem.storage)
            
            if not source_oper:
                return TransferInfo(
                    success=False,
                    message=f"不支持的存储类型: {fileitem.storage}",
                    fileitem=fileitem
                )
            
            # 获取目标操作对象
            if not target_oper:
                target_oper = self._get_storage_oper(target_storage)
            
            if not target_oper:
                return TransferInfo(
                    success=False,
                    message=f"不支持的存储类型: {target_storage}",
                    fileitem=fileitem
                )
            
            # 执行传输
            if transfer_type == "copy":
                success = source_oper.copy(fileitem, target_path, fileitem.name)
            elif transfer_type == "move":
                success = source_oper.move(fileitem, target_path, fileitem.name)
            elif transfer_type == "link":
                success = source_oper.link(fileitem, target_path / fileitem.name)
            elif transfer_type == "softlink":
                success = source_oper.softlink(fileitem, target_path / fileitem.name)
            else:
                return TransferInfo(
                    success=False,
                    message=f"不支持的传输类型: {transfer_type}",
                    fileitem=fileitem
                )
            
            if success:
                return TransferInfo(
                    success=True,
                    message=f"文件{transfer_type}成功",
                    fileitem=fileitem,
                    transfer_type=transfer_type,
                    file_count=1
                )
            else:
                return TransferInfo(
                    success=False,
                    message=f"文件{transfer_type}失败",
                    fileitem=fileitem,
                    transfer_type=transfer_type
                )
            
        except Exception as e:
            self.logger.error(f"执行传输失败: {e}")
            return TransferInfo(
                success=False,
                message=str(e),
                fileitem=fileitem,
                transfer_type=transfer_type
            )
    
    def _get_storage_oper(self, storage_type: str) -> Optional[StorageBase]:
        """
        获取存储操作对象
        """
        # 这里需要实现存储管理器的获取逻辑
        # 简化实现：根据存储类型返回对应的操作对象
        if storage_type == "local":
            from .storage_local import LocalStorage
            return LocalStorage()
        elif storage_type == "cloud_123":
            from .storage_123 import Cloud123Storage
            return Cloud123Storage()
        elif storage_type == "cloud_115":
            # 115网盘存储
            # from .storage_115 import Cloud115Storage
            # return Cloud115Storage()
            pass
        
        return None
    
    def media_files(self, mediainfo: MediaInfo) -> List[FileItem]:
        """
        获取对应媒体的媒体库文件列表
        :param mediainfo: 媒体信息
        """
        ret_fileitems = []
        
        # 这里需要实现媒体库扫描逻辑
        # 简化实现：返回空列表
        
        return ret_fileitems
    
    def media_exists(self, mediainfo: MediaInfo, **kwargs) -> Optional[ExistMediaInfo]:
        """
        判断媒体文件是否存在于文件系统
        :param mediainfo: 识别的媒体信息
        :return: 如不存在返回None，存在时返回信息
        """
        # 检查媒体库
        fileitems = self.media_files(mediainfo)
        if not fileitems:
            return None
        
        if mediainfo.type == MediaType.MOVIE:
            # 电影存在任何文件为存在
            return ExistMediaInfo(type=MediaType.MOVIE)
        else:
            # 电视剧检索集数
            seasons: Dict[int, List[int]] = {}
            
            for fileitem in fileitems:
                # 解析文件名获取季集信息
                file_meta = self._parse_filename(fileitem.name)
                season_index = file_meta.season or 1
                episode_index = file_meta.episode
                
                if not episode_index:
                    continue
                
                if season_index not in seasons:
                    seasons[season_index] = []
                
                if episode_index not in seasons[season_index]:
                    seasons[season_index].append(episode_index)
            
            return ExistMediaInfo(type=MediaType.TV, seasons=seasons)
    
    def _parse_filename(self, filename: str) -> MetaInfo:
        """
        解析文件名获取元数据
        """
        # 简化实现：基本文件名解析
        meta = MetaInfo(title=filename)
        
        # 尝试从文件名中提取季集信息
        # 例如：S01E01, S1E1, 第1季第1集等
        season_episode_patterns = [
            r'[Ss](\d+)[Ee](\d+)',  # S01E01
            r'第(\d+)季.*第(\d+)集',  # 第1季第1集
            r'Season(\d+).*Episode(\d+)',  # Season1Episode1
        ]
        
        for pattern in season_episode_patterns:
            match = re.search(pattern, filename)
            if match:
                meta.season = int(match.group(1))
                meta.episode = int(match.group(2))
                meta.type = MediaType.TV
                break
        
        # 尝试提取年份
        year_match = re.search(r'\((\d{4})\)', filename)
        if year_match:
            meta.year = year_match.group(1)
        
        return meta