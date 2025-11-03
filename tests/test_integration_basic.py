"""
基础集成测试 - 测试核心功能
"""

import pytest
from fastapi.testclient import TestClient

from core.api import VabHubAPI
from core.config import Config


class TestIntegrationBasic:
    """基础集成测试"""

    @pytest.fixture
    def test_client(self):
        """创建测试客户端"""
        config = Config()
        api = VabHubAPI(config)
        app = api.get_app()
        return TestClient(app)

    def test_api_structure(self, test_client):
        """测试API结构"""
        # 测试主要API端点是否存在
        endpoints = [
            "/api/subscriptions",
            "/api/tasks", 
            "/api/scraper/config",
            "/api/library/servers",
            "/api/dl/instances",
            "/api/storage/status",
            "/api/strm/files"
        ]
        
        for endpoint in endpoints:
            response = test_client.get(endpoint)
            # 端点应该返回200或422（参数验证错误）
            assert response.status_code in [200, 422]

    def test_error_handling(self, test_client):
        """测试错误处理"""
        # 测试无效参数
        response = test_client.get("/api/charts?source=invalid&region=XX")
        assert response.status_code == 422
        
        # 测试缺少参数
        response = test_client.get("/api/charts")
        assert response.status_code == 422

    def test_health_check(self, test_client):
        """测试健康检查"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_version_info(self, test_client):
        """测试版本信息"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "message" in data

    def test_config_endpoint(self, test_client):
        """测试配置端点"""
        response = test_client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_404_handling(self, test_client):
        """测试404错误处理"""
        response = test_client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_cors_support(self, test_client):
        """测试CORS支持"""
        response = test_client.options("/")
        # CORS预检请求应该成功
        assert response.status_code == 200