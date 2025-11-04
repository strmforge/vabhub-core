"""
下载管理器 - 基于DownloadClient抽象的统一管理接口
"""

from typing import Dict, Any, List, Optional, Union
from .download_client import (
    DownloadClient,
    DownloadClientFactory,
    DownloadClientConfig,
    DownloadClientType,
    TorrentInfo,
    TorrentStatus,
)
import logging

logger = logging.getLogger(__name__)


class DownloadManager:
    """下载管理器"""

    def __init__(self):
        self._clients: Dict[str, DownloadClient] = {}
        self._default_client: Optional[str] = None

    async def add_client(
        self,
        client_id: str,
        client_type: DownloadClientType,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        timeout: int = 30,
        set_as_default: bool = False,
        **kwargs,
    ) -> bool:
        """添加下载器客户端"""
        try:
            config = DownloadClientConfig(
                client_type=client_type,
                host=host,
                port=port,
                username=username,
                password=password,
                timeout=timeout,
                **kwargs,
            )

            client = DownloadClientFactory.create_client(config)

            # 测试连接
            test_result = await client.test_connection()
            if not test_result.get("ok", False):
                logger.error(
                    f"下载器连接测试失败: {test_result.get('error', 'Unknown error')}"
                )
                return False

            # 正式连接
            connected = await client.connect()
            if not connected:
                logger.error(f"下载器连接失败: {client_id}")
                return False

            self._clients[client_id] = client

            if set_as_default or self._default_client is None:
                self._default_client = client_id

            logger.info(f"成功添加下载器: {client_id} ({client_type.value})")
            return True

        except Exception as e:
            logger.error(f"添加下载器失败: {e}")
            return False

    async def remove_client(self, client_id: str) -> bool:
        """移除下载器客户端"""
        if client_id not in self._clients:
            return False

        try:
            client = self._clients[client_id]
            await client.disconnect()

            del self._clients[client_id]

            if self._default_client == client_id:
                self._default_client = (
                    next(iter(self._clients.keys()), None) if self._clients else None
                )

            logger.info(f"成功移除下载器: {client_id}")
            return True

        except Exception as e:
            logger.error(f"移除下载器失败: {e}")
            return False

    def set_default_client(self, client_id: str) -> bool:
        """设置默认下载器"""
        if client_id not in self._clients:
            return False

        self._default_client = client_id
        logger.info(f"设置默认下载器: {client_id}")
        return True

    def get_default_client(self) -> Optional[DownloadClient]:
        """获取默认下载器"""
        if self._default_client and self._default_client in self._clients:
            return self._clients[self._default_client]
        return None

    def get_client(self, client_id: str) -> Optional[DownloadClient]:
        """获取指定下载器"""
        return self._clients.get(client_id)

    async def add_torrent(
        self,
        torrent: Union[str, bytes],
        client_id: Optional[str] = None,
        save_path: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs,
    ) -> bool:
        """添加种子"""
        client = self._get_target_client(client_id)
        if not client:
            logger.error("没有可用的下载器")
            return False

        # 确保传递给客户端的参数类型正确
        # 使用空字符串作为默认值，避免None值问题
        return await client.add_torrent(
            torrent=torrent,
            save_path=save_path or "",
            category=category or "",
            tags=tags or [],
            **kwargs,
        )

    async def pause_torrent(
        self, torrent_hash: str, client_id: Optional[str] = None
    ) -> bool:
        """暂停种子"""
        client = self._get_target_client(client_id)
        if not client:
            return False

        return await client.pause_torrent(torrent_hash)

    async def resume_torrent(
        self, torrent_hash: str, client_id: Optional[str] = None
    ) -> bool:
        """恢复种子"""
        client = self._get_target_client(client_id)
        if not client:
            return False

        return await client.resume_torrent(torrent_hash)

    async def remove_torrent(
        self,
        torrent_hash: str,
        delete_files: bool = False,
        client_id: Optional[str] = None,
    ) -> bool:
        """删除种子"""
        client = self._get_target_client(client_id)
        if not client:
            return False

        return await client.remove_torrent(torrent_hash, delete_files)

    async def get_torrents(
        self,
        client_id: Optional[str] = None,
        status_filter: Optional[TorrentStatus] = None,
        category: Optional[str] = None,
    ) -> List[TorrentInfo]:
        """获取种子列表"""
        if client_id:
            # 获取指定客户端的种子
            client = self.get_client(client_id)
            if client:
                return await client.get_torrents(status_filter, category)
            return []
        else:
            # 获取所有客户端的种子
            all_torrents = []
            for client in self._clients.values():
                torrents = await client.get_torrents(status_filter, category)
                all_torrents.extend(torrents)
            return all_torrents

    async def get_torrent(
        self, torrent_hash: str, client_id: Optional[str] = None
    ) -> Optional[TorrentInfo]:
        """获取单个种子信息"""
        if client_id:
            # 在指定客户端中查找
            client = self.get_client(client_id)
            if client:
                return await client.get_torrent(torrent_hash)
        else:
            # 在所有客户端中查找
            for client in self._clients.values():
                torrent = await client.get_torrent(torrent_hash)
                if torrent:
                    return torrent

        return None

    async def set_category(
        self, torrent_hash: str, category: str, client_id: Optional[str] = None
    ) -> bool:
        """设置种子分类"""
        client = self._get_target_client(client_id)
        if not client:
            return False

        return await client.set_category(torrent_hash, category)

    async def set_ratio_limit(
        self, torrent_hash: str, ratio: float, client_id: Optional[str] = None
    ) -> bool:
        """设置分享率限制"""
        client = self._get_target_client(client_id)
        if not client:
            return False

        return await client.set_ratio_limit(torrent_hash, ratio)

    async def set_speed_limit(
        self,
        torrent_hash: str,
        download_limit: int = 0,
        upload_limit: int = 0,
        client_id: Optional[str] = None,
    ) -> bool:
        """设置速度限制"""
        client = self._get_target_client(client_id)
        if not client:
            return False

        return await client.set_speed_limit(torrent_hash, download_limit, upload_limit)

    async def get_transfer_info(
        self, client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取传输统计信息"""
        if client_id:
            client = self.get_client(client_id)
            if client:
                return await client.get_transfer_info()
            return {}
        else:
            # 汇总所有客户端的信息
            total_info = {
                "total_download_speed": 0,
                "total_upload_speed": 0,
                "total_downloaded": 0,
                "total_uploaded": 0,
                "clients": {},
            }

            for cid, client in self._clients.items():
                info = await client.get_transfer_info()
                if info:
                    # 安全地更新统计信息
                    if isinstance(info, dict):
                        total_info["total_download_speed"] += info.get(
                            "dl_info_speed", 0
                        )
                        total_info["total_upload_speed"] += info.get("up_info_speed", 0)
                        total_info["total_downloaded"] += info.get("dl_info_data", 0)
                        total_info["total_uploaded"] += info.get("up_info_data", 0)
                        total_info["clients"][cid] = info

            return total_info

    async def test_connection(self, client_id: str) -> Dict[str, Any]:
        """测试连接"""
        client = self.get_client(client_id)
        if not client:
            return {"ok": False, "error": "客户端不存在"}

        return await client.test_connection()

    def list_clients(self) -> List[Dict[str, Any]]:
        """列出所有客户端"""
        clients = []
        for client_id, client in self._clients.items():
            clients.append(
                {
                    "id": client_id,
                    "type": client.config.client_type.value,
                    "host": client.config.host,
                    "port": client.config.port,
                    "connected": client.is_connected,
                    "is_default": client_id == self._default_client,
                }
            )
        return clients

    async def close_all(self):
        """关闭所有客户端连接"""
        for client in self._clients.values():
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"关闭客户端连接失败: {e}")

        self._clients.clear()
        self._default_client = None

    def _get_target_client(
        self, client_id: Optional[str] = None
    ) -> Optional[DownloadClient]:
        """获取目标客户端"""
        if client_id:
            return self.get_client(client_id)
        else:
            return self.get_default_client()


# 全局下载管理器实例
download_manager = DownloadManager()
