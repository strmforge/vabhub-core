#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多设备同步引擎
集成 MediaMaster 的多设备媒体库同步精华功能
"""

import asyncio
import logging
import hashlib
import json
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles
import aiohttp

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """同步状态"""
    SYNCING = "syncing"
    IDLE = "idle"
    ERROR = "error"
    PAUSED = "paused"


class DeviceType(Enum):
    """设备类型"""
    NAS = "nas"
    PC = "pc"
    MOBILE = "mobile"
    CLOUD = "cloud"


@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    name: str
    type: DeviceType
    host: str
    port: int
    protocol: str = "http"
    api_key: str = ""
    last_seen: Optional[datetime] = None
    is_online: bool = False
    storage_path: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_id': self.device_id,
            'name': self.name,
            'type': self.type.value,
            'host': self.host,
            'port': self.port,
            'protocol': self.protocol,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'is_online': self.is_online,
            'storage_path': self.storage_path
        }


@dataclass
class MediaItem:
    """媒体项"""
    item_id: str
    title: str
    file_path: str
    file_size: int
    file_hash: str
    media_type: str  # movie, tv, music, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_modified: Optional[datetime] = None
    play_count: int = 0
    last_played: Optional[datetime] = None
    rating: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'item_id': self.item_id,
            'title': self.title,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'media_type': self.media_type,
            'metadata': self.metadata,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'play_count': self.play_count,
            'last_played': self.last_played.isoformat() if self.last_played else None,
            'rating': self.rating
        }


@dataclass
class SyncOperation:
    """同步操作"""
    operation_id: str
    source_device: str
    target_device: str
    media_items: List[MediaItem]
    operation_type: str  # upload, download, sync
    status: SyncStatus = SyncStatus.IDLE
    progress: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation_id': self.operation_id,
            'source_device': self.source_device,
            'target_device': self.target_device,
            'media_items': [item.to_dict() for item in self.media_items],
            'operation_type': self.operation_type,
            'status': self.status.value,
            'progress': self.progress,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message
        }


class SyncEngine:
    """同步引擎 - MediaMaster风格"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.devices: Dict[str, DeviceInfo] = {}
        self.media_library: Dict[str, MediaItem] = {}
        self.sync_operations: Dict[str, SyncOperation] = {}
        self.sync_status: SyncStatus = SyncStatus.IDLE
        
        # 同步配置
        self.sync_interval = 3600  # 1小时同步一次
        self.max_concurrent_operations = 3
        self.chunk_size = 1024 * 1024  # 1MB分块
        
        # 统计信息
        self.stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'total_bytes_transferred': 0,
            'last_sync_time': None
        }
        
        self._load_data()
    
    def _load_data(self):
        """加载持久化数据"""
        try:
            # 加载设备信息
            devices_file = self.data_dir / "devices.json"
            if devices_file.exists():
                with open(devices_file, 'r', encoding='utf-8') as f:
                    devices_data = json.load(f)
                    for device_id, device_data in devices_data.items():
                        device = DeviceInfo(
                            device_id=device_data['device_id'],
                            name=device_data['name'],
                            type=DeviceType(device_data['type']),
                            host=device_data['host'],
                            port=device_data['port'],
                            protocol=device_data.get('protocol', 'http'),
                            last_seen=datetime.fromisoformat(device_data['last_seen']) if device_data['last_seen'] else None,
                            is_online=device_data.get('is_online', False),
                            storage_path=device_data.get('storage_path', '')
                        )
                        self.devices[device_id] = device
        
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
    
    def _save_data(self):
        """保存数据到文件"""
        try:
            # 保存设备信息
            devices_file = self.data_dir / "devices.json"
            devices_data = {device_id: device.to_dict() for device_id, device in self.devices.items()}
            with open(devices_file, 'w', encoding='utf-8') as f:
                json.dump(devices_data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
    
    async def add_device(self, device_info: DeviceInfo) -> bool:
        """添加设备"""
        # 测试设备连接
        if not await self._test_device_connection(device_info):
            logger.error(f"设备连接测试失败: {device_info.name}")
            return False
        
        self.devices[device_info.device_id] = device_info
        self._save_data()
        logger.info(f"添加设备: {device_info.name}")
        return True
    
    async def remove_device(self, device_id: str) -> bool:
        """移除设备"""
        if device_id in self.devices:
            del self.devices[device_id]
            self._save_data()
            logger.info(f"移除设备: {device_id}")
            return True
        return False
    
    async def _test_device_connection(self, device_info: DeviceInfo) -> bool:
        """测试设备连接"""
        try:
            url = f"{device_info.protocol}://{device_info.host}:{device_info.port}/api/status"
            
            async with aiohttp.ClientSession() as session:
                headers = {}
                if device_info.api_key:
                    headers['X-API-Key'] = device_info.api_key
                
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        device_info.is_online = True
                        device_info.last_seen = datetime.now()
                        return True
        
        except Exception as e:
            logger.error(f"设备连接测试失败: {e}")
            device_info.is_online = False
        
        return False
    
    async def scan_local_media(self, scan_path: str) -> List[MediaItem]:
        """扫描本地媒体文件"""
        media_items = []
        scan_dir = Path(scan_path)
        
        if not scan_dir.exists():
            logger.error(f"扫描路径不存在: {scan_path}")
            return media_items
        
        # 支持的媒体文件扩展名
        media_extensions = {
            'video': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'],
            'audio': ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        }
        
        try:
            for file_path in scan_dir.rglob('*'):
                if file_path.is_file():
                    # 检查文件扩展名
                    ext = file_path.suffix.lower()
                    media_type = None
                    
                    for category, extensions in media_extensions.items():
                        if ext in extensions:
                            media_type = category
                            break
                    
                    if media_type:
                        # 计算文件哈希
                        file_hash = await self._calculate_file_hash(file_path)
                        
                        # 创建媒体项
                        item = MediaItem(
                            item_id=file_hash,
                            title=file_path.stem,
                            file_path=str(file_path),
                            file_size=file_path.stat().st_size,
                            file_hash=file_hash,
                            media_type=media_type,
                            last_modified=datetime.fromtimestamp(file_path.stat().st_mtime)
                        )
                        
                        media_items.append(item)
                        self.media_library[file_hash] = item
            
            logger.info(f"扫描完成，发现 {len(media_items)} 个媒体文件")
        
        except Exception as e:
            logger.error(f"扫描媒体文件失败: {e}")
        
        return media_items
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        hash_md5 = hashlib.md5()
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                while True:
                    chunk = await f.read(8192)
                    if not chunk:
                        break
                    hash_md5.update(chunk)
        
        except Exception as e:
            logger.error(f"计算文件哈希失败: {e}")
            return ""
        
        return hash_md5.hexdigest()
    
    async def sync_devices(self, source_device: str, target_devices: List[str]) -> str:
        """同步设备"""
        if self.sync_status == SyncStatus.SYNCING:
            logger.warning("同步操作正在进行中")
            return ""
        
        if source_device not in self.devices:
            logger.error(f"源设备不存在: {source_device}")
            return ""
        
        operation_id = f"sync_{int(datetime.now().timestamp())}"
        
        # 创建同步操作
        operation = SyncOperation(
            operation_id=operation_id,
            source_device=source_device,
            target_device=",".join(target_devices),
            media_items=[],
            operation_type="sync",
            status=SyncStatus.SYNCING,
            start_time=datetime.now()
        )
        
        self.sync_operations[operation_id] = operation
        self.sync_status = SyncStatus.SYNCING
        
        # 异步执行同步
        asyncio.create_task(self._perform_sync(operation))
        
        return operation_id
    
    async def _perform_sync(self, operation: SyncOperation):
        """执行同步操作"""
        try:
            source_device = self.devices[operation.source_device]
            target_devices = [self.devices[device_id] for device_id in operation.target_device.split(',')]
            
            # 获取源设备的媒体库
            source_media = await self._get_device_media(source_device)
            
            # 为每个目标设备执行同步
            for target_device in target_devices:
                if not target_device.is_online:
                    logger.warning(f"目标设备离线: {target_device.name}")
                    continue
                
                # 获取目标设备的媒体库
                target_media = await self._get_device_media(target_device)
                
                # 计算需要同步的文件
                files_to_sync = await self._calculate_sync_files(source_media, target_media)
                
                if files_to_sync:
                    logger.info(f"需要同步 {len(files_to_sync)} 个文件到 {target_device.name}")
                    
                    # 执行文件同步
                    await self._sync_files(source_device, target_device, files_to_sync, operation)
                else:
                    logger.info(f"没有需要同步的文件到 {target_device.name}")
            
            # 同步完成
            operation.status = SyncStatus.IDLE
            operation.end_time = datetime.now()
            operation.progress = 100.0
            
            self.sync_status = SyncStatus.IDLE
            self.stats['total_syncs'] += 1
            self.stats['successful_syncs'] += 1
            self.stats['last_sync_time'] = datetime.now()
            
            logger.info(f"同步操作完成: {operation.operation_id}")
        
        except Exception as e:
            logger.error(f"同步操作失败: {e}")
            operation.status = SyncStatus.ERROR
            operation.error_message = str(e)
            operation.end_time = datetime.now()
            
            self.sync_status = SyncStatus.ERROR
            self.stats['total_syncs'] += 1
            self.stats['failed_syncs'] += 1
    
    async def _get_device_media(self, device: DeviceInfo) -> List[MediaItem]:
        """获取设备的媒体库"""
        # 如果是本地设备，直接扫描
        if device.type == DeviceType.PC:
            return await self.scan_local_media(device.storage_path)
        
        # 远程设备通过API获取
        try:
            url = f"{device.protocol}://{device.host}:{device.port}/api/media"
            
            async with aiohttp.ClientSession() as session:
                headers = {}
                if device.api_key:
                    headers['X-API-Key'] = device.api_key
                
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [MediaItem(**item) for item in data.get('media_items', [])]
        
        except Exception as e:
            logger.error(f"获取设备媒体库失败: {e}")
        
        return []
    
    async def _calculate_sync_files(self, source_media: List[MediaItem], target_media: List[MediaItem]) -> List[MediaItem]:
        """计算需要同步的文件"""
        # 使用文件哈希进行比较
        target_hashes = {item.file_hash for item in target_media}
        
        files_to_sync = []
        
        for source_item in source_media:
            if source_item.file_hash not in target_hashes:
                files_to_sync.append(source_item)
        
        return files_to_sync
    
    async def _sync_files(self, source_device: DeviceInfo, target_device: DeviceInfo, 
                         files: List[MediaItem], operation: SyncOperation):
        """同步文件"""
        total_files = len(files)
        
        for i, media_item in enumerate(files):
            try:
                # 更新进度
                operation.progress = (i / total_files) * 100
                
                # 传输文件
                await self._transfer_file(source_device, target_device, media_item)
                
                logger.info(f"同步文件完成: {media_item.title} ({i+1}/{total_files})")
                
            except Exception as e:
                logger.error(f"同步文件失败: {media_item.title}, 错误: {e}")
    
    async def _transfer_file(self, source_device: DeviceInfo, target_device: DeviceInfo, 
                            media_item: MediaItem):
        """传输单个文件"""
        if source_device.type == DeviceType.PC and target_device.type == DeviceType.PC:
            # 本地到本地，直接复制
            await self._copy_file_local(media_item.file_path, target_device.storage_path)
        else:
            # 远程传输
            await self._transfer_file_remote(source_device, target_device, media_item)
    
    async def _copy_file_local(self, source_path: str, target_dir: str):
        """本地文件复制"""
        source_file = Path(source_path)
        target_file = Path(target_dir) / source_file.name
        
        # 确保目标目录存在
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用aiofiles进行异步复制
        async with aiofiles.open(source_file, 'rb') as src:
            async with aiofiles.open(target_file, 'wb') as dst:
                while True:
                    chunk = await src.read(self.chunk_size)
                    if not chunk:
                        break
                    await dst.write(chunk)
    
    async def _transfer_file_remote(self, source_device: DeviceInfo, target_device: DeviceInfo,
                                  media_item: MediaItem):
        """远程文件传输"""
        # 简化实现，实际需要处理分块上传、断点续传等
        try:
            # 从源设备下载
            download_url = f"{source_device.protocol}://{source_device.host}:{source_device.port}/api/download/{media_item.item_id}"
            
            async with aiohttp.ClientSession() as session:
                headers = {}
                if source_device.api_key:
                    headers['X-API-Key'] = source_device.api_key
                
                # 下载文件
                async with session.get(download_url, headers=headers) as response:
                    if response.status == 200:
                        file_data = await response.read()
                        
                        # 上传到目标设备
                        upload_url = f"{target_device.protocol}://{target_device.host}:{target_device.port}/api/upload"
                        
                        headers = {}
                        if target_device.api_key:
                            headers['X-API-Key'] = target_device.api_key
                        
                        form_data = aiohttp.FormData()
                        form_data.add_field('file', file_data, filename=Path(media_item.file_path).name)
                        form_data.add_field('metadata', json.dumps(media_item.to_dict()))
                        
                        async with session.post(upload_url, data=form_data, headers=headers) as upload_response:
                            if upload_response.status != 200:
                                raise Exception(f"上传失败: {upload_response.status}")
        
        except Exception as e:
            raise Exception(f"远程文件传输失败: {e}")
    
    async def get_sync_progress(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """获取同步进度"""
        if operation_id in self.sync_operations:
            operation = self.sync_operations[operation_id]
            return operation.to_dict()
        return None
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            'status': self.sync_status.value,
            'device_count': len(self.devices),
            'media_count': len(self.media_library),
            'active_operations': len([op for op in self.sync_operations.values() if op.status == SyncStatus.SYNCING]),
            'stats': self.stats
        }
    
    async def start_auto_sync(self):
        """开始自动同步"""
        while True:
            try:
                if self.sync_status == SyncStatus.IDLE and len(self.devices) > 1:
                    # 选择主设备作为源
                    main_device = next((device for device in self.devices.values() if device.type == DeviceType.NAS), None)
                    
                    if main_device:
                        target_devices = [device_id for device_id, device in self.devices.items() 
                                       if device_id != main_device.device_id and device.is_online]
                        
                        if target_devices:
                            await self.sync_devices(main_device.device_id, target_devices)
                
                # 等待下一次同步
                await asyncio.sleep(self.sync_interval)
            
            except Exception as e:
                logger.error(f"自动同步错误: {e}")
                await asyncio.sleep(60)  # 错误后等待1分钟


# 使用示例
async def demo():
    """演示使用方法"""
    engine = SyncEngine()
    
    # 添加设备
    nas_device = DeviceInfo(
        device_id="nas_001",
        name="家庭NAS",
        type=DeviceType.NAS,
        host="192.168.1.100",
        port=8080,
        storage_path="/media"
    )
    
    pc_device = DeviceInfo(
        device_id="pc_001", 
        name="办公电脑",
        type=DeviceType.PC,
        host="localhost",
        port=8080,
        storage_path="D:\\Media"
    )
    
    await engine.add_device(nas_device)
    await engine.add_device(pc_device)
    
    # 扫描本地媒体
    await engine.scan_local_media("D:\\Media")
    
    # 开始同步
    operation_id = await engine.sync_devices("nas_001", ["pc_001"])
    
    # 监控进度
    while True:
        progress = await engine.get_sync_progress(operation_id)
        if progress and progress['status'] == 'idle':
            break
        await asyncio.sleep(5)
    
    # 获取状态
    status = engine.get_sync_status()
    print(f"同步完成: {status}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())