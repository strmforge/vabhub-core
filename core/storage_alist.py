#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenList存储适配器
基于OpenList WebDAV API实现
"""

import os
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from urllib.parse import quote, urljoin

from core.storage_base import StorageBase, FileItem, StorageUsage, StorageSchema


class AlistStorage(StorageBase):
    """OpenList存储适配器"""
    
    schema = StorageSchema.ALIST
    transtype = {
        "copy": "复制",
        "move": "移动",
        "rename": "重命名"
    }
    
    def __init__(self):
        super().__init__()
        self.base_url = None
        self.username = None
        self.password = None
        self.token = None
        
    def init_storage(self) -> bool:
        """初始化OpenList存储"""
        try:
            from core.config import Config
            config = Config()
            
            self.base_url = config.get('alist_base_url')
            self.username = config.get('alist_username')
            self.password = config.get('alist_password')
            
            if not self.base_url:
                return False
                
            # 登录获取token
            return self._login()
            
        except Exception as e:
            print(f"初始化OpenList存储失败: {e}")
            return False
    
    def _login(self) -> bool:
        """登录OpenList获取token"""
        try:
            login_url = urljoin(self.base_url, '/api/auth/login')
            
            data = {
                'username': self.username,
                'password': self.password
            }
            
            response = requests.post(login_url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                self.token = result.get('data', {}).get('token')
                return self.token is not None
            
            return False
            
        except Exception as e:
            print(f"OpenList登录失败: {e}")
            return False
    
    def check(self) -> bool:
        """检查OpenList是否可用"""
        try:
            if not self.token:
                return False
                
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            me_url = urljoin(self.base_url, '/api/me')
            response = requests.get(me_url, headers=headers)
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"检查OpenList失败: {e}")
            return False
    
    def list(self, fileitem: FileItem) -> List[FileItem]:
        """浏览文件列表"""
        try:
            path = fileitem.path if fileitem.path else "/"
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            list_url = urljoin(self.base_url, f'/api/fs/list')
            data = {
                'path': path,
                'password': '',
                'page': 1,
                'per_page': 200,
                'refresh': False
            }
            
            response = requests.post(list_url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('data', {}).get('content', [])
                items = []
                
                for item in content:
                    file_item = FileItem(
                        name=item.get('name', ''),
                        path=item.get('path', ''),
                        type=item.get('type', 'file'),
                        size=item.get('size', 0),
                        modify_time=self._parse_time(item.get('modified')),
                        is_dir=item.get('is_dir', False),
                        parent=path
                    )
                    items.append(file_item)
                
                return items
            
            return []
            
        except Exception as e:
            print(f"获取OpenList文件列表失败: {e}")
            return []
    
    def _parse_time(self, time_str: str) -> float:
        """解析时间字符串"""
        if not time_str:
            return 0
        try:
            from datetime import datetime
            # OpenList时间格式: 2023-10-24T15:30:45.123Z
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.timestamp()
        except:
            return 0
    
    def create_folder(self, fileitem: FileItem, name: str) -> Optional[FileItem]:
        """创建目录"""
        try:
            parent_path = fileitem.path if fileitem else "/"
            new_folder_path = f"{parent_path}/{name}".replace('//', '/')
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            mkdir_url = urljoin(self.base_url, '/api/fs/mkdir')
            data = {
                'path': new_folder_path
            }
            
            response = requests.post(mkdir_url, headers=headers, json=data)
            
            if response.status_code == 200:
                return FileItem(
                    name=name,
                    path=new_folder_path,
                    type='folder',
                    is_dir=True,
                    parent=parent_path
                )
            
            return None
            
        except Exception as e:
            print(f"创建OpenList目录失败: {e}")
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
            file_path = str(path)
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            get_url = urljoin(self.base_url, '/api/fs/get')
            data = {
                'path': file_path
            }
            
            response = requests.post(get_url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                item = result.get('data', {})
                
                return FileItem(
                    name=item.get('name', ''),
                    path=item.get('path', ''),
                    type=item.get('type', 'file'),
                    size=item.get('size', 0),
                    modify_time=self._parse_time(item.get('modified')),
                    is_dir=item.get('is_dir', False),
                    parent=Path(file_path).parent
                )
            
            return None
            
        except Exception as e:
            print(f"获取OpenList文件信息失败: {e}")
            return None
    
    def delete(self, fileitem: FileItem) -> bool:
        """删除文件"""
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            delete_url = urljoin(self.base_url, '/api/fs/remove')
            data = {
                'dir': fileitem.parent,
                'names': [fileitem.name]
            }
            
            response = requests.post(delete_url, headers=headers, json=data)
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"删除OpenList文件失败: {e}")
            return False
    
    def rename(self, fileitem: FileItem, name: str) -> bool:
        """重命名文件"""
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            rename_url = urljoin(self.base_url, '/api/fs/rename')
            data = {
                'path': fileitem.path,
                'name': name
            }
            
            response = requests.post(rename_url, headers=headers, json=data)
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"重命名OpenList文件失败: {e}")
            return False
    
    def download(self, fileitem: FileItem, path: Path = None) -> Path:
        """下载文件"""
        try:
            local_path = path or Path(fileitem.name)
            
            headers = {
                'Authorization': f'Bearer {self.token}'
            }
            
            # 获取下载链接
            get_url = urljoin(self.base_url, '/api/fs/get')
            data = {
                'path': fileitem.path
            }
            
            response = requests.post(get_url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                download_url = result.get('data', {}).get('raw_url')
                
                if download_url:
                    # 下载文件
                    response = requests.get(download_url, stream=True)
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    return local_path
            
            return None
            
        except Exception as e:
            print(f"下载OpenList文件失败: {e}")
            return None
    
    def upload(self, fileitem: FileItem, path: Path, new_name: Optional[str] = None) -> Optional[FileItem]:
        """上传文件"""
        try:
            remote_path = fileitem.path if fileitem else "/"
            file_name = new_name or path.name
            
            headers = {
                'Authorization': f'Bearer {self.token}'
            }
            
            # 获取上传链接
            upload_url = urljoin(self.base_url, '/api/fs/put')
            
            with open(path, 'rb') as f:
                files = {'file': (file_name, f)}
                data = {
                    'path': f"{remote_path}/{file_name}".replace('//', '/')
                }
                
                response = requests.put(upload_url, headers=headers, 
                                      files=files, data=data)
            
            if response.status_code == 200:
                return FileItem(
                    name=file_name,
                    path=f"{remote_path}/{file_name}".replace('//', '/'),
                    type='file',
                    size=path.stat().st_size,
                    modify_time=path.stat().st_mtime,
                    is_dir=False,
                    parent=remote_path
                )
            
            return None
            
        except Exception as e:
            print(f"上传文件到OpenList失败: {e}")
            return None
    
    def copy(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """复制文件"""
        try:
            target_path = str(path / new_name)
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            copy_url = urljoin(self.base_url, '/api/fs/copy')
            data = {
                'src_dir': fileitem.parent,
                'src_names': [fileitem.name],
                'dst_dir': str(path)
            }
            
            response = requests.post(copy_url, headers=headers, json=data)
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"复制OpenList文件失败: {e}")
            return False
    
    def move(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """移动文件"""
        try:
            target_path = str(path / new_name)
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            move_url = urljoin(self.base_url, '/api/fs/move')
            data = {
                'src_dir': fileitem.parent,
                'src_names': [fileitem.name],
                'dst_dir': str(path)
            }
            
            response = requests.post(move_url, headers=headers, json=data)
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"移动OpenList文件失败: {e}")
            return False
    
    def usage(self) -> Optional[StorageUsage]:
        """存储使用情况"""
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # OpenList通常不提供存储使用情况API
            # 这里返回默认值
            return StorageUsage(
                total=1024**4,  # 1TB
                used=0,
                free=1024**4
            )
            
        except Exception as e:
            print(f"获取OpenList使用情况失败: {e}")
            return None