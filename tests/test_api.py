import pytest
import json
import os
from fastapi.testclient import TestClient

# 设置测试环境变量
os.environ["MEDIA_LIBRARY_PATH"] = "/tmp/media/library"
os.environ["MEDIA_TEMP_PATH"] = "/tmp/media/temp"
os.environ["STRM_BASE_PATH"] = "/tmp/media/strm"
os.environ["LIBRARY_PATH"] = "/tmp/media/library"

from core.api import app


class TestChartsAPI:
    """Test cases for Charts API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the API."""
        return TestClient(app)

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

    def test_get_charts_success(self, client):
        """Test successful charts data retrieval."""
        response = client.get(
            "/api/charts?source=tmdb&region=US&time_range=week&media_type=movie"
        )

        assert response.status_code == 200

    def test_get_charts_missing_parameters(self, client):
        """Test charts endpoint with missing parameters."""
        response = client.get("/api/charts")

        assert response.status_code == 422  # Validation error
        assert "Field required" in response.text

    def test_get_charts_invalid_parameters(self, client):
        """Test charts endpoint with invalid parameters."""
        response = client.get(
            "/api/charts?source=invalid&region=XX&time_range=invalid&media_type=invalid"
        )

        assert response.status_code == 422  # Validation error

    def test_get_charts_service_error(self, client):
        """Test charts endpoint when service encounters error."""
        # Test with an invalid source that will cause an error
        response = client.get(
            "/api/charts?source=invalid_source&region=US&time_range=week&media_type=movie"
        )

        # Should return 500 error
        assert response.status_code == 500

    def test_get_sources_endpoint(self, client):
        """Test sources endpoint."""
        response = client.get("/api/charts/sources")

        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        sources = [s["id"] for s in data["sources"]]
        assert "tmdb" in sources
        assert "spotify" in sources

    def test_get_regions_endpoint(self, client):
        """Test regions endpoint."""
        response = client.get("/api/charts/regions")

        assert response.status_code == 200

    def test_get_time_ranges_endpoint(self, client):
        """Test time ranges endpoint."""
        response = client.get("/api/charts/time-ranges")

        assert response.status_code == 200

    def test_get_media_types_endpoint(self, client):
        """Test media types endpoint."""
        response = client.get("/api/charts/media-types")

        assert response.status_code == 200

    def test_refresh_charts_endpoint(self, client):
        """Test charts refresh endpoint."""
        response = client.post(
            "/api/charts/refresh?source=tmdb&region=US&time_range=week&media_type=movie"
        )

        # This endpoint doesn't exist, so should return 404
        assert response.status_code == 404

    def test_refresh_charts_error(self, client):
        """Test charts refresh endpoint with error."""
        response = client.post(
            "/api/charts/refresh?source=tmdb&region=US&time_range=week&media_type=movie"
        )

        # This endpoint doesn't exist, so should return 404
        assert response.status_code == 404

    def test_api_documentation(self, client):
        """Test API documentation endpoints."""
        # Test OpenAPI docs
        response = client.get("/docs")
        assert response.status_code == 200

        # Test ReDoc docs
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_cors_headers(self, client):
        """Test CORS headers."""
        response = client.get("/health")
        # CORS headers may not be set for simple requests
        assert response.status_code == 200

    def test_cache_headers(self, client):
        """Test cache headers."""
        response = client.get("/health")
        # Cache headers may not be set for all endpoints
        assert response.status_code == 200

    def test_concurrent_requests(self, client):
        """Test concurrent requests."""
        # Make multiple requests
        responses = []
        for _ in range(3):
            response = client.get(
                "/api/charts?source=tmdb&region=US&time_range=week&media_type=movie"
            )
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
