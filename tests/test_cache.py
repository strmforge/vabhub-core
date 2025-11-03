import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from core.cache import RedisCacheManager


class TestRedisCacheManager:
    """Test cases for RedisCacheManager class."""

    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache_manager):
        """Test cache manager initialization."""
        assert cache_manager.redis_url == "redis://localhost:6379/1"
        assert cache_manager.ttl == 300
        assert cache_manager.redis is not None

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_manager):
        """Test setting and getting values from cache."""
        # Mock Redis set and get operations
        cache_manager.redis.set.return_value = True
        cache_manager.redis.get.return_value = json.dumps({"test": "data"})

        # Test set
        success = await cache_manager.set("test_key", {"test": "data"})
        assert success is True

        # Test get
        result = await cache_manager.get("test_key")
        assert result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_get_not_found(self, cache_manager):
        """Test getting non-existent key from cache."""
        cache_manager.redis.get.return_value = None

        result = await cache_manager.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache_manager):
        """Test deleting key from cache."""
        cache_manager.redis.delete.return_value = 1

        success = await cache_manager.delete("test_key")
        assert success is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, cache_manager):
        """Test deleting non-existent key from cache."""
        cache_manager.redis.delete.return_value = 0

        success = await cache_manager.delete("nonexistent_key")
        assert success is False

    @pytest.mark.asyncio
    async def test_exists(self, cache_manager):
        """Test checking if key exists in cache."""
        cache_manager.redis.exists.return_value = 1

        exists = await cache_manager.exists("test_key")
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_not_found(self, cache_manager):
        """Test checking if non-existent key exists in cache."""
        cache_manager.redis.exists.return_value = 0

        exists = await cache_manager.exists("nonexistent_key")
        assert exists is False

    @pytest.mark.asyncio
    async def test_clear(self, cache_manager):
        """Test clearing all keys from cache."""
        cache_manager.redis.flushdb.return_value = True

        success = await cache_manager.clear()
        assert success is True

    @pytest.mark.asyncio
    async def test_get_stats(self, cache_manager):
        """Test getting cache statistics."""
        cache_manager.redis.dbsize.return_value = 10
        cache_manager.redis.info.return_value = {
            "used_memory": 1024000,
            "connected_clients": 5,
        }

        stats = await cache_manager.get_stats()

        assert "keys_count" in stats
        assert "memory_usage" in stats
        assert "connected_clients" in stats
        assert stats["keys_count"] == 10
        assert stats["memory_usage"] == "1.02 MB"

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, cache_manager):
        """Test setting value with custom TTL."""
        cache_manager.redis.setex.return_value = True

        success = await cache_manager.set("test_key", {"test": "data"}, ttl=600)
        assert success is True

        # Verify setex was called with correct TTL
        cache_manager.redis.setex.assert_called_once()
        args = cache_manager.redis.setex.call_args[0]
        assert args[2] == 600  # TTL in seconds

    @pytest.mark.asyncio
    async def test_json_serialization_error(self, cache_manager):
        """Test handling of JSON serialization errors."""

        # Test with unserializable object
        class Unserializable:
            pass

        unserializable_obj = Unserializable()

        success = await cache_manager.set("test_key", unserializable_obj)
        assert success is False

    @pytest.mark.asyncio
    async def test_json_deserialization_error(self, cache_manager):
        """Test handling of JSON deserialization errors."""
        # Mock Redis to return invalid JSON
        cache_manager.redis.get.return_value = "invalid json"

        result = await cache_manager.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_connection_error(self, cache_manager):
        """Test handling of Redis connection errors."""
        # Mock Redis to raise connection error
        cache_manager.redis.set.side_effect = Exception("Connection error")

        success = await cache_manager.set("test_key", {"test": "data"})
        assert success is False

    @pytest.mark.asyncio
    async def test_cache_pattern_matching(self, cache_manager):
        """Test cache operations with pattern matching."""
        # Mock keys pattern matching
        cache_manager.redis.keys.return_value = [
            b"chart_tmdb_US_week_movie_123",
            b"chart_tmdb_US_week_tv_456",
        ]

        keys = await cache_manager.keys("chart_tmdb_*")
        assert len(keys) == 2
        assert "chart_tmdb_US_week_movie_123" in keys
        assert "chart_tmdb_US_week_tv_456" in keys

    @pytest.mark.asyncio
    async def test_bulk_operations(self, cache_manager):
        """Test bulk cache operations."""
        # Mock pipeline operations
        mock_pipeline = AsyncMock()
        mock_pipeline.set.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [True, True, True]
        cache_manager.redis.pipeline.return_value.__aenter__.return_value = (
            mock_pipeline
        )

        items = {"key1": "value1", "key2": "value2", "key3": "value3"}

        success = await cache_manager.bulk_set(items)
        assert success is True

        # Verify pipeline was used
        assert mock_pipeline.set.call_count == 3

    @pytest.mark.asyncio
    async def test_increment_decrement(self, cache_manager):
        """Test increment and decrement operations."""
        cache_manager.redis.incr.return_value = 2
        cache_manager.redis.decr.return_value = 1

        # Test increment
        new_value = await cache_manager.increment("counter")
        assert new_value == 2

        # Test decrement
        new_value = await cache_manager.decrement("counter")
        assert new_value == 1

    @pytest.mark.asyncio
    async def test_expire_operation(self, cache_manager):
        """Test setting expiration on existing key."""
        cache_manager.redis.expire.return_value = True

        success = await cache_manager.expire("test_key", 600)
        assert success is True

    @pytest.mark.asyncio
    async def test_ttl_operation(self, cache_manager):
        """Test getting TTL of a key."""
        cache_manager.redis.ttl.return_value = 300

        ttl = await cache_manager.ttl("test_key")
        assert ttl == 300

    @pytest.mark.asyncio
    async def test_cache_hit_miss_statistics(self, cache_manager):
        """Test cache hit/miss statistics."""
        # Reset statistics
        cache_manager._hits = 0
        cache_manager._misses = 0

        # Mock get operations
        cache_manager.redis.get.side_effect = [
            json.dumps({"hit": "data"}),  # First call: hit
            None,  # Second call: miss
            json.dumps({"hit2": "data"}),  # Third call: hit
        ]

        # Perform operations
        await cache_manager.get("key1")  # Hit
        await cache_manager.get("key2")  # Miss
        await cache_manager.get("key3")  # Hit

        stats = cache_manager.get_statistics()

        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2 / 3

    @pytest.mark.asyncio
    async def test_cache_performance(self, cache_manager):
        """Test cache performance with multiple operations."""
        import time

        # Mock fast Redis operations
        cache_manager.redis.set.return_value = True
        cache_manager.redis.get.return_value = json.dumps({"test": "data"})

        start_time = time.time()

        # Perform multiple operations
        for i in range(100):
            await cache_manager.set(f"key_{i}", {"value": i})
            await cache_manager.get(f"key_{i}")

        end_time = time.time()

        # Should complete quickly (under 1 second for 200 operations)
        assert (end_time - start_time) < 1.0
