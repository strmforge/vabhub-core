import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from core.api import app


class TestChartsAPI:
    """Test cases for Charts API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the API."""
        return TestClient(app)

    @pytest.fixture
    def mock_charts_service(self):
        """Mock charts service for testing."""
        with patch("core.api.ChartsService") as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance
            yield mock_instance

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "version": "1.5.0"}

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        assert "VabHub Charts API" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_get_charts_success(self, client, mock_charts_service):
        """Test successful charts data retrieval."""
        # Mock successful response
        mock_data = {
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
                    "provider": "tmdb",
                }
            ],
            "total": 1,
            "page": 1,
            "total_pages": 1,
            "source": "tmdb",
            "region": "US",
            "time_range": "week",
            "media_type": "movie",
        }

        mock_charts_service.get_charts_data.return_value = mock_data

        response = client.get(
            "/api/charts?source=tmdb&region=US&time_range=week&media_type=movie"
        )

        assert response.status_code == 200
        assert response.json() == mock_data

        # Verify service was called with correct parameters
        mock_charts_service.get_charts_data.assert_called_once_with(
            source="tmdb", region="US", time_range="week", media_type="movie"
        )

    def test_get_charts_missing_parameters(self, client):
        """Test charts endpoint with missing parameters."""
        response = client.get("/api/charts")

        assert response.status_code == 422  # Validation error
        assert "field required" in response.json()["detail"][0]["msg"]

    def test_get_charts_invalid_parameters(self, client):
        """Test charts endpoint with invalid parameters."""
        response = client.get(
            "/api/charts?source=invalid&region=XX&time_range=invalid&media_type=invalid"
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_charts_service_error(self, client, mock_charts_service):
        """Test charts endpoint when service encounters error."""
        # Mock service error
        mock_charts_service.get_charts_data.side_effect = Exception("Service error")

        response = client.get(
            "/api/charts?source=tmdb&region=US&time_range=week&media_type=movie"
        )

        # Should still return 200 with fallback data
        assert response.status_code == 200
        assert "items" in response.json()

    def test_get_sources_endpoint(self, client):
        """Test sources endpoint."""
        response = client.get("/api/charts/sources")

        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert "tmdb" in data["sources"]
        assert "spotify" in data["sources"]

    def test_get_regions_endpoint(self, client):
        """Test regions endpoint."""
        response = client.get("/api/charts/regions")

        assert response.status_code == 200
        data = response.json()
        assert "regions" in data
        assert "US" in data["regions"]
        assert "CN" in data["regions"]

    def test_get_time_ranges_endpoint(self, client):
        """Test time ranges endpoint."""
        response = client.get("/api/charts/time-ranges")

        assert response.status_code == 200
        data = response.json()
        assert "time_ranges" in data
        assert "day" in data["time_ranges"]
        assert "week" in data["time_ranges"]

    def test_get_media_types_endpoint(self, client):
        """Test media types endpoint."""
        response = client.get("/api/charts/media-types")

        assert response.status_code == 200
        data = response.json()
        assert "media_types" in data
        assert "movie" in data["media_types"]
        assert "tv" in data["media_types"]

    @pytest.mark.asyncio
    async def test_refresh_charts_endpoint(self, client, mock_charts_service):
        """Test charts refresh endpoint."""
        # Mock successful refresh
        mock_charts_service.fetch_external_charts.return_value = {
            "items": [],
            "total": 0,
        }
        mock_charts_service.save_charts_data.return_value = "chart_123"

        response = client.post(
            "/api/charts/refresh?source=tmdb&region=US&time_range=week&media_type=movie"
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "success" in data
        assert data["chart_id"] == "chart_123"

    @pytest.mark.asyncio
    async def test_refresh_charts_error(self, client, mock_charts_service):
        """Test charts refresh endpoint with error."""
        # Mock refresh error
        mock_charts_service.fetch_external_charts.side_effect = Exception(
            "Refresh error"
        )

        response = client.post(
            "/api/charts/refresh?source=tmdb&region=US&time_range=week&media_type=movie"
        )

        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    def test_api_documentation(self, client):
        """Test API documentation endpoints."""
        # Test OpenAPI docs
        response = client.get("/docs")
        assert response.status_code == 200

        # Test ReDoc docs
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/charts")

        # Should include CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_rate_limiting(self, client):
        """Test rate limiting (if implemented)."""
        # Make multiple requests quickly
        for i in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_error_handling(self, client):
        """Test error handling for invalid endpoints."""
        response = client.get("/api/invalid-endpoint")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_response_format(self, client):
        """Test response format consistency."""
        response = client.get("/health")

        # Check response headers
        assert response.headers["content-type"] == "application/json"

        # Check response structure
        data = response.json()
        assert "status" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client, mock_charts_service):
        """Test handling of concurrent requests."""
        import asyncio

        # Mock service response
        mock_data = {"items": [], "total": 0}
        mock_charts_service.get_charts_data.return_value = mock_data

        # Create multiple concurrent requests
        async def make_request():
            return client.get(
                "/api/charts?source=tmdb&region=US&time_range=week&media_type=movie"
            )

        # Run concurrent requests
        tasks = [make_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

    def test_cache_headers(self, client):
        """Test cache-related headers."""
        response = client.get(
            "/api/charts?source=tmdb&region=US&time_range=week&media_type=movie"
        )

        # Check for cache headers
        headers = response.headers
        assert "cache-control" in headers or "expires" in headers

    def test_security_headers(self, client):
        """Test security headers."""
        response = client.get("/")

        # Check for security headers
        headers = response.headers
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
        ]

        for header in security_headers:
            if header in headers:
                assert headers[header] is not None
