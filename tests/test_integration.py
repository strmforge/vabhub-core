import pytest
import json
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from core.api import VabHubAPI
from core.config import Config

# Create test app instance
config = Config()
api = VabHubAPI(config)
app = api.get_app()
from core.database import DatabaseManager
from core.cache import RedisCacheManager
from core.charts import ChartsService


class TestIntegration:
    """Integration tests for VabHub Core components."""

    @pytest.fixture
    async def integration_setup(self, temp_db_path):
        """Setup for integration tests."""
        # Setup database
        db_url = f"sqlite:///{temp_db_path}"
        db = DatabaseManager(db_url)
        await db.initialize()
        
        # Setup cache (mocked)
        with patch('core.cache.redis.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            cache = RedisCacheManager("redis://localhost:6379/1", 300)
            
            # Setup charts service
            config = type('Config', (), {
                'CACHE_TTL': 300,
                'SECRET_KEY': 'test-secret-key',
                'ALGORITHM': 'HS256',
                'ACCESS_TOKEN_EXPIRE_MINUTES': 30
            })()
            
            charts_service = ChartsService(config)
            charts_service.db = db
            charts_service.cache = cache
            
            yield {
                'db': db,
                'cache': cache,
                'charts_service': charts_service,
                'client': TestClient(app)
            }
            
            await db.close()

    @pytest.mark.asyncio
    async def test_full_charts_workflow(self, integration_setup):
        """Test complete charts workflow from API to database."""
        db = integration_setup['db']
        cache = integration_setup['cache']
        charts_service = integration_setup['charts_service']
        client = integration_setup['client']
        
        # Mock external API call
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_response = {
                "results": [
                    {
                        "id": 1,
                        "title": "Integration Test Movie",
                        "vote_average": 8.5,
                        "popularity": 1000,
                        "release_date": "2023-01-01",
                        "poster_path": "/poster.jpg"
                    }
                ],
                "total_results": 1,
                "total_pages": 1
            }
            
            mock_instance.get.return_value.status_code = 200
            mock_instance.get.return_value.json.return_value = mock_response
            
            # Test API endpoint
            response = client.get("/api/charts?source=tmdb&region=US&time_range=week&media_type=movie")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert 'items' in data
            assert 'total' in data
            assert data['source'] == 'tmdb'
            
            # Verify data was saved to database
            db_data = await db.get_charts_data('tmdb', 'US', 'week', 'movie')
            assert db_data is not None
            
            # Verify cache was updated
            cache.set.assert_called()

    @pytest.mark.asyncio
    async def test_charts_refresh_integration(self, integration_setup):
        """Test charts refresh integration."""
        client = integration_setup['client']
        
        # Mock external API for refresh
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_response = {
                "results": [
                    {
                        "id": 1,
                        "title": "Refreshed Movie",
                        "vote_average": 9.0,
                        "popularity": 1500,
                        "release_date": "2023-02-01",
                        "poster_path": "/new_poster.jpg"
                    }
                ],
                "total_results": 1,
                "total_pages": 1
            }
            
            mock_instance.get.return_value.status_code = 200
            mock_instance.get.return_value.json.return_value = mock_response
            
            # Test refresh endpoint
            response = client.post("/api/charts/refresh?source=tmdb&region=US&time_range=week&media_type=movie")
            
            assert response.status_code == 200
            data = response.json()
            
            assert 'message' in data
            assert 'success' in data
            assert data['success'] is True

    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(self, integration_setup):
        """Test handling of concurrent requests."""
        client = integration_setup['client']
        
        # Create multiple concurrent requests
        async def make_request():
            return client.get("/api/charts?source=tmdb&region=US&time_range=week&media_type=movie")
        
        # Run concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert 'items' in data

    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, integration_setup):
        """Test error recovery in integration scenarios."""
        client = integration_setup['client']
        
        # Mock database failure
        with patch('core.database.DatabaseManager.get_charts_data') as mock_db:
            mock_db.side_effect = Exception("Database temporarily unavailable")
            
            # API should still return fallback data
            response = client.get("/api/charts?source=tmdb&region=US&time_range=week&media_type=movie")
            
            assert response.status_code == 200
            data = response.json()
            assert 'items' in data
            assert data['source'] == 'tmdb'

    @pytest.mark.asyncio
    async def test_cache_database_synchronization(self, integration_setup):
        """Test cache and database synchronization."""
        db = integration_setup['db']
        cache = integration_setup['cache']
        charts_service = integration_setup['charts_service']
        
        # Save data to database
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        chart_id = await db.save_charts_data(
            source='tmdb',
            region='US',
            time_range='week',
            media_type='movie',
            chart_data=json.dumps({'items': [], 'total': 0}),
            expires_at=expires_at
        )
        
        # Get data through service (should populate cache)
        cache.get.return_value = None  # Force cache miss
        
        data = await charts_service.get_charts_data('tmdb', 'US', 'week', 'movie')
        
        assert data is not None
        
        # Verify cache was populated
        cache.set.assert_called()
        
        # Now test cache hit
        cache.get.return_value = data
        
        cached_data = await charts_service.get_charts_data('tmdb', 'US', 'week', 'movie')
        
        assert cached_data == data
        # Verify cache was used for the second call
        cache.get.assert_called()

    @pytest.mark.asyncio
    async def test_performance_integration(self, integration_setup):
        """Test performance under load."""
        import time
        
        client = integration_setup['client']
        
        start_time = time.time()
        
        # Make multiple API calls
        for i in range(20):
            response = client.get("/api/charts?source=tmdb&region=US&time_range=week&media_type=movie")
            assert response.status_code == 200
        
        end_time = time.time()
        
        # Should complete within reasonable time
        assert (end_time - start_time) < 5.0  # 20 requests in under 5 seconds

    @pytest.mark.asyncio
    async def test_data_consistency(self, integration_setup):
        """Test data consistency across components."""
        db = integration_setup['db']
        cache = integration_setup['cache']
        charts_service = integration_setup['charts_service']
        
        # Create test data
        test_data = {
            'items': [
                {
                    'id': 1,
                    'title': 'Consistency Test',
                    'type': 'movie',
                    'rank': 1,
                    'score': 8.5,
                    'popularity': 1000,
                    'release_date': '2023-01-01',
                    'poster_url': 'http://example.com/poster.jpg',
                    'provider': 'tmdb'
                }
            ],
            'total': 1,
            'page': 1,
            'total_pages': 1,
            'source': 'tmdb',
            'region': 'US',
            'time_range': 'week',
            'media_type': 'movie'
        }
        
        # Save to cache
        await cache.set('chart_tmdb_US_week_movie', test_data)
        
        # Verify service returns same data
        cache.get.return_value = test_data
        service_data = await charts_service.get_charts_data('tmdb', 'US', 'week', 'movie')
        
        assert service_data == test_data
        
        # Save to database
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        await db.save_charts_data(
            source='tmdb',
            region='US',
            time_range='week',
            media_type='movie',
            chart_data=json.dumps(test_data),
            expires_at=expires_at
        )
        
        # Verify database returns consistent data
        db_data = await db.get_charts_data('tmdb', 'US', 'week', 'movie')
        assert db_data is not None
        
        # Compare key fields
        db_chart_data = json.loads(db_data['chart_data'])
        assert db_chart_data['total'] == test_data['total']
        assert db_chart_data['source'] == test_data['source']

    @pytest.mark.asyncio
    async def test_security_integration(self, integration_setup):
        """Test security aspects in integration."""
        client = integration_setup['client']
        
        # Test various security headers
        response = client.get("/")
        
        security_headers = [
            'x-content-type-options',
            'x-frame-options',
            'x-xss-protection'
        ]
        
        for header in security_headers:
            if header in response.headers:
                assert response.headers[header] is not None
        
        # Test CORS
        response = client.options("/api/charts")
        assert 'access-control-allow-origin' in response.headers

    @pytest.mark.asyncio
    async def test_error_scenarios_integration(self, integration_setup):
        """Test various error scenarios."""
        client = integration_setup['client']
        
        # Test invalid parameters
        response = client.get("/api/charts?source=invalid&region=XX&time_range=invalid&media_type=invalid")
        assert response.status_code == 422
        
        # Test missing parameters
        response = client.get("/api/charts")
        assert response.status_code == 422
        
        # Test non-existent endpoint
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        
        # Test malformed requests
        response = client.post("/api/charts/refresh", data="invalid json")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_monitoring_integration(self, integration_setup):
        """Test monitoring and health checks."""
        client = integration_setup['client']
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'version' in data
        
        # Test metrics endpoint (if implemented)
        response = client.get("/metrics")
        # Should either return 200 or 404 if not implemented
        assert response.status_code in [200, 404]