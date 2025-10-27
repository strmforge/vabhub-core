#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一存储基类架构
基于MoviePilot的存储架构设计
"""

from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Callable, Union
from enum import Enum


class StorageSchema(Enum):
    """支持的存储类型"""
    LOCAL = "local"
    U115 = "u115"
    RCLONE = "rclone"
    ALIST = "alist"
    SMB = "smb"


class FileItem:
    """文件项数据模型"""
    
    def __init__(self, 
                 name: str,
                 path: str,
                 type: str,
                 size: int = 0,
                 modify_time: float = 0,
                 is_dir: bool = False,
                 parent: str = None):
        self.name = name
        self.path = path
        self.type = type
        self.size = size
        self.modify_time = modify_time
        self.is_dir = is_dir
        self.parent = parent


class StorageUsage:
    """存储使用情况"""
    
    def __init__(self, total: int = 0, used: int = 0, free: int = 0):
        self.total = total
        self.used = used
        self.free = free


class StorageBase(metaclass=ABCMeta):
    """
    存储基类
    所有存储适配器必须继承此类
    """
    
    schema = None
    transtype = {}
    snapshot_check_folder_modtime = True

    def __init__(self):
        pass

    @abstractmethod
    def init_storage(self) -> bool:
        """初始化存储"""
        pass

    @abstractmethod
    def check(self) -> bool:
        """检查存储是否可用"""
        pass

    @abstractmethod
    def list(self, fileitem: FileItem) -> List[FileItem]:
        """浏览文件"""
        pass

    @abstractmethod
    def create_folder(self, fileitem: FileItem, name: str) -> Optional[FileItem]:
        """创建目录"""
        pass

    @abstractmethod
    def get_folder(self, path: Path) -> Optional[FileItem]:
        """获取目录，如目录不存在则创建"""
        pass

    @abstractmethod
    def get_item(self, path: Path) -> Optional[FileItem]:
        """获取文件或目录，不存在返回None"""
        pass

    @abstractmethod
    def delete(self, fileitem: FileItem) -> bool:
        """删除文件"""
        pass

    @abstractmethod
    def rename(self, fileitem: FileItem, name: str) -> bool:
        """重命名文件"""
        pass

    @abstractmethod
    def download(self, fileitem: FileItem, path: Path = None) -> Path:
        """下载文件，保存到本地"""
        pass

    @abstractmethod
    def upload(self, fileitem: FileItem, path: Path, 
               new_name: Optional[str] = None) -> Optional[FileItem]:
        """上传文件"""
        pass

    @abstractmethod
    def copy(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """复制文件"""
        pass

    @abstractmethod
    def move(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """移动文件"""
        pass

    @abstractmethod
    def usage(self) -> Optional[StorageUsage]:
        """存储使用情况"""
        pass

    def get_parent(self, fileitem: FileItem) -> Optional[FileItem]:
        """获取父目录"""
        return self.get_item(Path(fileitem.path).parent)

    def support_transtype(self) -> dict:
        """支持的整理方式"""
        return self.transtype

    def is_support_transtype(self, transtype: str) -> bool:
        """是否支持整理方式"""
        return transtype in self.transtype

    def snapshot(self, path: Path, last_snapshot_time: float = None, 
                 max_depth: int = 5) -> Dict[str, Dict]:
        """快照文件系统"""
        files_info = {}

        def __snapshot_file(_fileitem: FileItem, current_depth: int = 0):
            try:
                if _fileitem.is_dir:
                    if current_depth >= max_depth:
                        return

                    if (self.snapshot_check_folder_modtime and
                            last_snapshot_time and
                            _fileitem.modify_time and
                            _fileitem.modify_time <= last_snapshot_time):
                        return

                    sub_files = self.list(_fileitem)
                    for sub_file in sub_files:
                        __snapshot_file(sub_file, current_depth + 1)
                else:
                    if _fileitem.modify_time > last_snapshot_time:
                        files_info[_fileitem.path] = {
                            'size': _fileitem.size or 0,
                            'modify_time': _fileitem.modify_time,
                            'type': _fileitem.type
                        }

            except Exception as e:
                print(f"Snapshot error for {_fileitem.path}: {e}")

        fileitem = self.get_item(path)
        if not fileitem:
            return {}

        __snapshot_file(fileitem)
        return files_info


class StorageManager:
    """存储管理器"""
    
    def __init__(self):
        self.storages = {}
        self._register_builtin_storages()

    def _register_builtin_storages(self):
        """注册内置存储适配器"""
        # 本地存储
        from core.storage_local import LocalStorage
        self.register_storage(StorageSchema.LOCAL, LocalStorage)
        
        # 115网盘存储
        from core.storage_115 import U115Storage
        self.register_storage(StorageSchema.U115, U115Storage)
        
        # 阿里云盘存储
        from core.storage_alipan import AliPanStorage
        self.register_storage(StorageSchema.ALIPAN, AliPanStorage)
        
        # RClone存储
        from core.storage_rclone import RCloneStorage
        self.register_storage(StorageSchema.RCLONE, RCloneStorage)
        
        # OpenList存储
        from core.storage_alist import AlistStorage
        self.register_storage(StorageSchema.ALIST, AlistStorage)

    def register_storage(self, schema: StorageSchema, storage_class):
        """注册存储适配器"""
        self.storages[schema.value] = storage_class

    def get_storage(self, schema: str) -> Optional[StorageBase]:
        """获取存储适配器实例"""
        if schema in self.storages:
            return self.storages[schema]()
        return None

    def list_available_storages(self) -> List[str]:
        """列出可用的存储类型"""
        return list(self.storages.keys())

    def check_storage_availability(self, schema: str) -> bool:
        """检查存储是否可用"""
        storage = self.get_storage(schema)
        if storage:
            return storage.check()
        return False