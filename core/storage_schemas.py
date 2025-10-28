"""
存储模块数据类型定义
基于MoviePilot的最佳实践
"""

from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class StorageSchema(str, Enum):
    """存储类型枚举"""
    LOCAL = "local"
    CLOUD_123 = "cloud_123"
    CLOUD_115 = "cloud_115"


class TransferType(str, Enum):
    """文件传输类型"""
    COPY = "copy"
    MOVE = "move"
    LINK = "link"
    SOFTLINK = "softlink"


class FileItem(BaseModel):
    """文件项"""
    storage: str = Field(..., description="存储类型")
    type: str = Field(..., description="文件类型: file/dir")
    path: str = Field(..., description="文件路径")
    name: str = Field("", description="文件名")
    basename: str = Field("", description="文件基本名（不含扩展名）")
    extension: Optional[str] = Field(None, description="文件扩展名")
    size: Optional[int] = Field(None, description="文件大小")
    modify_time: Optional[float] = Field(None, description="修改时间")
    create_time: Optional[float] = Field(None, description="创建时间")


class StorageUsage(BaseModel):
    """存储使用情况"""
    total: float = Field(0.0, description="总空间（GB）")
    available: float = Field(0.0, description="可用空间（GB）")
    used: float = Field(0.0, description="已用空间（GB）")
    usage_percent: float = Field(0.0, description="使用百分比")


class StorageConf(BaseModel):
    """存储配置"""
    name: str = Field(..., description="存储名称")
    schema: StorageSchema = Field(..., description="存储类型")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置信息")
    enabled: bool = Field(True, description="是否启用")


class TransferInfo(BaseModel):
    """文件传输信息"""
    success: bool = Field(False, description="是否成功")
    message: str = Field("", description="消息")
    fileitem: Optional[FileItem] = Field(None, description="源文件项")
    target_item: Optional[FileItem] = Field(None, description="目标文件项")
    transfer_type: Optional[str] = Field(None, description="传输类型")
    file_count: int = Field(0, description="处理文件数")
    fail_list: List[str] = Field(default_factory=list, description="失败文件列表")
    need_notify: bool = Field(False, description="是否需要通知")


class TransferDirectoryConf(BaseModel):
    """传输目录配置"""
    name: str = Field(..., description="目录名称")
    download_path: str = Field("", description="下载目录路径")
    library_path: str = Field("", description="媒体库目录路径")
    storage: str = Field("local", description="存储类型")
    library_storage: str = Field("local", description="媒体库存储类型")
    transfer_type: Optional[str] = Field(None, description="传输类型")
    renaming: bool = Field(True, description="是否重命名")
    scraping: bool = Field(True, description="是否刮削")
    notify: bool = Field(True, description="是否通知")
    overwrite_mode: str = Field("never", description="覆盖模式: always/size/never/latest")


class StorageTransType(BaseModel):
    """存储传输类型"""
    transtype: Optional[Dict[str, str]] = Field(default_factory=dict, description="支持的传输类型")


class MediaType(str, Enum):
    """媒体类型"""
    MOVIE = "movie"
    TV = "tv"
    ANIME = "anime"
    DOCUMENTARY = "documentary"
    VARIETY = "variety"
    UNKNOWN = "unknown"


class MediaInfo(BaseModel):
    """媒体信息"""
    type: MediaType = Field(..., description="媒体类型")
    title: str = Field("", description="标题")
    year: Optional[str] = Field(None, description="年份")
    season: Optional[int] = Field(None, description="季数")
    episode: Optional[int] = Field(None, description="集数")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID")
    douban_id: Optional[str] = Field(None, description="豆瓣ID")


class MetaInfo(BaseModel):
    """元数据信息"""
    title: str = Field("", description="标题")
    year: Optional[str] = Field(None, description="年份")
    season: Optional[int] = Field(None, description="季数")
    episode: Optional[int] = Field(None, description="集数")
    type: MediaType = Field(MediaType.UNKNOWN, description="媒体类型")


class ExistMediaInfo(BaseModel):
    """已存在媒体信息"""
    type: MediaType = Field(..., description="媒体类型")
    seasons: Optional[Dict[int, List[int]]] = Field(None, description="已存在的季集信息")


class TmdbEpisode(BaseModel):
    """TMDB剧集信息"""
    episode_number: int = Field(..., description="集数")
    name: str = Field("", description="集名")
    overview: str = Field("", description="简介")
    air_date: Optional[str] = Field(None, description="播出日期")