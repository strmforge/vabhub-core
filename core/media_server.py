"""
Media server integration module for VabHub Core
"""

import httpx
from typing import Dict, Any, List, Optional, Union
from .config import Config


class MediaServerManager:
    """Manager for media server integrations (Emby/Jellyfin)"""

    def __init__(self, config: Config):
        self.config = config
        self.client = httpx.AsyncClient()

    async def test_connection(self, server_url: str, api_key: str) -> Dict[str, Any]:
        """Test connection to media server"""
        try:
            headers = {"X-Emby-Token": api_key} if api_key else {}
            response = await self.client.get(
                f"{server_url}/System/Info", headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "ok": True,
                    "server_name": data.get("ServerName", "Unknown"),
                    "version": data.get("Version", "Unknown"),
                    "operating_system": data.get("OperatingSystem", "Unknown"),
                }
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_libraries(
        self, server_url: str, api_key: str
    ) -> List[Dict[str, Any]]:
        """Get media libraries from server"""
        try:
            headers = {"X-Emby-Token": api_key} if api_key else {}
            response = await self.client.get(
                f"{server_url}/Library/VirtualFolders", headers=headers
            )

            if response.status_code == 200:
                libraries = response.json()
                return [
                    {
                        "name": lib.get("Name", "Unknown"),
                        "type": lib.get("CollectionType", "Unknown"),
                        "path": lib.get("Path", "Unknown"),
                    }
                    for lib in libraries
                ]
            else:
                return []
        except Exception:
            return []

    async def refresh_library(
        self, server_url: str, api_key: str, library_name: str
    ) -> Dict[str, Any]:
        """Refresh a specific library"""
        try:
            headers = {"X-Emby-Token": api_key} if api_key else {}
            response = await self.client.post(
                f"{server_url}/Library/Refresh",
                headers=headers,
                params={"path": library_name},
            )

            if response.status_code == 204:
                return {
                    "ok": True,
                    "message": f"Library {library_name} refresh initiated",
                }
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def search_media(
        self, server_url: str, api_key: str, query: str, media_type: str = "All"
    ) -> List[Dict[str, Any]]:
        """Search for media on the server"""
        try:
            headers = {"X-Emby-Token": api_key} if api_key else {}
            params = {"SearchTerm": query, "IncludeItemTypes": media_type}
            response = await self.client.get(
                f"{server_url}/Search/Hints", headers=headers, params=params
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "name": item.get("Name", "Unknown"),
                        "type": item.get("Type", "Unknown"),
                        "year": item.get("ProductionYear"),
                        "id": item.get("Id"),
                    }
                    for item in data.get("SearchHints", [])
                ]
            else:
                return []
        except Exception:
            return []

    async def get_recently_added(
        self, server_url: str, api_key: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recently added media"""
        try:
            headers = {"X-Emby-Token": api_key} if api_key else {}
            params = {
                "Limit": limit,
                "SortBy": "DateCreated",
                "SortOrder": "Descending",
            }
            typed_params: Dict[str, Union[str, int]] = params  # type: ignore
            response = await self.client.get(
                f"{server_url}/Items/Latest", headers=headers, params=typed_params
            )

            if response.status_code == 200:
                items = response.json()
                return [
                    {
                        "name": item.get("Name", "Unknown"),
                        "type": item.get("Type", "Unknown"),
                        "year": item.get("ProductionYear"),
                        "added": item.get("DateCreated"),
                    }
                    for item in items
                ]
            else:
                return []
        except Exception:
            return []

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
