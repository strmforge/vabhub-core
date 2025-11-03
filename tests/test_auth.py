import pytest
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from core.api_auth import create_jwt_token, verify_jwt_token, verify_api_key
from core.auth import AuthManager


class TestAuthManager:
    def test_create_token(self):
        """测试JWT Token创建"""
        auth_manager = AuthManager("test-secret-key")
        token = auth_manager.create_token("test-user-id")

        assert token is not None
        assert isinstance(token, str)

        # 验证Token可以正确解码
        payload = auth_manager.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "test-user-id"

    def test_verify_token_valid(self):
        """测试有效的Token验证"""
        auth_manager = AuthManager("test-secret-key")
        token = auth_manager.create_token("test-user-id")

        payload = auth_manager.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "test-user-id"

    def test_verify_token_invalid(self):
        """测试无效的Token验证"""
        auth_manager = AuthManager("test-secret-key")

        # 使用错误的密钥
        invalid_auth_manager = AuthManager("wrong-secret-key")
        token = invalid_auth_manager.create_token("test-user-id")

        payload = auth_manager.verify_token(token)
        assert payload is None

    def test_get_user_id_from_token(self):
        """测试从Token中提取用户ID"""
        auth_manager = AuthManager("test-secret-key")
        token = auth_manager.create_token("test-user-id")

        user_id = auth_manager.get_user_id_from_token(token)
        assert user_id == "test-user-id"


class TestAPIAuth:
    def test_create_jwt_token(self):
        """测试API认证模块的Token创建"""
        token = create_jwt_token("test-user-id")

        assert token is not None
        assert isinstance(token, str)

        # 验证Token可以正确解码
        payload = verify_jwt_token(token)
        assert payload is not None
        assert payload["sub"] == "test-user-id"

    def test_verify_jwt_token_valid(self):
        """测试有效的JWT Token验证"""
        token = create_jwt_token("test-user-id")

        payload = verify_jwt_token(token)
        assert payload is not None
        assert payload["sub"] == "test-user-id"

    def test_verify_jwt_token_expired(self):
        """测试过期的Token验证"""
        # 创建过期的Token
        import core.api_auth

        original_expire = core.api_auth.JWT_EXPIRE_HOURS
        core.api_auth.JWT_EXPIRE_HOURS = -1  # 设置为过期

        token = create_jwt_token("test-user-id")

        # 恢复设置
        core.api_auth.JWT_EXPIRE_HOURS = original_expire

        payload = verify_jwt_token(token)
        assert payload is None

    def test_verify_api_key_valid(self):
        """测试有效的API Key验证"""
        valid_api_key = "vabhub_valid_api_key_123"
        assert verify_api_key(valid_api_key) is True

    def test_verify_api_key_invalid(self):
        """测试无效的API Key验证"""
        invalid_api_key = "invalid_api_key"
        assert verify_api_key(invalid_api_key) is False

        # 空值测试
        assert verify_api_key("") is False
        assert verify_api_key(None) is False


class TestAuthEndpoints:
    def setup_method(self):
        """测试设置"""
        from core.api import APIServer

        self.api_server = APIServer()
        self.client = TestClient(self.api_server.app)

    def test_login_endpoint_missing_credentials(self):
        """测试登录端点缺少凭据"""
        response = self.client.post("/auth/login", json={})
        assert response.status_code == 422  # 验证错误

    def test_login_endpoint_invalid_credentials(self):
        """测试登录端点无效凭据"""
        response = self.client.post(
            "/auth/login", json={"username": "invalid", "password": "invalid"}
        )
        assert response.status_code == 401

    def test_protected_endpoint_without_token(self):
        """测试未提供Token访问受保护端点"""
        response = self.client.get("/auth/me")
        assert response.status_code == 403  # 未认证

    def test_api_key_endpoint_without_key(self):
        """测试未提供API Key访问端点"""
        response = self.client.get("/auth/apikey-test")
        assert response.status_code == 401  # 未认证

    def test_refresh_token_without_auth(self):
        """测试未认证时刷新Token"""
        response = self.client.post("/auth/refresh")
        assert response.status_code == 403  # 未认证


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
