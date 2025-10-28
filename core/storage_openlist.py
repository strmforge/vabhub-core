"""
OpenList存储模块
基于MoviePilot的存储架构设计，替换Alist功能
"""

import os
import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from .storage_base import StorageBase
from .storage_schemas import (
    StorageInfo, FileItem, TransferRequest, TransferResult,
    RenameRequest, RenameResult, MediaInfo
)
from .system_utils import SystemUtils


class OpenListStorage(StorageBase):
    """OpenList存储实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "openlist"
        self.display_name = "OpenList"
        self.transfer_types = ["move", "copy"]  # OpenList支持移动和复制
        
        # OpenList配置
        self.api_base = config.get("api_base", "http://localhost:5244")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.token = config.get("token", "")
        
        # 会话管理
        self.session = None
        self.is_authenticated = False
    
    async def initialize(self) -> bool:
        """初始化OpenList存储"""
        try:
            self.session = aiohttp.ClientSession()
            
            # 检查认证状态
            if not await self._check_auth():
                if self.token:
                    # 尝试使用现有token
                    if not await self._validate_token():
                        # 需要重新登录
                        if not await self._login():
                            return False
                else:
                    # 需要登录
                    if not await self._login():
                        return False
            
            self.is_authenticated = True
            return True
            
        except Exception as e:
            self.logger.error(f"初始化OpenList失败: {e}")
            return False
    
    async def _check_auth(self) -> bool:
        """检查认证状态"""
        return self.is_authenticated and self.token
    
    async def _validate_token(self) -> bool:
        """验证token有效性"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with self.session.get(f"{self.api_base}/api/me", headers=headers) as resp:
                return resp.status == 200
        except:
            return False
    
    async def _login(self) -> bool:
        """登录OpenList"""
        try:
            data = {
                "username": self.username,
                "password": self.password
            }
            
            async with self.session.post(f"{self.api_base}/api/auth/login", json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    self.token = result.get("data", {}).get("token", "")
                    
                    # 保存配置
                    await self._save_config()
                    
                    return True
        except Exception as e:
            self.logger.error(f"登录OpenList失败: {e}")
        
        return False
    
    async def _save_config(self):
        """保存配置到文件"""
        config_path = Path("config/storage_openlist.json")
        config_path.parent.mkdir(exist_ok=True)
        
        config = {
            "api_base": self.api_base,
            "username": self.username,
            "password": self.password,
            "token": self.token
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    async def list_files(self, path: str = "", page: int = 1, page_size: int = 100) -> List[FileItem]:
        """列出文件"""
        if not self.is_authenticated:
            return []
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            params = {
                "path": path or "/",
                "page": page,
                "per_page": page_size
            }
            
            async with self.session.get(f"{self.api_base}/api/fs/list", headers=headers, params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    files = result.get("data", {}).get("content", [])
                    
                    return [
                        FileItem(
                            name=file["name"],
                            path=file["path"],
                            is_dir=file["is_dir"],
                            size=file.get("size", 0),
                            modify_time=datetime.fromtimestamp(file.get("modified", 0)),
                            create_time=datetime.fromtimestamp(file.get("created", 0))
                        )
                        for file in files
                    ]
        except Exception as e:
            self.logger.error(f"列出文件失败: {e}")
        
        return []
    
    async def mkdir(self, path: str) -> bool:
        """创建目录"""
        if not self.is_authenticated:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = {"path": path}
            
            async with self.session.post(f"{self.api_base}/api/fs/mkdir", headers=headers, json=data) as resp:
                return resp.status == 200
        except Exception as e:
            self.logger.error(f"创建目录失败: {e}")
            return False
    
    async def delete(self, path: str) -> bool:
        """删除文件"""
        if not self.is_authenticated:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = {"paths": [path]}
            
            async with self.session.post(f"{self.api_base}/api/fs/remove", headers=headers, json=data) as resp:
                return resp.status == 200
        except Exception as e:
            self.logger.error(f"删除文件失败: {e}")
            return False
    
    async def rename(self, old_path: str, new_path: str) -> bool:
        """重命名文件"""
        if not self.is_authenticated:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = {
                "src_path": old_path,
                "dst_path": new_path
            }
            
            async with self.session.post(f"{self.api_base}/api/fs/rename", headers=headers, json=data) as resp:
                return resp.status == 200
        except Exception as e:
            self.logger.error(f"重命名文件失败: {e}")
            return False
    
    async def transfer(self, request: TransferRequest) -> TransferResult:
        """文件转移"""
        if not self.is_authenticated:
            return TransferResult(success=False, message="未认证")
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            if request.transfer_type == "move":
                # 移动文件
                data = {
                    "src_path": request.source_path,
                    "dst_path": request.target_path
                }
                async with self.session.post(f"{self.api_base}/api/fs/move", headers=headers, json=data) as resp:
                    if resp.status == 200:
                        return TransferResult(success=True, message="移动成功")
            
            elif request.transfer_type == "copy":
                # 复制文件
                data = {
                    "src_path": request.source_path,
                    "dst_path": request.target_path
                }
                async with self.session.post(f"{self.api_base}/api/fs/copy", headers=headers, json=data) as resp:
                    if resp.status == 200:
                        return TransferResult(success=True, message="复制成功")
            
            return TransferResult(success=False, message="传输失败")
            
        except Exception as e:
            self.logger.error(f"文件转移失败: {e}")
            return TransferResult(success=False, message=f"传输失败: {e}")
    
    async def get_storage_info(self) -> StorageInfo:
        """获取存储信息"""
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
            headers = {"Authorization": f"Bearer {self.token}"}
            
            async with self.session.get(f"{self.api_base}/api/fs/status", headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    data = result.get("data", {})
                    
                    return StorageInfo(
                        name=self.name,
                        display_name=self.display_name,
                        total_space=data.get("total", 0),
                        used_space=data.get("used", 0),
                        free_space=data.get("free", 0),
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
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None
        self.is_authenticated = False