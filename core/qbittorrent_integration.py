"""
qBittorrent深度集成模块
集成MoviePilot规则的智能下载管理功能
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TorrentState(Enum):
    """种子状态枚举"""

    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class TorrentInfo:
    """种子信息"""

    hash: str
    name: str
    size: int
    progress: float
    state: TorrentState
    download_speed: int
    upload_speed: int
    ratio: float
    eta: int
    added_on: datetime
    tags: List[str]
    category: str
    save_path: str


class QBittorrentIntegration:
    """qBittorrent深度集成管理器"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        username: str = "admin",
        password: str = "adminadmin",
    ):
        self.base_url = f"http://{host}:{port}"
        self.username = username
        self.password = password
        self.session = None
        self.cookies = None

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.logout()

    async def login(self):
        """登录qBittorrent"""
        try:
            self.session = aiohttp.ClientSession()
            login_data = {"username": self.username, "password": self.password}

            async with self.session.post(
                f"{self.base_url}/api/v2/auth/login", data=login_data
            ) as response:
                if response.status == 200:
                    self.cookies = response.cookies
                    logger.info("qBittorrent登录成功")
                    return True
                else:
                    logger.error(f"qBittorrent登录失败: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"qBittorrent登录异常: {str(e)}")
            return False

    async def logout(self):
        """登出qBittorrent"""
        if self.session:
            await self.session.close()

    async def add_torrent(
        self,
        torrent_file: Optional[bytes] = None,
        torrent_url: Optional[str] = None,
        save_path: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        paused: bool = False,
    ) -> bool:
        """添加种子"""
        try:
            data = aiohttp.FormData()

            if torrent_file:
                data.add_field(
                    "torrents",
                    torrent_file,
                    filename="torrent.torrent",
                    content_type="application/x-bittorrent",
                )
            elif torrent_url:
                data.add_field("urls", torrent_url)
            else:
                logger.error("必须提供种子文件或URL")
                return False

            if save_path:
                data.add_field("savepath", save_path)
            if category:
                data.add_field("category", category)
            if tags:
                data.add_field("tags", ",".join(tags))
            if paused:
                data.add_field("paused", "true")

            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return False

            async with self.session.post(
                f"{self.base_url}/api/v2/torrents/add", data=data, cookies=self.cookies
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"添加种子失败: {str(e)}")
            return False

    async def get_torrents(
        self, hashes: Optional[List[str]] = None
    ) -> List[TorrentInfo]:
        """获取种子列表"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return []

            params = {}
            if hashes:
                params["hashes"] = "|".join(hashes)

            async with self.session.get(
                f"{self.base_url}/api/v2/torrents/info",
                params=params,
                cookies=self.cookies,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    torrents = []

                    for item in data:
                        torrent = TorrentInfo(
                            hash=item["hash"],
                            name=item["name"],
                            size=item["size"],
                            progress=item["progress"],
                            state=TorrentState(item["state"]),
                            download_speed=item["dlspeed"],
                            upload_speed=item["upspeed"],
                            ratio=item["ratio"],
                            eta=item["eta"],
                            added_on=datetime.fromtimestamp(item["added_on"]),
                            tags=item["tags"].split(",") if item["tags"] else [],
                            category=item["category"],
                            save_path=item["save_path"],
                        )
                        torrents.append(torrent)

                    return torrents
                else:
                    logger.error(f"获取种子列表失败: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"获取种子列表异常: {str(e)}")
            return []

    async def set_torrent_tags(self, hashes: List[str], tags: List[str]):
        """设置种子标签"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return False

            data = {"hashes": "|".join(hashes), "tags": ",".join(tags)}

            async with self.session.post(
                f"{self.base_url}/api/v2/torrents/addTags",
                data=data,
                cookies=self.cookies,
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"设置种子标签失败: {str(e)}")
            return False

    async def set_torrent_category(self, hashes: List[str], category: str):
        """设置种子分类"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return False

            data = {"hashes": "|".join(hashes), "category": category}

            async with self.session.post(
                f"{self.base_url}/api/v2/torrents/setCategory",
                data=data,
                cookies=self.cookies,
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"设置种子分类失败: {str(e)}")
            return False

    async def set_upload_limit(self, hashes: List[str], limit: int):
        """设置上传限制"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return False

            data = {"hashes": "|".join(hashes), "limit": limit}

            async with self.session.post(
                f"{self.base_url}/api/v2/torrents/setUploadLimit",
                data=data,
                cookies=self.cookies,
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"设置上传限制失败: {str(e)}")
            return False

    async def set_download_limit(self, hashes: List[str], limit: int):
        """设置下载限制"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return False

            data = {"hashes": "|".join(hashes), "limit": limit}

            async with self.session.post(
                f"{self.base_url}/api/v2/torrents/setDownloadLimit",
                data=data,
                cookies=self.cookies,
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"设置下载限制失败: {str(e)}")
            return False

    async def pause_torrents(self, hashes: List[str]):
        """暂停种子"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return False

            data = {"hashes": "|".join(hashes)}

            async with self.session.post(
                f"{self.base_url}/api/v2/torrents/pause",
                data=data,
                cookies=self.cookies,
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"暂停种子失败: {str(e)}")
            return False

    async def resume_torrents(self, hashes: List[str]):
        """恢复种子"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return False

            data = {"hashes": "|".join(hashes)}

            async with self.session.post(
                f"{self.base_url}/api/v2/torrents/resume",
                data=data,
                cookies=self.cookies,
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"恢复种子失败: {str(e)}")
            return False

    async def delete_torrents(self, hashes: List[str], delete_files: bool = False):
        """删除种子"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return False

            data = {
                "hashes": "|".join(hashes),
                "deleteFiles": "true" if delete_files else "false",
            }

            async with self.session.post(
                f"{self.base_url}/api/v2/torrents/delete",
                data=data,
                cookies=self.cookies,
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"删除种子失败: {str(e)}")
            return False

    async def get_categories(self) -> Dict[str, Any]:
        """获取分类列表"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return {}

            async with self.session.get(
                f"{self.base_url}/api/v2/torrents/categories", cookies=self.cookies
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"获取分类列表失败: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"获取分类列表异常: {str(e)}")
            return {}

    async def get_tags(self) -> List[str]:
        """获取标签列表"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return []

            async with self.session.get(
                f"{self.base_url}/api/v2/torrents/tags", cookies=self.cookies
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"获取标签列表失败: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"获取标签列表异常: {str(e)}")
            return []

    async def create_category(self, name: str, save_path: str):
        """创建分类"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return False

            data = {"category": name, "savePath": save_path}

            async with self.session.post(
                f"{self.base_url}/api/v2/torrents/createCategory",
                data=data,
                cookies=self.cookies,
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"创建分类失败: {str(e)}")
            return False

    async def get_transfer_info(self) -> Dict[str, Any]:
        """获取传输信息"""
        try:
            if self.session is None:
                logger.error("qBittorrent会话未初始化")
                return {}

            async with self.session.get(
                f"{self.base_url}/api/v2/transfer/info", cookies=self.cookies
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"获取传输信息失败: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"获取传输信息异常: {str(e)}")
            return {}
