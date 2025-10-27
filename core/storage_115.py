#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
115网盘官方API存储适配器
基于官方OAuth2.0 API实现
"""

import json
import time
import requests
from pathlib import Path
from typing import Optional, List, Dict

from core.storage_base import StorageBase, StorageSchema, FileItem, StorageUsage
from core.strm_generator import STRMGenerator, STRMType


class U115Storage(StorageBase):
    """115网盘官方API存储适配器"""
    
    schema = StorageSchema.U115
    transtype = {
        "move": "移动",
        "copy": "复制"
    }
    
    # 官方API端点
    BASE_URL = "https://openapi.115.com"
    AUTH_URL = "https://openapi.115.com/oauth/authorize"
    TOKEN_URL = "https://openapi.115.com/oauth/token"
    
    def __init__(self):
        super().__init__()
        self.client_id = ""
        self.client_secret = ""
        self.access_token = ""
        self.refresh_token = ""
        self.token_expires = 0
        self.session = requests.Session()

    def init_storage(self) -> bool:
        """初始化存储"""
        # 从配置获取认证信息
        from core.config_loader import get_config_loader
        config = get_config_loader()
        
        self.client_id = config.get('115_client_id', '')
        self.client_secret = config.get('115_client_secret', '')
        self.access_token = config.get('115_access_token', '')
        self.refresh_token = config.get('115_refresh_token', '')
        self.token_expires = config.get('115_token_expires', 0)
        
        if not self.client_id or not self.client_secret:
            print("警告: 115网盘官方API配置不完整")
            return False
            
        # 检查token是否过期
        if self._is_token_expired():
            return self._refresh_access_token()
            
        return True

    def check(self) -> bool:
        """检查存储是否可用"""
        if not self.access_token:
            return False
            
        try:
            response = self._api_request("GET", "/files")
            return response.status_code == 200
        except Exception as e:
            print(f"115网盘检查失败: {e}")
            return False

    def list(self, fileitem: FileItem) -> List[FileItem]:
        """浏览文件"""
        if not fileitem.is_dir:
            return []
            
        folder_id = self._get_folder_id(fileitem.path)
        
        try:
            response = self._api_request("GET", f"/files?folder_id={folder_id}")
            if response.status_code == 200:
                data = response.json()
                return self._parse_file_list(data.get('data', []), fileitem.path)
        except Exception as e:
            print(f"115网盘列表文件失败: {e}")
            
        return []

    def create_folder(self, fileitem: FileItem, name: str) -> Optional[FileItem]:
        """创建目录"""
        if not fileitem.is_dir:
            return None
            
        parent_id = self._get_folder_id(fileitem.path)
        
        try:
            data = {
                "pid": parent_id,
                "cname": name
            }
            response = self._api_request("POST", "/files/add_folder", data)
            if response.status_code == 200:
                result = response.json()
                if result.get('state'):
                    folder_id = result.get('folder_id')
                    new_path = f"{fileitem.path}/{name}"
                    return FileItem(
                        name=name,
                        path=new_path,
                        type="dir",
                        is_dir=True,
                        parent=fileitem.path
                    )
        except Exception as e:
            print(f"115网盘创建目录失败: {e}")
            
        return None

    def get_folder(self, path: Path) -> Optional[FileItem]:
        """获取目录"""
        folder_id = self._get_folder_id(str(path))
        if folder_id:
            return FileItem(
                name=path.name,
                path=str(path),
                type="dir",
                is_dir=True,
                parent=str(path.parent)
            )
        return None

    def get_item(self, path: Path) -> Optional[FileItem]:
        """获取文件或目录"""
        # 简化实现：通过路径解析
        path_str = str(path)
        if path_str == "/":
            return FileItem(
                name="根目录",
                path="/",
                type="dir",
                is_dir=True
            )
            
        # 这里需要实现根据路径获取文件信息的逻辑
        # 简化实现：返回基础信息
        return FileItem(
            name=path.name,
            path=str(path),
            type="dir" if path_str.endswith('/') else "file",
            is_dir=path_str.endswith('/')
        )

    def delete(self, fileitem: FileItem) -> bool:
        """删除文件"""
        file_id = self._get_file_id(fileitem.path)
        
        try:
            data = {
                "fid": file_id
            }
            response = self._api_request("POST", "/files/delete", data)
            return response.status_code == 200 and response.json().get('state')
        except Exception as e:
            print(f"115网盘删除文件失败: {e}")
            return False

    def rename(self, fileitem: FileItem, name: str) -> bool:
        """重命名文件"""
        file_id = self._get_file_id(fileitem.path)
        
        try:
            data = {
                "fid": file_id,
                "new_name": name
            }
            response = self._api_request("POST", "/files/rename", data)
            return response.status_code == 200 and response.json().get('state')
        except Exception as e:
            print(f"115网盘重命名文件失败: {e}")
            return False

    def download(self, fileitem: FileItem, path: Path = None) -> Path:
        """下载文件"""
        file_id = self._get_file_id(fileitem.path)
        
        try:
            # 获取下载链接
            response = self._api_request("GET", f"/files/download?fid={file_id}")
            if response.status_code == 200:
                download_url = response.json().get('url')
                if download_url:
                    # 下载文件到本地
                    local_path = path or Path(f"/tmp/{fileitem.name}")
                    self._download_file(download_url, local_path)
                    return local_path
        except Exception as e:
            print(f"115网盘下载文件失败: {e}")
            
        return Path("/tmp/error")

    def upload(self, fileitem: FileItem, path: Path, 
               new_name: Optional[str] = None) -> Optional[FileItem]:
        """上传文件"""
        if not fileitem.is_dir:
            return None
            
        folder_id = self._get_folder_id(fileitem.path)
        upload_name = new_name or path.name
        
        try:
            # 获取上传信息
            upload_info = self._get_upload_info(folder_id, upload_name, path.stat().st_size)
            if upload_info:
                # 执行上传
                if self._upload_file(path, upload_info):
                    return FileItem(
                        name=upload_name,
                        path=f"{fileitem.path}/{upload_name}",
                        type="file",
                        is_dir=False,
                        parent=fileitem.path
                    )
        except Exception as e:
            print(f"115网盘上传文件失败: {e}")
            
        return None

    def copy(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """复制文件"""
        source_id = self._get_file_id(fileitem.path)
        target_folder_id = self._get_folder_id(str(path))
        
        try:
            data = {
                "fid": source_id,
                "pid": target_folder_id,
                "new_name": new_name
            }
            response = self._api_request("POST", "/files/copy", data)
            return response.status_code == 200 and response.json().get('state')
        except Exception as e:
            print(f"115网盘复制文件失败: {e}")
            return False

    def move(self, fileitem: FileItem, path: Path, new_name: str) -> bool:
        """移动文件"""
        source_id = self._get_file_id(fileitem.path)
        target_folder_id = self._get_folder_id(str(path))
        
        try:
            data = {
                "fid": source_id,
                "pid": target_folder_id,
                "new_name": new_name
            }
            response = self._api_request("POST", "/files/move", data)
            return response.status_code == 200 and response.json().get('state')
        except Exception as e:
            print(f"115网盘移动文件失败: {e}")
            return False

    def usage(self) -> Optional[StorageUsage]:
        """存储使用情况"""
        try:
            response = self._api_request("GET", "/user/space")
            if response.status_code == 200:
                data = response.json()
                space_info = data.get('data', {})
                return StorageUsage(
                    total=space_info.get('total_size', 0),
                    used=space_info.get('used_size', 0),
                    free=space_info.get('free_size', 0)
                )
        except Exception as e:
            print(f"115网盘获取使用情况失败: {e}")
            
        return None

    def _api_request(self, method: str, endpoint: str, data: Dict = None) -> requests.Response:
        """API请求封装"""
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        if method.upper() == "GET":
            return self.session.get(url, headers=headers)
        else:
            return self.session.post(url, headers=headers, json=data)

    def _is_token_expired(self) -> bool:
        """检查token是否过期"""
        return time.time() > self.token_expires

    def _refresh_access_token(self) -> bool:
        """刷新访问令牌"""
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = requests.post(self.TOKEN_URL, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token', self.refresh_token)
                self.token_expires = time.time() + token_data.get('expires_in', 3600)
                
                # 保存到配置
                from core.config_loader import get_config_loader
                config = get_config_loader()
                config.set('115_access_token', self.access_token)
                config.set('115_refresh_token', self.refresh_token)
                config.set('115_token_expires', self.token_expires)
                
                return True
        except Exception as e:
            print(f"115网盘刷新token失败: {e}")
            
        return False

    def _get_folder_id(self, path: str) -> str:
        """根据路径获取文件夹ID"""
        # 简化实现：根目录ID为0
        if path == "/" or path == "":
            return "0"
        
        # 这里需要实现路径到文件夹ID的映射
        # 简化实现：返回固定值
        return "0"

    def _get_file_id(self, path: str) -> str:
        """根据路径获取文件ID"""
        # 这里需要实现路径到文件ID的映射
        # 简化实现：返回固定值
        return "123456"

    def _parse_file_list(self, data: List, parent_path: str) -> List[FileItem]:
        """解析文件列表"""
        items = []
        for item in data:
            file_item = FileItem(
                name=item.get('name', ''),
                path=f"{parent_path}/{item.get('name', '')}",
                type="dir" if item.get('type') == 'folder' else "file",
                size=item.get('size', 0),
                modify_time=item.get('modify_time', 0),
                is_dir=item.get('type') == 'folder',
                parent=parent_path
            )
            items.append(file_item)
        return items

    def _get_upload_info(self, folder_id: str, filename: str, file_size: int) -> Dict:
        """获取上传信息"""
        try:
            data = {
                "pid": folder_id,
                "file_name": filename,
                "file_size": file_size
            }
            response = self._api_request("POST", "/files/upload_info", data)
            if response.status_code == 200:
                return response.json().get('data', {})
        except Exception as e:
            print(f"获取上传信息失败: {e}")
            
        return {}

    def _upload_file(self, local_path: Path, upload_info: Dict) -> bool:
        """上传文件"""
        try:
            with open(local_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    upload_info.get('url', ''),
                    files=files,
                    data=upload_info.get('params', {})
                )
                return response.status_code == 200
        except Exception as e:
            print(f"上传文件失败: {e}")
            return False

    def _download_file(self, download_url: str, local_path: Path) -> bool:
        """下载文件"""
        try:
            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return True
        except Exception as e:
            print(f"下载文件失败: {e}")
            
        return False

    # STRM相关功能
    def generate_strm_file(self, fileitem: FileItem, output_path: Path, 
                          strm_type: STRMType = STRMType.PROXY) -> bool:
        """
        为115网盘文件生成STRM文件
        
        Args:
            fileitem: 文件项
            output_path: 输出路径
            strm_type: STRM类型
            
        Returns:
            是否成功
        """
        try:
            # 获取文件ID
            file_id = self._get_file_id(fileitem.path)
            
            # 生成文件URL
            file_url = f"http://localhost:8000/api/strm/stream/u115/{file_id}"
            
            # 创建STRM生成器
            strm_gen = STRMGenerator()
            
            # 生成元数据
            metadata = {
                "storage_type": "u115",
                "file_id": file_id,
                "file_name": fileitem.name,
                "size": fileitem.size,
                "media_type": self._detect_media_type(fileitem.name)
            }
            
            # 创建STRM文件
            return strm_gen.create_strm_file(
                str(output_path), file_url, strm_type, metadata
            )
            
        except Exception as e:
            print(f"生成STRM文件失败: {e}")
            return False

    def batch_generate_strm(self, file_list: List[FileItem], output_dir: Path,
                           organize_by_type: bool = True) -> Dict[str, Any]:
        """
        批量生成STRM文件
        
        Args:
            file_list: 文件列表
            output_dir: 输出目录
            organize_by_type: 是否按类型组织
            
        Returns:
            生成结果统计
        """
        strm_gen = STRMGenerator()
        
        # 准备文件信息
        strm_files = []
        for fileitem in file_list:
            if not fileitem.is_dir:
                file_id = self._get_file_id(fileitem.path)
                metadata = {
                    "storage_type": "u115",
                    "file_id": file_id,
                    "file_name": fileitem.name,
                    "size": fileitem.size,
                    "media_type": self._detect_media_type(fileitem.name)
                }
                
                strm_files.append({
                    "storage_type": "u115",
                    "file_id": file_id,
                    "file_name": fileitem.name,
                    "metadata": metadata
                })
        
        # 批量生成
        return strm_gen.batch_generate_strm(strm_files, str(output_dir), organize_by_type)

    def get_download_url(self, fileitem: FileItem) -> Optional[str]:
        """
        获取文件下载URL（用于STRM重定向）
        
        Args:
            fileitem: 文件项
            
        Returns:
            下载URL
        """
        try:
            file_id = self._get_file_id(fileitem.path)
            
            # 调用115网盘API获取下载链接
            response = self._api_request("GET", f"/files/download?fid={file_id}")
            if response.status_code == 200:
                data = response.json()
                return data.get('url')
                
        except Exception as e:
            print(f"获取下载URL失败: {e}")
            
        return None

    def _detect_media_type(self, filename: str) -> str:
        """检测媒体类型"""
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
        file_ext = Path(filename).suffix.lower()
        
        if file_ext in video_extensions:
            # 根据文件名模式判断具体类型
            filename_lower = filename.lower()
            if any(keyword in filename_lower for keyword in ['season', 's\d', 'e\d']):
                return 'tv'
            elif any(keyword in filename_lower for keyword in ['movie', 'film']):
                return 'movie'
            elif any(keyword in filename_lower for keyword in ['anime', 'animation']):
                return 'anime'
            else:
                return 'video'
        else:
            return 'other'

    # STRM相关功能
    def generate_strm_file(self, fileitem: FileItem, output_path: Path, 
                          strm_type: STRMType = STRMType.PROXY) -> bool:
        """
        为115网盘文件生成STRM文件
        
        Args:
            fileitem: 文件项
            output_path: 输出路径
            strm_type: STRM类型
            
        Returns:
            是否成功
        """
        try:
            # 获取文件ID
            file_id = self._get_file_id(fileitem.path)
            
            # 生成文件URL
            file_url = f"http://localhost:8000/api/strm/stream/u115/{file_id}"
            
            # 创建STRM生成器
            strm_gen = STRMGenerator()
            
            # 生成元数据
            metadata = {
                "storage_type": "u115",
                "file_id": file_id,
                "file_name": fileitem.name,
                "size": fileitem.size,
                "media_type": self._detect_media_type(fileitem.name)
            }
            
            # 创建STRM文件
            return strm_gen.create_strm_file(
                str(output_path), file_url, strm_type, metadata
            )
            
        except Exception as e:
            print(f"生成STRM文件失败: {e}")
            return False

    def batch_generate_strm(self, file_list: List[FileItem], output_dir: Path,
                           organize_by_type: bool = True) -> Dict[str, Any]:
        """
        批量生成STRM文件
        
        Args:
            file_list: 文件列表
            output_dir: 输出目录
            organize_by_type: 是否按类型组织
            
        Returns:
            生成结果统计
        """
        strm_gen = STRMGenerator()
        
        # 准备文件信息
        strm_files = []
        for fileitem in file_list:
            if not fileitem.is_dir:
                file_id = self._get_file_id(fileitem.path)
                metadata = {
                    "storage_type": "u115",
                    "file_id": file_id,
                    "file_name": fileitem.name,
                    "size": fileitem.size,
                    "media_type": self._detect_media_type(fileitem.name)
                }
                
                strm_files.append({
                    "storage_type": "u115",
                    "file_id": file_id,
                    "file_name": fileitem.name,
                    "metadata": metadata
                })
        
        # 批量生成
        return strm_gen.batch_generate_strm(strm_files, str(output_dir), organize_by_type)

    def get_download_url(self, fileitem: FileItem) -> Optional[str]:
        """
        获取文件下载URL（用于STRM重定向）
        
        Args:
            fileitem: 文件项
            
        Returns:
            下载URL
        """
        try:
            file_id = self._get_file_id(fileitem.path)
            
            # 调用115网盘API获取下载链接
            response = self._api_request("GET", f"/files/download?fid={file_id}")
            if response.status_code == 200:
                data = response.json()
                return data.get('url')
                
        except Exception as e:
            print(f"获取下载URL失败: {e}")
            
        return None

    def _detect_media_type(self, filename: str) -> str:
        """检测媒体类型"""
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
        file_ext = Path(filename).suffix.lower()
        
        if file_ext in video_extensions:
            # 根据文件名模式判断具体类型
            filename_lower = filename.lower()
            if any(keyword in filename_lower for keyword in ['season', 's\d', 'e\d']):
                return 'tv'
            elif any(keyword in filename_lower for keyword in ['movie', 'film']):
                return 'movie'
            elif any(keyword in filename_lower for keyword in ['anime', 'animation']):
                return 'anime'
            else:
                return 'video'
        else:
            return 'other'