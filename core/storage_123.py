"""
123云盘存储模块
基于MoviePilot的存储架构设计，替换阿里云盘功能
集成123云盘官方API文档功能
"""

import os
import json
import asyncio
import aiohttp
import base64
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from .storage_base import StorageBase
from .storage_schemas import (
    StorageInfo, FileItem, TransferRequest, TransferResult,
    RenameRequest, RenameResult, MediaInfo
)
from .system_utils import SystemUtils
from .encryption import encrypt_sensitive_field, decrypt_sensitive_field


class Cloud123Storage(StorageBase):
    """123云盘存储实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "cloud123"
        self.display_name = "123云盘"
        self.transfer_types = ["move", "copy"]  # 云盘不支持硬链接和软链接
        
        # 123云盘API配置 - 根据官方文档
        self.api_base = "https://api.123pan.com/v1"
        
        # 敏感字段解密
        sensitive_fields = ["access_token", "refresh_token", "client_id", "client_secret"]
        decrypted_config = decrypt_sensitive_field(config, sensitive_fields)
        
        self.access_token = decrypted_config.get("access_token", "")
        self.refresh_token = decrypted_config.get("refresh_token", "")
        self.client_id = decrypted_config.get("client_id", "")
        self.client_secret = decrypted_config.get("client_secret", "")
        
        # 如果client_id为空，使用默认值（已申请通过的）
        if not self.client_id:
            self.client_id = "03fe53676da44ddcbb5a22c04936ec4e"
            self.client_secret = "bfc256b0357b456c8a4e350445a4bd54"
        
        # 会话管理
        self.session = None
        self.is_authenticated = False
    
    async def initialize(self) -> bool:
        """初始化123云盘存储"""
        try:
            self.session = aiohttp.ClientSession()
            
            # 检查认证状态
            if not await self._check_auth():
                if self.access_token:
                    # 尝试刷新token
                    await self._refresh_token()
                else:
                    # 需要重新认证
                    return False
            
            self.is_authenticated = True
            return True
            
        except Exception as e:
            self.logger.error(f"初始化123云盘失败: {e}")
            return False
    
    async def _check_auth(self) -> bool:
        """检查认证状态 - 根据API文档实现"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            async with self.session.get(f"{self.api_base}/user/info", headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("code", 0) == 0
                return False
        except:
            return False
    
    async def _refresh_token(self) -> bool:
        """刷新访问令牌 - 根据API文档实现"""
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            async with self.session.post(f"{self.api_base}/oauth/token", json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code", 0) == 0:
                        self.access_token = result.get("access_token", "")
                        self.refresh_token = result.get("refresh_token", "")
                        
                        # 保存加密后的配置
                        await self._save_config()
                        return True
        except Exception as e:
            self.logger.error(f"刷新token失败: {e}")
        
        return False
    
    async def get_qrcode(self) -> Dict[str, Any]:
        """获取二维码登录信息 - 根据API文档实现"""
        try:
            data = {
                "client_id": self.client_id,
                "scope": "user:read file:read file:write"
            }
            
            async with self.session.post(f"{self.api_base}/oauth/qrcode", json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code", 0) == 0:
                        return {
                            "qrcode_url": result.get("qrcode_url", ""),
                            "qrcode_key": result.get("qrcode_key", ""),
                            "expires_in": result.get("expires_in", 300)
                        }
        except Exception as e:
            self.logger.error(f"获取二维码失败: {e}")
        
        return {}
    
    async def check_qrcode(self, qrcode_key: str) -> Dict[str, Any]:
        """检查二维码登录状态 - 根据API文档实现"""
        try:
            data = {"qrcode_key": qrcode_key}
            
            async with self.session.post(f"{self.api_base}/oauth/qrcode/check", json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code", 0) == 0:
                        status = result.get("status", "")
                        
                        if status == "confirmed":
                            self.access_token = result.get("access_token", "")
                            self.refresh_token = result.get("refresh_token", "")
                            self.is_authenticated = True
                            
                            # 保存加密后的配置
                            await self._save_config()
                        
                        return {
                            "status": status,
                            "message": result.get("message", "")
                        }
        except Exception as e:
            self.logger.error(f"检查二维码状态失败: {e}")
        
        return {"status": "error", "message": "检查失败"}
    
    async def _save_config(self):
        """保存加密配置到文件"""
        config_path = Path("config/storage_123.json")
        config_path.parent.mkdir(exist_ok=True)
        
        # 原始配置
        config = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        # 加密敏感字段
        sensitive_fields = ["access_token", "refresh_token", "client_id", "client_secret"]
        encrypted_config = encrypt_sensitive_field(config, sensitive_fields)
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(encrypted_config, f, ensure_ascii=False, indent=2)
        
        # 设置文件权限为600
        config_path.chmod(0o600)
    
    async def list_files(self, path: str = "", page: int = 1, page_size: int = 100) -> List[FileItem]:
        """列出文件 - 根据API文档实现"""
        if not self.is_authenticated:
            return []
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            params = {
                "path": path or "/",
                "page": page,
                "page_size": page_size
            }
            
            async with self.session.get(f"{self.api_base}/files", headers=headers, params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code", 0) == 0:
                        files = result.get("data", {}).get("files", [])
                        
                        return [
                            FileItem(
                                name=file.get("name", ""),
                                path=file.get("path", ""),
                                is_dir=file.get("type", "") == "dir",
                                size=file.get("size", 0),
                                modify_time=datetime.fromtimestamp(file.get("mtime", 0)),
                                create_time=datetime.fromtimestamp(file.get("ctime", 0))
                            )
                            for file in files
                        ]
        except Exception as e:
            self.logger.error(f"列出文件失败: {e}")
        
        return []
    
    async def mkdir(self, path: str) -> bool:
        """创建目录 - 根据API文档实现"""
        if not self.is_authenticated:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            data = {"path": path}
            
            async with self.session.post(f"{self.api_base}/files/mkdir", headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("code", 0) == 0
        except Exception as e:
            self.logger.error(f"创建目录失败: {e}")
        
        return False
    
    async def delete(self, path: str) -> bool:
        """删除文件 - 根据API文档实现"""
        if not self.is_authenticated:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            data = {"paths": [path]}
            
            async with self.session.post(f"{self.api_base}/files/delete", headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("code", 0) == 0
        except Exception as e:
            self.logger.error(f"删除文件失败: {e}")
        
        return False
    
    async def rename(self, old_path: str, new_path: str) -> bool:
        """重命名文件 - 根据API文档实现"""
        if not self.is_authenticated:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            data = {
                "old_path": old_path,
                "new_path": new_path
            }
            
            async with self.session.post(f"{self.api_base}/files/rename", headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("code", 0) == 0
        except Exception as e:
            self.logger.error(f"重命名文件失败: {e}")
        
        return False
    
    async def transfer(self, request: TransferRequest) -> TransferResult:
        """文件转移 - 根据API文档实现"""
        if not self.is_authenticated:
            return TransferResult(success=False, message="未认证")
        
        try:
            # 123云盘支持移动和复制
            if request.transfer_type not in ["move", "copy"]:
                return TransferResult(success=False, message="不支持的传输类型")
            
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            if request.transfer_type == "move":
                # 移动文件
                data = {
                    "source_path": request.source_path,
                    "target_path": request.target_path
                }
                async with self.session.post(f"{self.api_base}/files/move", headers=headers, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("code", 0) == 0:
                            return TransferResult(success=True, message="移动成功")
                        else:
                            return TransferResult(success=False, message=result.get("message", "移动失败"))
            
            elif request.transfer_type == "copy":
                # 复制文件
                data = {
                    "source_path": request.source_path,
                    "target_path": request.target_path
                }
                async with self.session.post(f"{self.api_base}/files/copy", headers=headers, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("code", 0) == 0:
                            return TransferResult(success=True, message="复制成功")
                        else:
                            return TransferResult(success=False, message=result.get("message", "复制失败"))
            
            return TransferResult(success=False, message="传输失败")
            
        except Exception as e:
            self.logger.error(f"文件转移失败: {e}")
            return TransferResult(success=False, message=f"传输失败: {e}")
    
    async def get_storage_info(self) -> StorageInfo:
        """获取存储信息 - 根据API文档实现"""
        if not self.is_authenticated:
            return StorageInfo(
                name=self.name,
                display_name=self.display_name,
                total_space=0,
                used_space=0,
                free_space=0,
                is_available=False
            )
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with self.session.get(f"{self.api_base}/user/space", headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code", 0) == 0:
                        data = result.get("data", {})
                        
                        return StorageInfo(
                            name=self.name,
                            display_name=self.display_name,
                            total_space=data.get("total_space", 0),
                            used_space=data.get("used_space", 0),
                            free_space=data.get("free_space", 0),
                            is_available=True
                        )
        except Exception as e:
            self.logger.error(f"获取存储信息失败: {e}")
        
        return StorageInfo(
            name=self.name,
            display_name=self.display_name,
            total_space=0,
            used_space=0,
            free_space=0,
            is_available=False
        )
    
    async def upload_file(self, local_path: str, remote_path: str) -> bool:
        """上传文件 - 根据API文档实现V2上传流程，支持秒传"""
        if not self.is_authenticated:
            return False
        
        try:
            # 1. 计算文件哈希值用于秒传
            file_hash = await self._calculate_file_hash(local_path)
            file_size = os.path.getsize(local_path)
            file_name = os.path.basename(remote_path)
            
            # 2. 尝试秒传
            if await self._try_instant_upload(remote_path, file_hash, file_size):
                self.logger.info(f"文件秒传成功: {file_name}")
                return True
            
            # 3. 普通上传流程
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # 创建上传任务（包含哈希值用于后续可能的秒传）
            create_data = {
                "path": remote_path,
                "size": file_size,
                "name": file_name,
                "hash": file_hash,
                "hash_type": "md5"
            }
            
            async with self.session.post(f"{self.api_base}/files/upload/create", 
                                        headers=headers, json=create_data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code", 0) == 0:
                        upload_info = result.get("data", {})
                        
                        # 检查是否触发了秒传
                        if upload_info.get("instant_upload", False):
                            self.logger.info(f"文件秒传成功: {file_name}")
                            return True
                        
                        upload_url = upload_info.get("upload_url", "")
                        
                        # 4. 分片上传（简化实现：小文件直接上传）
                        if file_size < 100 * 1024 * 1024:  # 100MB以下直接上传
                            with open(local_path, "rb") as f:
                                file_data = f.read()
                            
                            async with self.session.put(upload_url, data=file_data) as upload_resp:
                                if upload_resp.status == 200:
                                    # 5. 确认上传完成
                                    confirm_data = {
                                        "upload_id": upload_info.get("upload_id", "")
                                    }
                                    async with self.session.post(f"{self.api_base}/files/upload/complete", 
                                                              headers=headers, json=confirm_data) as confirm_resp:
                                        return confirm_resp.status == 200
            
            return False
            
        except Exception as e:
            self.logger.error(f"文件上传失败: {e}")
            return False
    
    async def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件MD5哈希值"""
        import hashlib
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    async def _try_instant_upload(self, remote_path: str, file_hash: str, file_size: int) -> bool:
        """尝试秒传 - 通过文件哈希值验证文件是否已存在"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # 秒传验证接口
            instant_data = {
                "path": remote_path,
                "hash": file_hash,
                "size": file_size,
                "hash_type": "md5"
            }
            
            async with self.session.post(f"{self.api_base}/files/upload/instant", 
                                       headers=headers, json=instant_data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code", 0) == 0:
                        return result.get("data", {}).get("instant_success", False)
            
            return False
            
        except Exception as e:
            self.logger.debug(f"秒传尝试失败，将使用普通上传: {e}")
            return False
    
    async def download_file(self, remote_path: str, local_path: str) -> bool:
        """下载文件 - 根据API文档实现"""
        if not self.is_authenticated:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            data = {"path": remote_path}
            
            # 获取下载链接
            async with self.session.post(f"{self.api_base}/files/download", 
                                       headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code", 0) == 0:
                        download_url = result.get("data", {}).get("download_url", "")
                        
                        if download_url:
                            # 下载文件
                            async with self.session.get(download_url) as download_resp:
                                if download_resp.status == 200:
                                    with open(local_path, "wb") as f:
                                        async for chunk in download_resp.content.iter_chunked(8192):
                                            f.write(chunk)
                                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"文件下载失败: {e}")
            return False
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None
        self.is_authenticated = False