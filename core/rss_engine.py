"""
RSS引擎模块 - 基于MoviePilot参考实现
支持多源RSS抓取、规则过滤、去重等功能
"""

import asyncio
import hashlib
from .logging_config import get_logger
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse

import aiohttp
import feedparser
from pydantic import BaseModel, Field


class RSSItem(BaseModel):
    """RSS条目模型"""

    title: str
    link: str
    description: str = ""
    pub_date: Optional[datetime] = None
    enclosure_url: str = ""
    enclosure_type: str = ""
    enclosure_length: int = 0
    guid: str = ""
    source: str = ""

    # 解析后的字段
    size: float = 0  # GB
    resolution: str = ""  # 分辨率
    codec: str = ""  # 编码
    audio: str = ""  # 音频
    season: int = 0  # 季
    episode: int = 0  # 集

    @property
    def hash_id(self) -> str:
        """生成唯一hash标识"""
        content = f"{self.title}_{self.guid}_{self.enclosure_url}"
        return hashlib.md5(content.encode()).hexdigest()


class RSSRule(BaseModel):
    """RSS规则模型"""

    name: str
    include_keywords: List[str] = []
    exclude_keywords: List[str] = []
    min_size: float = 0  # GB
    max_size: float = 1000  # GB
    resolutions: List[str] = []  # 支持的分辨率
    codecs: List[str] = []  # 支持的编码
    audio_formats: List[str] = []  # 支持的音频格式

    def match(self, item: RSSItem) -> bool:
        """检查条目是否匹配规则"""
        # 大小检查
        if not (self.min_size <= item.size <= self.max_size):
            return False

        # 分辨率检查
        if self.resolutions and item.resolution not in self.resolutions:
            return False

        # 编码检查
        if self.codecs and item.codec not in self.codecs:
            return False

        # 音频检查
        if self.audio_formats and item.audio not in self.audio_formats:
            return False

        # 关键词包含检查
        title_lower = item.title.lower()
        if self.include_keywords:
            if not any(
                keyword.lower() in title_lower for keyword in self.include_keywords
            ):
                return False

        # 关键词排除检查
        if self.exclude_keywords:
            if any(keyword.lower() in title_lower for keyword in self.exclude_keywords):
                return False

        return True


class RSSParser(ABC):
    """RSS解析器抽象类"""

    @abstractmethod
    async def parse_feed(self, feed_url: str) -> List[RSSItem]:
        """解析RSS源"""
        pass

    @abstractmethod
    def parse_item_info(self, item: RSSItem) -> RSSItem:
        """解析条目详细信息"""
        pass


class DefaultRSSParser(RSSParser):
    """默认RSS解析器"""

    # 分辨率映射
    RESOLUTION_PATTERNS = {
        "2160p": ["2160p", "4k", "uhd"],
        "1080p": ["1080p", "1080"],
        "720p": ["720p", "720"],
        "480p": ["480p", "480"],
    }

    # 编码映射
    CODEC_PATTERNS = {
        "H265": ["h265", "hevc", "x265"],
        "H264": ["h264", "x264", "avc"],
        "AV1": ["av1"],
    }

    # 音频格式映射
    AUDIO_PATTERNS = {
        "DTS-HD": ["dts-hd", "dtshd"],
        "DTS": ["dts"],
        "Dolby Atmos": ["atmos"],
        "Dolby Digital": ["ac3", "dd", "dolbydigital"],
        "AAC": ["aac"],
        "FLAC": ["flac"],
    }

    # 大小解析正则
    SIZE_PATTERN = r"(\d+\.?\d*)\s*(GB|MB|gb|mb)"

    # 季集解析正则
    SEASON_PATTERN = r"[Ss](\d+)"
    EPISODE_PATTERN = r"[Ee](\d+)"

    async def parse_feed(self, feed_url: str) -> List[RSSItem]:
        """解析RSS源"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(feed_url) as response:
                    if response.status != 200:
                        logging.error(f"RSS feed fetch failed: {response.status}")
                        return []

                    content = await response.text()
                    feed = feedparser.parse(content)

                    items = []
                    for entry in feed.entries:
                        item = RSSItem(
                            title=entry.get("title", ""),
                            link=entry.get("link", ""),
                            description=entry.get("description", ""),
                            guid=entry.get("id", entry.get("link", "")),
                            source=feed_url,
                        )

                        # 解析发布时间
                        if "published" in entry:
                            try:
                                item.pub_date = datetime.fromisoformat(
                                    entry.published.replace("Z", "+00:00")
                                )
                            except:
                                pass

                        # 解析附件信息
                        if "enclosures" in entry and entry.enclosures:
                            enclosure = entry.enclosures[0]
                            item.enclosure_url = enclosure.get("href", "")
                            item.enclosure_type = enclosure.get("type", "")
                            item.enclosure_length = int(enclosure.get("length", 0))

                        # 解析详细信息
                        item = self.parse_item_info(item)
                        items.append(item)

                    return items

        except Exception as e:
            logging.error(f"RSS parsing error: {e}")
            return []

    def parse_item_info(self, item: RSSItem) -> RSSItem:
        """解析条目详细信息"""
        title_lower = item.title.lower()

        # 解析大小
        size_match = re.search(self.SIZE_PATTERN, item.title)
        if size_match:
            size_value = float(size_match.group(1))
            unit = size_match.group(2).lower()
            if unit == "gb":
                item.size = size_value
            elif unit == "mb":
                item.size = size_value / 1024

        # 解析分辨率
        for resolution, patterns in self.RESOLUTION_PATTERNS.items():
            if any(pattern in title_lower for pattern in patterns):
                item.resolution = resolution
                break

        # 解析编码
        for codec, patterns in self.CODEC_PATTERNS.items():
            if any(pattern in title_lower for pattern in patterns):
                item.codec = codec
                break

        # 解析音频
        for audio, patterns in self.AUDIO_PATTERNS.items():
            if any(pattern in title_lower for pattern in patterns):
                item.audio = audio
                break

        # 解析季集
        season_match = re.search(self.SEASON_PATTERN, item.title)
        if season_match:
            item.season = int(season_match.group(1))

        episode_match = re.search(self.EPISODE_PATTERN, item.title)
        if episode_match:
            item.episode = int(episode_match.group(1))

        return item


class RSSFilter:
    """RSS过滤器"""

    def __init__(self):
        self.seen_items: Set[str] = set()

    def filter_items(self, items: List[RSSItem], rules: List[RSSRule]) -> List[RSSItem]:
        """过滤RSS条目"""
        filtered_items = []

        for item in items:
            # 去重检查
            if item.hash_id in self.seen_items:
                continue

            # 规则匹配
            matched = False
            for rule in rules:
                if rule.match(item):
                    matched = True
                    break

            if matched:
                filtered_items.append(item)
                self.seen_items.add(item.hash_id)

        return filtered_items


class RSSManager:
    """RSS管理器"""

    def __init__(self):
        self.parser = DefaultRSSParser()
        self.filter = RSSFilter()
        self.feeds: Dict[str, Dict[str, Any]] = {}
        self.rules: List[RSSRule] = []

    def add_feed(self, name: str, url: str, interval: int = 3600):
        """添加RSS源"""
        self.feeds[name] = {"url": url, "interval": interval, "last_fetch": None}

    def add_rule(self, rule: RSSRule):
        """添加规则"""
        self.rules.append(rule)

    async def fetch_all_feeds(self) -> List[RSSItem]:
        """抓取所有RSS源"""
        all_items = []

        tasks = []
        for name, feed_info in self.feeds.items():
            tasks.append(self.fetch_feed(name, feed_info["url"]))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_items.extend(result)

        # 过滤条目
        filtered_items = self.filter.filter_items(all_items, self.rules)

        return filtered_items

    async def fetch_feed(self, name: str, url: str) -> List[RSSItem]:
        """抓取单个RSS源"""
        try:
            logging.info(f"Fetching RSS feed: {name}")
            items = await self.parser.parse_feed(url)
            logging.info(f"Fetched {len(items)} items from {name}")
            return items
        except Exception as e:
            logging.error(f"Failed to fetch RSS feed {name}: {e}")
            return []


# 示例规则配置
DEFAULT_RULES = [
    RSSRule(
        name="电影规则",
        include_keywords=["BluRay", "WEB-DL"],
        exclude_keywords=["Sample", "Trailer"],
        min_size=1.0,
        max_size=50.0,
        resolutions=["2160p", "1080p"],
        codecs=["H265", "H264"],
        audio_formats=["DTS-HD", "Dolby Atmos", "Dolby Digital"],
    ),
    RSSRule(
        name="电视剧规则",
        include_keywords=["S\d+", "E\d+"],
        exclude_keywords=["Sample", "Trailer"],
        min_size=0.5,
        max_size=10.0,
        resolutions=["1080p", "720p"],
        codecs=["H265", "H264"],
        audio_formats=["AAC", "Dolby Digital"],
    ),
]
