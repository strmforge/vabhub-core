"""
路径管理器 - 优化重命名和路径管理
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


class PathManager:
    """路径管理器，负责文件路径的优化和管理"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        # 移除非法字符
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, "_", filename)

        # 移除连续的下划线
        sanitized = re.sub(r"_+", "_", sanitized)

        # 移除首尾的下划线和空格
        sanitized = sanitized.strip(" _")

        # 确保文件名不为空
        if not sanitized:
            sanitized = "unnamed_file"

        return sanitized

    def get_unique_filename(self, filepath: str) -> Path:
        """
        获取唯一的文件名，避免冲突

        Args:
            filepath: 目标文件路径

        Returns:
            唯一的文件路径
        """
        path = Path(filepath)

        # 如果文件不存在，直接返回
        if not path.exists():
            return path

        # 如果文件存在，添加后缀
        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        counter = 1
        while True:
            new_filename = f"{stem}_{counter:03d}{suffix}"
            new_path = parent / new_filename

            if not new_path.exists():
                return new_path

            counter += 1

    def organize_by_type(self, filepath: str, media_type: str) -> Path:
        """
        根据媒体类型组织文件

        Args:
            filepath: 文件路径
            media_type: 媒体类型（movie, tv, music, etc.）

        Returns:
            组织后的文件路径
        """
        path = Path(filepath)
        filename = path.name

        # 根据类型创建目录结构
        if media_type == "movie":
            target_dir = self.base_path / "Movies"
        elif media_type == "tv":
            target_dir = self.base_path / "TV Shows"
        elif media_type == "music":
            target_dir = self.base_path / "Music"
        else:
            target_dir = self.base_path / "Other"

        target_dir.mkdir(parents=True, exist_ok=True)

        return target_dir / filename

    def create_symlink(
        self, source: str, destination: str, hard_link: bool = False
    ) -> bool:
        """
        创建符号链接或硬链接

        Args:
            source: 源文件路径
            destination: 目标路径
            hard_link: 是否创建硬链接

        Returns:
            是否成功创建
        """
        try:
            source_path = Path(source)
            dest_path = Path(destination)

            # 确保目标目录存在
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if hard_link:
                # 创建硬链接
                os.link(source_path, dest_path)
            else:
                # 创建符号链接
                if dest_path.exists():
                    dest_path.unlink()
                dest_path.symlink_to(source_path)

            return True
        except Exception as e:
            print(f"创建链接失败: {e}")
            return False

    def batch_rename(
        self, files: List[Dict[str, Any]], template: str
    ) -> List[Dict[str, Any]]:
        """
        批量重命名文件

        Args:
            files: 文件信息列表
            template: 命名模板

        Returns:
            重命名结果列表
        """
        results = []

        for file_info in files:
            try:
                # 根据媒体类型应用不同的重命名策略
                media_type = file_info.get("type", "other")

                if media_type == "music":
                    # 音乐文件重命名：艺术家 - 专辑 - 曲目编号 - 曲目标题
                    artist = file_info.get("artist", "Unknown Artist")
                    album = file_info.get("album", "Unknown Album")
                    track = file_info.get("track", 0)
                    title = file_info.get("title", "Unknown Title")

                    # 清理文件名
                    artist = self.sanitize_filename(artist)
                    album = self.sanitize_filename(album)
                    title = self.sanitize_filename(title)

                    # 构建音乐文件名
                    new_filename = f"{artist} - {album} - {track:02d} - {title}"

                elif media_type == "movie":
                    # 电影文件重命名：标题.年份.质量.编码
                    title = file_info.get("title", "Unknown Movie")
                    year = file_info.get("year", "")
                    quality = file_info.get("quality", "")
                    codec = file_info.get("codec", "")

                    title = self.sanitize_filename(title)
                    new_filename = f"{title}"
                    if year:
                        new_filename += f".{year}"
                    if quality:
                        new_filename += f".{quality}"
                    if codec:
                        new_filename += f".{codec}"

                elif media_type == "tv":
                    # 电视剧文件重命名：标题.S季号E集号.质量.编码
                    title = file_info.get("title", "Unknown TV Show")
                    season = file_info.get("season", 1)
                    episode = file_info.get("episode", 1)
                    quality = file_info.get("quality", "")
                    codec = file_info.get("codec", "")

                    title = self.sanitize_filename(title)
                    new_filename = f"{title}.S{season:02d}E{episode:02d}"
                    if quality:
                        new_filename += f".{quality}"
                    if codec:
                        new_filename += f".{codec}"

                else:
                    # 其他类型文件使用简单重命名
                    title = file_info.get("title", "Unknown")
                    new_filename = self.sanitize_filename(title)

                # 添加文件扩展名
                extension = file_info.get("extension", "")
                if extension:
                    new_filename += f".{extension}"

                # 获取原始文件路径
                original_path = Path(file_info["path"])

                # 构建新路径
                new_path = original_path.parent / new_filename

                # 确保文件名唯一
                new_path = self.get_unique_filename(new_path)

                # 重命名文件
                original_path.rename(new_path)

                # 记录结果
                result = {
                    "original_path": str(original_path),
                    "new_path": str(new_path),
                    "success": True,
                    "error": None,
                }
                results.append(result)

            except Exception as e:
                # 记录错误
                result = {
                    "original_path": file_info.get("path", "unknown"),
                    "new_path": None,
                    "success": False,
                    "error": str(e),
                }
                results.append(result)

        return results

    def _render_template(self, template: str, file_info: Dict[str, Any]) -> str:
        """
        渲染命名模板

        Args:
            template: 模板字符串
            file_info: 文件信息

        Returns:
            渲染后的文件名
        """
        # 提取模板变量
        variables = {
            "title": file_info.get("title", ""),
            "year": file_info.get("year", ""),
            "season": file_info.get("season", ""),
            "episode": file_info.get("episode", ""),
            "quality": file_info.get("quality", ""),
            "codec": file_info.get("codec", ""),
            "audio": file_info.get("audio", ""),
            "extension": file_info.get("extension", ""),
        }

        # 清理变量
        for key, value in variables.items():
            if value:
                variables[key] = self.sanitize_filename(str(value))

        # 渲染模板
        filename = template.format(**variables)

        # 确保有文件扩展名
        if "extension" not in template and variables["extension"]:
            filename += f".{variables['extension']}"

        return filename

    def find_duplicates(self, directory: str) -> List[Tuple[str, str]]:
        """
        查找重复文件

        Args:
            directory: 要检查的目录

        Returns:
            重复文件对列表
        """
        duplicates = []
        file_hashes = {}

        dir_path = Path(directory)

        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                # 计算文件哈希（简化实现）
                file_hash = self._get_file_hash(file_path)

                if file_hash in file_hashes:
                    duplicates.append((str(file_hashes[file_hash]), str(file_path)))
                else:
                    file_hashes[file_hash] = file_path

        return duplicates

    def _get_file_hash(self, filepath: Path) -> str:
        """
        计算文件哈希（简化实现）

        Args:
            filepath: 文件路径

        Returns:
            文件哈希
        """
        import hashlib

        # 简化实现：使用文件大小和修改时间
        stat = filepath.stat()
        hash_data = f"{filepath.name}_{stat.st_size}_{stat.st_mtime}"

        return hashlib.md5(hash_data.encode()).hexdigest()

    def cleanup_empty_dirs(self, directory: str) -> List[str]:
        """
        清理空目录

        Args:
            directory: 要清理的目录

        Returns:
            被删除的目录列表
        """
        removed_dirs = []
        dir_path = Path(directory)

        for root, dirs, files in os.walk(dir_path, topdown=False):
            root_path = Path(root)

            # 检查目录是否为空
            if not any(root_path.iterdir()):
                try:
                    root_path.rmdir()
                    removed_dirs.append(str(root_path))
                except OSError:
                    # 目录不为空或无法删除
                    pass

        return removed_dirs


class FileOrganizer:
    """文件组织器，负责自动组织文件结构"""

    def __init__(self, path_manager: PathManager):
        self.path_manager = path_manager

    def organize_media_files(self, source_dir: str, target_base: str) -> Dict[str, Any]:
        """
        组织媒体文件

        Args:
            source_dir: 源目录
            target_base: 目标基础目录

        Returns:
            组织结果
        """
        results = {"processed": 0, "success": 0, "errors": [], "moved_files": []}

        source_path = Path(source_dir)

        for file_path in source_path.rglob("*"):
            if file_path.is_file():
                try:
                    # 识别文件类型
                    media_type = self._identify_media_type(file_path)

                    # 组织文件
                    target_path = self.path_manager.organize_by_type(
                        str(file_path), media_type
                    )

                    # 移动文件
                    shutil.move(str(file_path), str(target_path))

                    results["processed"] = results["processed"] + 1
                    results["success"] = results["success"] + 1
                    results["moved_files"].append(
                        {
                            "source": str(file_path),
                            "target": str(target_path),
                            "type": media_type,
                        }
                    )

                except Exception as e:
                    results["processed"] = results["processed"] + 1
                    results["errors"].append({"file": str(file_path), "error": str(e)})

        return results

    def _identify_media_type(self, filepath: Path) -> str:
        """
        识别媒体文件类型

        Args:
            filepath: 文件路径

        Returns:
            媒体类型
        """
        filename = filepath.name.lower()

        # 视频文件扩展名
        video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}

        # 音频文件扩展名
        audio_extensions = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}

        # 图片文件扩展名
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}

        if filepath.suffix.lower() in video_extensions:
            # 进一步识别视频类型
            if any(
                keyword in filename for keyword in ["season", "s\\d", "e\\d", "episode"]
            ):
                return "tv"
            else:
                return "movie"
        elif filepath.suffix.lower() in audio_extensions:
            return "music"
        elif filepath.suffix.lower() in image_extensions:
            return "image"
        else:
            return "other"
