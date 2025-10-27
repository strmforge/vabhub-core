#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体数据访问对象 (DAO)
提供对媒体数据的CRUD操作
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from core.media_models import MediaLibrary, MediaItem, TVSeason, TVEpisode, Plugin, SystemSettings

logger = structlog.get_logger()


class MediaDAO:
    """媒体数据访问对象"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    # 媒体库操作
    async def create_library(self, library_data: Dict[str, Any]) -> MediaLibrary:
        """创建媒体库"""
        try:
            library = MediaLibrary(**library_data)
            self.db_session.add(library)
            await self.db_session.commit()
            await self.db_session.refresh(library)
            return library
        except Exception as e:
            await self.db_session.rollback()
            logger.error("创建媒体库失败", error=str(e))
            raise
    
    async def get_library(self, library_id: int) -> Optional[MediaLibrary]:
        """获取媒体库"""
        try:
            result = await self.db_session.execute(
                select(MediaLibrary).where(MediaLibrary.id == library_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("获取媒体库失败", error=str(e))
            return None
    
    async def get_all_libraries(self, enabled_only: bool = True) -> List[MediaLibrary]:
        """获取所有媒体库"""
        try:
            query = select(MediaLibrary)
            if enabled_only:
                query = query.where(MediaLibrary.enabled == True)
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error("获取媒体库列表失败", error=str(e))
            return []
    
    async def update_library(self, library_id: int, updates: Dict[str, Any]) -> bool:
        """更新媒体库"""
        try:
            await self.db_session.execute(
                update(MediaLibrary)
                .where(MediaLibrary.id == library_id)
                .values(**updates)
            )
            await self.db_session.commit()
            return True
        except Exception as e:
            await self.db_session.rollback()
            logger.error("更新媒体库失败", error=str(e))
            return False
    
    async def delete_library(self, library_id: int) -> bool:
        """删除媒体库"""
        try:
            await self.db_session.execute(
                delete(MediaLibrary).where(MediaLibrary.id == library_id)
            )
            await self.db_session.commit()
            return True
        except Exception as e:
            await self.db_session.rollback()
            logger.error("删除媒体库失败", error=str(e))
            return False
    
    # 媒体项目操作
    async def create_media_item(self, media_data: Dict[str, Any]) -> MediaItem:
        """创建媒体项目"""
        try:
            media_item = MediaItem(**media_data)
            self.db_session.add(media_item)
            await self.db_session.commit()
            await self.db_session.refresh(media_item)
            return media_item
        except Exception as e:
            await self.db_session.rollback()
            logger.error("创建媒体项目失败", error=str(e))
            raise
    
    async def get_media_item(self, media_id: int) -> Optional[MediaItem]:
        """获取媒体项目"""
        try:
            result = await self.db_session.execute(
                select(MediaItem).where(MediaItem.id == media_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("获取媒体项目失败", error=str(e))
            return None
    
    async def get_media_items(
        self, 
        library_id: Optional[int] = None,
        media_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[MediaItem]:
        """获取媒体项目列表"""
        try:
            query = select(MediaItem)
            
            # 添加过滤条件
            if library_id:
                query = query.where(MediaItem.library_id == library_id)
            
            if media_type:
                query = query.where(MediaItem.type == media_type)
            
            if search:
                query = query.where(
                    or_(
                        MediaItem.title.ilike(f"%{search}%"),
                        MediaItem.original_title.ilike(f"%{search}%")
                    )
                )
            
            # 添加分页
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            # 按创建时间倒序排列
            query = query.order_by(MediaItem.created_at.desc())
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error("获取媒体项目列表失败", error=str(e))
            return []
    
    async def get_media_count(
        self, 
        library_id: Optional[int] = None,
        media_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> int:
        """获取媒体项目数量"""
        try:
            query = select(MediaItem.id)
            
            if library_id:
                query = query.where(MediaItem.library_id == library_id)
            
            if media_type:
                query = query.where(MediaItem.type == media_type)
            
            if search:
                query = query.where(
                    or_(
                        MediaItem.title.ilike(f"%{search}%"),
                        MediaItem.original_title.ilike(f"%{search}%")
                    )
                )
            
            result = await self.db_session.execute(query)
            return len(result.scalars().all())
        except Exception as e:
            logger.error("获取媒体项目数量失败", error=str(e))
            return 0
    
    async def update_media_item(self, media_id: int, updates: Dict[str, Any]) -> bool:
        """更新媒体项目"""
        try:
            await self.db_session.execute(
                update(MediaItem)
                .where(MediaItem.id == media_id)
                .values(**updates)
            )
            await self.db_session.commit()
            return True
        except Exception as e:
            await self.db_session.rollback()
            logger.error("更新媒体项目失败", error=str(e))
            return False
    
    async def delete_media_item(self, media_id: int) -> bool:
        """删除媒体项目"""
        try:
            await self.db_session.execute(
                delete(MediaItem).where(MediaItem.id == media_id)
            )
            await self.db_session.commit()
            return True
        except Exception as e:
            await self.db_session.rollback()
            logger.error("删除媒体项目失败", error=str(e))
            return False
    
    # 插件操作
    async def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """获取插件"""
        try:
            result = await self.db_session.execute(
                select(Plugin).where(Plugin.id == plugin_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("获取插件失败", error=str(e))
            return None
    
    async def get_all_plugins(self, installed_only: bool = False) -> List[Plugin]:
        """获取所有插件"""
        try:
            query = select(Plugin)
            if installed_only:
                query = query.where(Plugin.installed == True)
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error("获取插件列表失败", error=str(e))
            return []
    
    async def create_or_update_plugin(self, plugin_data: Dict[str, Any]) -> Plugin:
        """创建或更新插件"""
        try:
            plugin_id = plugin_data.get('id')
            existing_plugin = await self.get_plugin(plugin_id)
            
            if existing_plugin:
                # 更新现有插件
                await self.db_session.execute(
                    update(Plugin)
                    .where(Plugin.id == plugin_id)
                    .values(**plugin_data)
                )
                await self.db_session.commit()
                await self.db_session.refresh(existing_plugin)
                return existing_plugin
            else:
                # 创建新插件
                plugin = Plugin(**plugin_data)
                self.db_session.add(plugin)
                await self.db_session.commit()
                await self.db_session.refresh(plugin)
                return plugin
        except Exception as e:
            await self.db_session.rollback()
            logger.error("创建或更新插件失败", error=str(e))
            raise
    
    async def update_plugin_status(self, plugin_id: str, enabled: bool) -> bool:
        """更新插件状态"""
        try:
            await self.db_session.execute(
                update(Plugin)
                .where(Plugin.id == plugin_id)
                .values(enabled=enabled)
            )
            await self.db_session.commit()
            return True
        except Exception as e:
            await self.db_session.rollback()
            logger.error("更新插件状态失败", error=str(e))
            return False
    
    # 系统设置操作
    async def get_setting(self, key: str) -> Optional[SystemSettings]:
        """获取系统设置"""
        try:
            result = await self.db_session.execute(
                select(SystemSettings).where(SystemSettings.key == key)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("获取系统设置失败", error=str(e))
            return None
    
    async def get_all_settings(self, category: Optional[str] = None) -> List[SystemSettings]:
        """获取所有系统设置"""
        try:
            query = select(SystemSettings)
            if category:
                query = query.where(SystemSettings.category == category)
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error("获取系统设置列表失败", error=str(e))
            return []
    
    async def set_setting(self, key: str, value: Any, description: str = "", category: str = "general") -> SystemSettings:
        """设置系统设置"""
        try:
            existing_setting = await self.get_setting(key)
            
            if existing_setting:
                # 更新现有设置
                await self.db_session.execute(
                    update(SystemSettings)
                    .where(SystemSettings.key == key)
                    .values(value=value, description=description, category=category)
                )
                await self.db_session.commit()
                await self.db_session.refresh(existing_setting)
                return existing_setting
            else:
                # 创建新设置
                setting = SystemSettings(
                    key=key,
                    value=value,
                    description=description,
                    category=category
                )
                self.db_session.add(setting)
                await self.db_session.commit()
                await self.db_session.refresh(setting)
                return setting
        except Exception as e:
            await self.db_session.rollback()
            logger.error("设置系统设置失败", error=str(e))
            raise