"""
下载器状态监控和任务管理模块
基于现有Downloader插件进行增强，支持qBittorrent/Transmission状态监控
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """下载状态枚举"""
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    QUEUED = "queued"
    CHECKING = "checking"
    SEEDING = "seeding"


class DownloaderType(Enum):
    """下载器类型枚举"""
    QBITTORRENT = "qbittorrent"
    TRANSMISSION = "transmission"
    DELUGE = "deluge"


@dataclass
class DownloadTask:
    """下载任务信息"""
    task_id: str
    name: str
    status: DownloadStatus
    progress: float  # 0-100
    download_speed: int  # bytes/s
    upload_speed: int  # bytes/s
    size: int  # bytes
    downloaded: int  # bytes
    upload_ratio: float
    eta: int  # seconds
    save_path: str
    added_time: datetime
    completion_time: Optional[datetime]
    tracker: str
    seeds: int
    peers: int
    category: str
    tags: List[str]


class DownloadManager:
    """下载管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.downloader_type = DownloaderType(config.get('downloader_type', 'qbittorrent'))
        self.downloader = None
        self.tasks: Dict[str, DownloadTask] = {}
        self.monitoring_task = None
        self.is_monitoring = False
        
    async def initialize(self) -> bool:
        """初始化下载管理器"""
        logger.info("初始化下载管理器")
        
        try:
            # 初始化下载器
            await self._initialize_downloader()
            
            # 启动监控任务
            await self.start_monitoring()
            
            logger.info("下载管理器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"下载管理器初始化失败: {e}")
            return False
    
    async def _initialize_downloader(self):
        """初始化下载器"""
        if self.downloader_type == DownloaderType.QBITTORRENT:
            from plugins.downloader_plugin import QBittorrentDownloader
            self.downloader = QBittorrentDownloader(self.config)
        elif self.downloader_type == DownloaderType.TRANSMISSION:
            from plugins.downloader_plugin import TransmissionDownloader
            self.downloader = TransmissionDownloader(self.config)
        else:
            raise ValueError(f"不支持的下载器类型: {self.downloader_type}")
        
        await self.downloader.initialize()
    
    async def start_monitoring(self):
        """开始监控下载状态"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("下载状态监控已启动")
    
    async def stop_monitoring(self):
        """停止监控下载状态"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("下载状态监控已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                await self._update_tasks_status()
                await asyncio.sleep(10)  # 每10秒更新一次状态
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(30)  # 出错后等待30秒重试
    
    async def _update_tasks_status(self):
        """更新任务状态"""
        try:
            # 获取下载器中的任务列表
            downloader_tasks = await self.downloader.get_tasks()
            
            # 更新本地任务状态
            for task_data in downloader_tasks:
                task_id = task_data.get('id')
                if task_id in self.tasks:
                    # 更新现有任务
                    self.tasks[task_id] = self._parse_task_data(task_data)
                else:
                    # 添加新任务
                    self.tasks[task_id] = self._parse_task_data(task_data)
            
            # 移除已完成的本地任务（如果下载器中不存在）
            downloader_task_ids = {task.get('id') for task in downloader_tasks}
            completed_tasks = [task_id for task_id, task in self.tasks.items() 
                             if task.status == DownloadStatus.COMPLETED and 
                             task_id not in downloader_task_ids]
            
            for task_id in completed_tasks:
                del self.tasks[task_id]
                
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
    
    def _parse_task_data(self, task_data: Dict[str, Any]) -> DownloadTask:
        """解析下载器返回的任务数据"""
        return DownloadTask(
            task_id=task_data.get('id', ''),
            name=task_data.get('name', ''),
            status=DownloadStatus(task_data.get('state', '')),
            progress=task_data.get('progress', 0),
            download_speed=task_data.get('download_speed', 0),
            upload_speed=task_data.get('upload_speed', 0),
            size=task_data.get('size', 0),
            downloaded=task_data.get('downloaded', 0),
            upload_ratio=task_data.get('upload_ratio', 0),
            eta=task_data.get('eta', 0),
            save_path=task_data.get('save_path', ''),
            added_time=datetime.fromisoformat(task_data.get('added_time', datetime.now().isoformat())),
            completion_time=datetime.fromisoformat(task_data.get('completion_time')) if task_data.get('completion_time') else None,
            tracker=task_data.get('tracker', ''),
            seeds=task_data.get('seeds', 0),
            peers=task_data.get('peers', 0),
            category=task_data.get('category', ''),
            tags=task_data.get('tags', [])
        )
    
    async def add_torrent(self, torrent_url: str, save_path: str, 
                         category: str = '', tags: List[str] = None) -> str:
        """添加种子下载任务"""
        logger.info(f"添加下载任务: {torrent_url}")
        
        try:
            task_id = await self.downloader.add_torrent(torrent_url, save_path, category)
            
            # 如果添加了标签
            if tags:
                await self.downloader.set_tags(task_id, tags)
            
            logger.info(f"下载任务添加成功: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"添加下载任务失败: {e}")
            raise
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停下载任务"""
        logger.info(f"暂停下载任务: {task_id}")
        
        try:
            success = await self.downloader.pause_task(task_id)
            if success:
                logger.info(f"下载任务暂停成功: {task_id}")
            return success
            
        except Exception as e:
            logger.error(f"暂停下载任务失败: {e}")
            return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复下载任务"""
        logger.info(f"恢复下载任务: {task_id}")
        
        try:
            success = await self.downloader.resume_task(task_id)
            if success:
                logger.info(f"下载任务恢复成功: {task_id}")
            return success
            
        except Exception as e:
            logger.error(f"恢复下载任务失败: {e}")
            return False
    
    async def delete_task(self, task_id: str, delete_files: bool = False) -> bool:
        """删除下载任务"""
        logger.info(f"删除下载任务: {task_id}")
        
        try:
            success = await self.downloader.delete_task(task_id, delete_files)
            if success:
                # 从本地任务列表中移除
                if task_id in self.tasks:
                    del self.tasks[task_id]
                logger.info(f"下载任务删除成功: {task_id}")
            return success
            
        except Exception as e:
            logger.error(f"删除下载任务失败: {e}")
            return False
    
    async def get_task_status(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    async def get_all_tasks(self) -> List[DownloadTask]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    async def get_tasks_by_status(self, status: DownloadStatus) -> List[DownloadTask]:
        """根据状态获取任务"""
        return [task for task in self.tasks.values() if task.status == status]
    
    async def get_download_stats(self) -> Dict[str, Any]:
        """获取下载统计信息"""
        total_tasks = len(self.tasks)
        
        stats = {
            'total_tasks': total_tasks,
            'downloading': len(await self.get_tasks_by_status(DownloadStatus.DOWNLOADING)),
            'paused': len(await self.get_tasks_by_status(DownloadStatus.PAUSED)),
            'completed': len(await self.get_tasks_by_status(DownloadStatus.COMPLETED)),
            'error': len(await self.get_tasks_by_status(DownloadStatus.ERROR)),
            'queued': len(await self.get_tasks_by_status(DownloadStatus.QUEUED)),
            'seeding': len(await self.get_tasks_by_status(DownloadStatus.SEEDING)),
            'total_download_speed': sum(task.download_speed for task in self.tasks.values()),
            'total_upload_speed': sum(task.upload_speed for task in self.tasks.values()),
            'total_downloaded': sum(task.downloaded for task in self.tasks.values()),
            'total_size': sum(task.size for task in self.tasks.values()),
        }
        
        return stats
    
    async def cleanup_completed_tasks(self, older_than_days: int = 7) -> int:
        """清理已完成的任务"""
        logger.info(f"清理已完成超过 {older_than_days} 天的任务")
        
        cutoff_time = datetime.now() - timedelta(days=older_than_days)
        cleaned_count = 0
        
        for task_id, task in list(self.tasks.items()):
            if (task.status == DownloadStatus.COMPLETED and 
                task.completion_time and 
                task.completion_time < cutoff_time):
                
                # 删除任务（保留文件）
                success = await self.delete_task(task_id, delete_files=False)
                if success:
                    cleaned_count += 1
        
        logger.info(f"清理完成，共清理 {cleaned_count} 个任务")
        return cleaned_count
    
    async def close(self):
        """关闭下载管理器"""
        logger.info("关闭下载管理器")
        
        await self.stop_monitoring()
        
        if self.downloader:
            await self.downloader.close()
        
        logger.info("下载管理器已关闭")


# 使用示例
async def main():
    """使用示例"""
    config = {
        'downloader_type': 'qbittorrent',
        'qbittorrent': {
            'host': 'localhost',
            'port': 8080,
            'username': 'admin',
            'password': 'adminadmin'
        }
    }
    
    manager = DownloadManager(config)
    
    # 初始化管理器
    success = await manager.initialize()
    if not success:
        print("初始化失败")
        return
    
    try:
        # 添加下载任务
        task_id = await manager.add_torrent(
            torrent_url="magnet:?xt=urn:btih:example",
            save_path="/downloads/movies",
            category="movies",
            tags=["movie", "high_quality"]
        )
        
        # 等待一段时间
        await asyncio.sleep(30)
        
        # 获取任务状态
        task = await manager.get_task_status(task_id)
        if task:
            print(f"任务状态: {task.status.value}")
            print(f"进度: {task.progress}%")
            print(f"下载速度: {task.download_speed / 1024 / 1024:.2f} MB/s")
        
        # 获取统计信息
        stats = await manager.get_download_stats()
        print(f"总任务数: {stats['total_tasks']}")
        print(f"总下载速度: {stats['total_download_speed'] / 1024 / 1024:.2f} MB/s")
        
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())