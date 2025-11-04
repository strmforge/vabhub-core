"""
智能文件整理系统核心模块
"""

import os
import re
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FileAction(Enum):
    """文件操作类型"""

    MOVE = "move"
    COPY = "copy"
    LINK = "link"
    RENAME = "rename"


class MediaType(Enum):
    """媒体类型"""

    MOVIE = "movie"
    TV = "tv"
    MUSIC = "music"
    ANIME = "anime"
    UNKNOWN = "unknown"


@dataclass
class FileInfo:
    """文件信息"""

    path: str
    name: str
    size: int
    modified_time: float
    media_type: MediaType
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class OrganizationRule:
    """整理规则"""

    name: str
    pattern: str
    target_template: str
    action: FileAction = FileAction.MOVE
    enabled: bool = True
    priority: int = 1

    def match(self, file_info: FileInfo) -> bool:
        """检查文件是否匹配规则"""
        try:
            return bool(re.search(self.pattern, file_info.name, re.IGNORECASE))
        except re.error:
            logger.error(f"Invalid regex pattern: {self.pattern}")
            return False


class FileOrganizer:
    """文件整理器"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.rules: List[OrganizationRule] = []
        self._load_default_rules()

    def _load_default_rules(self):
        """加载默认整理规则"""
        default_rules = [
            OrganizationRule(
                name="电影整理",
                pattern=r"\.(mp4|mkv|avi|mov)$",
                target_template="Movies/{title} ({year})/{title} ({year}).{ext}",
                action=FileAction.MOVE,
                priority=1,
            ),
            OrganizationRule(
                name="电视剧整理",
                pattern=r"S\d{2}E\d{2}",
                target_template="TV Shows/{title}/Season {season}/{title} - S{season}E{episode}.{ext}",
                action=FileAction.MOVE,
                priority=1,
            ),
            OrganizationRule(
                name="音乐整理",
                pattern=r"\.(mp3|flac|wav|aac)$",
                target_template="Music/{artist}/{album}/{track_number} - {title}.{ext}",
                action=FileAction.MOVE,
                priority=2,
            ),
            OrganizationRule(
                name="动漫整理",
                pattern=r"\[.*?\].*\[.*?\]",
                target_template="Anime/{title}/Season {season}/{title} - S{season}E{episode}.{ext}",
                action=FileAction.MOVE,
                priority=1,
            ),
        ]
        self.rules.extend(default_rules)

    def add_rule(self, rule: OrganizationRule):
        """添加整理规则"""
        self.rules.append(rule)
        self.rules.sort(key=lambda x: x.priority, reverse=True)

    def remove_rule(self, rule_name: str) -> bool:
        """移除整理规则"""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules.pop(i)
                return True
        return False

    def scan_directory(self, directory: Optional[str] = None) -> List[FileInfo]:
        """扫描目录获取文件信息"""
        scan_path = Path(directory) if directory else self.base_path
        file_infos = []

        try:
            for file_path in scan_path.rglob("*"):
                if file_path.is_file():
                    file_info = self._analyze_file(file_path)
                    if file_info:
                        file_infos.append(file_info)
        except Exception as e:
            logger.error(f"Error scanning directory {scan_path}: {e}")

        return file_infos

    def _analyze_file(self, file_path: Path) -> Optional[FileInfo]:
        """分析文件信息"""
        try:
            stat = file_path.stat()

            # 提取文件名和扩展名
            name = file_path.name
            ext = file_path.suffix.lower()[1:] if file_path.suffix else ""

            # 识别媒体类型
            media_type = self._detect_media_type(name, ext)

            # 提取元数据
            metadata = self._extract_metadata(name)

            return FileInfo(
                path=str(file_path),
                name=name,
                size=stat.st_size,
                modified_time=stat.st_mtime,
                media_type=media_type,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return None

    def _detect_media_type(self, filename: str, ext: str) -> MediaType:
        """检测媒体类型"""
        # 视频文件
        if ext in ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm"]:
            # 检查是否是电视剧
            if re.search(r"S\d{1,2}E\d{1,2}", filename, re.IGNORECASE):
                return MediaType.TV
            # 检查是否是动漫
            elif re.search(r"\[.*?\].*\[.*?\]", filename):
                return MediaType.ANIME
            else:
                return MediaType.MOVIE

        # 音频文件
        elif ext in ["mp3", "flac", "wav", "aac", "ogg", "m4a"]:
            return MediaType.MUSIC

        return MediaType.UNKNOWN

    def _extract_metadata(self, filename: str) -> Dict[str, Any]:
        """从文件名提取元数据"""
        metadata = {}

        # 提取年份
        year_match = re.search(r"(19|20)\d{2}", filename)
        if year_match:
            metadata["year"] = year_match.group()

        # 提取季集信息
        season_episode_match = re.search(
            r"S(\d{1,2})E(\d{1,2})", filename, re.IGNORECASE
        )
        if season_episode_match:
            metadata["season"] = str(int(season_episode_match.group(1)))
            metadata["episode"] = str(int(season_episode_match.group(2)))

        # 提取分辨率
        resolution_match = re.search(
            r"(480p|720p|1080p|4K|2160p)", filename, re.IGNORECASE
        )
        if resolution_match:
            metadata["resolution"] = resolution_match.group().lower()

        # 提取编码信息
        codec_match = re.search(
            r"(H\.?264|H\.?265|HEVC|AVC|X264|X265)", filename, re.IGNORECASE
        )
        if codec_match:
            metadata["codec"] = codec_match.group().upper()

        # 提取音频信息
        audio_match = re.search(r"(DTS|AC3|AAC|FLAC|MP3)", filename, re.IGNORECASE)
        if audio_match:
            metadata["audio"] = audio_match.group().upper()

        # 提取发布组信息
        group_match = re.search(r"\[(.*?)\]", filename)
        if group_match:
            metadata["release_group"] = group_match.group(1)

        # 提取标题（移除各种标识符）
        title = re.sub(r"[\[\]].*?[\[\]]", "", filename)  # 移除括号内容
        title = re.sub(
            r"S\d{1,2}E\d{1,2}", "", title, flags=re.IGNORECASE
        )  # 移除季集信息
        title = re.sub(
            r"(480p|720p|1080p|4K|2160p)", "", title, flags=re.IGNORECASE
        )  # 移除分辨率
        title = re.sub(
            r"(H\.?264|H\.?265|HEVC|AVC|X264|X265)", "", title, flags=re.IGNORECASE
        )  # 移除编码
        title = re.sub(
            r"(DTS|AC3|AAC|FLAC|MP3)", "", title, flags=re.IGNORECASE
        )  # 移除音频
        title = re.sub(r"[\[\]()]", "", title)  # 移除括号
        title = re.sub(r"[\.\-_]", " ", title)  # 替换分隔符为空格
        title = re.sub(r"\s+", " ", title).strip()  # 清理多余空格

        metadata["title"] = title

        return metadata

    def organize_file(
        self, file_info: FileInfo, rule: Optional[OrganizationRule] = None
    ) -> Dict[str, Any]:
        """整理单个文件"""
        try:
            # 如果没有指定规则，自动匹配规则
            if rule is None:
                matched_rule = self._find_matching_rule(file_info)
                if matched_rule is None:
                    return {
                        "success": False,
                        "message": "No matching rule found",
                        "file": file_info.name,
                    }
                rule = matched_rule

            # 生成目标路径
            target_path = self._generate_target_path(file_info, rule)

            # 执行文件操作
            result = self._perform_file_action(file_info.path, target_path, rule.action)

            return {
                "success": True,
                "action": rule.action.value,
                "original_path": file_info.path,
                "target_path": target_path,
                "rule_used": rule.name,
                "metadata": file_info.metadata,
            }

        except Exception as e:
            logger.error(f"Error organizing file {file_info.path}: {e}")
            return {"success": False, "message": str(e), "file": file_info.name}

    def _find_matching_rule(self, file_info: FileInfo) -> Optional[OrganizationRule]:
        """查找匹配的整理规则"""
        for rule in self.rules:
            if rule.enabled and rule.match(file_info):
                return rule
        return None

    def _generate_target_path(self, file_info: FileInfo, rule: OrganizationRule) -> str:
        """生成目标路径"""
        # 获取文件扩展名
        ext = Path(file_info.path).suffix

        # 准备模板变量
        metadata = file_info.metadata or {}
        template_vars = metadata.copy()
        template_vars.update(
            {
                "title": metadata.get("title", "Unknown"),
                "year": metadata.get("year", ""),
                "season": metadata.get("season", 1),
                "episode": metadata.get("episode", 1),
                "ext": ext[1:] if ext else "",
                "resolution": metadata.get("resolution", ""),
                "codec": metadata.get("codec", ""),
                "audio": metadata.get("audio", ""),
                "release_group": metadata.get("release_group", ""),
            }
        )

        # 渲染模板
        target_path = rule.target_template
        for key, value in template_vars.items():
            placeholder = f"{{{key}}}"
            if placeholder in target_path:
                target_path = target_path.replace(placeholder, str(value))

        # 确保路径有效
        target_path = re.sub(r'[<>:"|?*]', "_", target_path)  # 移除非法字符
        target_path = re.sub(r"/+", "/", target_path)  # 清理多余斜杠

        return str(self.base_path / target_path)

    def _perform_file_action(
        self, source_path: str, target_path: str, action: FileAction
    ) -> bool:
        """执行文件操作"""
        source = Path(source_path)
        target = Path(target_path)

        # 确保目标目录存在
        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            if action == FileAction.MOVE:
                shutil.move(str(source), str(target))
            elif action == FileAction.COPY:
                shutil.copy2(str(source), str(target))
            elif action == FileAction.LINK:
                if target.exists():
                    target.unlink()
                target.symlink_to(source)
            elif action == FileAction.RENAME:
                source.rename(target)

            return True

        except Exception as e:
            logger.error(
                f"Error performing {action.value} from {source} to {target}: {e}"
            )
            return False

    def batch_organize(self, directory: Optional[str] = None) -> List[Dict[str, Any]]:
        """批量整理目录中的文件"""
        file_infos = self.scan_directory(directory)
        results = []

        for file_info in file_infos:
            result = self.organize_file(file_info)
            results.append(result)

        return results

    def preview_organization(
        self, directory: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """预览整理结果"""
        file_infos = self.scan_directory(directory)
        previews = []

        for file_info in file_infos:
            rule = self._find_matching_rule(file_info)
            if rule:
                target_path = self._generate_target_path(file_info, rule)
                previews.append(
                    {
                        "file": file_info.name,
                        "current_path": file_info.path,
                        "target_path": target_path,
                        "rule": rule.name,
                        "action": rule.action.value,
                        "metadata": file_info.metadata,
                    }
                )

        return previews

    def validate_rules(self) -> List[Dict[str, Any]]:
        """验证所有规则的有效性"""
        validation_results = []

        for rule in self.rules:
            try:
                # 测试正则表达式
                re.compile(rule.pattern)

                # 测试模板变量
                test_vars = {
                    "title": "Test Title",
                    "year": "2023",
                    "season": 1,
                    "episode": 1,
                    "ext": "mp4",
                    "resolution": "1080p",
                    "codec": "H264",
                    "audio": "DTS",
                    "release_group": "TEST",
                }

                target_path = rule.target_template
                for key, value in test_vars.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in target_path:
                        target_path = target_path.replace(placeholder, str(value))

                validation_results.append(
                    {
                        "rule": rule.name,
                        "valid": True,
                        "pattern_valid": True,
                        "template_valid": True,
                        "test_path": target_path,
                    }
                )

            except re.error:
                validation_results.append(
                    {
                        "rule": rule.name,
                        "valid": False,
                        "pattern_valid": False,
                        "template_valid": True,
                        "error": "Invalid regex pattern",
                    }
                )
            except Exception as e:
                validation_results.append(
                    {
                        "rule": rule.name,
                        "valid": False,
                        "pattern_valid": True,
                        "template_valid": False,
                        "error": str(e),
                    }
                )

        return validation_results
