"""
文件重命名器 - 基于MoviePilot参考实现
支持模板化重命名、软硬链接、STRM文件生成
"""

import os
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse


class RenameTemplate:
    """重命名模板类"""

    def __init__(self, template: str = "{title}.{year}.{SxxExx}.{codec}.{audio}"):
        self.template = template
        self.logger = logging.getLogger(__name__)
        self.placeholders = {
            "{title}": "title",
            "{year}": "year",
            "{SxxExx}": "season_episode",
            "{codec}": "codec",
            "{audio}": "audio",
            "{resolution}": "resolution",
            "{group}": "release_group",
            "{source}": "source_type",
        }

    def render(self, media_info: Dict[str, Any]) -> str:
        """渲染模板"""
        result = self.template

        for placeholder, field in self.placeholders.items():
            value = media_info.get(field, "")
            if value:
                result = result.replace(placeholder, str(value))
            else:
                # 如果字段为空，移除占位符
                result = result.replace(placeholder, "")

        # 清理多余的分隔符
        result = re.sub(r"[._]+", ".", result)
        result = result.strip("._")

        return result


class FileRenamer:
    """文件重命名器"""

    def __init__(self, base_path: str, template: Optional[str] = None):
        self.base_path = Path(base_path)
        self.template = RenameTemplate(
            template or "{title}.{year}.{SxxExx}.{codec}.{audio}"
        )
        self.logger = logging.getLogger(__name__)

        # 支持的媒体文件扩展名
        self.video_extensions = {
            ".mp4",
            ".mkv",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".3gp",
            ".ts",
            ".mts",
            ".m2ts",
        }

        # 支持的音频文件扩展名
        self.audio_extensions = {
            ".mp3",
            ".wav",
            ".flac",
            ".aac",
            ".ogg",
            ".wma",
            ".m4a",
        }

    def parse_filename(self, filename: str) -> Dict[str, Any]:
        """解析文件名获取媒体信息"""
        info = {}

        # 提取年份
        year_match = re.search(r"(19|20)\d{2}", filename)
        if year_match:
            info["year"] = year_match.group()

        # 提取季集信息
        season_episode_match = re.search(r"[Ss](\d+)[Ee](\d+)", filename)
        if season_episode_match:
            season = int(season_episode_match.group(1))
            episode = int(season_episode_match.group(2))
            info["season"] = str(season)
            info["episode"] = str(episode)
            info["season_episode"] = f"S{season:02d}E{episode:02d}"

        # 提取分辨率
        resolution_patterns = {
            "2160p": ["2160p", "4k", "uhd"],
            "1080p": ["1080p", "1080"],
            "720p": ["720p", "720"],
            "480p": ["480p", "480"],
        }

        for resolution, patterns in resolution_patterns.items():
            if any(pattern in filename.lower() for pattern in patterns):
                info["resolution"] = resolution
                break

        # 提取编码
        codec_patterns = {
            "H265": ["h265", "hevc", "x265"],
            "H264": ["h264", "x264", "avc"],
            "AV1": ["av1"],
        }

        for codec, patterns in codec_patterns.items():
            if any(pattern in filename.lower() for pattern in patterns):
                info["codec"] = codec
                break

        # 提取音频格式
        audio_patterns = {
            "DTS-HD": ["dts-hd", "dtshd"],
            "DTS": ["dts"],
            "Dolby Atmos": ["atmos"],
            "Dolby Digital": ["ac3", "dd", "dolbydigital"],
            "AAC": ["aac"],
            "FLAC": ["flac"],
        }

        for audio, patterns in audio_patterns.items():
            if any(pattern in filename.lower() for pattern in patterns):
                info["audio"] = audio
                break

        # 提取发布组
        group_match = re.search(r"-([A-Za-z0-9]+)(?:\.[^.]+)?$", filename)
        if group_match:
            info["release_group"] = group_match.group(1)

        # 提取来源类型
        source_patterns = {
            "BluRay": ["bluray", "bdrip", "brrip"],
            "WEB-DL": ["webdl", "web-dl", "webrip"],
            "HDTV": ["hdtv"],
            "DVD": ["dvdrip", "dvd"],
        }

        for source, patterns in source_patterns.items():
            if any(pattern in filename.lower() for pattern in patterns):
                info["source_type"] = source
                break

        # 提取标题（移除其他信息）
        title = filename

        # 移除扩展名
        title = Path(title).stem

        # 移除常见标识符
        patterns_to_remove = [
            r"[Ss]\d+[Ee]\d+",  # 季集信息
            r"(19|20)\d{2}",  # 年份
            r"2160p|1080p|720p|480p",  # 分辨率
            r"h265|h264|hevc|x265|x264|av1",  # 编码
            r"dts[-_]?hd|dts|atmos|ac3|aac|flac",  # 音频
            r"bluray|bdrip|webdl|hdtv|dvdrip",  # 来源
            r"\[.*?\]",  # 方括号内容
            r"\(.*?\)",  # 圆括号内容
        ]

        for pattern in patterns_to_remove:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        # 清理标题
        title = re.sub(r"[._]+", " ", title)
        title = title.strip(" ._-")

        info["title"] = title

        return info

    def generate_new_filename(
        self, old_filename: str, media_info: Dict[str, Any]
    ) -> str:
        """生成新文件名"""
        # 如果media_info为空，尝试从文件名解析
        if not media_info:
            media_info = self.parse_filename(old_filename)

        # 使用模板生成新文件名
        new_name = self.template.render(media_info)

        # 获取文件扩展名
        extension = Path(old_filename).suffix.lower()

        # 确保扩展名有效
        if not extension or extension not in (
            self.video_extensions | self.audio_extensions
        ):
            extension = ".mkv"  # 默认扩展名

        return f"{new_name}{extension}"

    def rename_file(
        self, old_path: str, new_filename: str, strategy: str = "move"
    ) -> bool:
        """重命名文件"""
        old_file = Path(old_path)

        if not old_file.exists():
            return False

        # 构建新路径
        new_file = old_file.parent / new_filename

        # 检查目标文件是否已存在
        if new_file.exists():
            # 处理文件名冲突
            counter = 1
            while new_file.exists():
                stem = Path(new_filename).stem
                extension = Path(new_filename).suffix
                new_filename = f"{stem}_{counter:02d}{extension}"
                new_file = old_file.parent / new_filename
                counter += 1

        try:
            if strategy == "move":
                shutil.move(str(old_file), str(new_file))
            elif strategy == "copy":
                shutil.copy2(str(old_file), str(new_file))
            elif strategy == "hardlink":
                os.link(str(old_file), str(new_file))
            elif strategy == "symlink":
                os.symlink(str(old_file), str(new_file))
            else:
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error renaming file: {e}")
            return False

    def batch_rename(self, directory: str, strategy: str = "move") -> Dict[str, str]:
        """批量重命名目录中的文件"""
        results: Dict[str, str] = {}

        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            return results

        for file_path in dir_path.iterdir():
            if (
                file_path.is_file()
                and file_path.suffix.lower() in self.video_extensions
            ):
                media_info = self.parse_filename(file_path.name)
                new_filename = self.generate_new_filename(file_path.name, media_info)

                if self.rename_file(str(file_path), new_filename, strategy):
                    results[str(file_path)] = new_filename

        return results


class STRMGenerator:
    """STRM文件生成器"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def generate_strm_file(self, media_info: Dict[str, Any], url: str) -> str:
        """生成STRM文件"""
        # 构建文件路径
        if media_info.get("type") == "movie":
            # 电影路径: Movies/Title (Year)/Title (Year).strm
            dir_name = f"{media_info['title']} ({media_info.get('year', '')})".strip()
            file_name = f"{media_info['title']} ({media_info.get('year', '')}).strm"
        elif media_info.get("type") == "tv":
            # 电视剧路径: TV Shows/Title/Season XX/Title - SXXEYY.strm
            dir_name = f"{media_info['title']}"
            season_dir = f"Season {media_info.get('season', 1):02d}"
            file_name = f"{media_info['title']} - S{media_info.get('season', 1):02d}E{media_info.get('episode', 1):02d}.strm"
        else:
            # 默认路径
            dir_name = "Other"
            file_name = f"{media_info.get('title', 'unknown')}.strm"

        # 清理文件名中的非法字符
        dir_name = self._sanitize_filename(dir_name)
        file_name = self._sanitize_filename(file_name)

        # 构建完整路径
        strm_path = self.base_path / dir_name / file_name

        # 确保目录存在
        strm_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入STRM文件内容
        with open(strm_path, "w", encoding="utf-8") as f:
            f.write(url)

        return str(strm_path)

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # Windows非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, "_", filename)

        # 移除首尾空格和点
        filename = filename.strip(" .")

        return filename

    def generate_nfo_file(self, media_info: Dict[str, Any], strm_path: str) -> str:
        """生成NFO文件"""
        nfo_path = Path(strm_path).with_suffix(".nfo")

        nfo_content = ""
        if media_info.get("type") == "movie":
            nfo_content = self._generate_movie_nfo(media_info)
        elif media_info.get("type") == "tv":
            nfo_content = self._generate_tv_nfo(media_info)

        if nfo_content:
            with open(nfo_path, "w", encoding="utf-8") as f:
                f.write(nfo_content)

        return str(nfo_path)

    def _generate_movie_nfo(self, media_info: Dict[str, Any]) -> str:
        """生成电影NFO文件内容"""
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
    <title>{media_info.get('title', '')}</title>
    <year>{media_info.get('year', '')}</year>
    <plot>{media_info.get('overview', '')}</plot>
    <runtime>{media_info.get('runtime', 0)}</runtime>
    <rating>{media_info.get('rating', 0.0)}</rating>
    <genre>{'/'.join(media_info.get('genres', []))}</genre>
</movie>"""

    def _generate_tv_nfo(self, media_info: Dict[str, Any]) -> str:
        """生成电视剧NFO文件内容"""
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<episodedetails>
    <title>{media_info.get('title', '')}</title>
    <showtitle>{media_info.get('show_title', media_info.get('title', ''))}</showtitle>
    <season>{media_info.get('season', 1)}</season>
    <episode>{media_info.get('episode', 1)}</episode>
    <plot>{media_info.get('overview', '')}</plot>
    <runtime>{media_info.get('runtime', 0)}</runtime>
    <rating>{media_info.get('rating', 0.0)}</rating>
</episodedetails>"""


class MediaOrganizer:
    """媒体文件组织器"""

    def __init__(self, base_path: str, template: Optional[str] = None):
        self.renamer = FileRenamer(base_path, template)
        self.strm_generator = STRMGenerator(base_path)
        self.logger = logging.getLogger(__name__)

    def organize_media_file(
        self,
        file_path: str,
        media_info: Dict[str, Any],
        url: Optional[str] = None,
        generate_strm: bool = False,
    ) -> Dict[str, str]:
        """组织单个媒体文件"""
        results: Dict[str, str] = {}

        # 重命名文件
        new_filename = self.renamer.generate_new_filename(
            Path(file_path).name, media_info
        )
        success = self.renamer.rename_file(file_path, new_filename, "move")

        if success:
            results["renamed"] = new_filename

            # 如果需要生成STRM文件
            if generate_strm and url:
                strm_path = self.strm_generator.generate_strm_file(media_info, url)
                results["strm"] = strm_path

                # 生成NFO文件
                nfo_path = self.strm_generator.generate_nfo_file(media_info, strm_path)
                results["nfo"] = nfo_path

        return results

    def scan_and_organize(
        self, source_dir: str, target_dir: Optional[str] = None
    ) -> Dict[str, Dict[str, str]]:
        """扫描并组织目录中的媒体文件"""
        if target_dir:
            self.renamer.base_path = Path(target_dir)
            self.strm_generator.base_path = Path(target_dir)

        results: Dict[str, Dict[str, str]] = {}

        source_path = Path(source_dir)
        if not source_path.exists() or not source_path.is_dir():
            return results

        for file_path in source_path.rglob("*"):
            if (
                file_path.is_file()
                and file_path.suffix.lower() in self.renamer.video_extensions
            ):
                try:
                    media_info = self.renamer.parse_filename(file_path.name)
                    file_results = self.organize_media_file(str(file_path), media_info)
                    results[str(file_path)] = file_results
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {e}")

        return results
