#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体管理数据库模型
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, List, Optional

Base = declarative_base()


class MediaLibrary(Base):
    """媒体库"""
    __tablename__ = "media_libraries"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    path = Column(String(1000), nullable=False)
    type = Column(String(50), nullable=False)  # movie, tv, music, photo
    enabled = Column(Boolean, default=True)
    auto_scan = Column(Boolean, default=True)
    scan_interval = Column(Integer, default=6)  # 小时
    last_scan_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    media_items = relationship("MediaItem", back_populates="library")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "enabled": self.enabled,
            "auto_scan": self.auto_scan,
            "scan_interval": self.scan_interval,
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class MediaItem(Base):
    """媒体项目"""
    __tablename__ = "media_items"
    
    id = Column(Integer, primary_key=True, index=True)
    library_id = Column(Integer, ForeignKey("media_libraries.id"), nullable=False)
    title = Column(String(500), nullable=False)
    original_title = Column(String(500), nullable=True)
    type = Column(String(50), nullable=False)  # movie, tv, music, photo
    year = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    poster = Column(String(1000), nullable=True)
    backdrop = Column(String(1000), nullable=True)
    path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=True)  # 秒
    file_format = Column(String(50), nullable=True)
    resolution = Column(String(50), nullable=True)
    tmdb_id = Column(Integer, nullable=True, index=True)
    imdb_id = Column(String(50), nullable=True, index=True)
    metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)  # 标签列表
    watched = Column(Boolean, default=False)
    favorite = Column(Boolean, default=False)
    created_time = Column(DateTime, nullable=False)
    file_modified_time = Column(DateTime, nullable=False)
    last_accessed_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    library = relationship("MediaLibrary", back_populates="media_items")
    tv_seasons = relationship("TVSeason", back_populates="media_item")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "library_id": self.library_id,
            "title": self.title,
            "original_title": self.original_title,
            "type": self.type,
            "year": self.year,
            "rating": self.rating,
            "poster": self.poster,
            "backdrop": self.backdrop,
            "path": self.path,
            "file_size": self.file_size,
            "duration": self.duration,
            "file_format": self.file_format,
            "resolution": self.resolution,
            "tmdb_id": self.tmdb_id,
            "imdb_id": self.imdb_id,
            "metadata": self.metadata or {},
            "tags": self.tags or [],
            "watched": self.watched,
            "favorite": self.favorite,
            "created_time": self.created_time.isoformat() if self.created_time else None,
            "file_modified_time": self.file_modified_time.isoformat() if self.file_modified_time else None,
            "last_accessed_time": self.last_accessed_time.isoformat() if self.last_accessed_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class TVSeason(Base):
    """电视剧季"""
    __tablename__ = "tv_seasons"
    
    id = Column(Integer, primary_key=True, index=True)
    media_item_id = Column(Integer, ForeignKey("media_items.id"), nullable=False)
    season_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=True)
    overview = Column(Text, nullable=True)
    poster = Column(String(1000), nullable=True)
    air_date = Column(DateTime, nullable=True)
    episode_count = Column(Integer, nullable=False, default=0)
    watched_episodes = Column(Integer, nullable=False, default=0)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    media_item = relationship("MediaItem", back_populates="tv_seasons")
    episodes = relationship("TVEpisode", back_populates="season")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "media_item_id": self.media_item_id,
            "season_number": self.season_number,
            "title": self.title,
            "overview": self.overview,
            "poster": self.poster,
            "air_date": self.air_date.isoformat() if self.air_date else None,
            "episode_count": self.episode_count,
            "watched_episodes": self.watched_episodes,
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class TVEpisode(Base):
    """电视剧集"""
    __tablename__ = "tv_episodes"
    
    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("tv_seasons.id"), nullable=False)
    episode_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    overview = Column(Text, nullable=True)
    still_path = Column(String(1000), nullable=True)
    air_date = Column(DateTime, nullable=True)
    runtime = Column(Integer, nullable=True)  # 分钟
    rating = Column(Float, nullable=True)
    path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_format = Column(String(50), nullable=True)
    resolution = Column(String(50), nullable=True)
    tmdb_id = Column(Integer, nullable=True)
    watched = Column(Boolean, default=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    season = relationship("TVSeason", back_populates="episodes")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "season_id": self.season_id,
            "episode_number": self.episode_number,
            "title": self.title,
            "overview": self.overview,
            "still_path": self.still_path,
            "air_date": self.air_date.isoformat() if self.air_date else None,
            "runtime": self.runtime,
            "rating": self.rating,
            "path": self.path,
            "file_size": self.file_size,
            "file_format": self.file_format,
            "resolution": self.resolution,
            "tmdb_id": self.tmdb_id,
            "watched": self.watched,
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Plugin(Base):
    """插件信息"""
    __tablename__ = "plugins"
    
    id = Column(String(100), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    version = Column(String(50), nullable=False)
    author = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    homepage = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=False)
    installed = Column(Boolean, default=False)
    install_path = Column(String(1000), nullable=True)
    dependencies = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "homepage": self.homepage,
            "enabled": self.enabled,
            "installed": self.installed,
            "install_path": self.install_path,
            "dependencies": self.dependencies or [],
            "settings": self.settings or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class SystemSettings(Base):
    """系统设置"""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(200), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False, default="general")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }