"""
DownloadClient抽象接口和具体实现
基于MoviePilot架构设计，提供统一的下载器接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, cast
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class DownloadClientType(Enum):
    """下载器类型枚举"""

    QBITTORRENT = "qbittorrent"
    TRANSMISSION = "transmission"
    ARIA2 = "aria2"


class TorrentStatus(Enum):
    """种子状态枚举"""

    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    PAUSED = "paused"
    CHECKING = "checking"
    ERROR = "error"
    COMPLETED = "completed"
    QUEUED = "queued"


class DownloadClientConfig:
    """下载器配置类"""

    def __init__(
        self,
        client_type: DownloadClientType,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        timeout: int = 30,
        **kwargs,
    ):
        self.client_type = client_type
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.extra_config = kwargs

    @property
    def base_url(self) -> str:
        """获取基础URL"""
        return f"http://{self.host}:{self.port}"


class TorrentInfo:
    """种子信息类"""

    def __init__(
        self,
        hash: str,
        name: str,
        size: int,
        progress: float,
        status: TorrentStatus,
        download_speed: int = 0,
        upload_speed: int = 0,
        ratio: float = 0.0,
        eta: int = 0,
        save_path: str = "",
        category: str = "",
        added_on: int = 0,
        **kwargs,
    ):
        self.hash = hash
        self.name = name
        self.size = size
        self.progress = progress
        self.status = status
        self.download_speed = download_speed
        self.upload_speed = upload_speed
        self.ratio = ratio
        self.eta = eta
        self.save_path = save_path
        self.category = category
        self.added_on = added_on
        self.extra_info = kwargs


class DownloadClient(ABC):
    """下载器抽象基类"""

    def __init__(self, config: DownloadClientConfig):
        self.config = config
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """连接下载器"""
        pass

    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    async def add_torrent(
        self,
        torrent: Union[str, bytes],
        save_path: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs,
    ) -> bool:
        """添加种子"""
        pass

    @abstractmethod
    async def pause_torrent(self, torrent_hash: str) -> bool:
        """暂停种子"""
        pass

    @abstractmethod
    async def resume_torrent(self, torrent_hash: str) -> bool:
        """恢复种子"""
        pass

    @abstractmethod
    async def remove_torrent(
        self, torrent_hash: str, delete_files: bool = False
    ) -> bool:
        """删除种子"""
        pass

    @abstractmethod
    async def get_torrents(
        self,
        status_filter: Optional[TorrentStatus] = None,
        category: Optional[str] = None,
    ) -> List[TorrentInfo]:
        """获取种子列表"""
        pass

    @abstractmethod
    async def get_torrent(self, torrent_hash: str) -> Optional[TorrentInfo]:
        """获取单个种子信息"""
        pass

    @abstractmethod
    async def set_category(self, torrent_hash: str, category: str) -> bool:
        """设置种子分类"""
        pass

    @abstractmethod
    async def set_ratio_limit(self, torrent_hash: str, ratio: float) -> bool:
        """设置分享率限制"""
        pass

    @abstractmethod
    async def set_speed_limit(
        self, torrent_hash: str, download_limit: int = 0, upload_limit: int = 0
    ) -> bool:
        """设置速度限制"""
        pass

    @abstractmethod
    async def get_transfer_info(self) -> Dict[str, Any]:
        """获取传输统计信息"""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        pass

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected


class QbittorrentClient(DownloadClient):
    """qBittorrent客户端实现"""

    def __init__(self, config: DownloadClientConfig):
        super().__init__(config)
        self._client = None  # type: Optional[Any]

    async def connect(self) -> bool:
        """连接qBittorrent"""
        try:
            # 使用已经导入的Client类
            self._client = cast(
                Any,
                Client(
                    host=self.config.host,
                    port=self.config.port,
                    username=self.config.username,
                    password=self.config.password,
                ),
            )

            # 测试连接
            if self._client:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._client.auth_log_in()
                )

            self._connected = True
            logger.info(f"成功连接到qBittorrent: {self.config.base_url}")
            return True

        except Exception as e:
            logger.error(f"连接qBittorrent失败: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """断开连接"""
        if self._client:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._client.auth_log_out()
                )
            except Exception as e:
                logger.warning(f"qBittorrent登出失败: {e}")
            finally:
                self._client = None
                self._connected = False

    async def add_torrent(
        self,
        torrent: Union[str, bytes],
        save_path: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs,
    ) -> bool:
        """添加种子到qBittorrent"""
        if not self._connected:
            logger.error("qBittorrent未连接")
            return False

        try:
            add_params = {}
            if save_path:
                add_params["savepath"] = save_path
            if category:
                add_params["category"] = category
            if tags:
                add_params["tags"] = ",".join(tags)

            # 合并额外参数
            add_params.update(kwargs)

            if self._client:
                if isinstance(torrent, str):
                    # URL或磁力链接
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._client.torrents_add(urls=torrent, **add_params),
                    )
                else:
                    # 种子文件内容
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._client.torrents_add(
                            torrent_files=torrent, **add_params
                        ),
                    )

            logger.info(
                f"成功添加种子到qBittorrent: {torrent if isinstance(torrent, str) else 'torrent file'}"
            )
            return True

        except Exception as e:
            logger.error(f"添加种子到qBittorrent失败: {e}")
            return False

    async def pause_torrent(self, torrent_hash: str) -> bool:
        """暂停种子"""
        if not self._connected or not self._client:
            return False

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._client.torrents_pause(torrent_hashes=torrent_hash)
            )
            return True
        except Exception as e:
            logger.error(f"暂停种子失败: {e}")
            return False

    async def resume_torrent(self, torrent_hash: str) -> bool:
        """恢复种子"""
        if not self._connected or not self._client:
            return False

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._client.torrents_resume(torrent_hashes=torrent_hash)
            )
            return True
        except Exception as e:
            logger.error(f"恢复种子失败: {e}")
            return False

    async def remove_torrent(
        self, torrent_hash: str, delete_files: bool = False
    ) -> bool:
        """删除种子"""
        if not self._connected or not self._client:
            return False

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.torrents_delete(
                    delete_files=delete_files, torrent_hashes=torrent_hash
                ),
            )
            return True
        except Exception as e:
            logger.error(f"删除种子失败: {e}")
            return False

    async def get_torrents(
        self,
        status_filter: Optional[TorrentStatus] = None,
        category: Optional[str] = None,
    ) -> List[TorrentInfo]:
        """获取种子列表"""
        if not self._connected or not self._client:
            return []

        try:
            # 构建查询参数
            params = {}
            if category:
                params["category"] = category

            torrents = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._client.torrents_info(**params)
            )

            result = []
            for torrent in torrents:
                # 转换状态
                status = self._map_qbittorrent_status(torrent.state)

                # 过滤状态
                if status_filter and status != status_filter:
                    continue

                torrent_info = TorrentInfo(
                    hash=torrent.hash,
                    name=torrent.name,
                    size=torrent.size,
                    progress=torrent.progress,
                    status=status,
                    download_speed=torrent.dlspeed,
                    upload_speed=torrent.upspeed,
                    ratio=torrent.ratio,
                    eta=torrent.eta,
                    save_path=torrent.save_path,
                    category=torrent.category,
                    added_on=torrent.added_on,
                )
                result.append(torrent_info)

            return result

        except Exception as e:
            logger.error(f"获取种子列表失败: {e}")
            return []

    async def get_torrent(self, torrent_hash: str) -> Optional[TorrentInfo]:
        """获取单个种子信息"""
        if not self._connected or not self._client:
            return None

        try:
            torrents = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._client.torrents_info(torrent_hashes=torrent_hash)
            )

            if not torrents:
                return None

            torrent = torrents[0]
            status = self._map_qbittorrent_status(torrent.state)

            return TorrentInfo(
                hash=torrent.hash,
                name=torrent.name,
                size=torrent.size,
                progress=torrent.progress,
                status=status,
                download_speed=torrent.dlspeed,
                upload_speed=torrent.upspeed,
                ratio=torrent.ratio,
                eta=torrent.eta,
                save_path=torrent.save_path,
                category=torrent.category,
                added_on=torrent.added_on,
            )

        except Exception as e:
            logger.error(f"获取种子信息失败: {e}")
            return None

    async def set_category(self, torrent_hash: str, category: str) -> bool:
        """设置种子分类"""
        if not self._connected or not self._client:
            return False

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.torrents_set_category(
                    categories=category, torrent_hashes=torrent_hash
                ),
            )
            return True
        except Exception as e:
            logger.error(f"设置分类失败: {e}")
            return False

    async def set_ratio_limit(self, torrent_hash: str, ratio: float) -> bool:
        """设置分享率限制"""
        if not self._connected or not self._client:
            return False

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.torrents_set_share_limits(
                    ratio_limit=ratio, torrent_hashes=torrent_hash
                ),
            )
            return True
        except Exception as e:
            logger.error(f"设置分享率限制失败: {e}")
            return False

    async def set_speed_limit(
        self, torrent_hash: str, download_limit: int = 0, upload_limit: int = 0
    ) -> bool:
        """设置速度限制"""
        if not self._connected or not self._client:
            return False

        try:
            if download_limit > 0:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.torrents_set_download_limit(
                        limit=download_limit, torrent_hashes=torrent_hash
                    ),
                )

            if upload_limit > 0:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.torrents_set_upload_limit(
                        limit=upload_limit, torrent_hashes=torrent_hash
                    ),
                )

            return True
        except Exception as e:
            logger.error(f"设置速度限制失败: {e}")
            return False

    async def get_transfer_info(self) -> Dict[str, Any]:
        """获取传输统计信息"""
        if not self._connected or not self._client:
            return {}

        try:
            transfer_info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._client.transfer_info()
            )

            return {
                "dl_info_speed": transfer_info.dl_info_speed,
                "up_info_speed": transfer_info.up_info_speed,
                "dl_info_data": transfer_info.dl_info_data,
                "up_info_data": transfer_info.up_info_data,
                "connection_status": transfer_info.connection_status,
            }
        except Exception as e:
            logger.error(f"获取传输信息失败: {e}")
            return {}

    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        try:
            connected = await self.connect()
            if connected and self._client:
                version = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._client.app_version()
                )
                return {"ok": True, "version": version, "type": "qbittorrent"}
            else:
                return {"ok": False, "error": "连接失败"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _map_qbittorrent_status(self, qb_status: str) -> TorrentStatus:
        """映射qBittorrent状态到统一状态"""
        status_map = {
            "downloading": TorrentStatus.DOWNLOADING,
            "seeding": TorrentStatus.SEEDING,
            "pausedDL": TorrentStatus.PAUSED,
            "pausedUP": TorrentStatus.PAUSED,
            "checkingDL": TorrentStatus.CHECKING,
            "checkingUP": TorrentStatus.CHECKING,
            "checkingResumeData": TorrentStatus.CHECKING,
            "moving": TorrentStatus.QUEUED,
            "queuedDL": TorrentStatus.QUEUED,
            "queuedUP": TorrentStatus.QUEUED,
            "stalledDL": TorrentStatus.DOWNLOADING,
            "stalledUP": TorrentStatus.SEEDING,
            "metaDL": TorrentStatus.DOWNLOADING,
            "forcedDL": TorrentStatus.DOWNLOADING,
            "forcedUP": TorrentStatus.SEEDING,
            "allocating": TorrentStatus.QUEUED,
            "error": TorrentStatus.ERROR,
        }
        return status_map.get(qb_status, TorrentStatus.ERROR)


class DownloadClientFactory:
    """下载器工厂类"""

    @staticmethod
    def create_client(config: DownloadClientConfig) -> DownloadClient:
        """创建下载器实例"""
        if config.client_type == DownloadClientType.QBITTORRENT:
            return QbittorrentClient(config)
        elif config.client_type == DownloadClientType.TRANSMISSION:
            # 后续实现Transmission客户端
            raise NotImplementedError("Transmission客户端暂未实现")
        elif config.client_type == DownloadClientType.ARIA2:
            # 后续实现Aria2客户端
            raise NotImplementedError("Aria2客户端暂未实现")
        else:
            raise ValueError(f"不支持的下载器类型: {config.client_type}")

# 为测试兼容性，在模块级别导出Client类
# 这样测试文件中的 patch("core.download_client.Client") 就可以正常工作
try:
    from qbittorrentapi import Client
except ImportError:
    # 如果qbittorrentapi未安装，创建一个虚拟类以满足测试需求
    class Client:
        pass
