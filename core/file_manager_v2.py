"""
文件管理器主模块 (v2)
基于MoviePilot设计，完整复刻存储管理功能
与配置系统集成
"""

import os
import shutil
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import logging

from .storage_base import StorageBase
from .storage_local import LocalStorage
from .storage_123 import Cloud123Storage
from .storage_schemas import (
    StorageInfo, FileItem, TransferRequest, TransferResult,
    RenameRequest, RenameResult, MediaInfo, NamingRule
)
from .system_utils import SystemUtils
from .storage_config import get_config_manager


class FileManager:
    """文件管理器主类"""
    
    def __init__(self):
        self.logger = logging.getLogger("file_manager")
        self.config_manager = get_config_manager()
        self.storages: Dict[str, StorageBase] = {}
        self._initialize_storages()
    
    def _initialize_storages(self):
        """初始化存储实例"""
        config = self.config_manager.settings
        if not config:
            self.logger.error("配置加载失败，无法初始化存储")
            return
        
        # 初始化本地存储
        if "local" in config.storages and config.storages["local"].get("enabled", True):
            local_config = config.storages["local"]
            try:
                self.storages["local"] = LocalStorage(
                    name=local_config.get("name", "本地存储"),
                    description=local_config.get("description", "本地文件系统存储"),
                    root_path=local_config.get("root_path", "/data")
                )
                self.logger.info("本地存储初始化成功")
            except Exception as e:
                self.logger.error(f"本地存储初始化失败: {e}")
        
        # 初始化123云盘存储
        if "123cloud" in config.storages and config.storages["123cloud"].get("enabled", True):
            cloud_config = config.storages["123cloud"]
            try:
                self.storages["123cloud"] = Cloud123Storage(
                    name=cloud_config.get("name", "123云盘"),
                    description=cloud_config.get("description", "123云盘存储"),
                    app_id=cloud_config.get("app_id", ""),
                    app_secret=cloud_config.get("app_secret", "")
                )
                self.logger.info("123云盘存储初始化成功")
            except Exception as e:
                self.logger.error(f"123云盘存储初始化失败: {e}")
    
    def list_storages(self) -> List[StorageInfo]:
        """获取存储列表"""
        storages = []
        
        for storage_id, storage in self.storages.items():
            try:
                storage_info = storage.get_info()
                storages.append(storage_info)
            except Exception as e:
                self.logger.error(f"获取存储 {storage_id} 信息失败: {e}")
        
        return storages
    
    def get_storage(self, storage_id: str) -> Optional[StorageBase]:
        """获取存储实例"""
        return self.storages.get(storage_id)
    
    def list_files(self, storage_id: str, path: str = "/", recursive: bool = False, 
                  page: int = 1, size: int = 100) -> Tuple[List[FileItem], int]:
        """浏览文件列表"""
        storage = self.get_storage(storage_id)
        if not storage:
            raise ValueError(f"存储 {storage_id} 不存在")
        
        # 验证路径安全性
        if not self.config_manager.validate_path(path):
            raise ValueError(f"路径 {path} 不在允许的路径列表中")
        
        try:
            files = storage.list_files(path, recursive)
            
            # 分页处理
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_files = files[start_idx:end_idx]
            
            return paginated_files, len(files)
        except Exception as e:
            self.logger.error(f"浏览文件失败: {e}")
            raise
    
    def create_directory(self, storage_id: str, path: str) -> bool:
        """创建目录"""
        storage = self.get_storage(storage_id)
        if not storage:
            raise ValueError(f"存储 {storage_id} 不存在")
        
        # 验证路径安全性
        if not self.config_manager.validate_path(path):
            raise ValueError(f"路径 {path} 不在允许的路径列表中")
        
        try:
            return storage.create_directory(path)
        except Exception as e:
            self.logger.error(f"创建目录失败: {e}")
            raise
    
    def delete_files(self, storage_id: str, paths: List[str]) -> bool:
        """删除文件/目录"""
        storage = self.get_storage(storage_id)
        if not storage:
            raise ValueError(f"存储 {storage_id} 不存在")
        
        # 验证路径安全性
        for path in paths:
            if not self.config_manager.validate_path(path):
                raise ValueError(f"路径 {path} 不在允许的路径列表中")
        
        try:
            return storage.delete_files(paths)
        except Exception as e:
            self.logger.error(f"删除文件失败: {e}")
            raise
    
    def rename_file(self, storage_id: str, old_path: str, new_path: str) -> bool:
        """重命名文件"""
        storage = self.get_storage(storage_id)
        if not storage:
            raise ValueError(f"存储 {storage_id} 不存在")
        
        # 验证路径安全性
        if not self.config_manager.validate_path(old_path) or not self.config_manager.validate_path(new_path):
            raise ValueError("路径不在允许的路径列表中")
        
        try:
            return storage.rename_file(old_path, new_path)
        except Exception as e:
            self.logger.error(f"重命名文件失败: {e}")
            raise
    
    def transfer_files(self, source_storage: str, source_paths: List[str], 
                      target_storage: str, target_path: str, 
                      transfer_type: str = "copy", overwrite: bool = False) -> List[TransferResult]:
        """转移文件"""
        source = self.get_storage(source_storage)
        target = self.get_storage(target_storage)
        
        if not source:
            raise ValueError(f"源存储 {source_storage} 不存在")
        if not target:
            raise ValueError(f"目标存储 {target_storage} 不存在")
        
        # 验证路径安全性
        for path in source_paths:
            if not self.config_manager.validate_path(path):
                raise ValueError(f"源路径 {path} 不在允许的路径列表中")
        if not self.config_manager.validate_path(target_path):
            raise ValueError(f"目标路径 {target_path} 不在允许的路径列表中")
        
        # 验证传输类型
        config = self.config_manager.settings
        if config:
            source_config = config.storages.get(source_storage, {})
            target_config = config.storages.get(target_storage, {})
            
            source_transfer_types = source_config.get("transfer_types", [])
            target_transfer_types = target_config.get("transfer_types", [])
            
            if transfer_type not in source_transfer_types:
                raise ValueError(f"源存储不支持传输类型: {transfer_type}")
            if transfer_type not in target_transfer_types:
                raise ValueError(f"目标存储不支持传输类型: {transfer_type}")
        
        try:
            results = []
            for source_path in source_paths:
                result = source.transfer_file(
                    source_path=source_path,
                    target_storage=target,
                    target_path=target_path,
                    transfer_type=transfer_type,
                    overwrite=overwrite
                )
                results.append(result)
            
            return results
        except Exception as e:
            self.logger.error(f"文件转移失败: {e}")
            raise
    
    def rename_media(self, storage_id: str, file_path: str, 
                    media_info: MediaInfo, naming_rule: str = "auto") -> RenameResult:
        """智能重命名媒体文件"""
        storage = self.get_storage(storage_id)
        if not storage:
            raise ValueError(f"存储 {storage_id} 不存在")
        
        # 验证路径安全性
        if not self.config_manager.validate_path(file_path):
            raise ValueError(f"路径 {file_path} 不在允许的路径列表中")
        
        try:
            # 获取文件信息
            files = storage.list_files(os.path.dirname(file_path))
            file_info = next((f for f in files if f.path == file_path), None)
            
            if not file_info:
                raise ValueError(f"文件 {file_path} 不存在")
            
            # 确定命名规则
            if naming_rule == "auto":
                naming_rule = self._detect_naming_rule(media_info)
            
            # 生成新文件名
            new_name = self._generate_new_filename(media_info, naming_rule)
            new_path = os.path.join(os.path.dirname(file_path), new_name)
            
            # 执行重命名
            success = storage.rename_file(file_path, new_path)
            
            return RenameResult(
                success=success,
                old_path=file_path,
                new_path=new_path,
                message="重命名成功" if success else "重命名失败"
            )
        except Exception as e:
            self.logger.error(f"重命名媒体文件失败: {e}")
            raise
    
    def _detect_naming_rule(self, media_info: MediaInfo) -> str:
        """检测命名规则"""
        if media_info.media_type == "movie":
            return "movie"
        elif media_info.media_type == "tv":
            return "tv"
        elif media_info.media_type == "anime":
            return "anime"
        else:
            return "movie"  # 默认使用电影命名规则
    
    def _generate_new_filename(self, media_info: MediaInfo, naming_rule: str) -> str:
        """生成新文件名"""
        config = self.config_manager.settings
        if not config:
            raise ValueError("配置未加载")
        
        pattern = config.renaming.movie_pattern  # 默认使用电影模式
        
        if naming_rule == "tv" and hasattr(config.renaming, 'tv_pattern'):
            pattern = config.renaming.tv_pattern
        elif naming_rule == "anime" and hasattr(config.renaming, 'anime_pattern'):
            pattern = config.renaming.anime_pattern
        
        # 替换模板变量
        filename = pattern.format(
            title=media_info.title,
            year=media_info.year or "",
            season=media_info.season or 1,
            episode=media_info.episode or 1,
            episode_title=media_info.episode_title or "",
            quality=media_info.quality or "",
            edition=media_info.edition or ""
        )
        
        # 清理文件名中的非法字符
        filename = self._sanitize_filename(filename)
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # 替换非法字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 移除多余的空格和分隔符
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        return filename
    
    def test_storage(self, storage_id: str) -> Tuple[bool, str]:
        """测试存储连接"""
        storage = self.get_storage(storage_id)
        if not storage:
            return False, f"存储 {storage_id} 不存在"
        
        try:
            success = storage.test_connection()
            message = "连接测试成功" if success else "连接测试失败"
            return success, message
        except Exception as e:
            return False, f"连接测试异常: {e}"
    
    def search_files(self, storage_id: str, keyword: str, 
                    extensions: Optional[List[str]] = None, 
                    path: str = "/") -> List[FileItem]:
        """搜索文件"""
        storage = self.get_storage(storage_id)
        if not storage:
            raise ValueError(f"存储 {storage_id} 不存在")
        
        # 验证路径安全性
        if not self.config_manager.validate_path(path):
            raise ValueError(f"路径 {path} 不在允许的路径列表中")
        
        try:
            return storage.search_files(keyword, extensions, path)
        except Exception as e:
            self.logger.error(f"搜索文件失败: {e}")
            raise
    
    def get_storage_space(self, storage_id: str) -> Dict[str, Any]:
        """获取存储空间信息"""
        storage = self.get_storage(storage_id)
        if not storage:
            raise ValueError(f"存储 {storage_id} 不存在")
        
        try:
            return storage.get_space_info()
        except Exception as e:
            self.logger.error(f"获取存储空间信息失败: {e}")
            raise
    
    def get_qrcode(self, storage_id: str) -> Dict[str, Any]:
        """获取二维码登录信息"""
        storage = self.get_storage(storage_id)
        if not storage:
            raise ValueError(f"存储 {storage_id} 不存在")
        
        try:
            return storage.get_qrcode()
        except Exception as e:
            self.logger.error(f"获取二维码失败: {e}")
            raise
    
    def check_login_status(self, storage_id: str) -> Dict[str, Any]:
        """检查登录状态"""
        storage = self.get_storage(storage_id)
        if not storage:
            raise ValueError(f"存储 {storage_id} 不存在")
        
        try:
            return storage.check_login_status()
        except Exception as e:
            self.logger.error(f"检查登录状态失败: {e}")
            raise


# 全局文件管理器实例
_file_manager: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    """获取文件管理器实例"""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager


# 导入正则表达式模块
import re