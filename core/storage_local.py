"""
本地存储模块
支持硬链接、软链接、移动、复制等完整功能
基于MoviePilot的最佳实践
"""

import shutil
from pathlib import Path
from typing import Optional, List, Tuple
import logging

from .storage_base import StorageBase
from .storage_schemas import (
    StorageSchema, FileItem, StorageUsage, StorageConf,
    TransferType
)
from .system_utils import SystemUtils


class LocalStorage(StorageBase):
    """
    本地文件存储
    支持硬链接、软链接、移动、复制等完整功能
    """
    
    schema = StorageSchema.LOCAL
    transtype = {
        TransferType.COPY: "复制",
        TransferType.MOVE: "移动", 
        TransferType.LINK: "硬链接",
        TransferType.SOFTLINK: "软链接"
    }
    
    # 文件块大小，默认10MB
    chunk_size = 10 * 1024 * 1024
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("storage.local")
    
    def init_storage(self) -> bool:
        """初始化存储"""
        return True
    
    def check(self) -> bool:
        """检查存储是否可用"""
        return True
    
    def __get_fileitem(self, path: Path) -> FileItem:
        """获取文件项"""
        stat = path.stat()
        return FileItem(
            storage=self.schema.value,
            type="file",
            path=path.as_posix(),
            name=path.name,
            basename=path.stem,
            extension=path.suffix[1:] if path.suffix else None,
            size=stat.st_size,
            modify_time=stat.st_mtime,
            create_time=stat.st_ctime
        )
    
    def __get_diritem(self, path: Path) -> FileItem:
        """获取目录项"""
        stat = path.stat()
        return FileItem(
            storage=self.schema.value,
            type="dir",
            path=path.as_posix() + "/",
            name=path.name,
            basename=path.stem,
            modify_time=stat.st_mtime,
            create_time=stat.st_ctime
        )
    
    def list(self, fileitem: FileItem) -> List[FileItem]:
        """浏览文件"""
        ret_items = []
        path = fileitem.path
        
        # 处理根目录
        if not path or path == "/":
            if SystemUtils.is_windows():
                partitions = SystemUtils.get_windows_drives() or ["C:/"]
                for partition in partitions:
                    ret_items.append(FileItem(
                        storage=self.schema.value,
                        type="dir",
                        path=partition + "/",
                        name=partition,
                        basename=partition
                    ))
                return ret_items
            else:
                path = "/"
        else:
            # Windows路径处理
            if SystemUtils.is_windows():
                path = path.lstrip("/")
            elif not path.startswith("/"):
                path = "/" + path
        
        # 遍历目录
        path_obj = Path(path)
        if not path_obj.exists():
            self.logger.warning(f"【本地】目录不存在：{path}")
            return []
        
        # 如果是文件
        if path_obj.is_file():
            ret_items.append(self.__get_fileitem(path_obj))
            return ret_items
        
        # 遍历所有子目录
        try:
            for item in path_obj.iterdir():
                if item.is_dir():
                    ret_items.append(self.__get_diritem(item))
                else:
                    ret_items.append(self.__get_fileitem(item))
        except Exception as e:
            self.logger.error(f"【本地】遍历目录失败：{e}")
        
        return ret_items
    
    def create_folder(self, fileitem: FileItem, name: str) -> Optional[FileItem]:
        """创建目录"""
        if not fileitem.path:
            return None
        
        path_obj = Path(fileitem.path) / name
        if not path_obj.exists():
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.logger.error(f"【本地】创建目录失败：{e}")
                return None
        
        return self.__get_diritem(path_obj)
    
    def get_folder(self, path: Path) -> Optional[FileItem]:
        """获取目录（不存在则创建）"""
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.logger.error(f"【本地】创建目录失败：{e}")
                return None
        
        return self.__get_diritem(path)
    
    def get_item(self, path: Path) -> Optional[FileItem]:
        """获取文件或目录"""
        if not path.exists():
            return None
        
        if path.is_file():
            return self.__get_fileitem(path)
        else:
            return self.__get_diritem(path)
    
    def detail(self, fileitem: FileItem) -> Optional[FileItem]:
        """获取文件详情"""
        path_obj = Path(fileitem.path)
        if not path_obj.exists():
            return None
        
        return self.__get_fileitem(path_obj)
    
    def delete(self, fileitem: FileItem) -> bool:
        """删除文件"""
        if not fileitem.path:
            return False
        
        path_obj = Path(fileitem.path)
        if not path_obj.exists():
            return True
        
        try:
            if path_obj.is_file():
                path_obj.unlink()
            else:
                shutil.rmtree(path_obj, ignore_errors=True)
        except Exception as e:
            self.logger.error(f"【本地】删除文件失败：{e}")
            return False
        
        return True
    
    def rename(self, fileitem: FileItem, name: str) -> bool:
        """重命名文件"""
        path_obj = Path(fileitem.path)
        if not path_obj.exists():
            return False
        
        try:
            new_path = path_obj.parent / name
            path_obj.rename(new_path)
        except Exception as e:
            self.logger.error(f"【本地】重命名文件失败：{e}")
            return False
        
        return True
    
    def download(self, fileitem: FileItem, path: Optional[Path] = None) -> Optional[Path]:
        """下载文件到本地"""
        return Path(fileitem.path)
    
    def upload(self, fileitem: FileItem, path: Path, new_name: Optional[str] = None) -> Optional[FileItem]:
        """上传文件"""
        try:
            dir_path = Path(fileitem.path)
            target_path = dir_path / (new_name or path.name)
            
            # 复制文件
            if self._copy_with_progress(path, target_path):
                # 上传后删除源文件
                path.unlink()
                return self.get_item(target_path)
        except Exception as e:
            self.logger.error(f"【本地】上传文件失败：{e}")
        
        return None
    
    def _copy_with_progress(self, src: Path, dest: Path) -> bool:
        """分块复制文件并回调进度"""
        total_size = src.stat().st_size
        copied_size = 0
        
        try:
            with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
                while True:
                    buf = fsrc.read(self.chunk_size)
                    if not buf:
                        break
                    fdst.write(buf)
                    copied_size += len(buf)
                    
                    # 更新进度
                    percent = copied_size / total_size * 100
                    self.logger.debug(f"复制进度: {percent:.1f}%")
            
            # 保留文件时间戳、权限等信息
            shutil.copystat(src, dest)
            return True
        except Exception as e:
            self.logger.error(f"【本地】复制文件 {src} 失败：{e}")
            return False
    
    def copy(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """复制文件"""
        try:
            src = Path(fileitem.path)
            dest = path / new_name
            
            if src == dest:
                return True
            
            if self._should_show_progress(src, dest):
                return self._copy_with_progress(src, dest)
            else:
                code, message = SystemUtils.copy(src, dest)
                return code == 0
        except Exception as e:
            self.logger.error(f"【本地】复制文件失败：{e}")
            return False
    
    def move(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """移动文件"""
        try:
            src = Path(fileitem.path)
            dest = path / new_name
            
            if src == dest:
                return True
            
            if self._should_show_progress(src, dest):
                if self._copy_with_progress(src, dest):
                    # 复制成功删除源文件
                    src.unlink()
                    return True
                return False
            else:
                code, message = SystemUtils.move(src, dest)
                return code == 0
        except Exception as e:
            self.logger.error(f"【本地】移动文件失败：{e}")
            return False
    
    def link(self, fileitem: FileItem, target_file: Path) -> bool:
        """硬链接文件"""
        file_path = Path(fileitem.path)
        code, message = SystemUtils.link(file_path, target_file)
        
        if code != 0:
            self.logger.error(f"【本地】硬链接文件失败：{message}")
            return False
        
        return True
    
    def softlink(self, fileitem: FileItem, target_file: Path) -> bool:
        """软链接文件"""
        file_path = Path(fileitem.path)
        code, message = SystemUtils.softlink(file_path, target_file)
        
        if code != 0:
            self.logger.error(f"【本地】软链接文件失败：{message}")
            return False
        
        return True
    
    def _should_show_progress(self, src: Path, dest: Path) -> bool:
        """是否显示进度条"""
        src_is_network = SystemUtils.is_network_filesystem(src)
        dest_is_network = SystemUtils.is_network_filesystem(dest)
        
        if src_is_network and dest_is_network and SystemUtils.is_same_disk(src, dest):
            return True
        
        return False
    
    def usage(self) -> Optional[StorageUsage]:
        """存储使用情况"""
        try:
            # 获取根目录使用情况
            root_path = Path("/")
            if SystemUtils.is_windows():
                root_path = Path("C:\\")
            
            total, used, free = SystemUtils.get_disk_usage(root_path)
            
            return StorageUsage(
                total=total,
                available=free,
                used=used,
                usage_percent=(used / total * 100) if total > 0 else 0
            )
        except Exception as e:
            self.logger.error(f"【本地】获取存储使用情况失败：{e}")
            return None