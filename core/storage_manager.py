#!/usr/bin/env python3
"""
存储管理器 - 管理本地和云存储集成
"""

import os
import shutil
import asyncio
import time
from typing import Dict, Any, List, Optional
from enum import Enum
import logging


class StorageType(Enum):
    """存储类型枚举"""

    LOCAL = "local"
    S3 = "s3"
    GOOGLE_CLOUD = "google_cloud"
    AZURE = "azure"
    ALIYUN = "aliyun"
    TENCENT_CLOUD = "tencent_cloud"


class StorageStatus(Enum):
    """存储状态枚举"""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    LIMITED = "limited"
    ERROR = "error"


class StorageConfig:
    """存储配置类"""

    def __init__(self, storage_type: StorageType, config: Dict[str, Any]):
        self.storage_type = storage_type
        self.config = config
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 1)
        self.max_size = config.get("max_size", 0)  # 0表示无限制
        self.used_size = 0

    def validate(self) -> bool:
        """验证配置"""
        if not self.enabled:
            return True

        if self.storage_type == StorageType.LOCAL:
            return self._validate_local_config()
        elif self.storage_type == StorageType.S3:
            return self._validate_s3_config()
        # 其他存储类型的验证...

        return True

    def _validate_local_config(self) -> bool:
        """验证本地存储配置"""
        path = self.config.get("path", "")
        if not path:
            return False

        try:
            os.makedirs(path, exist_ok=True)
            # 测试写入权限
            test_file = os.path.join(path, "test_write")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception:
            return False

    def _validate_s3_config(self) -> bool:
        """验证S3配置"""
        required_keys = ["endpoint", "access_key", "secret_key", "bucket"]
        for key in required_keys:
            if key not in self.config or not self.config[key]:
                return False
        return True


class StorageManager:
    """存储管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("storage_manager")
        self.storage_configs: Dict[str, StorageConfig] = {}
        self.storage_status: Dict[str, StorageStatus] = {}
        self._setup_storages()

    def _setup_storages(self):
        """设置存储配置"""
        # 加载存储配置
        storages_config = self.config.get("storages", {})

        for storage_name, storage_config in storages_config.items():
            try:
                storage_type = StorageType(storage_config.get("type", "local"))
                config = StorageConfig(storage_type, storage_config)

                if config.validate():
                    self.storage_configs[storage_name] = config
                    self.storage_status[storage_name] = StorageStatus.AVAILABLE
                    self.logger.info(
                        f"Storage configured: {storage_name} ({storage_type.value})"
                    )
                else:
                    self.storage_status[storage_name] = StorageStatus.ERROR
                    self.logger.error(
                        f"Storage config validation failed: {storage_name}"
                    )
            except Exception as e:
                self.logger.error(f"Failed to setup storage {storage_name}: {e}")
                self.storage_status[storage_name] = StorageStatus.ERROR

    async def upload_file(
        self,
        file_path: str,
        target_path: str,
        storage_name: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """上传文件到存储"""
        try:
            if not os.path.exists(file_path):
                return {"error": "Source file does not exist"}

            # 选择存储
            if storage_name is None:
                storage_name = "default"
            selected_storage = await self._select_storage(
                storage_name, target_path, **kwargs
            )
            if not selected_storage:
                return {"error": "No suitable storage available"}

            # 执行上传
            result = await self._upload_to_storage(
                selected_storage, file_path, target_path, **kwargs
            )

            # 更新存储使用情况
            await self._update_storage_usage(selected_storage, result.get("size", 0))

            self.logger.info(
                f"File uploaded: {file_path} -> {target_path} on {selected_storage}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Upload file failed: {e}")
            return {"error": str(e)}

    async def download_file(
        self,
        source_path: str,
        target_path: str,
        storage_name: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """从存储下载文件"""
        try:
            # 选择存储
            if storage_name is None:
                storage_name = "default"
            selected_storage = await self._select_storage(
                storage_name, source_path, **kwargs
            )
            if not selected_storage:
                return {"error": "No suitable storage available"}

            # 执行下载
            result = await self._download_from_storage(
                selected_storage, source_path, target_path, **kwargs
            )

            self.logger.info(
                f"File downloaded: {source_path} -> {target_path} from {selected_storage}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Download file failed: {e}")
            return {"error": str(e)}

    async def delete_file(
        self, file_path: str, storage_name: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """删除存储中的文件"""
        try:
            # 选择存储
            if storage_name is None:
                storage_name = "default"
            selected_storage = await self._select_storage(
                storage_name, file_path, **kwargs
            )
            if not selected_storage:
                return {"error": "No suitable storage available"}

            # 执行删除
            result = await self._delete_from_storage(
                selected_storage, file_path, **kwargs
            )

            # 更新存储使用情况
            await self._update_storage_usage(selected_storage, -result.get("size", 0))

            self.logger.info(f"File deleted: {file_path} from {selected_storage}")
            return result

        except Exception as e:
            self.logger.error(f"Delete file failed: {e}")
            return {"error": str(e)}

    async def list_files(
        self,
        path: str = "",
        storage_name: Optional[str] = None,
        recursive: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """列出存储中的文件"""
        try:
            # 选择存储
            if storage_name is None:
                storage_name = "default"
            selected_storage = await self._select_storage(storage_name, path, **kwargs)
            if not selected_storage:
                return {"error": "No suitable storage available"}

            # 执行列表操作
            result = await self._list_storage_files(
                selected_storage, path, recursive, **kwargs
            )

            return result

        except Exception as e:
            self.logger.error(f"List files failed: {e}")
            return {"error": str(e)}

    async def get_file_info(
        self, file_path: str, storage_name: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            # 选择存储
            if storage_name is None:
                storage_name = "default"
            selected_storage = await self._select_storage(
                storage_name, file_path, **kwargs
            )
            if not selected_storage:
                return {"error": "No suitable storage available"}

            # 获取文件信息
            result = await self._get_storage_file_info(
                selected_storage, file_path, **kwargs
            )

            return result

        except Exception as e:
            self.logger.error(f"Get file info failed: {e}")
            return {"error": str(e)}

    async def get_storage_stats(
        self, storage_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            if storage_name is not None:
                if storage_name not in self.storage_configs:
                    return {"error": "Storage not found"}

                config = self.storage_configs[storage_name]
                status = self.storage_status.get(
                    storage_name, StorageStatus.UNAVAILABLE
                )

                return {
                    "name": storage_name,
                    "type": config.storage_type.value,
                    "status": status.value,
                    "max_size": config.max_size,
                    "used_size": config.used_size,
                    "available_size": (
                        config.max_size - config.used_size
                        if config.max_size > 0
                        else float("inf")
                    ),
                    "enabled": config.enabled,
                    "priority": config.priority,
                }
            else:
                # 返回所有存储的统计信息
                stats = {}
                for name, config in self.storage_configs.items():
                    status = self.storage_status.get(name, StorageStatus.UNAVAILABLE)
                    stats[name] = {
                        "type": config.storage_type.value,
                        "status": status.value,
                        "max_size": config.max_size,
                        "used_size": config.used_size,
                        "available_size": (
                            config.max_size - config.used_size
                            if config.max_size > 0
                            else float("inf")
                        ),
                        "enabled": config.enabled,
                        "priority": config.priority,
                    }

                return {"storages": stats}

        except Exception as e:
            self.logger.error(f"Get storage stats failed: {e}")
            return {"error": str(e)}

    async def _select_storage(
        self, storage_name: Optional[str] = None, path: str = "", **kwargs
    ) -> Optional[str]:
        """选择合适的存储"""
        try:
            # 如果指定了存储名称，直接使用
            if storage_name is not None:
                if (
                    storage_name in self.storage_configs
                    and self.storage_status.get(storage_name) == StorageStatus.AVAILABLE
                ):
                    return storage_name
                return None

            # 根据路径和策略选择存储
            available_storages = []
            for name, config in self.storage_configs.items():
                if (
                    config.enabled
                    and self.storage_status.get(name) == StorageStatus.AVAILABLE
                ):
                    available_storages.append((name, config))

            if not available_storages:
                return None

            # 按优先级排序
            available_storages.sort(key=lambda x: x[1].priority)

            # 选择第一个可用的存储
            return available_storages[0][0]

        except Exception as e:
            self.logger.error(f"Select storage failed: {e}")
            return None

    async def _upload_to_storage(
        self, storage_name: str, file_path: str, target_path: str, **kwargs
    ) -> Dict[str, Any]:
        """上传文件到指定存储"""
        config = self.storage_configs[storage_name]

        if config.storage_type == StorageType.LOCAL:
            return await self._upload_to_local(
                storage_name, file_path, target_path, **kwargs
            )
        elif config.storage_type == StorageType.S3:
            return await self._upload_to_s3(
                storage_name, file_path, target_path, **kwargs
            )
        # 其他存储类型的上传实现...

        return {"error": f"Unsupported storage type: {config.storage_type.value}"}

    async def _upload_to_local(
        self, storage_name: str, file_path: str, target_path: str, **kwargs
    ) -> Dict[str, Any]:
        """上传到本地存储"""
        try:
            config = self.storage_configs[storage_name]
            storage_path = config.config.get("path", "")

            full_target_path = os.path.join(storage_path, target_path)

            # 确保目标目录存在
            os.makedirs(os.path.dirname(full_target_path), exist_ok=True)

            # 复制文件
            shutil.copy2(file_path, full_target_path)

            # 获取文件信息
            file_size = os.path.getsize(full_target_path)

            return {
                "storage": storage_name,
                "path": target_path,
                "size": file_size,
                "uploaded_at": time.time(),
            }
        except Exception as e:
            self.logger.error(f"Upload to local failed: {e}")
            return {"error": str(e)}

    async def _upload_to_s3(
        self, storage_name: str, file_path: str, target_path: str, **kwargs
    ) -> Dict[str, Any]:
        """上传到S3存储"""
        try:
            config = self.storage_configs[storage_name]

            # 这里应该使用boto3或其他S3客户端库
            # 暂时使用模拟实现
            await asyncio.sleep(0.1)  # 模拟上传延迟

            file_size = os.path.getsize(file_path)

            return {
                "storage": storage_name,
                "path": target_path,
                "size": file_size,
                "uploaded_at": time.time(),
                "url": f"https://{config.config.get('bucket')}.s3.amazonaws.com/{target_path}",
            }
        except Exception as e:
            self.logger.error(f"Upload to S3 failed: {e}")
            return {"error": str(e)}

    async def _download_from_storage(
        self, storage_name: str, source_path: str, target_path: str, **kwargs
    ) -> Dict[str, Any]:
        """从存储下载文件"""
        config = self.storage_configs[storage_name]

        if config.storage_type == StorageType.LOCAL:
            return await self._download_from_local(
                storage_name, source_path, target_path, **kwargs
            )
        elif config.storage_type == StorageType.S3:
            return await self._download_from_s3(
                storage_name, source_path, target_path, **kwargs
            )
        # 其他存储类型的下载实现...

        return {"error": f"Unsupported storage type: {config.storage_type.value}"}

    async def _download_from_local(
        self, storage_name: str, source_path: str, target_path: str, **kwargs
    ) -> Dict[str, Any]:
        """从本地存储下载"""
        try:
            config = self.storage_configs[storage_name]
            storage_path = config.config.get("path", "")

            full_source_path = os.path.join(storage_path, source_path)

            if not os.path.exists(full_source_path):
                return {"error": "Source file does not exist"}

            # 确保目标目录存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # 复制文件
            shutil.copy2(full_source_path, target_path)

            file_size = os.path.getsize(target_path)

            return {
                "storage": storage_name,
                "path": source_path,
                "size": file_size,
                "downloaded_at": time.time(),
            }
        except Exception as e:
            self.logger.error(f"Download from local failed: {e}")
            return {"error": str(e)}

    async def _download_from_s3(
        self, storage_name: str, source_path: str, target_path: str, **kwargs
    ) -> Dict[str, Any]:
        """从S3存储下载"""
        try:
            config = self.storage_configs[storage_name]

            # 这里应该使用boto3或其他S3客户端库
            # 暂时使用模拟实现
            await asyncio.sleep(0.1)  # 模拟下载延迟

            # 模拟文件大小
            file_size = 1024 * 1024  # 1MB

            return {
                "storage": storage_name,
                "path": source_path,
                "size": file_size,
                "downloaded_at": time.time(),
            }
        except Exception as e:
            self.logger.error(f"Download from S3 failed: {e}")
            return {"error": str(e)}

    async def _delete_from_storage(
        self, storage_name: str, file_path: str, **kwargs
    ) -> Dict[str, Any]:
        """从存储删除文件"""
        config = self.storage_configs[storage_name]

        if config.storage_type == StorageType.LOCAL:
            return await self._delete_from_local(storage_name, file_path, **kwargs)
        elif config.storage_type == StorageType.S3:
            return await self._delete_from_s3(storage_name, file_path, **kwargs)
        # 其他存储类型的删除实现...

        return {"error": f"Unsupported storage type: {config.storage_type.value}"}

    async def _delete_from_local(
        self, storage_name: str, file_path: str, **kwargs
    ) -> Dict[str, Any]:
        """从本地存储删除"""
        try:
            config = self.storage_configs[storage_name]
            storage_path = config.config.get("path", "")

            full_file_path = os.path.join(storage_path, file_path)

            if not os.path.exists(full_file_path):
                return {"error": "File does not exist"}

            file_size = os.path.getsize(full_file_path)

            # 删除文件
            os.remove(full_file_path)

            return {
                "storage": storage_name,
                "path": file_path,
                "size": file_size,
                "deleted_at": time.time(),
            }
        except Exception as e:
            self.logger.error(f"Delete from local failed: {e}")
            return {"error": str(e)}

    async def _delete_from_s3(
        self, storage_name: str, file_path: str, **kwargs
    ) -> Dict[str, Any]:
        """从S3存储删除"""
        try:
            config = self.storage_configs[storage_name]

            # 这里应该使用boto3或其他S3客户端库
            # 暂时使用模拟实现
            await asyncio.sleep(0.1)  # 模拟删除延迟

            return {
                "storage": storage_name,
                "path": file_path,
                "size": 0,  # 实际实现中应该获取文件大小
                "deleted_at": time.time(),
            }
        except Exception as e:
            self.logger.error(f"Delete from S3 failed: {e}")
            return {"error": str(e)}

    async def _list_storage_files(
        self, storage_name: str, path: str = "", recursive: bool = False, **kwargs
    ) -> Dict[str, Any]:
        """列出存储中的文件"""
        config = self.storage_configs[storage_name]

        if config.storage_type == StorageType.LOCAL:
            return await self._list_local_files(storage_name, path, recursive, **kwargs)
        elif config.storage_type == StorageType.S3:
            return await self._list_s3_files(storage_name, path, recursive, **kwargs)
        # 其他存储类型的列表实现...

        return {"error": f"Unsupported storage type: {config.storage_type.value}"}

    async def _list_local_files(
        self, storage_name: str, path: str = "", recursive: bool = False, **kwargs
    ) -> Dict[str, Any]:
        """列出本地存储文件"""
        try:
            config = self.storage_configs[storage_name]
            storage_path = config.config.get("path", "")

            full_path = os.path.join(storage_path, path)

            if not os.path.exists(full_path):
                return {"error": "Path does not exist"}

            files = []

            if recursive:
                for root, dirs, filenames in os.walk(full_path):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, storage_path)

                        file_info = {
                            "name": filename,
                            "path": relative_path,
                            "size": os.path.getsize(file_path),
                            "modified_at": os.path.getmtime(file_path),
                            "is_directory": False,
                        }
                        files.append(file_info)
            else:
                for item in os.listdir(full_path):
                    item_path = os.path.join(full_path, item)
                    relative_path = os.path.join(path, item) if path else item

                    file_info = {
                        "name": item,
                        "path": relative_path,
                        "size": (
                            os.path.getsize(item_path)
                            if os.path.isfile(item_path)
                            else 0
                        ),
                        "modified_at": os.path.getmtime(item_path),
                        "is_directory": os.path.isdir(item_path),
                    }
                    files.append(file_info)

            return {
                "storage": storage_name,
                "path": path,
                "files": files,
                "total": len(files),
            }
        except Exception as e:
            self.logger.error(f"List local files failed: {e}")
            return {"error": str(e)}

    async def _list_s3_files(
        self, storage_name: str, path: str = "", recursive: bool = False, **kwargs
    ) -> Dict[str, Any]:
        """列出S3存储文件"""
        try:
            config = self.storage_configs[storage_name]

            # 这里应该使用boto3或其他S3客户端库
            # 暂时使用模拟实现
            await asyncio.sleep(0.1)  # 模拟列表延迟

            # 模拟文件列表
            files = [
                {
                    "name": "file1.txt",
                    "path": "file1.txt",
                    "size": 1024,
                    "modified_at": time.time() - 3600,
                    "is_directory": False,
                },
                {
                    "name": "file2.txt",
                    "path": "file2.txt",
                    "size": 2048,
                    "modified_at": time.time() - 7200,
                    "is_directory": False,
                },
            ]

            return {
                "storage": storage_name,
                "path": path,
                "files": files,
                "total": len(files),
            }
        except Exception as e:
            self.logger.error(f"List S3 files failed: {e}")
            return {"error": str(e)}

    async def _get_storage_file_info(
        self, storage_name: str, file_path: str, **kwargs
    ) -> Dict[str, Any]:
        """获取存储文件信息"""
        config = self.storage_configs[storage_name]

        if config.storage_type == StorageType.LOCAL:
            return await self._get_local_file_info(storage_name, file_path, **kwargs)
        elif config.storage_type == StorageType.S3:
            return await self._get_s3_file_info(storage_name, file_path, **kwargs)
        # 其他存储类型的信息获取实现...

        return {"error": f"Unsupported storage type: {config.storage_type.value}"}

    async def _get_local_file_info(
        self, storage_name: str, file_path: str, **kwargs
    ) -> Dict[str, Any]:
        """获取本地存储文件信息"""
        try:
            config = self.storage_configs[storage_name]
            storage_path = config.config.get("path", "")

            full_file_path = os.path.join(storage_path, file_path)

            if not os.path.exists(full_file_path):
                return {"error": "File does not exist"}

            file_info = {
                "storage": storage_name,
                "path": file_path,
                "size": os.path.getsize(full_file_path),
                "modified_at": os.path.getmtime(full_file_path),
                "created_at": os.path.getctime(full_file_path),
                "is_directory": os.path.isdir(full_file_path),
            }

            return file_info
        except Exception as e:
            self.logger.error(f"Get local file info failed: {e}")
            return {"error": str(e)}

    async def _get_s3_file_info(
        self, storage_name: str, file_path: str, **kwargs
    ) -> Dict[str, Any]:
        """获取S3存储文件信息"""
        try:
            config = self.storage_configs[storage_name]

            # 这里应该使用boto3或其他S3客户端库
            # 暂时使用模拟实现
            await asyncio.sleep(0.1)  # 模拟信息获取延迟

            file_info = {
                "storage": storage_name,
                "path": file_path,
                "size": 1024 * 1024,  # 1MB
                "modified_at": time.time() - 3600,
                "created_at": time.time() - 7200,
                "is_directory": False,
                "url": f"https://{config.config.get('bucket')}.s3.amazonaws.com/{file_path}",
            }

            return file_info
        except Exception as e:
            self.logger.error(f"Get S3 file info failed: {e}")
            return {"error": str(e)}

    async def _update_storage_usage(self, storage_name: str, size_delta: int):
        """更新存储使用情况"""
        try:
            if storage_name in self.storage_configs:
                config = self.storage_configs[storage_name]
                config.used_size = max(0, config.used_size + size_delta)

                # 检查存储是否已满
                if config.max_size > 0 and config.used_size >= config.max_size:
                    self.storage_status[storage_name] = StorageStatus.LIMITED
                else:
                    self.storage_status[storage_name] = StorageStatus.AVAILABLE

        except Exception as e:
            self.logger.error(f"Update storage usage failed: {e}")

    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 检查是否有可用的存储
            available_storages = [
                name
                for name, status in self.storage_status.items()
                if status == StorageStatus.AVAILABLE
            ]

            return len(available_storages) > 0
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
