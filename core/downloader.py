"""
Downloader integration module for VabHub Core
"""

import httpx
from typing import Dict, Any, List, Optional
from .config import Config


class DownloaderManager:
    """Manager for downloader integrations (qBittorrent/Transmission)"""

    def __init__(self, config: Config):
        self.config = config
        self.client = httpx.AsyncClient()

    async def test_qbittorrent_connection(
        self, url: str, username: str = "", password: str = ""
    ) -> Dict[str, Any]:
        """Test connection to qBittorrent"""
        try:
            # First, login if credentials provided
            if username and password:
                login_data = {"username": username, "password": password}
                login_response = await self.client.post(
                    f"{url}/api/v2/auth/login", data=login_data
                )
                if login_response.status_code != 200:
                    return {"ok": False, "error": "Login failed"}

            # Test connection
            response = await self.client.get(f"{url}/api/v2/app/version")

            if response.status_code == 200:
                version = response.text
                return {"ok": True, "version": version, "type": "qbittorrent"}
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def test_transmission_connection(
        self, url: str, username: str = "", password: str = ""
    ) -> Dict[str, Any]:
        """Test connection to Transmission"""
        try:
            headers = {}
            if username and password:
                import base64

                auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {auth}"

            # Test connection with RPC call
            rpc_data = {"method": "session-get", "arguments": {}}
            response = await self.client.post(
                f"{url}/transmission/rpc", json=rpc_data, headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                version = data.get("arguments", {}).get("version", "Unknown")
                return {"ok": True, "version": version, "type": "transmission"}
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def test_connection(
        self, url: str, downloader_type: str, username: str = "", password: str = ""
    ) -> Dict[str, Any]:
        """Test connection to downloader"""
        if downloader_type.lower() == "qbittorrent":
            return await self.test_qbittorrent_connection(url, username, password)
        elif downloader_type.lower() == "transmission":
            return await self.test_transmission_connection(url, username, password)
        else:
            return {
                "ok": False,
                "error": f"Unsupported downloader type: {downloader_type}",
            }

    async def get_qbittorrent_stats(
        self, url: str, username: str = "", password: str = ""
    ) -> Dict[str, Any]:
        """Get qBittorrent statistics"""
        try:
            # Login if credentials provided
            if username and password:
                login_data = {"username": username, "password": password}
                await self.client.post(f"{url}/api/v2/auth/login", data=login_data)

            # Get transfer info
            response = await self.client.get(f"{url}/api/v2/transfer/info")

            if response.status_code == 200:
                data = response.json()
                return {
                    "ok": True,
                    "download_speed": data.get("dl_info_speed", 0),
                    "upload_speed": data.get("up_info_speed", 0),
                    "total_downloaded": data.get("dl_info_data", 0),
                    "total_uploaded": data.get("up_info_data", 0),
                    "queue_size": data.get("queue_size", 0),
                }
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_transmission_stats(
        self, url: str, username: str = "", password: str = ""
    ) -> Dict[str, Any]:
        """Get Transmission statistics"""
        try:
            headers = {}
            if username and password:
                import base64

                auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {auth}"

            # Get session stats
            rpc_data = {"method": "session-stats", "arguments": {}}
            response = await self.client.post(
                f"{url}/transmission/rpc", json=rpc_data, headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                args = data.get("arguments", {})
                return {
                    "ok": True,
                    "download_speed": args.get("downloadSpeed", 0),
                    "upload_speed": args.get("uploadSpeed", 0),
                    "total_downloaded": args.get("downloadedBytes", 0),
                    "total_uploaded": args.get("uploadedBytes", 0),
                    "active_torrent_count": args.get("activeTorrentCount", 0),
                }
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_stats(
        self, url: str, downloader_type: str, username: str = "", password: str = ""
    ) -> Dict[str, Any]:
        """Get downloader statistics"""
        if downloader_type.lower() == "qbittorrent":
            return await self.get_qbittorrent_stats(url, username, password)
        elif downloader_type.lower() == "transmission":
            return await self.get_transmission_stats(url, username, password)
        else:
            return {
                "ok": False,
                "error": f"Unsupported downloader type: {downloader_type}",
            }

    async def add_qbittorrent_torrent(
        self, url: str, torrent_url: str, username: str = "", password: str = ""
    ) -> Dict[str, Any]:
        """Add torrent to qBittorrent"""
        try:
            # Login if credentials provided
            if username and password:
                login_data = {"username": username, "password": password}
                await self.client.post(f"{url}/api/v2/auth/login", data=login_data)

            # Add torrent
            add_data = {"urls": torrent_url}
            response = await self.client.post(
                f"{url}/api/v2/torrents/add", data=add_data
            )

            if response.status_code == 200:
                return {"ok": True, "message": "Torrent added successfully"}
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def add_transmission_torrent(
        self, url: str, torrent_url: str, username: str = "", password: str = ""
    ) -> Dict[str, Any]:
        """Add torrent to Transmission"""
        try:
            headers = {}
            if username and password:
                import base64

                auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {auth}"

            # Add torrent
            rpc_data = {"method": "torrent-add", "arguments": {"filename": torrent_url}}
            response = await self.client.post(
                f"{url}/transmission/rpc", json=rpc_data, headers=headers
            )

            if response.status_code == 200:
                return {"ok": True, "message": "Torrent added successfully"}
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def add_torrent(
        self,
        url: str,
        downloader_type: str,
        torrent_url: str,
        username: str = "",
        password: str = "",
    ) -> Dict[str, Any]:
        """Add torrent to downloader"""
        if downloader_type.lower() == "qbittorrent":
            return await self.add_qbittorrent_torrent(
                url, torrent_url, username, password
            )
        elif downloader_type.lower() == "transmission":
            return await self.add_transmission_torrent(
                url, torrent_url, username, password
            )
        else:
            return {
                "ok": False,
                "error": f"Unsupported downloader type: {downloader_type}",
            }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
