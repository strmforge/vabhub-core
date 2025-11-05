import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from core.charts import ChartsService, ChartItem


class TestChartsService:
    """Test cases for ChartsService class."""

    @pytest.fixture
    def charts_service(self):
        """Create a charts service instance for testing."""
        config = MagicMock()
        config.CACHE_TTL = 300

        service = ChartsService(config)
        return service

    def test_charts_service_initialization(self, charts_service):
        """Test charts service initialization."""
        assert charts_service.config is not None

    def test_generate_fallback_data(self, charts_service):
        """Test fallback data generation."""
        result = charts_service.generate_fallback_data(
            source="tmdb", region="US", time_range="week", media_type="movie"
        )

        assert result is not None
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "total_pages" in result
        assert result["source"] == "tmdb"
        assert result["region"] == "US"
        assert result["time_range"] == "week"
        assert result["media_type"] == "movie"

    def test_validate_chart_parameters(self, charts_service):
        """Test chart parameters validation."""
        # Test valid parameters
        assert charts_service.validate_parameters("tmdb", "US", "week", "movie") is True

        # Test invalid source
        assert (
            charts_service.validate_parameters("invalid", "US", "week", "movie")
            is False
        )

        # Test invalid region
        assert (
            charts_service.validate_parameters("tmdb", "XX", "week", "movie") is False
        )

        # Test invalid time range
        assert (
            charts_service.validate_parameters("tmdb", "US", "invalid", "movie")
            is False
        )

        # Test invalid media type
        assert (
            charts_service.validate_parameters("tmdb", "US", "week", "invalid") is False
        )

    def test_get_supported_sources(self, charts_service):
        """Test getting supported data sources."""
        sources = charts_service.get_supported_sources()

        expected_sources = ["tmdb", "spotify", "apple_music", "bangumi"]
        for source in expected_sources:
            assert source in sources

    def test_get_supported_regions(self, charts_service):
        """Test getting supported regions."""
        regions = charts_service.get_supported_regions()

        expected_regions = ["US", "GB", "JP", "KR", "CN"]
        for region in expected_regions:
            assert region in regions

    def test_get_supported_time_ranges(self, charts_service):
        """Test getting supported time ranges."""
        time_ranges = charts_service.get_supported_time_ranges()

        expected_ranges = ["day", "week", "month", "year"]
        for time_range in expected_ranges:
            assert time_range in time_ranges

    def test_get_supported_media_types(self, charts_service):
        """Test getting supported media types."""
        media_types = charts_service.get_supported_media_types()

        expected_types = ["movie", "tv", "music", "anime", "all"]
        for media_type in expected_types:
            assert media_type in media_types

    def test_chart_item_creation(self):
        """Test chart item creation."""
        chart_item_data = {
            "id": "1",
            "title": "Test Movie",
            "type": "movie",
            "rank": 1,
            "score": 8.5,
            "popularity": 1000,
            "release_date": "2023-01-01",
            "poster_url": "http://example.com/poster.jpg",
            "provider": "tmdb",
            "region": "US",
            "time_range": "week",
        }

        chart_item = ChartItem(**chart_item_data)
        assert chart_item.id == "1"
        assert chart_item.title == "Test Movie"
        assert chart_item.type == "movie"
        assert chart_item.rank == 1
        assert chart_item.score == 8.5
        assert chart_item.popularity == 1000
        assert chart_item.release_date == "2023-01-01"
        assert chart_item.poster_url == "http://example.com/poster.jpg"
        assert chart_item.provider == "tmdb"
        assert chart_item.region == "US"
        assert chart_item.time_range == "week"

    def test_cache_key_generation(self, charts_service):
        """Test cache key generation."""
        cache_key = charts_service._generate_cache_key(
            "tmdb", "US", "week", "movie", 10
        )
        assert cache_key == "tmdb:US:week:movie:10"

    def test_data_normalization(self, charts_service):
        """Test data normalization."""
        raw_data = {
            "title": "test movie",
            "popularity": "1000",
            "score": "8.5",
        }

        normalized_data = charts_service._normalize_tmdb_data(raw_data)
        assert normalized_data["title"] == "Test Movie"
        assert normalized_data["popularity"] == 1000
        assert normalized_data["score"] == 8.5
