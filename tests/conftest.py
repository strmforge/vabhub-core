import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from core.config import Config
from core.database import DatabaseManager
from core.cache import RedisCacheManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        yield tmp.name
    os.unlink(tmp.name)


@pytest.fixture
async def test_config():
    """Create a test configuration."""
    config = Config()
    config.DATABASE_URL = "sqlite:///test.db"
    config.REDIS_URL = "redis://localhost:6379/1"
    config.CACHE_TTL = 300
    config.SECRET_KEY = "test-secret-key"
    config.ALGORITHM = "HS256"
    config.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    return config


@pytest.fixture
async def database_manager(temp_db_path):
    """Create a database manager for testing."""
    db_url = f"sqlite:///{temp_db_path}"
    db = DatabaseManager(db_url)
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
async def cache_manager():
    """Create a mock cache manager for testing."""
    with patch('core.cache.redis.Redis') as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis.return_value = mock_redis_instance
        
        cache = RedisCacheManager("redis://localhost:6379/1", 300)
        yield cache


@pytest.fixture
def mock_httpx_client():
    """Create a mock HTTPX client for testing external API calls."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_requests():
    """Create a mock requests module for testing."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def sample_chart_data():
    """Sample chart data for testing."""
    return {
        "source": "tmdb",
        "region": "US",
        "time_range": "week",
        "media_type": "movie",
        "chart_data": {
            "items": [
                {
                    "id": 1,
                    "title": "Test Movie",
                    "type": "movie",
                    "rank": 1,
                    "score": 8.5,
                    "popularity": 1000,
                    "release_date": "2023-01-01",
                    "poster_url": "http://example.com/poster.jpg",
                    "provider": "tmdb"
                }
            ],
            "total": 1,
            "page": 1,
            "total_pages": 1
        }
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "password": "testpassword",
        "email": "test@example.com",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_auth_token():
    """Sample JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTYxNzI5NjAwMH0.test_signature"


@pytest.fixture
def mock_jwt():
    """Mock JWT functions for testing."""
    with patch('core.auth.jwt') as mock_jwt:
        mock_jwt.encode.return_value = "mock_token"
        mock_jwt.decode.return_value = {"sub": "testuser", "exp": 1617296000}
        yield mock_jwt