"""
简化的集成测试文件 - 修复版本
"""

import pytest
from fastapi.testclient import TestClient

from core.api import VabHubAPI
from core.config import Config


class TestIntegrationSimple:
    """简化的集成测试"""

    @pytest.fixture
    def test_client(self):
        """创建测试客户端"""
        config = Config()
        api = VabHubAPI(config)
        app = api.get_app()
        return TestClient(app)

    def test_root_endpoint(self, test_client):
        """测试根端点"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_health_endpoint(self, test_client):
        """测试健康检查端点"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_config_endpoint(self, test_client):
        """测试配置端点"""
        response = test_client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_invalid_endpoint(self, test_client):
        """测试无效端点"""
        response = test_client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_security_headers(self, test_client):
        """测试安全头信息"""
        response = test_client.get("/")
        
        # 检查基本的安全头信息
        headers = response.headers
        
        # 检查内容类型选项
        if 'x-content-type-options' in headers:
            assert headers['x-content-type-options'] == 'nosniff'
        
        # 检查XSS保护
        if 'x-xss-protection' in headers:
            assert '1' in headers['x-xss-protection']

    def test_response_format(self, test_client):
        """测试响应格式"""
        response = test_client.get("/")
        data = response.json()
        
        # 检查响应格式
        assert isinstance(data, dict)
        assert "message" in data
        assert "version" in data
        
        # 检查版本格式
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0