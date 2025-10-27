#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RClone存储适配器
基于RClone命令行工具实现
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from core.storage_base import StorageBase, FileItem, StorageUsage, StorageSchema


class RCloneStorage(StorageBase):
    """RClone存储适配器"""
    
    schema = StorageSchema.RCLONE
    transtype = {
        "copy": "复制",
        "move": "移动",
        "sync": "同步"
    }
    
    def __init__(self):
        super().__init__()
        self.remote_name = None
        self.config_path = None
        self._check_rclone()
        
    def _check_rclone(self) -> bool:
        """检查RClone是否可用"""
        try:
            result = subprocess.run(['rclone', 'version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def init_storage(self) -> bool:
        """初始化RClone存储"""
        try:
            from core.config import Config
            config = Config()
            
            self.remote_name = config.get('rclone_remote_name', 'remote')
            self.config_path = config.get('rclone_config_path')
            
            # 检查远程配置
            return self._check_remote()
            
        except Exception as e:
            print(f"初始化RClone存储失败: {e}")
            return False
    
    def _check_remote(self) -> bool:
        """检查远程配置"""
        try:
            cmd = ['rclone', 'about']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.append(f'{self.remote_name}:')
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"检查RClone远程配置失败: {e}")
            return False
    
    def check(self) -> bool:
        """检查RClone是否可用"""
        return self._check_rclone() and self._check_remote()
    
    def list(self, fileitem: FileItem) -> List[FileItem]:
        """浏览文件列表"""
        try:
            remote_path = fileitem.path if fileitem.path else ""
            
            cmd = ['rclone', 'lsjson']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.extend([f'{self.remote_name}:{remote_path}', '--recursive'])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                items = []
                
                for item in data:
                    file_item = FileItem(
                        name=item.get('Name', ''),
                        path=item.get('Path', ''),
                        type=item.get('MimeType', 'file'),
                        size=item.get('Size', 0),
                        modify_time=self._parse_time(item.get('ModTime')),
                        is_dir=item.get('IsDir', False),
                        parent=remote_path
                    )
                    items.append(file_item)
                
                return items
            
            return []
            
        except Exception as e:
            print(f"获取RClone文件列表失败: {e}")
            return []
    
    def _parse_time(self, time_str: str) -> float:
        """解析时间字符串"""
        if not time_str:
            return 0
        try:
            from datetime import datetime
            # RClone时间格式: 2023-10-24T15:30:45.123Z
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.timestamp()
        except:
            return 0
    
    def create_folder(self, fileitem: FileItem, name: str) -> Optional[FileItem]:
        """创建目录"""
        try:
            parent_path = fileitem.path if fileitem else ""
            new_folder_path = f"{parent_path}/{name}".lstrip('/')
            
            cmd = ['rclone', 'mkdir']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.append(f'{self.remote_name}:{new_folder_path}')
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return FileItem(
                    name=name,
                    path=new_folder_path,
                    type='folder',
                    is_dir=True,
                    parent=parent_path
                )
            
            return None
            
        except Exception as e:
            print(f"创建RClone目录失败: {e}")
            return None
    
    def get_folder(self, path: Path) -> Optional[FileItem]:
        """获取目录，如目录不存在则创建"""
        folder_item = self.get_item(path)
        if not folder_item:
            # 创建目录
            return self.create_folder(None, str(path))
        return folder_item
    
    def get_item(self, path: Path) -> Optional[FileItem]:
        """获取文件或目录"""
        try:
            remote_path = str(path)
            
            cmd = ['rclone', 'lsjson']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.append(f'{self.remote_name}:{remote_path}')
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data:
                    item = data[0]
                    return FileItem(
                        name=item.get('Name', ''),
                        path=item.get('Path', ''),
                        type=item.get('MimeType', 'file'),
                        size=item.get('Size', 0),
                        modify_time=self._parse_time(item.get('ModTime')),
                        is_dir=item.get('IsDir', False),
                        parent=Path(remote_path).parent
                    )
            
            return None
            
        except Exception as e:
            print(f"获取RClone文件信息失败: {e}")
            return None
    
    def delete(self, fileitem: FileItem) -> bool:
        """删除文件"""
        try:
            cmd = ['rclone', 'delete']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.append(f'{self.remote_name}:{fileitem.path}')
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"删除RClone文件失败: {e}")
            return False
    
    def rename(self, fileitem: FileItem, name: str) -> bool:
        """重命名文件"""
        try:
            old_path = fileitem.path
            new_path = str(Path(old_path).parent / name)
            
            cmd = ['rclone', 'moveto']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.extend([
                f'{self.remote_name}:{old_path}',
                f'{self.remote_name}:{new_path}'
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"重命名RClone文件失败: {e}")
            return False
    
    def download(self, fileitem: FileItem, path: Path = None) -> Path:
        """下载文件"""
        try:
            local_path = path or Path(fileitem.name)
            
            cmd = ['rclone', 'copy']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.extend([
                f'{self.remote_name}:{fileitem.path}',
                str(local_path.parent)
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return local_path
            
            return None
            
        except Exception as e:
            print(f"下载RClone文件失败: {e}")
            return None
    
    def upload(self, fileitem: FileItem, path: Path, new_name: Optional[str] = None) -> Optional[FileItem]:
        """上传文件"""
        try:
            remote_path = fileitem.path if fileitem else ""
            file_name = new_name or path.name
            
            cmd = ['rclone', 'copy']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.extend([
                str(path),
                f'{self.remote_name}:{remote_path}'
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return FileItem(
                    name=file_name,
                    path=f"{remote_path}/{file_name}".lstrip('/'),
                    type='file',
                    size=path.stat().st_size,
                    modify_time=path.stat().st_mtime,
                    is_dir=False,
                    parent=remote_path
                )
            
            return None
            
        except Exception as e:
            print(f"上传文件到RClone失败: {e}")
            return None
    
    def copy(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """复制文件"""
        try:
            target_path = str(path / new_name)
            
            cmd = ['rclone', 'copy']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.extend([
                f'{self.remote_name}:{fileitem.path}',
                f'{self.remote_name}:{target_path}'
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"复制RClone文件失败: {e}")
            return False
    
    def move(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """移动文件"""
        try:
            target_path = str(path / new_name)
            
            cmd = ['rclone', 'moveto']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.extend([
                f'{self.remote_name}:{fileitem.path}',
                f'{self.remote_name}:{target_path}'
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"移动RClone文件失败: {e}")
            return False
    
    def usage(self) -> Optional[StorageUsage]:
        """存储使用情况"""
        try:
            cmd = ['rclone', 'about']
            if self.config_path:
                cmd.extend(['--config', self.config_path])
            cmd.append(f'{self.remote_name}:')
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # 解析RClone about输出
                lines = result.stdout.split('\n')
                total = 0
                used = 0
                
                for line in lines:
                    if 'Total:' in line:
                        total = self._parse_size(line.split(':')[1].strip())
                    elif 'Used:' in line:
                        used = self._parse_size(line.split(':')[1].strip())
                
                return StorageUsage(
                    total=total,
                    used=used,
                    free=total - used
                )
            
            return None
            
        except Exception as e:
            print(f"获取RClone使用情况失败: {e}")
            return None
    
    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串"""
        if not size_str:
            return 0
        
        try:
            # 支持格式: 1.5G, 500M, 2T
            size_str = size_str.upper()
            multipliers = {
                'B': 1,
                'K': 1024,
                'M': 1024**2,
                'G': 1024**3,
                'T': 1024**4
            }
            
            for unit, multiplier in multipliers.items():
                if unit in size_str:
                    num_str = size_str.replace(unit, '').strip()
                    return int(float(num_str) * multiplier)
            
            return int(size_str)
            
        except:
            return 0