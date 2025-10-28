"""
存储基类
基于MoviePilot的最佳实践
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Union, Callable
import logging

from .storage_schemas import (
    StorageSchema, FileItem, StorageUsage, StorageConf, 
    TransferInfo, MediaInfo, MetaInfo
)


class StorageBase(ABC):
    """
    存储基类
    所有存储后端的通用接口
    """
    
    schema: StorageSchema = None
    transtype: Dict[str, str] = {}
    snapshot_check_folder_modtime: bool = True
    
    def __init__(self):
        self.logger = logging.getLogger(f"storage.{self.schema.value if self.schema else 'unknown'}")
    
    @abstractmethod
    def init_storage(self) -> bool:
        """初始化存储"""
        pass
    
    def generate_qrcode(self, *args, **kwargs) -> Optional[Tuple[Dict[str, Any], str]]:
        """生成二维码（用于网盘登录）"""
        return None
    
    def check_login(self, *args, **kwargs) -> Optional[Dict[str, str]]:
        """检查登录状态"""
        return None
    
    def get_config(self) -> Optional[StorageConf]:
        """获取配置"""
        # 需要子类实现配置管理
        return None
    
    def set_config(self, conf: Dict[str, Any]):
        """设置配置"""
        # 需要子类实现配置管理
        pass
    
    def support_transtype(self) -> Dict[str, str]:
        """支持的传输类型"""
        return self.transtype
    
    def is_support_transtype(self, transtype: str) -> bool:
        """是否支持特定传输类型"""
        return transtype in self.transtype
    
    def reset_config(self):
        """重置配置"""
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
        """获取目录（不存在则创建）"""
        pass
    
    @abstractmethod
    def get_item(self, path: Path) -> Optional[FileItem]:
        """获取文件或目录"""
        pass
    
    def get_parent(self, fileitem: FileItem) -> Optional[FileItem]:
        """获取父目录"""
        if not fileitem.path:
            return None
        parent_path = Path(fileitem.path).parent
        return self.get_item(parent_path)
    
    @abstractmethod
    def delete(self, fileitem: FileItem) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    def rename(self, fileitem: FileItem, name: str) -> bool:
        """重命名文件"""
        pass
    
    @abstractmethod
    def download(self, fileitem: FileItem, path: Optional[Path] = None) -> Optional[Path]:
        """下载文件到本地"""
        pass
    
    @abstractmethod
    def upload(self, fileitem: FileItem, path: Path, new_name: Optional[str] = None) -> Optional[FileItem]:
        """上传文件"""
        pass
    
    @abstractmethod
    def detail(self, fileitem: FileItem) -> Optional[FileItem]:
        """获取文件详情"""
        pass
    
    @abstractmethod
    def copy(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """复制文件"""
        pass
    
    @abstractmethod
    def move(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """移动文件"""
        pass
    
    def link(self, fileitem: FileItem, target_file: Path) -> bool:
        """硬链接文件（仅本地存储支持）"""
        return False
    
    def softlink(self, fileitem: FileItem, target_file: Path) -> bool:
        """软链接文件（仅本地存储支持）"""
        return False
    
    @abstractmethod
    def usage(self) -> Optional[StorageUsage]:
        """存储使用情况"""
        pass
    
    def snapshot(self, path: Path, last_snapshot_time: Optional[float] = None, max_depth: int = 5) -> Dict[str, Dict]:
        """
        快照文件系统
        :param path: 路径
        :param last_snapshot_time: 上次快照时间
        :param max_depth: 最大递归深度
        """
        files_info = {}
        
        def __snapshot_file(_fileitem: FileItem, current_depth: int = 0):
            """递归获取文件信息"""
            try:
                if _fileitem.type == "dir":
                    # 检查递归深度限制
                    if current_depth >= max_depth:
                        return
                    
                    # 增量检查：如果目录修改时间早于上次快照，跳过
                    if (self.snapshot_check_folder_modtime and
                            last_snapshot_time and
                            _fileitem.modify_time and
                            _fileitem.modify_time <= last_snapshot_time):
                        return
                    
                    # 遍历子文件
                    sub_files = self.list(_fileitem)
                    for sub_file in sub_files:
                        __snapshot_file(sub_file, current_depth + 1)
                else:
                    # 记录文件的完整信息用于比对
                    if getattr(_fileitem, 'modify_time', 0) > last_snapshot_time:
                        files_info[_fileitem.path] = {
                            'size': _fileitem.size or 0,
                            'modify_time': getattr(_fileitem, 'modify_time', 0),
                            'type': _fileitem.type
                        }
            
            except Exception as e:
                self.logger.debug(f"Snapshot error for {_fileitem.path}: {e}")
        
        fileitem = self.get_item(path)
        if not fileitem:
            return {}
        
        __snapshot_file(fileitem)
        return files_info
    
    def transfer_process(self, path: str) -> Callable[[Union[int, float]], None]:
        """传输进度回调"""
        def update_progress(percent: Union[int, float]) -> None:
            """更新进度百分比"""
            self.logger.info(f"{path} 传输进度: {percent}%")
        
        return update_progress