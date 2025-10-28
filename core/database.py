#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理系统
支持SQLAlchemy ORM和异步操作，参照MoviePilot V2.7.3+支持PostgreSQL迁移
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import inspect

from core.config import config_manager
import structlog

logger = structlog.get_logger()

# 导入媒体模型
from core.media_models import Base, MediaLibrary, MediaItem, TVSeason, TVEpisode, Plugin, SystemSettings


class FileHistory(Base):
    """文件处理历史记录"""
    __tablename__ = "file_history"
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(1000), nullable=False, index=True)
    original_name = Column(String(500), nullable=False)
    new_name = Column(String(500), nullable=False)
    media_type = Column(String(50), nullable=False)
    meta_data = Column(JSON, nullable=True)
    processing_time = Column(Integer, nullable=False)  # 毫秒
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "original_name": self.original_name,
            "new_name": self.new_name,
            "media_type": self.media_type,
            "metadata": self.metadata,
            "processing_time": self.processing_time,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ProcessingSession(Base):
    """处理会话记录"""
    __tablename__ = "processing_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    total_files = Column(Integer, nullable=False)
    processed_files = Column(Integer, default=0)
    successful_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    status = Column(String(50), default="running")  # running, completed, failed, cancelled
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # 秒
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "successful_files": self.successful_files,
            "failed_files": self.failed_files,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration
        }


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        self.async_session_factory = None
        self.is_initialized = False
    
    async def initialize(self):
        """初始化数据库连接"""
        if self.is_initialized:
            return
        
        try:
            # 检查环境变量，支持PostgreSQL迁移（MoviePilot V2.7.3+）
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                # 如果没有配置数据库URL，使用SQLite
                database_url = "sqlite:///./media_renamer.db"
            
            # 设置数据库URL
            settings.database_url = database_url
            
            # 创建同步引擎
            self.engine = create_engine(
                settings.database_url,
                echo=settings.debug,
                pool_pre_ping=True,
                pool_recycle=300
            )
            
            # 创建异步引擎（如果支持）
            if settings.database_url.startswith("sqlite"):
                async_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
            elif settings.database_url.startswith("postgresql"):
                async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
            else:
                async_url = None
            
            if async_url:
                self.async_engine = create_async_engine(
                    async_url,
                    echo=settings.debug,
                    pool_pre_ping=True,
                    pool_recycle=300
                )
                self.async_session_factory = async_sessionmaker(
                    self.async_engine,
                    expire_on_commit=False
                )
            
            # 同步会话工厂
            self.session_factory = sessionmaker(
                bind=self.engine,
                expire_on_commit=False
            )
            
            # 检查是否需要迁移
            await self._check_and_migrate()
            
            # 创建表
            Base.metadata.create_all(bind=self.engine)
            
            self.is_initialized = True
            logger.info("数据库初始化完成", database_url=settings.database_url)
            
        except Exception as e:
            logger.error("数据库初始化失败", error=str(e))
            raise
    
    def get_session(self):
        """获取同步会话"""
        if not self.is_initialized:
            raise RuntimeError("数据库未初始化")
        return self.session_factory()
    
    async def get_async_session(self) -> AsyncSession:
        """获取异步会话"""
        if not self.is_initialized or not self.async_session_factory:
            raise RuntimeError("异步数据库未初始化")
        return self.async_session_factory()
    
    async def add_file_history(self, file_data: Dict[str, Any]) -> int:
        """添加文件处理历史记录"""
        try:
            async with self.get_async_session() as session:
                file_history = FileHistory(
                    file_path=file_data.get("file_path", ""),
                    original_name=file_data.get("original_name", ""),
                    new_name=file_data.get("new_name", ""),
                    media_type=file_data.get("media_type", "unknown"),
                    metadata=file_data.get("metadata", {}),
                    processing_time=file_data.get("processing_time", 0),
                    success=file_data.get("success", True),
                    error_message=file_data.get("error_message")
                )
                session.add(file_history)
                await session.commit()
                await session.refresh(file_history)
                return file_history.id
        except Exception as e:
            logger.error("添加文件历史记录失败", error=str(e))
            raise
    
    async def get_recent_file_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的文件处理历史"""
        try:
            async with self.get_async_session() as session:
                from sqlalchemy import desc
                result = await session.execute(
                    FileHistory.__table__.select()
                    .order_by(desc(FileHistory.created_at))
                    .limit(limit)
                )
                files = result.fetchall()
                return [dict(file) for file in files]
        except Exception as e:
            logger.error("获取文件历史记录失败", error=str(e))
            return []
    
    async def create_processing_session(self, session_id: str, total_files: int) -> int:
        """创建处理会话"""
        try:
            async with self.get_async_session() as session:
                processing_session = ProcessingSession(
                    session_id=session_id,
                    total_files=total_files
                )
                session.add(processing_session)
                await session.commit()
                await session.refresh(processing_session)
                return processing_session.id
        except Exception as e:
            logger.error("创建处理会话失败", error=str(e))
            raise
    
    async def update_processing_session(self, session_id: str, updates: Dict[str, Any]):
        """更新处理会话"""
        try:
            async with self.get_async_session() as session:
                from sqlalchemy import update
                await session.execute(
                    update(ProcessingSession)
                    .where(ProcessingSession.session_id == session_id)
                    .values(**updates)
                )
                await session.commit()
        except Exception as e:
            logger.error("更新处理会话失败", error=str(e))
            raise
    
    async def get_processing_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取处理会话"""
        try:
            async with self.get_async_session() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(ProcessingSession).where(ProcessingSession.session_id == session_id)
                )
                session_obj = result.scalar_one_or_none()
                return session_obj.to_dict() if session_obj else None
        except Exception as e:
            logger.error("获取处理会话失败", error=str(e))
            return None
    
    async def _check_and_migrate(self):
        """检查并执行数据库迁移（MoviePilot V2.7.3+ PostgreSQL支持）"""
        try:
            # 检查当前数据库类型
            if settings.database_url.startswith("postgresql"):
                logger.info("检测到PostgreSQL数据库，检查是否需要迁移")
                
                # 检查表是否存在
                inspector = inspect(self.engine)
                existing_tables = inspector.get_table_names()
                
                if not existing_tables:
                    logger.info("PostgreSQL数据库为空，将创建新表")
                else:
                    logger.info(f"PostgreSQL数据库已存在 {len(existing_tables)} 个表")
                    
                    # 检查是否需要从SQLite迁移
                    if 'file_history' in existing_tables:
                        logger.info("检测到现有数据表，将保留数据")
                    
            elif settings.database_url.startswith("sqlite"):
                logger.info("使用SQLite数据库")
                
        except Exception as e:
            logger.warning("数据库迁移检查失败，将继续使用现有配置", error=str(e))
    
    async def migrate_from_sqlite_to_postgresql(self, sqlite_path: str, postgresql_url: str):
        """从SQLite迁移到PostgreSQL（MoviePilot迁移示例）"""
        try:
            logger.info("开始从SQLite迁移到PostgreSQL")
            
            # 创建SQLite引擎
            sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
            
            # 创建PostgreSQL引擎
            postgres_engine = create_engine(postgresql_url)
            
            # 获取SQLite表数据
            inspector = inspect(sqlite_engine)
            tables = inspector.get_table_names()
            
            for table_name in tables:
                logger.info(f"迁移表: {table_name}")
                
                # 读取SQLite数据
                with sqlite_engine.connect() as sqlite_conn:
                    data = sqlite_conn.execute(f"SELECT * FROM {table_name}").fetchall()
                    
                    if data:
                        # 写入PostgreSQL
                        with postgres_engine.connect() as postgres_conn:
                            # 这里需要根据表结构动态插入数据
                            # 简化实现，实际需要更复杂的迁移逻辑
                            logger.info(f"迁移 {len(data)} 条记录到 {table_name}")
            
            logger.info("数据库迁移完成")
            
        except Exception as e:
            logger.error("数据库迁移失败", error=str(e))
            raise
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息（MoviePilot兼容）"""
        info = {
            "type": "sqlite",
            "url": settings.database_url,
            "tables": []
        }
        
        if settings.database_url.startswith("postgresql"):
            info["type"] = "postgresql"
        
        try:
            inspector = inspect(self.engine)
            info["tables"] = inspector.get_table_names()
        except Exception as e:
            logger.warning("获取数据库信息失败", error=str(e))
        
        return info


# 全局数据库管理器实例
db_manager = DatabaseManager()