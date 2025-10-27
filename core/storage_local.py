#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地存储适配器
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List

from core.storage_base import StorageBase, StorageSchema, FileItem, StorageUsage


class LocalStorage(StorageBase):
    """本地存储适配器"""
    
    schema = StorageSchema.LOCAL
    transtype = {
        "move": "移动",
        "copy": "复制",
        "link": "硬链接",
        "softlink": "软链接"
    }

    def __init__(self):
        super().__init__()
        self.base_path = Path.cwd()

    def init_storage(self) -> bool:
        """初始化存储"""
        return True

    def check(self) -> bool:
        """检查存储是否可用"""
        return os.path.exists(self.base_path)

    def list(self, fileitem: FileItem) -> List[FileItem]:
        """浏览文件"""
        if not fileitem.is_dir:
            return []
        
        path = Path(fileitem.path)
        if not path.exists():
            return []
        
        items = []
        try:
            for item in path.iterdir():
                stat = item.stat()
                file_item = FileItem(
                    name=item.name,
                    path=str(item),
                    type="dir" if item.is_dir() else "file",
                    size=stat.st_size if item.is_file() else 0,
                    modify_time=stat.st_mtime,
                    is_dir=item.is_dir(),
                    parent=str(path)
                )
                items.append(file_item)
        except Exception as e:
            print(f"List files error: {e}")
        
        return items

    def create_folder(self, fileitem: FileItem, name: str) -> Optional[FileItem]:
        """创建目录"""
        if not fileitem.is_dir:
            return None
        
        new_path = Path(fileitem.path) / name
        try:
            new_path.mkdir(parents=True, exist_ok=True)
            return FileItem(
                name=name,
                path=str(new_path),
                type="dir",
                is_dir=True,
                parent=str(fileitem.path)
            )
        except Exception as e:
            print(f"Create folder error: {e}")
            return None

    def get_folder(self, path: Path) -> Optional[FileItem]:
        """获取目录，如目录不存在则创建"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return FileItem(
                name=path.name,
                path=str(path),
                type="dir",
                is_dir=True,
                parent=str(path.parent)
            )
        except Exception as e:
            print(f"Get folder error: {e}")
            return None

    def get_item(self, path: Path) -> Optional[FileItem]:
        """获取文件或目录"""
        if not path.exists():
            return None
        
        stat = path.stat()
        return FileItem(
            name=path.name,
            path=str(path),
            type="dir" if path.is_dir() else "file",
            size=stat.st_size if path.is_file() else 0,
            modify_time=stat.st_mtime,
            is_dir=path.is_dir(),
            parent=str(path.parent)
        )

    def delete(self, fileitem: FileItem) -> bool:
        """删除文件"""
        path = Path(fileitem.path)
        try:
            if fileitem.is_dir:
                shutil.rmtree(path)
            else:
                path.unlink()
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False

    def rename(self, fileitem: FileItem, name: str) -> bool:
        """重命名文件"""
        old_path = Path(fileitem.path)
        new_path = old_path.parent / name
        
        try:
            old_path.rename(new_path)
            return True
        except Exception as e:
            print(f"Rename error: {e}")
            return False

    def download(self, fileitem: FileItem, path: Path = None) -> Path:
        """下载文件（本地存储直接返回路径）"""
        return Path(fileitem.path)

    def upload(self, fileitem: FileItem, path: Path, 
               new_name: Optional[str] = None) -> Optional[FileItem]:
        """上传文件（本地存储直接复制）"""
        if not fileitem.is_dir:
            return None
        
        target_name = new_name or path.name
        target_path = Path(fileitem.path) / target_name
        
        try:
            shutil.copy2(path, target_path)
            return self.get_item(target_path)
        except Exception as e:
            print(f"Upload error: {e}")
            return None

    def copy(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """复制文件"""
        source_path = Path(fileitem.path)
        target_path = path / new_name
        
        try:
            if fileitem.is_dir:
                shutil.copytree(source_path, target_path)
            else:
                shutil.copy2(source_path, target_path)
            return True
        except Exception as e:
            print(f"Copy error: {e}")
            return False

    def move(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """移动文件"""
        source_path = Path(fileitem.path)
        target_path = path / new_name
        
        try:
            shutil.move(str(source_path), str(target_path))
            return True
        except Exception as e:
            print(f"Move error: {e}")
            return False

    def link(self, fileitem: FileItem, target_file: Path) -> bool:
        """硬链接文件"""
        source_path = Path(fileitem.path)
        
        try:
            os.link(source_path, target_file)
            return True
        except Exception as e:
            print(f"Link error: {e}")
            return False

    def softlink(self, fileitem: FileItem, target_file: Path) -> bool:
        """软链接文件"""
        source_path = Path(fileitem.path)
        
        try:
            os.symlink(source_path, target_file)
            return True
        except Exception as e:
            print(f"Softlink error: {e}")
            return False

    def usage(self) -> Optional[StorageUsage]:
        """存储使用情况"""
        try:
            stat = shutil.disk_usage(self.base_path)
            return StorageUsage(
                total=stat.total,
                used=stat.used,
                free=stat.free
            )
        except Exception as e:
            print(f"Get usage error: {e}")
            return None