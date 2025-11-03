import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from core.charts import ChartsService, ChartItem


class TestChartsService:
    """Test cases for ChartsService class."""

    @pytest.fixture
    async def charts_service(self, database_manager, cache_manager):
        """Create a charts service instance for testing."""
        config = MagicMock()
        config.CACHE_TTL = 300

        service = ChartsService(config)
        service.db = database_manager
        service.cache = cache_manager
        return service

    @pytest.mark.asyncio
    async def test_charts_service_initialization(self, charts_service):
        """Test charts service initialization."""
        assert charts_service.config is not None
        assert charts_service.db is not None
        assert charts_service.cache is not None
        assert charts_service.cache == {}

    @pytest.mark.asyncio
    async def test_get_charts_data_cached(self, charts_service, sample_chart_data):
        """Test getting charts data from cache."""
        # Mock cache hit
        charts_service.cache.get.return_value = sample_chart_data

        result = await charts_service.get_charts_data(
            source="tmdb", region="US", time_range="week", media_type="movie"
        )

        assert result == sample_chart_data
        # Verify cache was checked
        charts_service.cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_charts_data_database(self, charts_service, sample_chart_data):
        """Test getting charts data from database when cache miss."""
        # Mock cache miss
        charts_service.cache.get.return_value = None
        # Mock database hit
        charts_service.db.get_charts_data.return_value = sample_chart_data

        result = await charts_service.get_charts_data(
            source="tmdb", region="US", time_range="week", media_type="movie"
        )

        assert result == sample_chart_data
        # Verify database was queried
        charts_service.db.get_charts_data.assert_called_once()
        # Verify cache was updated
        charts_service.cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_charts_data_fallback(self, charts_service):
        """Test getting charts data with fallback when both cache and database miss."""
        # Mock cache miss
        charts_service.cache.get.return_value = None
        # Mock database miss
        charts_service.db.get_charts_data.return_value = None

        result = await charts_service.get_charts_data(
            source="tmdb", region="US", time_range="week", media_type="movie"
        )

        # Should return fallback data
        assert result is not None
        assert "items" in result
        assert "total" in result
        assert result["source"] == "tmdb"

    @pytest.mark.asyncio
    async def test_save_charts_data(self, charts_service, sample_chart_data):
        """Test saving charts data."""
        # Mock database save
        charts_service.db.save_charts_data.return_value = "chart_123"
        charts_service.db.save_chart_items.return_value = True

        result = await charts_service.save_charts_data(
            source="tmdb",
            region="US",
            time_range="week",
            media_type="movie",
            chart_data=sample_chart_data["chart_data"],
        )

        assert result == "chart_123"
        # Verify database was called
        charts_service.db.save_charts_data.assert_called_once()
        charts_service.db.save_chart_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_external_charts_success(
        self, charts_service, mock_httpx_client
    ):
        """Test successful external charts data fetch."""
        # Mock successful API response
        mock_response = {
            "results": [
                {
                    "id": 1,
                    "title": "Test Movie",
                    "vote_average": 8.5,
                    "popularity": 1000,
                    "release_date": "2023-01-01",
                    "poster_path": "/poster.jpg",
                }
            ],
            "total_results": 1,
            "total_pages": 1,
        }

        mock_httpx_client.get.return_value.status_code = 200
        mock_httpx_client.get.return_value.json.return_value = mock_response

        result = await charts_service.fetch_external_charts(
            source="tmdb", region="US", time_range="week", media_type="movie"
        )

        assert result is not None
        assert "items" in result
        assert result["items"][0]["title"] == "Test Movie"

    @pytest.mark.asyncio
    async def test_fetch_external_charts_failure(
        self, charts_service, mock_httpx_client
    ):
        """Test external charts data fetch failure."""
        # Mock API failure
        mock_httpx_client.get.return_value.status_code = 500

        result = await charts_service.fetch_external_charts(
            source="tmdb", region="US", time_range="week", media_type="movie"
        )

        # Should return fallback data
        assert result is not None
        assert "items" in result

    @pytest.mark.asyncio
    async def test_generate_fallback_data(self, charts_service):
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

    @pytest.mark.asyncio
    async def test_validate_chart_parameters(self, charts_service):
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

    @pytest.mark.asyncio
    async def test_get_supported_sources(self, charts_service):
        """Test getting supported data sources."""
        sources = charts_service.get_supported_sources()

        expected_sources = ["tmdb", "spotify", "apple_music", "bangumi"]
        for source in expected_sources:
            assert source in sources

    @pytest.mark.asyncio
    async def test_get_supported_regions(self, charts_service):
        """Test getting supported regions."""
        regions = charts_service.get_supported_regions()

        expected_regions = ["US", "CN", "JP", "KR", "GB", "FR", "DE", "CA", "AU", "BR"]
        for region in expected_regions:
            assert region in regions

    @pytest.mark.asyncio
    async def test_get_supported_time_ranges(self, charts_service):
        """Test getting supported time ranges."""
        time_ranges = charts_service.get_supported_time_ranges()

        expected_ranges = ["day", "week", "month", "year", "all"]
        for time_range in expected_ranges:
            assert time_range in time_ranges

    @pytest.mark.asyncio
    async def test_get_supported_media_types(self, charts_service):
        """Test getting supported media types."""
        media_types = charts_service.get_supported_media_types()

        expected_types = ["movie", "tv", "music", "book", "game"]
        for media_type in expected_types:
            assert media_type in media_types

    @pytest.mark.asyncio
    async def test_chart_item_creation(self):
        """Test ChartItem data class."""
        item = ChartItem(
            id=1,
            title="Test Movie",
            type="movie",
            rank=1,
            score=8.5,
            popularity=1000,
            release_date="2023-01-01",
            poster_url="http://example.com/poster.jpg",
            provider="tmdb",
        )

        assert item.id == 1
        assert item.title == "Test Movie"
        assert item.type == "movie"
        assert item.rank == 1
        assert item.score == 8.5
        assert item.popularity == 1000
        assert item.release_date == "2023-01-01"
        assert item.poster_url == "http://example.com/poster.jpg"
        assert item.provider == "tmdb"

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, charts_service):
        """Test cache key generation."""
        key = charts_service._generate_cache_key("tmdb", "US", "week", "movie")

        expected_key = "chart_tmdb_US_week_movie"
        assert key == expected_key

    @pytest.mark.asyncio
    async def test_data_normalization(self, charts_service):
        """Test data normalization for different sources."""
        # Test TMDB data normalization
        tmdb_data = {
            "results": [
                {
                    "id": 1,
                    "title": "Test Movie",
                    "vote_average": 8.5,
                    "popularity": 1000,
                    "release_date": "2023-01-01",
                    "poster_path": "/poster.jpg",
                }
            ],
            "total_results": 1,
            "total_pages": 1,
        }

        normalized = charts_service._normalize_tmdb_data(tmdb_data, "movie")

        assert normalized["items"][0]["title"] == "Test Movie"
        assert normalized["items"][0]["score"] == 8.5
        assert normalized["items"][0]["provider"] == "tmdb"

    @pytest.mark.asyncio
    async def test_error_handling(self, charts_service):
        """Test error handling in charts service."""
        # Mock database exception
        charts_service.db.get_charts_data.side_effect = Exception("Database error")

        # Should handle exception gracefully and return fallback data
        result = await charts_service.get_charts_data(
            source="tmdb", region="US", time_range="week", media_type="movie"
        )

        assert result is not None
        assert "items" in result

    @pytest.mark.asyncio
    async def test_performance_benchmark(self, charts_service):
        """Test charts service performance."""
        import time

        # Mock fast responses
        charts_service.cache.get.return_value = None
        charts_service.db.get_charts_data.return_value = None

        start_time = time.time()

        # Perform multiple operations
        for i in range(10):
            await charts_service.get_charts_data(
                source="tmdb", region="US", time_range="week", media_type="movie"
            )

        end_time = time.time()

        # Should complete quickly (under 2 seconds for 10 operations)
        assert (end_time - start_time) < 2.0
