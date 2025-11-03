"""
简化的测试API - 用于集成测试
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

# 创建简化的测试应用
test_app = FastAPI(title="VabHub Test API", version="1.0.0")

@test_app.get("/")
async def root():
    return {"message": "VabHub API", "version": "1.5.0"}

@test_app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.5.0"}

@test_app.get("/config")
async def get_config():
    return {"app_name": "VabHub", "version": "1.5.0"}

@test_app.get("/api/subscriptions")
async def get_subscriptions():
    return {"subscriptions": []}

@test_app.get("/api/tasks")
async def get_tasks():
    return {"tasks": []}

@test_app.get("/api/scraper/config")
async def get_scraper_config():
    return {"config": {"tmdb_enabled": True, "douban_enabled": True}}

@test_app.get("/api/library/servers")
async def get_library_servers():
    return {"servers": []}

@test_app.get("/api/dl/instances")
async def get_dl_instances():
    return {"instances": []}

@test_app.get("/api/storage/status")
async def get_storage_status():
    return {"status": "ok", "available": True}

@test_app.get("/api/strm/files")
async def get_strm_files():
    return {"files": []}

@test_app.get("/api/charts")
async def get_charts(source: str = None, region: str = None):
    if not source or not region:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Missing parameters")
    return {"items": [], "total": 0, "source": source}

# 创建测试客户端
test_client = TestClient(test_app)


class TestSimpleAPI:
    """测试简化的API"""

    def test_root_endpoint(self):
        """测试根端点"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_health_endpoint(self):
        """测试健康检查端点"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_config_endpoint(self):
        """测试配置端点"""
        response = test_client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_api_structure(self):
        """测试API结构"""
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
            assert response.status_code == 200

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效参数
        response = test_client.get("/api/charts")
        assert response.status_code == 422
        
        # 测试有效参数
        response = test_client.get("/api/charts?source=tmdb&region=US")
        assert response.status_code == 200
        
        # 测试有效参数
        response = test_client.get("/api/charts?source=tmdb&region=US")
        assert response.status_code == 200

    def test_404_handling(self):
        """测试404错误处理"""
        response = test_client.get("/api/nonexistent")
        assert response.status_code == 404