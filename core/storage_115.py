#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
115网盘官方API存储适配器
基于MoviePilot的OAuth2 PKCE方案实现长期授权
"""

import base64
import hashlib
import secrets
import threading
import time
import json
import requests
import oss2
from oss2 import SizedFileAdapter, determine_part_size
from oss2.models import PartInfo
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Union, Any

from core.storage_base import StorageBase, StorageSchema, FileItem, StorageUsage
from core.strm_generator import STRMGenerator, STRMType


class NoCheckInException(Exception):
    """未登录异常"""
    pass


class U115Storage(StorageBase):
    """115网盘官方API存储适配器（基于MoviePilot方案）"""
    
    schema = StorageSchema.U115
    transtype = {
        "move": "移动",
        "copy": "复制"
    }
    
    # 官方API端点（使用MoviePilot验证的端点）
    BASE_URL = "https://proapi.115.com"
    AUTH_DEVICE_CODE_URL = "https://passportapi.115.com/open/authDeviceCode"
    DEVICE_CODE_TO_TOKEN_URL = "https://passportapi.115.com/open/deviceCodeToToken"
    REFRESH_TOKEN_URL = "https://passportapi.115.com/open/refreshToken"
    
    # 文件块大小，默认10MB
    chunk_size = 10 * 1024 * 1024
    
    # 流控重试间隔时间
    retry_delay = 70
    
    def __init__(self):
        super().__init__()
        self._auth_state = {}
        self.session = requests.Session()
        self._init_session()
        self.lock = threading.Lock()

    def _init_session(self):
        """初始化带速率限制的会话"""
        self.session.headers.update({
            "User-Agent": "W115Storage/2.0",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded"
        })

    def init_storage(self) -> bool:
        """初始化存储（使用MoviePilot安全策略）"""
        # 从安全配置获取认证信息
        from core.config import CloudStorageConfig
        config = CloudStorageConfig()
        
        # 使用硬编码但受保护的AppID/AppKey
        self.client_id = config.u115_app_id
        self.client_secret = config.u115_app_key
        
        if not self.client_id or self.client_id == "100197729":
            # 检查是否被环境变量覆盖
            import os
            env_app_id = os.environ.get("U115_APP_ID")
            if env_app_id:
                self.client_id = env_app_id
                self.client_secret = os.environ.get("U115_APP_KEY", "")
        
        if not self.client_id:
            print("警告: 115网盘AppID未配置")
            return False
            
        # 检查token是否有效
        return self.access_token is not None

    def _check_session(self):
        """检查会话是否过期"""
        if not self.access_token:
            raise NoCheckInException("【115】请先扫码登录！")

    @property
    def access_token(self) -> Optional[str]:
        """访问token（自动刷新，使用MoviePilot安全策略）"""
        with self.lock:
            from core.config_loader import get_config_loader
            config = get_config_loader()
            
            # 使用安全配置获取token信息
            tokens = {
                "refresh_token": config.get('115_refresh_token', ''),
                "access_token": config.get('115_access_token', ''),
                "expires_in": config.get('115_token_expires', 0),
                "refresh_time": config.get('115_refresh_time', 0)
            }
            
            refresh_token = tokens.get("refresh_token")
            if not refresh_token:
                return None
                
            expires_in = tokens.get("expires_in", 0)
            refresh_time = tokens.get("refresh_time", 0)
            
            # 检查token是否过期
            if expires_in and refresh_time + expires_in < int(time.time()):
                # 自动刷新token
                new_tokens = self.__refresh_access_token(refresh_token)
                if new_tokens:
                    # 保存新token
                    config.set('115_access_token', new_tokens.get('access_token'))
                    config.set('115_refresh_token', new_tokens.get('refresh_token', refresh_token))
                    config.set('115_token_expires', new_tokens.get('expires_in', 3600))
                    config.set('115_refresh_time', int(time.time()))
                    
                    # 更新会话头
                    access_token = new_tokens.get('access_token')
                    if access_token:
                        self.session.headers.update({"Authorization": f"Bearer {access_token}"})
                    return access_token
                else:
                    return None
                    
            access_token = tokens.get('access_token')
            if access_token:
                self.session.headers.update({"Authorization": f"Bearer {access_token}"})
            return access_token

    def generate_qrcode(self) -> Tuple[dict, str]:
        """实现PKCE规范的设备授权二维码生成"""
        # 生成PKCE参数
        code_verifier = secrets.token_urlsafe(96)[:128]
        code_challenge = base64.b64encode(
            hashlib.sha256(code_verifier.encode("utf-8")).digest()
        ).decode("utf-8")
        
        # 请求设备码
        resp = self.session.post(
            self.AUTH_DEVICE_CODE_URL,
            data={
                "client_id": self.client_id,
                "code_challenge": code_challenge,
                "code_challenge_method": "sha256"
            }
        )
        
        if resp is None:
            return {}, "网络错误"
            
        result = resp.json()
        if result.get("code") != 0:
            return {}, result.get("message")
            
        # 持久化验证参数
        self._auth_state = {
            "code_verifier": code_verifier,
            "uid": result["data"]["uid"],
            "time": result["data"]["time"],
            "sign": result["data"]["sign"]
        }

        # 生成二维码内容
        return {
            "codeContent": result['data']['qrcode']
        }, ""

    def check_login(self) -> Optional[Tuple[dict, str]]:
        """改进的带PKCE校验的登录状态检查"""
        if not self._auth_state:
            return {}, "生成二维码失败"
            
        try:
            resp = self.session.get(
                "https://qrcodeapi.115.com/get/status/",
                params={
                    "uid": self._auth_state["uid"],
                    "time": self._auth_state["time"],
                    "sign": self._auth_state["sign"]
                }
            )
            
            if resp is None:
                return {}, "网络错误"
                
            result = resp.json()
            if result.get("code") != 0 or not result.get("data"):
                return {}, result.get("message")
                
            if result["data"]["status"] == 2:
                # 登录成功，获取token
                tokens = self.__get_access_token()
                
                # 保存token到配置
                from core.config_loader import get_config_loader
                config = get_config_loader()
                config.set('115_access_token', tokens.get('access_token'))
                config.set('115_refresh_token', tokens.get('refresh_token'))
                config.set('115_token_expires', tokens.get('expires_in', 3600))
                config.set('115_refresh_time', int(time.time()))
                
            return {"status": result["data"]["status"], "tip": result["data"]["msg"]}, ""
            
        except Exception as e:
            return {}, str(e)

    def __get_access_token(self) -> dict:
        """确认登录后，获取相关token"""
        if not self._auth_state:
            raise Exception("【115】请先生成二维码")
            
        resp = self.session.post(
            self.DEVICE_CODE_TO_TOKEN_URL,
            data={
                "uid": self._auth_state["uid"],
                "code_verifier": self._auth_state["code_verifier"]
            }
        )
        
        if resp is None:
            raise Exception("获取 access_token 失败")
            
        result = resp.json()
        if result.get("code") != 0:
            raise Exception(result.get("message"))
            
        return result["data"]

    def __refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        """刷新access_token"""
        resp = self.session.post(
            self.REFRESH_TOKEN_URL,
            data={
                "refresh_token": refresh_token
            }
        )
        
        if resp is None:
            print(f"【115】刷新 access_token 失败：refresh_token={refresh_token}")
            return None
            
        result = resp.json()
        if result.get("code") != 0:
            print(f"【115】刷新 access_token 失败：{result.get('code')} - {result.get('message')}！")
            return None
            
        return result.get("data")

    def check(self) -> bool:
        """检查存储是否可用"""
        return self.access_token is not None

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
        """
        上传文件（使用秒传和分片上传）
        """
        if not fileitem.is_dir:
            return None
            
        try:
            # 使用高级上传功能（支持秒传和分片上传）
            return self._upload_file_advanced(fileitem, path, new_name)
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

    def _api_request(self, method: str, endpoint: str,
                     result_key: Optional[str] = None, **kwargs) -> Optional[Union[dict, list]]:
        """带错误处理和速率限制的API请求"""
        # 检查会话
        self._check_session()

        # 错误日志标志
        no_error_log = kwargs.pop("no_error_log", False)
        # 重试次数
        retry_times = kwargs.pop("retry_limit", 5)

        try:
            resp = self.session.request(
                method, f"{self.BASE_URL}{endpoint}",
                **kwargs
            )
        except requests.exceptions.RequestException as e:
            print(f"【115】{method} 请求 {endpoint} 网络错误: {str(e)}")
            return None

        if resp is None:
            print(f"【115】{method} 请求 {endpoint} 失败！")
            return None

        kwargs["retry_limit"] = retry_times

        # 处理速率限制
        if resp.status_code == 429:
            reset_time = 5 + int(resp.headers.get("X-RateLimit-Reset", 60))
            print(f"【115】{method} 请求 {endpoint} 限流，等待{reset_time}秒后重试")
            time.sleep(reset_time)
            return self._api_request(method, endpoint, result_key, **kwargs)

        # 处理请求错误
        resp.raise_for_status()

        # 返回数据
        ret_data = resp.json()
        if ret_data.get("code") != 0:
            error_msg = ret_data.get("message")
            if not no_error_log:
                print(f"【115】{method} 请求 {endpoint} 出错：{error_msg}")
            if "已达到当前访问上限" in error_msg:
                if retry_times <= 0:
                    print(f"【115】{method} 请求 {endpoint} 达到访问上限，重试次数用尽！")
                    return None
                kwargs["retry_limit"] = retry_times - 1
                print(f"【115】{method} 请求 {endpoint} 达到访问上限，等待 {self.retry_delay} 秒后重试...")
                time.sleep(self.retry_delay)
                return self._api_request(method, endpoint, result_key, **kwargs)
            return None

        if result_key:
            return ret_data.get(result_key)
        return ret_data

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

    # ========== 秒传和分片上传功能 ==========

    @staticmethod
    def _calc_sha1(filepath: Path, size: Optional[int] = None) -> str:
        """
        计算文件SHA1（符合115规范）
        size: 前多少字节
        """
        sha1 = hashlib.sha1()
        with open(filepath, 'rb') as f:
            if size:
                chunk = f.read(size)
                sha1.update(chunk)
            else:
                while chunk := f.read(8192):
                    sha1.update(chunk)
        return sha1.hexdigest()

    def _delay_get_item(self, path: Path) -> Optional[FileItem]:
        """
        自动延迟重试 get_item 模块
        """
        for i in range(1, 4):
            time.sleep(2 ** i)
            fileitem = self.get_item(path)
            if fileitem:
                return fileitem
        return None

    def _encode_callback(self, cb: str) -> str:
        """编码回调参数"""
        return oss2.utils.b64encode_as_string(cb)

    def _upload_file_advanced(self, target_dir: FileItem, local_path: Path,
                             new_name: Optional[str] = None) -> Optional[FileItem]:
        """
        实现带秒传、断点续传和二次认证的文件上传（基于MoviePilot方案）
        """
        target_name = new_name or local_path.name
        target_path = Path(target_dir.path) / target_name
        
        # 计算文件特征值
        file_size = local_path.stat().st_size
        file_sha1 = self._calc_sha1(local_path)
        file_preid = self._calc_sha1(local_path, 128 * 1024 * 1024)  # 前128MB的SHA1

        # 获取目标目录CID
        target_cid = self._get_folder_id(target_dir.path)
        target_param = f"U_1_{target_cid}"

        # Step 1: 初始化上传
        init_data = {
            "file_name": target_name,
            "file_size": file_size,
            "target": target_param,
            "fileid": file_sha1,
            "preid": file_preid
        }
        
        init_resp = self._api_request(
            "POST",
            "/open/upload/init",
            data=init_data
        )
        
        if not init_resp:
            return None
            
        if not init_resp.get("state"):
            print(f"【115】初始化上传失败: {init_resp.get('error')}")
            return None
            
        # 结果
        init_result = init_resp.get("data")
        print(f"【115】上传 Step 1 初始化结果: {init_result}")
        
        # 回调信息
        bucket_name = init_result.get("bucket")
        object_name = init_result.get("object")
        callback = init_result.get("callback")
        # 二次认证信息
        sign_check = init_result.get("sign_check")
        pick_code = init_result.get("pick_code")
        sign_key = init_result.get("sign_key")

        # Step 2: 处理二次认证
        if init_result.get("code") in [700, 701] and sign_check:
            sign_checks = sign_check.split("-")
            start = int(sign_checks[0])
            end = int(sign_checks[1])
            
            # 计算指定区间的SHA1
            with open(local_path, "rb") as f:
                f.seek(start)
                chunk = f.read(end - start + 1)
                sign_val = hashlib.sha1(chunk).hexdigest().upper()
                
            # 重新初始化请求
            init_data.update({
                "pick_code": pick_code,
                "sign_key": sign_key,
                "sign_val": sign_val
            })
            
            init_resp = self._api_request(
                "POST",
                "/open/upload/init",
                data=init_data
            )
            
            if not init_resp:
                return None
                
            if not init_resp.get("state"):
                print(f"【115】上传二次认证失败: {init_resp.get('error')}")
                return None
                
            # 二次认证结果
            init_result = init_resp.get("data")
            print(f"【115】上传 Step 2 二次认证结果: {init_result}")
            
            if not pick_code:
                pick_code = init_result.get("pick_code")
            if not bucket_name:
                bucket_name = init_result.get("bucket")
            if not object_name:
                object_name = init_result.get("object")
            if not callback:
                callback = init_result.get("callback")

        # Step 3: 秒传
        if init_result.get("status") == 2:
            print(f"【115】{target_name} 秒传成功")
            file_id = init_result.get("file_id", None)
            
            if file_id:
                print(f"【115】{target_name} 使用秒传返回ID获取文件信息")
                time.sleep(2)
                
                info_resp = self._api_request(
                    "GET",
                    "/open/folder/get_info",
                    params={
                        "file_id": int(file_id)
                    }
                )
                
                if info_resp:
                    return FileItem(
                        name=info_resp.get("file_name", target_name),
                        path=str(target_path),
                        type="file",
                        is_dir=False,
                        parent=target_dir.path,
                        size=info_resp.get('size', 0),
                        modify_time=info_resp.get('utime', int(time.time()))
                    )
                    
            return self._delay_get_item(target_path)

        # Step 4: 获取上传凭证
        token_resp = self._api_request(
            "GET",
            "/open/upload/get_token"
        )
        
        if not token_resp:
            print("【115】获取上传凭证失败")
            return None
            
        print(f"【115】上传 Step 4 获取上传凭证结果: {token_resp}")
        
        # 上传凭证
        endpoint = token_resp.get("endpoint")
        AccessKeyId = token_resp.get("AccessKeyId")
        AccessKeySecret = token_resp.get("AccessKeySecret")
        SecurityToken = token_resp.get("SecurityToken")

        # Step 5: 断点续传
        resume_resp = self._api_request(
            "POST",
            "/open/upload/resume",
            data={
                "file_size": file_size,
                "target": target_param,
                "fileid": file_sha1,
                "pick_code": pick_code
            }
        )
        
        if resume_resp:
            print(f"【115】上传 Step 5 断点续传结果: {resume_resp}")
            if resume_resp.get("callback"):
                callback = resume_resp["callback"]

        # Step 6: 对象存储上传
        auth = oss2.StsAuth(
            access_key_id=AccessKeyId,
            access_key_secret=AccessKeySecret,
            security_token=SecurityToken
        )
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        
        # 确定分片大小
        part_size = determine_part_size(file_size, preferred_size=10 * 1024 * 1024)

        # 初始化进度条
        print(f"【115】开始上传: {local_path} -> {target_path}，分片大小：{part_size}")

        # 初始化分片
        upload_id = bucket.init_multipart_upload(object_name,
                                                 params={
                                                     "encoding-type": "url",
                                                     "sequential": ""
                                                 }).upload_id
        parts = []
        
        # 逐个上传分片（带进度显示和错误重试）
        with open(local_path, 'rb') as fileobj:
            part_number = 1
            offset = 0
            
            while offset < file_size:
                num_to_upload = min(part_size, file_size - offset)
                
                print(f"【115】开始上传 {target_name} 分片 {part_number}: {offset} -> {offset + num_to_upload}")
                
                # 分片上传（带重试机制）
                success = False
                for attempt in range(3):  # 最大重试次数
                    try:
                        result = bucket.upload_part(object_name, upload_id, part_number,
                                                    data=SizedFileAdapter(fileobj, num_to_upload))
                        if result.status == 200:
                            parts.append(PartInfo(part_number, result.etag))
                            success = True
                            break
                        else:
                            print(f"【115】{target_name} 分片 {part_number} 第 {attempt + 1} 次上传失败：{result.status}")
                    except Exception as e:
                        print(f"【115】{target_name} 分片 {part_number} 上传异常: {str(e)}")
                
                if not success:
                    raise Exception(f"【115】{target_name} 分片 {part_number} 上传失败！")
                
                print(f"【115】{target_name} 分片 {part_number} 上传完成")
                
                # 更新进度
                offset += num_to_upload
                progress = (offset * 100) / file_size
                print(f"【115】上传进度: {progress:.1f}%")
                part_number += 1

        # 完成上传
        headers = {
            'X-oss-callback': self._encode_callback(callback["callback"]),
            'x-oss-callback-var': self._encode_callback(callback["callback_var"]),
            'x-oss-forbid-overwrite': 'false'
        }
        
        try:
            result = bucket.complete_multipart_upload(object_name, upload_id, parts,
                                                      headers=headers)
            if result.status == 200:
                print(f"【115】上传 Step 6 回调结果：{result.resp.response.json()}")
                print(f"【115】{target_name} 上传成功")
            else:
                print(f"【115】{target_name} 上传失败，错误码: {result.status}")
                return None
                
        except oss2.exceptions.OssError as e:
            if e.code == "FileAlreadyExists":
                print(f"【115】{target_name} 已存在")
            else:
                print(f"【115】{target_name} 上传失败: {e.status}, 错误码: {e.code}, 详情: {e.message}")
                return None
                
        # 返回结果
        return self._delay_get_item(target_path)

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

    # ========== 秒传和分片上传功能 ==========

    @staticmethod
    def _calc_sha1(filepath: Path, size: Optional[int] = None) -> str:
        """
        计算文件SHA1（符合115规范）
        size: 前多少字节
        """
        sha1 = hashlib.sha1()
        with open(filepath, 'rb') as f:
            if size:
                chunk = f.read(size)
                sha1.update(chunk)
            else:
                while chunk := f.read(8192):
                    sha1.update(chunk)
        return sha1.hexdigest()

    def _delay_get_item(self, path: Path) -> Optional[FileItem]:
        """
        自动延迟重试 get_item 模块
        """
        for i in range(1, 4):
            time.sleep(2 ** i)
            fileitem = self.get_item(path)
            if fileitem:
                return fileitem
        return None

    def _encode_callback(self, cb: str) -> str:
        """编码回调参数"""
        return oss2.utils.b64encode_as_string(cb)

    def _upload_file_advanced(self, target_dir: FileItem, local_path: Path,
                             new_name: Optional[str] = None) -> Optional[FileItem]:
        """
        实现带秒传、断点续传和二次认证的文件上传（基于MoviePilot方案）
        """
        target_name = new_name or local_path.name
        target_path = Path(target_dir.path) / target_name
        
        # 计算文件特征值
        file_size = local_path.stat().st_size
        file_sha1 = self._calc_sha1(local_path)
        file_preid = self._calc_sha1(local_path, 128 * 1024 * 1024)  # 前128MB的SHA1

        # 获取目标目录CID
        target_cid = self._get_folder_id(target_dir.path)
        target_param = f"U_1_{target_cid}"

        # Step 1: 初始化上传
        init_data = {
            "file_name": target_name,
            "file_size": file_size,
            "target": target_param,
            "fileid": file_sha1,
            "preid": file_preid
        }
        
        init_resp = self._api_request(
            "POST",
            "/open/upload/init",
            data=init_data
        )
        
        if not init_resp:
            return None
            
        if not init_resp.get("state"):
            print(f"【115】初始化上传失败: {init_resp.get('error')}")
            return None
            
        # 结果
        init_result = init_resp.get("data")
        print(f"【115】上传 Step 1 初始化结果: {init_result}")
        
        # 回调信息
        bucket_name = init_result.get("bucket")
        object_name = init_result.get("object")
        callback = init_result.get("callback")
        # 二次认证信息
        sign_check = init_result.get("sign_check")
        pick_code = init_result.get("pick_code")
        sign_key = init_result.get("sign_key")

        # Step 2: 处理二次认证
        if init_result.get("code") in [700, 701] and sign_check:
            sign_checks = sign_check.split("-")
            start = int(sign_checks[0])
            end = int(sign_checks[1])
            
            # 计算指定区间的SHA1
            with open(local_path, "rb") as f:
                f.seek(start)
                chunk = f.read(end - start + 1)
                sign_val = hashlib.sha1(chunk).hexdigest().upper()
                
            # 重新初始化请求
            init_data.update({
                "pick_code": pick_code,
                "sign_key": sign_key,
                "sign_val": sign_val
            })
            
            init_resp = self._api_request(
                "POST",
                "/open/upload/init",
                data=init_data
            )
            
            if not init_resp:
                return None
                
            if not init_resp.get("state"):
                print(f"【115】上传二次认证失败: {init_resp.get('error')}")
                return None
                
            # 二次认证结果
            init_result = init_resp.get("data")
            print(f"【115】上传 Step 2 二次认证结果: {init_result}")
            
            if not pick_code:
                pick_code = init_result.get("pick_code")
            if not bucket_name:
                bucket_name = init_result.get("bucket")
            if not object_name:
                object_name = init_result.get("object")
            if not callback:
                callback = init_result.get("callback")

        # Step 3: 秒传
        if init_result.get("status") == 2:
            print(f"【115】{target_name} 秒传成功")
            file_id = init_result.get("file_id", None)
            
            if file_id:
                print(f"【115】{target_name} 使用秒传返回ID获取文件信息")
                time.sleep(2)
                
                info_resp = self._api_request(
                    "GET",
                    "/open/folder/get_info",
                    params={
                        "file_id": int(file_id)
                    }
                )
                
                if info_resp:
                    return FileItem(
                        name=info_resp.get("file_name", target_name),
                        path=str(target_path),
                        type="file",
                        is_dir=False,
                        parent=target_dir.path,
                        size=info_resp.get('size', 0),
                        modify_time=info_resp.get('utime', int(time.time()))
                    )
                    
            return self._delay_get_item(target_path)

        # Step 4: 获取上传凭证
        token_resp = self._api_request(
            "GET",
            "/open/upload/get_token"
        )
        
        if not token_resp:
            print("【115】获取上传凭证失败")
            return None
            
        print(f"【115】上传 Step 4 获取上传凭证结果: {token_resp}")
        
        # 上传凭证
        endpoint = token_resp.get("endpoint")
        AccessKeyId = token_resp.get("AccessKeyId")
        AccessKeySecret = token_resp.get("AccessKeySecret")
        SecurityToken = token_resp.get("SecurityToken")

        # Step 5: 断点续传
        resume_resp = self._api_request(
            "POST",
            "/open/upload/resume",
            data={
                "file_size": file_size,
                "target": target_param,
                "fileid": file_sha1,
                "pick_code": pick_code
            }
        )
        
        if resume_resp:
            print(f"【115】上传 Step 5 断点续传结果: {resume_resp}")
            if resume_resp.get("callback"):
                callback = resume_resp["callback"]

        # Step 6: 对象存储上传
        auth = oss2.StsAuth(
            access_key_id=AccessKeyId,
            access_key_secret=AccessKeySecret,
            security_token=SecurityToken
        )
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        
        # 确定分片大小
        part_size = determine_part_size(file_size, preferred_size=10 * 1024 * 1024)

        # 初始化进度条
        print(f"【115】开始上传: {local_path} -> {target_path}，分片大小：{part_size}")

        # 初始化分片
        upload_id = bucket.init_multipart_upload(object_name,
                                                 params={
                                                     "encoding-type": "url",
                                                     "sequential": ""
                                                 }).upload_id
        parts = []
        
        # 逐个上传分片（带进度显示和错误重试）
        with open(local_path, 'rb') as fileobj:
            part_number = 1
            offset = 0
            
            while offset < file_size:
                num_to_upload = min(part_size, file_size - offset)
                
                print(f"【115】开始上传 {target_name} 分片 {part_number}: {offset} -> {offset + num_to_upload}")
                
                # 分片上传（带重试机制）
                success = False
                for attempt in range(3):  # 最大重试次数
                    try:
                        result = bucket.upload_part(object_name, upload_id, part_number,
                                                    data=SizedFileAdapter(fileobj, num_to_upload))
                        if result.status == 200:
                            parts.append(PartInfo(part_number, result.etag))
                            success = True
                            break
                        else:
                            print(f"【115】{target_name} 分片 {part_number} 第 {attempt + 1} 次上传失败：{result.status}")
                    except Exception as e:
                        print(f"【115】{target_name} 分片 {part_number} 上传异常: {str(e)}")
                
                if not success:
                    raise Exception(f"【115】{target_name} 分片 {part_number} 上传失败！")
                
                print(f"【115】{target_name} 分片 {part_number} 上传完成")
                
                # 更新进度
                offset += num_to_upload
                progress = (offset * 100) / file_size
                print(f"【115】上传进度: {progress:.1f}%")
                part_number += 1

        # 完成上传
        headers = {
            'X-oss-callback': self._encode_callback(callback["callback"]),
            'x-oss-callback-var': self._encode_callback(callback["callback_var"]),
            'x-oss-forbid-overwrite': 'false'
        }
        
        try:
            result = bucket.complete_multipart_upload(object_name, upload_id, parts,
                                                      headers=headers)
            if result.status == 200:
                print(f"【115】上传 Step 6 回调结果：{result.resp.response.json()}")
                print(f"【115】{target_name} 上传成功")
            else:
                print(f"【115】{target_name} 上传失败，错误码: {result.status}")
                return None
                
        except oss2.exceptions.OssError as e:
            if e.code == "FileAlreadyExists":
                print(f"【115】{target_name} 已存在")
            else:
                print(f"【115】{target_name} 上传失败: {e.status}, 错误码: {e.code}, 详情: {e.message}")
                return None
                
        # 返回结果
        return self._delay_get_item(target_path)