"""
元数据管理器测试模块
"""

import pytest
import asyncio
from datetime import datetime

from core.metadata_manager import (
    MediaType,
    MediaEntity,
    Movie,
    TVShow,
    Season,
    Episode,
    TMDBProvider,
    MetadataManager,
)


class TestMediaEntities:
    """测试媒体实体"""

    def test_movie_creation(self):
        """测试电影实体创建"""
        movie = Movie(
            id="123",
            title="测试电影",
            original_title="Test Movie",
            overview="测试描述",
            release_date=datetime(2023, 1, 1),
            rating=8.5,
            vote_count=1000,
        )

        assert movie.type == MediaType.MOVIE
        assert movie.title == "测试电影"
        assert movie.rating == 8.5
        assert movie.vote_count == 1000

    def test_tv_show_creation(self):
        """测试电视剧实体创建"""
        tv_show = TVShow(
            id="456", title="测试电视剧", number_of_seasons=3, number_of_episodes=24
        )

        assert tv_show.type == MediaType.TV_SHOW
        assert tv_show.title == "测试电视剧"
        assert tv_show.number_of_seasons == 3
        assert tv_show.number_of_episodes == 24


class TestTMDBProvider:
    """测试TMDb提供者"""

    def test_provider_creation(self):
        """测试提供者创建"""
        provider = TMDBProvider("test_api_key")

        assert provider.api_key == "test_api_key"
        assert provider.base_url == "https://api.themoviedb.org/3"

    def test_parse_movie(self):
        """测试电影数据解析"""
        provider = TMDBProvider("test_api_key")

        movie_data = {
            "id": 123,
            "title": "Test Movie",
            "original_title": "Original Test Movie",
            "overview": "Test overview",
            "poster_path": "/test.jpg",
            "backdrop_path": "/backdrop.jpg",
            "release_date": "2023-01-01",
            "genres": [{"id": 1, "name": "Action"}],
            "vote_average": 8.5,
            "vote_count": 1000,
            "runtime": 120,
            "tagline": "Test tagline",
            "budget": 1000000,
            "revenue": 2000000,
            "production_companies": [{"id": 1, "name": "Test Studio"}],
            "production_countries": [{"iso_3166_1": "US", "name": "United States"}],
            "spoken_languages": [{"iso_639_1": "en", "name": "English"}],
        }

        movie = provider._parse_movie(movie_data)

        assert movie.id == "123"
        assert movie.title == "Test Movie"
        assert movie.original_title == "Original Test Movie"
        assert movie.rating == 8.5
        assert movie.vote_count == 1000
        assert movie.runtime == 120
        assert movie.budget == 1000000
        assert movie.revenue == 2000000
        assert "Action" in movie.genres
        assert "Test Studio" in movie.production_companies


class TestMetadataManager:
    """测试元数据管理器"""

    def test_manager_creation(self):
        """测试管理器创建"""
        config = {
            "tmdb_api_key": "test_key",
            "douban_enabled": False,
            "provider_priority": ["tmdb"],
        }

        manager = MetadataManager(config)

        assert "tmdb" in manager.providers
        assert manager.priority == ["tmdb"]
        assert manager.cache_dir == "./cache"

    def test_manager_without_api_key(self):
        """测试没有API密钥的管理器创建"""
        config = {"tmdb_api_key": "", "douban_enabled": False}

        manager = MetadataManager(config)

        # 没有API密钥时不应该创建提供者
        assert len(manager.providers) == 0


@pytest.mark.asyncio
async def test_metadata_integration():
    """集成测试"""
    config = {
        "tmdb_api_key": "test_key",
        "douban_enabled": False,
        "provider_priority": ["tmdb"],
    }

    manager = MetadataManager(config)

    # 测试搜索功能（使用mock数据）
    # 实际使用中应该使用mock来测试网络请求

    assert len(manager.providers) == 1
    assert "tmdb" in manager.providers
    assert manager.priority == ["tmdb"]


class TestSeasonAndEpisode:
    """测试季和剧集实体"""

    def test_season_creation(self):
        """测试季实体创建"""
        season = Season(
            id="789", tv_show_id="456", season_number=1, title="第一季", episode_count=8
        )

        assert season.tv_show_id == "456"
        assert season.season_number == 1
        assert season.title == "第一季"
        assert season.episode_count == 8

    def test_episode_creation(self):
        """测试剧集实体创建"""
        episode = Episode(
            id="101",
            season_id="789",
            tv_show_id="456",
            episode_number=1,
            title="第一集",
            runtime=45,
        )

        assert episode.season_id == "789"
        assert episode.tv_show_id == "456"
        assert episode.episode_number == 1
        assert episode.title == "第一集"
        assert episode.runtime == 45
