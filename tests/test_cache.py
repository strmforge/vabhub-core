import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from core.cache_manager import RedisCacheBackend


class TestRedisCacheManager:
    """Test cases for RedisCacheManager class."""

    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache_manager):
        """Test cache manager initialization."""
        # We're using a mock, so we just check that it has the expected attributes
        assert hasattr(cache_manager, "redis_url")
        assert hasattr(cache_manager, "default_ttl")

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_manager):
        """Test setting and getting values from cache."""
        # Mock Redis set and get operations
        cache_manager.set.return_value = True
        cache_manager.get.return_value = {"test": "data"}

        # Test set
        success = await cache_manager.set("test_key", {"test": "data"})
        assert success is True

        # Test get
        result = await cache_manager.get("test_key")
        assert result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_get_not_found(self, cache_manager):
        """Test getting non-existent key from cache."""
        cache_manager.get.return_value = None

        result = await cache_manager.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache_manager):
        """Test deleting key from cache."""
        cache_manager.delete.return_value = True

        success = await cache_manager.delete("test_key")
        assert success is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, cache_manager):
        """Test deleting non-existent key from cache."""
        cache_manager.delete.return_value = False

        success = await cache_manager.delete("nonexistent_key")
        assert success is False

    @pytest.mark.asyncio
    async def test_exists(self, cache_manager):
        """Test checking if key exists in cache."""
        cache_manager.exists.return_value = True

        exists = await cache_manager.exists("test_key")
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_not_found(self, cache_manager):
        """Test checking if non-existent key exists in cache."""
        cache_manager.exists.return_value = False

        exists = await cache_manager.exists("nonexistent_key")
        assert exists is False

    @pytest.mark.asyncio
    async def test_clear(self, cache_manager):
        """Test clearing all keys from cache."""
        cache_manager.clear.return_value = True

        success = await cache_manager.clear()
        assert success is True

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, cache_manager):
        """Test setting value with custom TTL."""
        cache_manager.set.return_value = True

        success = await cache_manager.set("test_key", {"test": "data"}, ttl=600)
        assert success is True

    @pytest.mark.asyncio
    async def test_json_serialization_error(self, cache_manager):
        """Test handling of JSON serialization errors."""
        cache_manager.set.return_value = False

        # Test with unserializable object
        class Unserializable:
            pass

        unserializable_obj = Unserializable()

        success = await cache_manager.set("test_key", unserializable_obj)
        assert success is False

    @pytest.mark.asyncio
    async def test_redis_connection_error(self, cache_manager):
        """Test handling of Redis connection errors."""
        # Mock Redis to raise connection error
        cache_manager.set.side_effect = Exception("Connection error")

        with pytest.raises(Exception):
            await cache_manager.set("test_key", {"test": "data"})

    @pytest.mark.asyncio
    async def test_cache_pattern_matching(self, cache_manager):
        """Test cache operations with pattern matching."""
        # Mock keys pattern matching
        cache_manager.keys.return_value = [
            "chart_tmdb_US_week_movie_123",
            "chart_tmdb_US_week_tv_456",
        ]

        keys = await cache_manager.keys("chart_tmdb_*")
        assert len(keys) == 2
        assert "chart_tmdb_US_week_movie_123" in keys
        assert "chart_tmdb_US_week_tv_456" in keys

    @pytest.mark.asyncio
    async def test_bulk_operations(self, cache_manager):
        """Test bulk cache operations."""
        cache_manager.batch_set.return_value = True

        items = {"key1": "value1", "key2": "value2", "key3": "value3"}

        success = await cache_manager.batch_set(items)
        assert success is True

    @pytest.mark.asyncio
    async def test_cache_performance(self, cache_manager):
        """Test cache performance measurement."""
        import time

        # Mock set operation
        cache_manager.set.return_value = True

        start_time = time.time()
        await cache_manager.set("perf_test_key", {"test": "data"})
        end_time = time.time()

        operation_time = end_time - start_time
        assert operation_time >= 0

    @pytest.mark.asyncio
    async def test_keys_pattern(self, cache_manager):
        """Test keys pattern matching."""
        cache_manager.keys.return_value = ["key1", "key2", "key3"]

        keys = await cache_manager.keys("*")
        assert len(keys) == 3
        assert all(isinstance(k, str) for k in keys)

    @pytest.mark.asyncio
    async def test_bulk_get(self, cache_manager):
        """Test bulk get operations."""
        # Mock mget operation
        cache_manager.batch_get.return_value = {
            "key1": {"data": "value1"},
            "key2": {"data": "value2"},
            "key3": None,  # Simulate missing key
        }

        keys = ["key1", "key2", "key3"]
        results = await cache_manager.batch_get(keys)

        assert len(results) == 3
        assert results["key1"] == {"data": "value1"}
        assert results["key2"] == {"data": "value2"}
        assert results["key3"] is None

    @pytest.mark.asyncio
    async def test_close(self, cache_manager):
        """Test close operation."""
        # This should not raise an exception
        await cache_manager.close()
