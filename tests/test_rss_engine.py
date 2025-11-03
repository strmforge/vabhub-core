"""
RSS引擎测试模块
"""

import pytest
import asyncio
from datetime import datetime

from core.rss_engine import RSSItem, RSSRule, DefaultRSSParser, RSSFilter, RSSManager


class TestRSSItem:
    """测试RSS条目模型"""

    def test_rss_item_creation(self):
        """测试RSS条目创建"""
        item = RSSItem(
            title="Test Movie 2023 BluRay 1080p H264 DTS-HD",
            link="http://example.com",
            guid="test-guid",
        )

        assert item.title == "Test Movie 2023 BluRay 1080p H264 DTS-HD"
        assert item.link == "http://example.com"
        assert item.guid == "test-guid"
        assert isinstance(item.hash_id, str)
        assert len(item.hash_id) == 32


class TestRSSRule:
    """测试RSS规则"""

    def test_rule_creation(self):
        """测试规则创建"""
        rule = RSSRule(
            name="电影规则",
            include_keywords=["BluRay"],
            exclude_keywords=["Sample"],
            min_size=1.0,
            max_size=50.0,
            resolutions=["1080p"],
            codecs=["H264"],
        )

        assert rule.name == "电影规则"
        assert "BluRay" in rule.include_keywords
        assert "Sample" in rule.exclude_keywords
        assert rule.min_size == 1.0
        assert rule.max_size == 50.0

    def test_rule_matching(self):
        """测试规则匹配"""
        rule = RSSRule(
            name="测试规则",
            include_keywords=["BluRay"],
            exclude_keywords=["Sample"],
            min_size=1.0,
            max_size=50.0,
            resolutions=["1080p"],
        )

        # 匹配的条目
        matching_item = RSSItem(
            title="Test Movie BluRay 1080p",
            link="http://example.com",
            guid="guid1",
            size=10.0,
            resolution="1080p",
        )

        # 不匹配的条目（包含排除关键词）
        non_matching_item1 = RSSItem(
            title="Test Movie BluRay Sample",
            link="http://example.com",
            guid="guid2",
            size=10.0,
            resolution="1080p",
        )

        # 不匹配的条目（大小超出范围）
        non_matching_item2 = RSSItem(
            title="Test Movie BluRay 1080p",
            link="http://example.com",
            guid="guid3",
            size=0.5,
            resolution="1080p",
        )

        assert rule.match(matching_item) is True
        assert rule.match(non_matching_item1) is False
        assert rule.match(non_matching_item2) is False


class TestDefaultRSSParser:
    """测试默认RSS解析器"""

    def test_parse_item_info(self):
        """测试条目信息解析"""
        parser = DefaultRSSParser()

        item = RSSItem(
            title="Test Movie 2023 BluRay 1080p H264 DTS-HD MA 5.1 10GB S01E01",
            link="http://example.com",
        )

        parsed_item = parser.parse_item_info(item)

        assert parsed_item.size == 10.0
        assert parsed_item.resolution == "1080p"
        assert parsed_item.codec == "H264"
        assert parsed_item.audio == "DTS-HD"
        assert parsed_item.season == 1
        assert parsed_item.episode == 1


class TestRSSFilter:
    """测试RSS过滤器"""

    def test_filter_duplicates(self):
        """测试去重功能"""
        filter = RSSFilter()

        item1 = RSSItem(
            title="Test Movie 1",
            link="http://example.com",
            guid="guid1",
            enclosure_url="url1",
        )

        item2 = RSSItem(
            title="Test Movie 1",
            link="http://example.com",
            guid="guid1",
            enclosure_url="url1",
        )

        items = [item1, item2]
        rules = [RSSRule(name="test")]

        filtered = filter.filter_items(items, rules)

        assert len(filtered) == 1
        assert filtered[0].title == "Test Movie 1"


class TestRSSManager:
    """测试RSS管理器"""

    def test_manager_creation(self):
        """测试管理器创建"""
        manager = RSSManager()

        assert isinstance(manager.parser, DefaultRSSParser)
        assert isinstance(manager.filter, RSSFilter)
        assert manager.feeds == {}
        assert manager.rules == []

    def test_add_feed_and_rule(self):
        """测试添加源和规则"""
        manager = RSSManager()

        manager.add_feed("测试源", "http://example.com/rss", 3600)

        rule = RSSRule(name="测试规则")
        manager.add_rule(rule)

        assert "测试源" in manager.feeds
        assert manager.feeds["测试源"]["url"] == "http://example.com/rss"
        assert len(manager.rules) == 1
        assert manager.rules[0].name == "测试规则"


@pytest.mark.asyncio
async def test_rss_integration():
    """集成测试"""
    manager = RSSManager()

    # 添加测试规则
    rule = RSSRule(
        name="集成测试规则", include_keywords=["Test"], min_size=0.0, max_size=1000.0
    )
    manager.add_rule(rule)

    # 注意：这里不实际抓取网络，只是测试管理器功能
    # 实际使用中应该使用mock来测试网络请求

    assert len(manager.rules) == 1
    assert manager.rules[0].name == "集成测试规则"
