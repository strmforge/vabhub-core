"""
STRM Gateway module for VabHub Core
"""

import os
from .logging_config import get_logger
from typing import Dict, List, Optional, Any
from pathlib import Path
import hashlib
import time

logger = get_logger("vabhub.strm_gateway")


class STRMGatewayManager:
    """STRM Gateway Manager for VabHub"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_path = config.get("strm_base_path", "/srv/media/strm")
        self.library_path = config.get("library_path", "/srv/media/library")
        self.gateway_url = config.get("gateway_url", "http://localhost:8000")

        # Create base directories
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(self.library_path, exist_ok=True)

    def generate_strm_file(self, media_info: Dict[str, Any]) -> str:
        """Generate STRM file for media content"""
        try:
            # Generate filename based on media info
            filename = self._generate_filename(media_info)
            strm_path = os.path.join(self.base_path, filename)

            # Generate signed URL for the media
            signed_url = self._generate_signed_url(media_info)

            # Write STRM file content
            with open(strm_path, "w", encoding="utf-8") as f:
                f.write(signed_url)

            logger.info(f"Generated STRM file: {strm_path}")
            return strm_path

        except Exception as e:
            logger.error(f"Failed to generate STRM file: {e}")
            raise

    def _generate_filename(self, media_info: Dict[str, Any]) -> str:
        """Generate filename for STRM file"""
        title = media_info.get("title", "unknown").replace(" ", "_")
        year = media_info.get("year", "")
        quality = media_info.get("quality", "unknown")

        if year:
            filename = f"{title}_{year}_{quality}.strm"
        else:
            filename = f"{title}_{quality}.strm"

        return filename

    def _generate_signed_url(self, media_info: Dict[str, Any]) -> str:
        """Generate signed URL for media streaming"""
        media_url = media_info.get("url", "")
        ttl = media_info.get("ttl", 3600)  # Default 1 hour

        if not media_url:
            raise ValueError("Media URL is required")

        # Generate signature based on URL and timestamp
        timestamp = int(time.time())
        signature_data = f"{media_url}{timestamp}{ttl}{self.config.get('signature_secret', 'default_secret')}"
        signature = hashlib.md5(signature_data.encode()).hexdigest()

        # Construct signed URL
        signed_url = f"{self.gateway_url}/stream?url={media_url}&t={timestamp}&e={timestamp + ttl}&s={signature}"

        return signed_url

    def scan_library_for_strm_files(self) -> List[Dict[str, Any]]:
        """Scan library directory for STRM files"""
        strm_files = []

        try:
            for root, dirs, files in os.walk(self.library_path):
                for file in files:
                    if file.endswith(".strm"):
                        file_path = os.path.join(root, file)
                        file_info = self._get_strm_file_info(file_path)
                        strm_files.append(file_info)

            logger.info(f"Found {len(strm_files)} STRM files in library")
            return strm_files

        except Exception as e:
            logger.error(f"Failed to scan library for STRM files: {e}")
            return []

    def _get_strm_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about STRM file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            file_stat = os.stat(file_path)

            return {
                "path": file_path,
                "filename": os.path.basename(file_path),
                "size": file_stat.st_size,
                "modified": file_stat.st_mtime,
                "content": content,
                "url": content,  # The content is the streaming URL
            }

        except Exception as e:
            logger.error(f"Failed to read STRM file {file_path}: {e}")
            return {"path": file_path, "error": str(e)}

    def organize_strm_files(self, organization_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Organize STRM files based on rules"""
        try:
            strm_files = self.scan_library_for_strm_files()
            organized_files: Dict[str, Any] = {"movies": [], "tv_shows": [], "other": []}

            for strm_file in strm_files:
                if "error" in strm_file:
                    organized_files["other"].append(strm_file)
                    continue

                filename = strm_file["filename"].lower()

                # Simple categorization based on filename patterns
                if any(
                    keyword in filename for keyword in ["season", "s0", "episode", "e0"]
                ):
                    organized_files["tv_shows"].append(strm_file)
                elif any(keyword in filename for keyword in ["movie", "film", ".strm"]):
                    organized_files["movies"].append(strm_file)
                else:
                    organized_files["other"].append(strm_file)

            # Apply organization rules
            if organization_rules.get("create_directories", True):
                self._create_organized_directories(organized_files)

            logger.info(f"Organized {len(strm_files)} STRM files")
            return organized_files

        except Exception as e:
            logger.error(f"Failed to organize STRM files: {e}")
            return {"error": str(e)}

    def _create_organized_directories(self, organized_files: Dict[str, Any]):
        """Create organized directory structure"""
        categories = ["movies", "tv_shows", "other"]

        for category in categories:
            category_path = os.path.join(self.library_path, category)
            os.makedirs(category_path, exist_ok=True)

    def validate_strm_file(self, file_path: str) -> Dict[str, Any]:
        """Validate STRM file content and accessibility"""
        try:
            file_info = self._get_strm_file_info(file_path)

            if "error" in file_info:
                return {
                    "valid": False,
                    "error": file_info["error"],
                    "file_path": file_path,
                }

            # Check if URL is accessible (basic validation)
            url = file_info.get("url", "")
            if not url.startswith("http"):
                return {
                    "valid": False,
                    "error": "Invalid URL format",
                    "file_path": file_path,
                }

            # Check file size and content
            if file_info["size"] == 0:
                return {"valid": False, "error": "Empty file", "file_path": file_path}

            return {
                "valid": True,
                "file_path": file_path,
                "url": url,
                "size": file_info["size"],
            }

        except Exception as e:
            return {"valid": False, "error": str(e), "file_path": file_path}

    def batch_generate_strm_files(
        self, media_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Batch generate STRM files for multiple media items"""
        results: Dict[str, Any] = {"success": [], "failed": [], "total": len(media_list)}

        for media_info in media_list:
            try:
                strm_path = self.generate_strm_file(media_info)
                results["success"].append(
                    {"media_info": media_info, "strm_path": strm_path}
                )
            except Exception as e:
                results["failed"].append({"media_info": media_info, "error": str(e)})

        logger.info(
            f"Batch generated STRM files: {len(results['success'])} success, {len(results['failed'])} failed"
        )
        return results

    def cleanup_old_strm_files(self, max_age_days: int = 30) -> Dict[str, Any]:
        """Clean up old STRM files"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60

            strm_files = self.scan_library_for_strm_files()
            cleaned_files = []

            for strm_file in strm_files:
                if "error" in strm_file:
                    continue

                file_age = current_time - strm_file["modified"]

                if file_age > max_age_seconds:
                    try:
                        os.remove(strm_file["path"])
                        cleaned_files.append(strm_file["path"])
                    except Exception as e:
                        logger.error(
                            f"Failed to remove old STRM file {strm_file['path']}: {e}"
                        )

            logger.info(f"Cleaned up {len(cleaned_files)} old STRM files")
            return {"cleaned_files": cleaned_files, "total_cleaned": len(cleaned_files)}

        except Exception as e:
            logger.error(f"Failed to clean up old STRM files: {e}")
            return {"error": str(e)}


class STRMPlugin:
    """STRM Plugin for integration with plugin system"""

    def __init__(self, config: Dict[str, Any]):
        self.name = "strm_gateway"
        self.version = "1.0.0"
        self.enabled = True
        self.manager = STRMGatewayManager(config)

    def setup(self):
        """Setup STRM plugin"""
        logger.info("STRM Gateway plugin setup completed")

    def cleanup(self):
        """Cleanup STRM plugin"""
        logger.info("STRM Gateway plugin cleanup completed")

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute STRM operation"""
        operation = data.get("operation", "")

        if operation == "generate_strm":
            return {"strm_path": self.manager.generate_strm_file(data.get("media_info", {}))}
        elif operation == "scan_library":
            return {"strm_files": self.manager.scan_library_for_strm_files()}
        elif operation == "organize_files":
            return self.manager.organize_strm_files(data.get("rules", {}))
        elif operation == "validate_file":
            return self.manager.validate_strm_file(data.get("file_path", ""))
        elif operation == "batch_generate":
            return self.manager.batch_generate_strm_files(data.get("media_list", []))
        elif operation == "cleanup_old":
            return self.manager.cleanup_old_strm_files(data.get("max_age_days", 30))
        else:
            return {"error": f"Unknown operation: {operation}"}

    def health_check(self) -> bool:
        """Health check for STRM plugin"""
        try:
            # Test basic functionality
            test_media = {
                "title": "Test Media",
                "url": "http://example.com/test.mp4",
                "quality": "1080p",
            }

            strm_path = self.manager.generate_strm_file(test_media)

            # Clean up test file
            if os.path.exists(strm_path):
                os.remove(strm_path)

            return True
        except Exception as e:
            logger.error(f"STRM plugin health check failed: {e}")
            return False
