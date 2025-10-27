#!/usr/bin/env python3
"""
Web接口测试
"""
import unittest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app


class TestWebInterface(unittest.TestCase):
    """Web接口测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.client = TestClient(app)
        
    def test_home_page(self):
        """测试主页访问"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
    def test_api_health(self):
        """测试健康检查接口"""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        
    def test_music_api(self):
        """测试音乐API接口"""
        response = self.client.get("/api/music/status")
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()